"""Production-grade integrated test: pipelined discovery + v4 validation.

Goal: measure ACTUAL sustained throughput + conversion rate over 10+ minutes,
NOT a tiny sample.

Architecture:
  Queries (curated + combinatorial) → discovery workers (video-owners)
                                    → channel_id queue (deduped)
                                    → validation workers (extract_v4)
                                    → results

Both stages run concurrently — discovery feeds the queue while validators drain it.

Configuration:
  - 10 discovery workers
  - 100 validation workers (v4: 1.36 stages/ch on average, ~22 ch/s ceiling)

Metrics tracked:
  - Eligible/sec sustained
  - Conversion rate (eligible / validated)
  - Total API calls
  - Errors / blocks over time
  - ETA projection for 700K target
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

import extract_v3  # noqa: F401 — Monkey Patch
from discovery_compare import discover_via_video_owners
from extract_v4 import extract as extract_v4_fn, is_brazil


# ----- curated query bank -------------------------------------------------

CURATED_CORE = [
    # Sports / very BR
    "futebol brasil", "vôlei brasil", "flamengo", "corinthians", "neymar",
    # BR-specific genres
    "sertanejo música", "funk carioca", "pagode", "forró", "axé music",
    # Food / heavy BR signal
    "receitas brasileiras", "churrasco brasileiro", "brigadeiro", "feijoada",
    # Lifestyle
    "vlog brasileiro", "humor brasileiro", "stand up comedy brasil",
    # News / BR-explicit
    "notícias brasil", "jornal brasil", "política brasileira",
    # Tutorials / how-to
    "tutorial maquiagem", "review celular brasil", "tecnologia brasil",
    # Religion / mainstream BR
    "gospel brasil", "igreja brasil",
    # Entertainment
    "podcast brasil", "youtuber brasileiro", "live brasil",
    # Education
    "aula português", "concurso público", "vestibular",
    # Beauty
    "skincare brasil", "cabelo cacheado", "maquiagem brasileira",
    # Travel
    "viagem brasil", "nordeste brasileiro", "amazônia",
    # Kids / family
    "crianças brasil", "maternidade brasileira",
    # Other niches
    "pets brasil", "carros brasil", "moto brasil",
    "tarot brasileiro", "horóscopo signos",
    # Gaming
    "free fire brasil", "minecraft brasil", "gameplay br",
]

# Suffix-based combinatorial expansion (gentle — pt-BR strong signals only)
PT_INTENTS = ["canal", "oficial", "shorts", "live", "podcast"]
PT_REGIONS = ["brasil", "brasileiro", "brasileira", "br"]


def build_query_bank() -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    def add(q: str):
        q = q.strip().lower()
        if 2 <= len(q.split()) <= 5 and q not in seen:
            seen.add(q); out.append(q)
    # Core queries first
    for q in CURATED_CORE: add(q)
    # Cross-add core × intent + core × region
    for core in CURATED_CORE:
        for s in PT_INTENTS:
            if s not in core: add(f"{core} {s}")
        for s in PT_REGIONS:
            if s not in core: add(f"{core} {s}")
    random.seed(0xB7A21)
    random.shuffle(out)
    return out


# ----- pipeline orchestration --------------------------------------------

@dataclass
class Counters:
    discovered: int = 0
    validated: int = 0
    errors: int = 0
    short_circuited: int = 0
    target: int = 0          # is_target == True (BR + langdetect-recovered)
    eligible: int = 0        # is_target AND subs >= 1000
    big: int = 0             # eligible AND subs >= 10_000
    huge: int = 0            # eligible AND subs >= 1_000_000
    lang_recovered: int = 0
    api_calls: int = 0
    started_at: float = field(default_factory=time.time)


async def run_pipeline(
    queries: List[str],
    discovery_workers: int = 10,
    validation_workers: int = 100,
    max_seconds: float = 600.0,
    status_every: float = 30.0,
    queue_max: int = 5000,
):
    counters = Counters()
    seen_channels: Set[str] = set()
    seen_lock = asyncio.Lock()
    ch_queue: asyncio.Queue = asyncio.Queue(maxsize=queue_max)
    query_idx = 0
    query_lock = asyncio.Lock()
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    disc_pool = ThreadPoolExecutor(max_workers=discovery_workers, thread_name_prefix="disc")
    val_pool = ThreadPoolExecutor(max_workers=validation_workers, thread_name_prefix="val")

    # ------- discovery worker -------
    async def discoverer(worker_id: int):
        nonlocal query_idx
        while not stop_event.is_set():
            async with query_lock:
                if query_idx >= len(queries):
                    return
                q = queries[query_idx]; query_idx += 1
            try:
                ids, _meta = await loop.run_in_executor(
                    disc_pool, discover_via_video_owners, q, 30
                )
            except Exception:
                continue
            async with seen_lock:
                new_ids = [c for c in ids if c not in seen_channels]
                for c in new_ids: seen_channels.add(c)
            counters.discovered += len(new_ids)
            for cid in new_ids:
                if stop_event.is_set(): return
                await ch_queue.put(cid)

    # ------- validation worker -------
    async def validator(worker_id: int):
        while not stop_event.is_set():
            try:
                cid = await asyncio.wait_for(ch_queue.get(), timeout=3.0)
            except asyncio.TimeoutError:
                # If discovery is done and queue is empty, exit.
                if query_idx >= len(queries) and ch_queue.empty():
                    return
                continue
            try:
                info = await loop.run_in_executor(val_pool, extract_v4_fn, None, cid)
            except Exception:
                counters.errors += 1
                ch_queue.task_done()
                continue
            counters.validated += 1
            counters.api_calls += info.stages_called
            if info.error:
                counters.errors += 1
            elif info.short_circuited:
                counters.short_circuited += 1
            else:
                if info.is_target:
                    counters.target += 1
                    if info.target_reason == "country=None,lang=pt":
                        counters.lang_recovered += 1
                    if (info.subscribers or 0) >= 1000:
                        counters.eligible += 1
                    if (info.subscribers or 0) >= 10_000:
                        counters.big += 1
                    if (info.subscribers or 0) >= 1_000_000:
                        counters.huge += 1
            ch_queue.task_done()

    # ------- monitor / timer -------
    async def monitor():
        last_validated = 0
        last_eligible = 0
        last_t = time.time()
        while not stop_event.is_set():
            await asyncio.sleep(status_every)
            now = time.time()
            elapsed = now - counters.started_at
            recent_s = now - last_t
            dv = counters.validated - last_validated
            de = counters.eligible - last_eligible
            print(
                f"[{elapsed:6.0f}s]  "
                f"disc={counters.discovered:>6d}  val={counters.validated:>6d}  "
                f"eligible={counters.eligible:>5d} (+{de})  "
                f"target={counters.target:>5d}  lang_rec={counters.lang_recovered:>4d}  "
                f"short_circuit={counters.short_circuited:>5d}  errors={counters.errors:>4d}  "
                f"q={ch_queue.qsize():>4d}  "
                f"val_rate={dv/max(0.001,recent_s):5.2f}/s  el_rate={de/max(0.001,recent_s):5.2f}/s",
                flush=True,
            )
            last_validated = counters.validated
            last_eligible = counters.eligible
            last_t = now
            if elapsed >= max_seconds:
                print(f"\n[stop] max_seconds={max_seconds} reached", flush=True)
                stop_event.set()
                return

    print(f"queries available: {len(queries)}; disc_workers={discovery_workers}; val_workers={validation_workers}; max_seconds={max_seconds}")
    print(f"starting pipeline...\n")

    disc_tasks = [asyncio.create_task(discoverer(i)) for i in range(discovery_workers)]
    val_tasks = [asyncio.create_task(validator(i)) for i in range(validation_workers)]
    mon_task = asyncio.create_task(monitor())

    try:
        # Wait until either: time elapsed OR (discovery exhausted + queue drained)
        while not stop_event.is_set():
            await asyncio.sleep(2)
            if all(t.done() for t in disc_tasks) and ch_queue.empty():
                # Give validators a moment to finish in-flight
                await asyncio.sleep(2)
                if ch_queue.empty():
                    print("\n[stop] all queries done + queue drained", flush=True)
                    stop_event.set()
                    break
            if time.time() - counters.started_at >= max_seconds:
                stop_event.set()
                break
    finally:
        mon_task.cancel()
        # cancel remaining tasks
        for t in disc_tasks + val_tasks:
            t.cancel()
        await asyncio.gather(*disc_tasks, *val_tasks, return_exceptions=True)
        await asyncio.gather(mon_task, return_exceptions=True)
        disc_pool.shutdown(wait=False)
        val_pool.shutdown(wait=False)

    return counters


def print_summary(c: Counters):
    elapsed = time.time() - c.started_at
    print("\n" + "=" * 70)
    print("PRODUCTION-RUN SUMMARY")
    print("=" * 70)
    print(f"  elapsed:           {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"  discovered:        {c.discovered}")
    print(f"  validated:         {c.validated}")
    print(f"    short-circuited: {c.short_circuited}  (subs<1k, skipped stage 2)")
    print(f"    errors:          {c.errors}")
    print(f"    target (full):   {c.target}")
    print(f"      lang-recovered:{c.lang_recovered}")
    print(f"    eligible (≥1k):  {c.eligible}")
    print(f"    big (≥10k):      {c.big}")
    print(f"    huge (≥1M):      {c.huge}")
    print(f"  api_calls:         {c.api_calls}  (avg {c.api_calls/max(1,c.validated):.2f}/channel)")
    print(f"  validation rate:   {c.validated/max(0.001,elapsed):.2f} ch/s")
    print(f"  eligible rate:     {c.eligible/max(0.001,elapsed):.2f} ch/s")
    print(f"  conversion rate:   {c.eligible/max(1,c.validated)*100:.1f}%")

    # ETA projection for 700K target
    if c.eligible > 0:
        eligibles_per_sec = c.eligible / elapsed
        eta_700k_s = 700_000 / eligibles_per_sec
        print(f"\n  ETA for 700K at this sustained rate: {eta_700k_s/3600:.1f} hours")
        # Best/worst bracket
        # Assume sustained rate ± 20% variance
        print(f"  Best-case  (rate +20%): {eta_700k_s/3600/1.2:.1f} hours")
        print(f"  Worst-case (rate -20%): {eta_700k_s/3600*1.25:.1f} hours")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=10.0)
    ap.add_argument("--disc-workers", type=int, default=10)
    ap.add_argument("--val-workers", type=int, default=100)
    ap.add_argument("--status-every", type=float, default=30.0)
    args = ap.parse_args()

    queries = build_query_bank()
    counters = await run_pipeline(
        queries=queries,
        discovery_workers=args.disc_workers,
        validation_workers=args.val_workers,
        max_seconds=args.minutes * 60,
        status_every=args.status_every,
    )
    print_summary(counters)


if __name__ == "__main__":
    asyncio.run(main())

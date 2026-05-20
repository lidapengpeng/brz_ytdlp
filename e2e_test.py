"""End-to-end test: curated keywords → video-owners discovery → v4 extraction.

Measures actual stacked conversion rate vs the predicted 72.6%.
"""
from __future__ import annotations

import asyncio
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Set, Tuple

import extract_v3  # noqa: F401 — applies Monkey Patch
from discovery_compare import discover_via_video_owners
from extract_v4 import extract as extract_v4_fn


# Curated queries: high-BR-signal, diverse verticals
QUERIES = [
    # Sports / very BR
    "futebol brasil",
    "vôlei brasil",
    "flamengo",
    # Music / BR-specific genres
    "sertanejo música",
    "funk carioca",
    "pagode",
    # Food / heavily BR
    "receitas brasileiras",
    "churrasco brasileiro",
    # Lifestyle
    "vlog brasileiro",
    "humor brasileiro",
    # News / explicit BR
    "notícias brasil",
    "jornal brasil",
    # Tech / lifestyle
    "tutorial maquiagem",
    "review celular brasil",
    "tecnologia brasil",
    # Religion / BR-mainstream
    "gospel brasil",
    # Entertainment
    "podcast brasil",
    "youtuber brasileiro",
    # Tutorials / DIY
    "aula português",
    "concurso público",
]


async def main():
    print(f"E2E test: {len(QUERIES)} curated queries × video-owners discovery × v4 extraction\n")

    # ---- Discovery: video-owners on each query ----
    all_ids: List[str] = []
    seen: Set[str] = set()
    src_per_id = {}  # provenance
    t0 = time.time()
    for q in QUERIES:
        ids, meta = discover_via_video_owners(q, limit=25)
        for cid in ids:
            if cid not in seen:
                seen.add(cid)
                src_per_id[cid] = q
                all_ids.append(cid)
    discovery_s = time.time() - t0
    print(f"discovery: {len(all_ids)} unique channels in {discovery_s:.1f}s "
          f"({len(QUERIES)} queries, avg {len(all_ids)/len(QUERIES):.1f} ch/query)\n")

    # ---- Validation via v4 ----
    concurrency = 30
    pool = ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="v4")
    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(concurrency)

    results = []
    last_status = time.time()
    status_lock = asyncio.Lock()
    done = 0

    async def one(cid):
        nonlocal done, last_status
        async with sem:
            info = await loop.run_in_executor(pool, extract_v4_fn, None, cid)
        async with status_lock:
            done += 1
            results.append(info)
            if done % 50 == 0:
                now = time.time()
                recent = now - last_status
                print(f"  [{done}/{len(all_ids)}] rate(recent)={50/recent:.1f}/s", flush=True)
                last_status = now

    t0 = time.time()
    await asyncio.gather(*[one(c) for c in all_ids])
    validation_s = time.time() - t0
    pool.shutdown(wait=True)

    # ---- Tallies ----
    n = len(results)
    errors = sum(1 for r in results if r.error)
    short_circuited = sum(1 for r in results if r.short_circuited)
    targets = [r for r in results if r.is_target]
    eligible = [r for r in targets if (r.subscribers or 0) >= 1000]
    lang_recovered = [r for r in targets if r.target_reason == "country=None,lang=pt"]
    big_eligible = [r for r in targets if (r.subscribers or 0) >= 10_000]
    huge_eligible = [r for r in targets if (r.subscribers or 0) >= 1_000_000]
    api_calls = sum(r.stages_called for r in results)

    print()
    print("=" * 70)
    print("E2E RESULT")
    print("=" * 70)
    print(f"  unique discovered:        {n}")
    print(f"  errors:                   {errors}")
    print(f"  short-circuited (subs<1k):{short_circuited}")
    print(f"  target (BR or lang=pt):   {len(targets)}")
    print(f"    of which lang-recovered:{len(lang_recovered)}")
    print(f"  eligible (target, ≥1k):   {len(eligible)}")
    print(f"  eligible+big (≥10k):      {len(big_eligible)}")
    print(f"  eligible+huge (≥1M):      {len(huge_eligible)}")
    print()
    print(f"  conversion rate:          {len(eligible) / max(1, n) * 100:.1f}%")
    print(f"  big-channel rate:         {len(big_eligible) / max(1, n) * 100:.1f}%")
    print(f"  api calls total:          {api_calls} (avg {api_calls/max(1,n):.2f}/ch)")
    print(f"  discovery time:           {discovery_s:.1f}s ({len(QUERIES)/discovery_s:.1f} queries/s)")
    print(f"  validation time:          {validation_s:.1f}s ({n/validation_s:.1f} channels/s)")

    # ---- ETA for 700K based on this sample's stats ----
    conv = len(eligible) / max(1, n)
    val_rate = n / validation_s
    calls_per_ch = api_calls / max(1, n)
    # If we use this conv rate + this val rate for 700K target
    if conv > 0:
        channels_needed = 700_000 / conv
        # Discovery cost: 25 ch/query, 1.5 query/s → 37.5 ch/s discovery
        # But realistically discovery may slow with many queries; estimate proportionally
        discovery_rate = len(all_ids) / discovery_s
        disc_eta = channels_needed / max(0.001, discovery_rate)
        val_eta = channels_needed / val_rate
        total_eta_s = max(disc_eta, val_eta)  # they can pipeline in parallel
        print(f"\n  ETA for 700K target:")
        print(f"    need to discover+validate {channels_needed:,.0f} channels")
        print(f"    discovery alone: {disc_eta/3600:.1f}h")
        print(f"    validation alone: {val_eta/3600:.1f}h")
        print(f"    pipelined parallel: ~{total_eta_s/3600:.1f}h")


if __name__ == "__main__":
    asyncio.run(main())

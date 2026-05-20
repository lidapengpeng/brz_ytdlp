"""Endurance test for the two-stage InnerTube approach.

Goal: pull real channel IDs from brazil700k's pending_channels table and run
them through the optimised extractor at sustained pace, measuring:
   - rate over time (does it degrade?)
   - first 429 / block (if any) — when?
   - eligible-rate (% returning country='Brasil'/'Brazil')
   - throughput at varying concurrency levels

Run modes:
   --sequential N      run N channels one-at-a-time, observe trend
   --parallel N C      run N channels with C concurrent workers
   --cookies-from-chrome  use Chrome login cookies (slower per-call but
                        reportedly ~4x rate-limit budget)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yt_dlp

from extract_v2 import (
    ChannelInfo,
    ExtractorConfig,
    extract,
    harvest_visitor_data,
    make_ydl,
)


BRAZIL_DB = Path(__file__).resolve().parent.parent / "brazil700k" / "channels.db"


def load_real_channel_ids(n: int) -> List[str]:
    """Sample N channel IDs from brazil700k's pending_channels (the real keyword-search results)."""
    if not BRAZIL_DB.exists():
        sys.exit(f"can't find {BRAZIL_DB}; need it to source real channel IDs")
    conn = sqlite3.connect(BRAZIL_DB)
    try:
        rows = conn.execute(
            "SELECT channel_id FROM pending_channels ORDER BY RANDOM() LIMIT ?", (n,)
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


# ----- sequential mode -----

def run_sequential(channel_ids: List[str], cfg: ExtractorConfig, status_every: int = 10):
    ydl = make_ydl(cfg)
    if cfg.fixed_visitor_data is None:
        vd = harvest_visitor_data(ydl)
        if vd:
            print(f"harvested visitor_data: {vd[:32]}...", flush=True)
            cfg.fixed_visitor_data = vd
            ydl = make_ydl(cfg)

    print(f"\n[seq] running {len(channel_ids)} channels sequentially with cfg={cfg.label}", flush=True)
    start = time.time()
    results: List[ChannelInfo] = []
    last_status = time.time()
    eligible = errors = blocks = 0
    for i, cid in enumerate(channel_ids, 1):
        t0 = time.time()
        info = extract(ydl, cid)
        results.append(info)
        if info.error:
            errors += 1
            if "429" in info.error or "Too Many" in info.error or "403" in info.error:
                blocks += 1
        elif info.country in ("Brasil", "Brazil") and (info.subscribers or 0) >= 1000:
            eligible += 1
        if i % status_every == 0 or i == len(channel_ids):
            now = time.time()
            elapsed = now - start
            recent_s = now - last_status
            print(f"  [{i:>4d}/{len(channel_ids)}]  elapsed={elapsed:6.1f}s  "
                  f"eligible={eligible:>4d}  errors={errors:>3d}  blocks={blocks:>3d}  "
                  f"rate(total)={i/elapsed:5.2f}/s  rate(last)={status_every/recent_s:5.2f}/s",
                  flush=True)
            last_status = now
    # Summary
    elapsed = time.time() - start
    ok = [r for r in results if not r.error]
    print(f"\n[seq summary] total={len(channel_ids)} ok={len(ok)} errors={errors} blocks={blocks}"
          f" eligible={eligible} elapsed={elapsed:.1f}s rate={len(ok)/elapsed:.2f}/s", flush=True)
    return results


# ----- parallel mode -----

async def run_parallel(channel_ids: List[str], cfg: ExtractorConfig, concurrency: int,
                       status_every: int = 10):
    """Use a thread pool: yt-dlp is synchronous, so we wrap calls with run_in_executor."""
    ydl = make_ydl(cfg)
    if cfg.fixed_visitor_data is None:
        vd = harvest_visitor_data(ydl)
        if vd:
            print(f"harvested visitor_data: {vd[:32]}...", flush=True)
            cfg.fixed_visitor_data = vd
            ydl = make_ydl(cfg)

    pool = ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="extract")
    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(concurrency)

    print(f"\n[par] running {len(channel_ids)} channels with concurrency={concurrency} cfg={cfg.label}", flush=True)
    start = time.time()
    eligible = errors = blocks = done = 0
    results: List[ChannelInfo] = []
    last_status = time.time()
    status_lock = asyncio.Lock()

    async def one(cid: str):
        nonlocal eligible, errors, blocks, done, last_status
        async with sem:
            info = await loop.run_in_executor(pool, extract, ydl, cid)
        async with status_lock:
            done += 1
            results.append(info)
            if info.error:
                errors += 1
                if "429" in info.error or "Too Many" in info.error or "403" in info.error:
                    blocks += 1
            elif info.country in ("Brasil", "Brazil") and (info.subscribers or 0) >= 1000:
                eligible += 1
            if done % status_every == 0 or done == len(channel_ids):
                now = time.time()
                elapsed = now - start
                recent = now - last_status
                print(f"  [{done:>4d}/{len(channel_ids)}]  elapsed={elapsed:6.1f}s  "
                      f"eligible={eligible:>4d}  errors={errors:>3d}  blocks={blocks:>3d}  "
                      f"rate={done/elapsed:5.2f}/s  recent={status_every/recent:5.2f}/s",
                      flush=True)
                last_status = now

    await asyncio.gather(*[one(c) for c in channel_ids])
    pool.shutdown(wait=True)
    elapsed = time.time() - start
    ok = [r for r in results if not r.error]
    print(f"\n[par summary] total={len(channel_ids)} ok={len(ok)} errors={errors} blocks={blocks}"
          f" eligible={eligible} elapsed={elapsed:.1f}s rate={len(ok)/elapsed:.2f}/s", flush=True)
    return results


# ----- CLI -----

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200, help="number of channels to test")
    ap.add_argument("--concurrency", type=int, default=1, help="parallel workers (1 = sequential)")
    ap.add_argument("--cookies-from-chrome", action="store_true")
    ap.add_argument("--status-every", type=int, default=10)
    ap.add_argument("--sleep", type=float, default=0.0, help="seconds to sleep between calls")
    args = ap.parse_args()

    channels = load_real_channel_ids(args.n)
    print(f"loaded {len(channels)} real channel IDs from {BRAZIL_DB}")

    cfg = ExtractorConfig(
        label=f"endurance c={args.concurrency} cookies={args.cookies_from_chrome}",
        use_cookies_from_chrome=args.cookies_from_chrome,
        skip_webpage=True,
        sleep_between_calls=args.sleep,
    )

    if args.concurrency <= 1:
        run_sequential(channels, cfg, args.status_every)
    else:
        asyncio.run(run_parallel(channels, cfg, args.concurrency, args.status_every))


if __name__ == "__main__":
    main()

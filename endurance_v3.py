"""Endurance test for extract_v3 (PDF mitigations applied).

The decisive question: do per-request visitor_data + gl=BR + Brazil XFF push
the safe-concurrency ceiling above v2's 10 workers?

v2 baseline at 20 workers: 20% block rate.
If v3 stays at ~0%, PDF's "shared visitor_data triggers Bot detection" is right.
"""
from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

from extract_v3 import ChannelInfo, ExtractorConfigV3, extract, is_brazil

BRAZIL_DB = Path(__file__).resolve().parent.parent / "brazil700k" / "channels.db"


def load_real_channel_ids(n: int) -> List[str]:
    if not BRAZIL_DB.exists():
        sys.exit(f"can't find {BRAZIL_DB}")
    conn = sqlite3.connect(BRAZIL_DB)
    try:
        rows = conn.execute(
            "SELECT channel_id FROM pending_channels ORDER BY RANDOM() LIMIT ?", (n,)
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


async def run(channels: List[str], concurrency: int, status_every: int = 25):
    cfg = ExtractorConfigV3()
    pool = ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="v3")
    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(concurrency)

    print(f"[v3] running {len(channels)} channels @ concurrency={concurrency}", flush=True)
    start = time.time()
    eligible = errors = blocks = done = 0
    results: List[ChannelInfo] = []
    last_status = time.time()
    status_lock = asyncio.Lock()

    async def one(cid: str):
        nonlocal eligible, errors, blocks, done, last_status
        async with sem:
            info = await loop.run_in_executor(pool, extract, None, cid)
        async with status_lock:
            done += 1
            results.append(info)
            if info.error:
                errors += 1
                if "429" in info.error or "Too Many" in info.error or "403" in info.error:
                    blocks += 1
            elif is_brazil(info.country) and (info.subscribers or 0) >= 1000:
                eligible += 1
            if done % status_every == 0 or done == len(channels):
                now = time.time()
                elapsed = now - start
                recent = now - last_status
                print(f"  [{done:>4d}/{len(channels)}]  elapsed={elapsed:6.1f}s  "
                      f"eligible={eligible:>4d}  errors={errors:>3d}  blocks={blocks:>3d}  "
                      f"rate={done/elapsed:5.2f}/s  recent={status_every/recent:5.2f}/s",
                      flush=True)
                last_status = now

    await asyncio.gather(*[one(c) for c in channels])
    pool.shutdown(wait=True)
    elapsed = time.time() - start
    ok = [r for r in results if not r.error]
    print(f"\n[v3 summary] total={len(channels)} ok={len(ok)} errors={errors} "
          f"blocks={blocks} eligible={eligible} elapsed={elapsed:.1f}s "
          f"rate={len(ok)/elapsed:.2f}/s", flush=True)
    # Sample a few error reasons for diagnosis
    err_kinds = {}
    for r in results:
        if r.error:
            key = r.error.split(":")[0]
            err_kinds[key] = err_kinds.get(key, 0) + 1
    if err_kinds:
        print(f"[v3 error breakdown] {err_kinds}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--concurrency", type=int, default=20)
    ap.add_argument("--status-every", type=int, default=25)
    args = ap.parse_args()

    channels = load_real_channel_ids(args.n)
    print(f"loaded {len(channels)} channels from {BRAZIL_DB}\n")
    asyncio.run(run(channels, args.concurrency, args.status_every))


if __name__ == "__main__":
    main()

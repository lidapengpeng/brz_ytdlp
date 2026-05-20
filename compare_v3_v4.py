"""Apples-to-apples comparison: v3 vs v4 on a real sample of pending channels.

Measures:
  - Eligible conversion rate (target / total)
  - API calls per channel (v4 short-circuits low-sub channels at stage 1)
  - Wall time
  - How many were recovered by langdetect (only v4)

Uses the same channel_ids for both, so the only variable is the extractor.
"""
from __future__ import annotations

import asyncio
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

# IMPORTANT: import v3 first so its Monkey Patch lands; v4 inherits the same patch
import extract_v3  # noqa: F401 — for the monkey patch side-effect
import extract_v4

from extract_v3 import extract as extract_v3_fn, is_brazil as is_brazil_v3
from extract_v4 import extract as extract_v4_fn

BRAZIL_DB = Path(__file__).resolve().parent.parent / "brazil700k" / "channels.db"


def load_channel_ids(n: int) -> List[str]:
    conn = sqlite3.connect(BRAZIL_DB)
    try:
        rows = conn.execute(
            "SELECT channel_id FROM pending_channels ORDER BY RANDOM() LIMIT ?", (n,)
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


async def run_v3(channels: List[str], concurrency: int = 20):
    pool = ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="v3")
    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(concurrency)
    results = []
    async def one(cid):
        async with sem:
            r = await loop.run_in_executor(pool, extract_v3_fn, None, cid)
        results.append(r)
    t0 = time.time()
    await asyncio.gather(*[one(c) for c in channels])
    elapsed = time.time() - t0
    pool.shutdown(wait=True)
    return results, elapsed


async def run_v4(channels: List[str], concurrency: int = 20):
    pool = ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="v4")
    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(concurrency)
    results = []
    async def one(cid):
        async with sem:
            r = await loop.run_in_executor(pool, extract_v4_fn, None, cid)
        results.append(r)
    t0 = time.time()
    await asyncio.gather(*[one(c) for c in channels])
    elapsed = time.time() - t0
    pool.shutdown(wait=True)
    return results, elapsed


def summarize_v3(results, elapsed):
    n = len(results)
    ok = [r for r in results if not r.error]
    brazil = [r for r in ok if is_brazil_v3(r.country)]
    eligible = [r for r in brazil if (r.subscribers or 0) >= 1000]
    # v3 always makes 2 API calls (always stage 1 + stage 2)
    api_calls = 2 * n
    return {
        "version": "v3",
        "total": n,
        "ok": len(ok),
        "brazil_country": len(brazil),
        "eligible_target": len(eligible),
        "conv_rate_target": round(len(eligible) / max(1, n) * 100, 1),
        "api_calls_total": api_calls,
        "api_calls_per_ch": round(api_calls / max(1, n), 2),
        "elapsed_s": round(elapsed, 1),
        "ch_per_s": round(n / max(0.001, elapsed), 2),
        "lang_recovered": 0,
    }


def summarize_v4(results, elapsed):
    n = len(results)
    ok = [r for r in results if not r.error]
    short_circuited = sum(1 for r in results if r.short_circuited)
    targets = [r for r in ok if r.is_target]
    eligible = [r for r in targets if (r.subscribers or 0) >= 1000]
    lang_recovered = [r for r in targets if r.target_reason == "country=None,lang=pt"]
    api_calls = sum(r.stages_called for r in results)
    return {
        "version": "v4",
        "total": n,
        "ok": len(ok),
        "short_circuited": short_circuited,
        "brazil_country": sum(1 for r in ok if r.country in ("Brasil", "Brazil")),
        "target_total": len(targets),
        "lang_recovered": len(lang_recovered),
        "eligible_target": len(eligible),
        "conv_rate_target": round(len(eligible) / max(1, n) * 100, 1),
        "api_calls_total": api_calls,
        "api_calls_per_ch": round(api_calls / max(1, n), 2),
        "elapsed_s": round(elapsed, 1),
        "ch_per_s": round(n / max(0.001, elapsed), 2),
    }


async def main():
    n = 200
    print(f"loading {n} random channels from pending_channels...")
    channels = load_channel_ids(n)
    print(f"loaded {len(channels)}\n")

    print("=== running v3 ===")
    res_v3, t_v3 = await run_v3(channels, concurrency=20)
    s_v3 = summarize_v3(res_v3, t_v3)
    print(f"  done in {t_v3:.1f}s")

    print("\n=== running v4 ===")
    res_v4, t_v4 = await run_v4(channels, concurrency=20)
    s_v4 = summarize_v4(res_v4, t_v4)
    print(f"  done in {t_v4:.1f}s")

    print("\n" + "=" * 78)
    print(f"{'metric':38s} {'v3':>18s} {'v4':>18s}")
    print("=" * 78)
    keys = [
        ("total", "total", ""),
        ("ok", "ok", ""),
        ("short_circuited (sub<1000)", "short_circuited", ""),
        ("brazil_country (definitive)", "brazil_country", ""),
        ("eligible_target (>=1000 + BR)", "eligible_target", ""),
        ("lang_recovered (PDF plan B)", "lang_recovered", ""),
        ("conv_rate_target", "conv_rate_target", "%"),
        ("api_calls_total", "api_calls_total", ""),
        ("api_calls_per_ch (avg)", "api_calls_per_ch", ""),
        ("elapsed_s", "elapsed_s", ""),
        ("channels/sec", "ch_per_s", ""),
    ]
    for label, key, suffix in keys:
        v3_val = s_v3.get(key, "—")
        v4_val = s_v4.get(key, "—")
        print(f"{label:38s} {v3_val!s:>17s}{suffix:1s} {v4_val!s:>17s}{suffix:1s}")

    print()
    delta_conv = s_v4["conv_rate_target"] - s_v3["conv_rate_target"]
    api_saved_pct = (1 - s_v4["api_calls_total"] / max(1, s_v3["api_calls_total"])) * 100
    print(f"v4 vs v3: conv_rate {delta_conv:+.1f}pp, API calls -{api_saved_pct:.0f}%")

    # Show some langdetect-recovered channels for inspection
    if s_v4.get("lang_recovered", 0) > 0:
        recovered = [r for r in res_v4 if r.is_target and r.target_reason == "country=None,lang=pt"]
        print(f"\nLang-detect recovered samples ({min(len(recovered), 5)}):")
        for r in recovered[:5]:
            desc = (r.description or "")[:80]
            print(f"  {r.channel_id}  subs={r.subscribers!s:>9s}  desc={desc!r}")


if __name__ == "__main__":
    asyncio.run(main())

"""Re-verify ALL channels with target_reason='country=None,lang=pt' using the
new strict rule:
  - description only (no name fallback)
  - description length >= 30 chars
  - BOTH langdetect AND langid must agree on 'pt'

For channels that:
  - now report country=Brasil/Brazil → keep (upgrade target_reason)
  - have description that passes strict pt detection → keep
  - otherwise → DELETE from results.db (false positive lang_recovered)

Country-confirmed channels (PASS_BR in earlier audit, 0% failure rate) are
NOT touched. This script only deals with the lang_recovered cohort.
"""
from __future__ import annotations

import asyncio
import sqlite3
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import extract_v3  # noqa — monkey patch
from extract_v4 import extract as extract_v4_fn, detect_pt, is_brazil

DB_PATH = Path(__file__).resolve().parent / "results.db"
WORKERS = 15


def collect_lang_recovered():
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT channel_id, subscribers, name FROM channels "
            "WHERE target_reason = 'country=None,lang=pt'"
        ).fetchall()
        return rows
    finally:
        conn.close()


def reverify_one(row):
    cid, db_subs, db_name = row
    try:
        info = extract_v4_fn(None, cid)
    except Exception as e:
        return {"cid": cid, "verdict": "FETCH_ERROR", "note": f"{type(e).__name__}:{str(e)[:60]}"}
    if info.error:
        return {"cid": cid, "verdict": "FETCH_ERROR", "note": info.error[:80]}

    # Subs check
    if info.subscribers is None or info.subscribers < 1000:
        return {"cid": cid, "verdict": "DELETE_SUBS", "note": f"live_subs={info.subscribers}"}

    # New country?
    if is_brazil(info.country):
        return {"cid": cid, "verdict": "UPGRADE_BR",
                "note": f"country={info.country} subs={info.subscribers}",
                "country": info.country, "subs": info.subscribers}

    # Still no country — check description with NEW strict detect_pt
    desc = (info.description or "").strip()
    if desc and detect_pt(desc):
        return {"cid": cid, "verdict": "KEEP_LANG",
                "note": f"desc {len(desc)}ch passes strict pt",
                "subs": info.subscribers}

    # Failed strict
    if not desc:
        reason = "no_desc"
    elif len(desc) < 30:
        reason = f"desc_too_short_{len(desc)}ch"
    else:
        reason = "lang_disagree"
    return {"cid": cid, "verdict": "DELETE_LANG", "note": reason,
            "desc_preview": desc[:60]}


async def main():
    print(f"loading lang_recovered cohort from {DB_PATH}...")
    rows = collect_lang_recovered()
    print(f"  {len(rows)} channels to re-verify\n")

    pool = ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="clean")
    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(WORKERS)

    counters = Counter()
    results = []
    done = 0
    start = time.time()
    lock = asyncio.Lock()

    async def one(row):
        nonlocal done
        async with sem:
            r = await loop.run_in_executor(pool, reverify_one, row)
        async with lock:
            done += 1
            counters[r["verdict"]] += 1
            results.append(r)
            if done % 100 == 0 or done == len(rows):
                elapsed = time.time() - start
                rate = done / max(0.001, elapsed)
                eta = (len(rows) - done) / max(0.001, rate)
                print(f"  [{done:>5d}/{len(rows)}]  elapsed={elapsed:>5.0f}s  "
                      f"rate={rate:>4.1f}/s  eta={eta:>4.0f}s  "
                      f"keep_lang={counters['KEEP_LANG']:>4d}  "
                      f"upgrade_BR={counters['UPGRADE_BR']:>4d}  "
                      f"delete_lang={counters['DELETE_LANG']:>4d}  "
                      f"delete_subs={counters['DELETE_SUBS']:>3d}  "
                      f"err={counters['FETCH_ERROR']:>3d}",
                      flush=True)

    await asyncio.gather(*[one(r) for r in rows])
    pool.shutdown(wait=True)

    # ----- apply changes to DB -----
    print("\nApplying changes to results.db...")
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        for r in results:
            if r["verdict"] == "UPGRADE_BR":
                cur.execute(
                    "UPDATE channels SET target_reason='country=Brazil', country=?, subscribers=? "
                    "WHERE channel_id=?",
                    (r.get("country"), r.get("subs"), r["cid"]))
            elif r["verdict"] in ("DELETE_LANG", "DELETE_SUBS"):
                cur.execute("DELETE FROM channels WHERE channel_id=?", (r["cid"],))
            # KEEP_LANG / FETCH_ERROR → leave as-is
        conn.commit()
        print(f"  committed {cur.rowcount} final ops (sqlite reports last cursor)")
    finally:
        conn.close()

    # ----- final summary -----
    print("\n" + "="*78)
    print("CLEANUP COMPLETE")
    print("="*78)
    print(f"  Lang-recovered cohort:        {len(rows)}")
    print(f"  ✓ KEEP_LANG (strict pt pass): {counters['KEEP_LANG']}")
    print(f"  ↑ UPGRADE_BR (country re-appeared): {counters['UPGRADE_BR']}")
    print(f"  ✗ DELETE_LANG (strict pt fail):  {counters['DELETE_LANG']}")
    print(f"  ✗ DELETE_SUBS (subs dropped):    {counters['DELETE_SUBS']}")
    print(f"  ⚠ FETCH_ERROR (kept, untouched): {counters['FETCH_ERROR']}")
    print()
    # Final DB state
    conn = sqlite3.connect(DB_PATH)
    try:
        for label, sql in [
            ("total kept in channels", "SELECT COUNT(*) FROM channels"),
            ("eligible (target+>=1k)", "SELECT COUNT(*) FROM channels WHERE is_target=1 AND subscribers>=1000"),
            ("country=Brasil/Brazil", "SELECT COUNT(*) FROM channels WHERE country IN ('Brasil','Brazil')"),
            ("lang_recovered remaining", "SELECT COUNT(*) FROM channels WHERE target_reason='country=None,lang=pt'"),
        ]:
            n = conn.execute(sql).fetchone()[0]
            print(f"  {label:35s} = {n}")
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())

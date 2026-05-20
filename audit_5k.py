"""5000-channel independent audit.

Samples 5000 random rows from results.db where is_target=1 AND subscribers>=1000.
For each, makes a fresh InnerTube call (extract_v4) and re-verifies:
  - subscribers still >= 1000 (allow live drift)
  - country is Brasil/Brazil  OR  country=None AND langdetect(description)=='pt'

Buckets:
  PASS_BR      — country confirmed Brasil/Brazil
  PASS_LANG    — country=None but langdetect says pt (PDF Plan B recovery)
  FAIL_SUBS    — live subs < 1000 (channel shrunk or DB had wrong value)
  FAIL_COUNTRY — country is non-Brasil now (or DB had wrong country)
  FAIL_LANG    — country=None and langdetect != pt (PDF Plan B false positive)
  FETCH_ERROR  — couldn't reach the channel (transient, separate from quality)

Results persist to audit_5k.db so we can pick up after interrupt.
"""
from __future__ import annotations

import asyncio
import sqlite3
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import extract_v3  # noqa — monkey patch side-effect
from extract_v4 import extract as extract_v4_fn, detect_pt, is_brazil

ROOT = Path(__file__).resolve().parent
SRC_DB = ROOT / "results.db"
AUDIT_DB = ROOT / "audit_5k.db"

SAMPLE_SIZE = 5000
WORKERS = 15           # conservative; protects IP burst budget


def sample_channels():
    conn = sqlite3.connect(SRC_DB)
    try:
        rows = conn.execute("""
            SELECT channel_id, name, subscribers, country, target_reason
            FROM channels
            WHERE is_target=1 AND subscribers >= 1000
            ORDER BY RANDOM()
            LIMIT ?
        """, (SAMPLE_SIZE,)).fetchall()
        return rows
    finally:
        conn.close()


def init_audit_db():
    conn = sqlite3.connect(AUDIT_DB)
    conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS audit (
            channel_id TEXT PRIMARY KEY,
            verdict TEXT,
            db_subs INTEGER,
            db_country TEXT,
            db_target_reason TEXT,
            live_subs INTEGER,
            live_country TEXT,
            live_desc TEXT,
            note TEXT,
            audited_at INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_verdict ON audit(verdict);
    """)
    conn.commit()
    return conn


def already_audited(conn) -> set:
    return {r[0] for r in conn.execute("SELECT channel_id FROM audit")}


def verify_one(row):
    """Returns dict with verdict + diagnostic fields."""
    cid, db_name, db_subs, db_country, db_reason = row
    try:
        info = extract_v4_fn(None, cid)
    except Exception as e:
        return {"channel_id": cid, "verdict": "FETCH_ERROR",
                "db_subs": db_subs, "db_country": db_country, "db_target_reason": db_reason,
                "live_subs": None, "live_country": None, "live_desc": None,
                "note": f"exception:{type(e).__name__}:{str(e)[:80]}"}
    if info.error:
        return {"channel_id": cid, "verdict": "FETCH_ERROR",
                "db_subs": db_subs, "db_country": db_country, "db_target_reason": db_reason,
                "live_subs": info.subscribers, "live_country": info.country, "live_desc": None,
                "note": f"err:{info.error[:80]}"}

    live_subs = info.subscribers
    live_country = info.country
    live_desc = (info.description or "")[:200] if info.description else None

    # 1) Subs check
    if live_subs is None:
        verdict = "FETCH_ERROR"
        note = "live subs is None (extractor couldn't parse)"
    elif live_subs < 1000:
        verdict = "FAIL_SUBS"
        note = f"live_subs={live_subs} < 1000"
    else:
        # 2) Country / lang check
        if is_brazil(live_country):
            verdict = "PASS_BR"
            note = f"country={live_country}"
        elif live_country is None:
            desc = (info.description or "").strip()
            if desc and detect_pt(desc):
                verdict = "PASS_LANG"
                note = f"country=None lang=pt"
            else:
                verdict = "FAIL_LANG"
                note = f"country=None lang!=pt desc={desc[:60]!r}"
        else:
            verdict = "FAIL_COUNTRY"
            note = f"live_country={live_country!r}"

    return {"channel_id": cid, "verdict": verdict,
            "db_subs": db_subs, "db_country": db_country, "db_target_reason": db_reason,
            "live_subs": live_subs, "live_country": live_country, "live_desc": live_desc,
            "note": note}


async def main():
    print(f"[init] sampling {SAMPLE_SIZE} channels from {SRC_DB}", flush=True)
    sample = sample_channels()
    print(f"[init] got {len(sample)} rows", flush=True)

    audit_conn = init_audit_db()
    audit_lock = asyncio.Lock()

    # resume: skip already-audited
    seen = already_audited(audit_conn)
    todo = [r for r in sample if r[0] not in seen]
    if seen:
        print(f"[init] resume — already audited {len(seen)}, still {len(todo)} to do", flush=True)

    pool = ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="audit")
    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(WORKERS)

    counters = Counter()
    # seed counters from already-audited
    for v in audit_conn.execute("SELECT verdict, COUNT(*) FROM audit GROUP BY verdict"):
        counters[v[0]] = v[1]

    done = len(seen)
    start = time.time()

    async def one(row):
        nonlocal done
        async with sem:
            r = await loop.run_in_executor(pool, verify_one, row)
        async with audit_lock:
            done += 1
            counters[r["verdict"]] += 1
            audit_conn.execute(
                """INSERT OR REPLACE INTO audit
                   (channel_id, verdict, db_subs, db_country, db_target_reason,
                    live_subs, live_country, live_desc, note, audited_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (r["channel_id"], r["verdict"], r["db_subs"], r["db_country"],
                 r["db_target_reason"], r["live_subs"], r["live_country"], r["live_desc"],
                 r["note"], int(time.time())))
            audit_conn.commit()
            if done % 100 == 0 or done == len(sample):
                elapsed = time.time() - start
                rate = (done - len(seen)) / max(0.001, elapsed)
                eta = max(0, (len(sample) - done)) / max(0.001, rate)
                pass_n = counters["PASS_BR"] + counters["PASS_LANG"]
                tot = sum(counters.values())
                err = counters["FETCH_ERROR"]
                evaluated = tot - err
                tpr = (pass_n / max(1, evaluated)) * 100
                print(f"  [{done:>5d}/{len(sample)}]  elapsed={elapsed:>5.0f}s  "
                      f"rate={rate:>4.1f}/s  eta={eta:>5.0f}s  "
                      f"PASS_BR={counters['PASS_BR']:>4d}  "
                      f"PASS_LANG={counters['PASS_LANG']:>4d}  "
                      f"FAIL_SUBS={counters['FAIL_SUBS']:>3d}  "
                      f"FAIL_CTRY={counters['FAIL_COUNTRY']:>3d}  "
                      f"FAIL_LANG={counters['FAIL_LANG']:>3d}  "
                      f"ERR={err:>3d}  "
                      f"TPR={tpr:>5.1f}%",
                      flush=True)

    await asyncio.gather(*[one(r) for r in todo])
    pool.shutdown(wait=True)

    # Final summary
    print("\n" + "="*78)
    print("AUDIT COMPLETE")
    print("="*78)
    elapsed = time.time() - start
    pass_total = counters["PASS_BR"] + counters["PASS_LANG"]
    fail_total = counters["FAIL_SUBS"] + counters["FAIL_COUNTRY"] + counters["FAIL_LANG"]
    err_total = counters["FETCH_ERROR"]
    evaluated = pass_total + fail_total
    print(f"  Total sampled:           {len(sample)}")
    print(f"  Elapsed:                 {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"")
    print(f"  ✓ PASS_BR   (country=Brasil/Brazil):     {counters['PASS_BR']:>5d}")
    print(f"  ✓ PASS_LANG (country=None + lang=pt):    {counters['PASS_LANG']:>5d}")
    print(f"  {'─'*55}")
    print(f"  ✓ TOTAL PASS:                            {pass_total:>5d}")
    print(f"")
    print(f"  ✗ FAIL_SUBS    (live subs < 1000):       {counters['FAIL_SUBS']:>5d}")
    print(f"  ✗ FAIL_COUNTRY (country not Brasil):     {counters['FAIL_COUNTRY']:>5d}")
    print(f"  ✗ FAIL_LANG    (country=None + not pt):  {counters['FAIL_LANG']:>5d}")
    print(f"  {'─'*55}")
    print(f"  ✗ TOTAL FAIL:                            {fail_total:>5d}")
    print(f"")
    print(f"  ⚠ FETCH_ERROR  (couldn't verify):        {err_total:>5d}")
    print(f"")
    if evaluated > 0:
        tpr = pass_total / evaluated * 100
        print(f"  TRUE POSITIVE RATE (of those evaluated): {tpr:.2f}%")
    print(f"\n  details: {AUDIT_DB}")
    audit_conn.close()


if __name__ == "__main__":
    asyncio.run(main())

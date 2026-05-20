"""bfs_experiment.py — Measure real BFS yield on 20 random BR seeds.

For each seed:
  1. Call discover_via_bfs (existing /channels tab strategy)
  2. Count returned cids
  3. Compute overlap with DB (channels + rejected_channel_ids)
  4. Optionally validate spot-check 10 to confirm BR ratio

Outputs JSON + per-seed details.
"""
import json
import random
import sqlite3
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

DB = Path(__file__).parent / "results.db"

# Read DB known IDs first
def load_known(db_path):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    known = set()
    for (cid,) in conn.execute("SELECT channel_id FROM channels"):
        known.add(cid)
    eligible_count = len(known)
    for (cid,) in conn.execute("SELECT channel_id FROM rejected_channel_ids"):
        known.add(cid)
    conn.close()
    return known, eligible_count


def pick_seeds(db_path, n=20, min_subs=10000, max_subs=1_000_000):
    """Random sample of mid-size BR seeds (10K-1M)."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.execute(
        """SELECT channel_id, name, subscribers, country
           FROM channels
           WHERE is_target=1 AND subscribers >= ? AND subscribers <= ?
             AND country IN ('Brazil','Brasil')
           ORDER BY RANDOM() LIMIT ?""",
        (min_subs, max_subs, n)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def pick_lang_recovered_seeds(db_path, n=10):
    """Random sample from lang_recovered=pt cohort."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.execute(
        """SELECT channel_id, name, subscribers, country
           FROM channels
           WHERE target_reason='country=None,lang=pt' AND subscribers >= 5000
           ORDER BY RANDOM() LIMIT ?""",
        (n,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def pick_huge_seeds(db_path, n=10):
    """Sample of very large BR seeds (>=1M)."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.execute(
        """SELECT channel_id, name, subscribers, country
           FROM channels
           WHERE is_target=1 AND subscribers >= 1000000 AND country IN ('Brazil','Brasil')
           ORDER BY RANDOM() LIMIT ?""",
        (n,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def main():
    sys.path.insert(0, str(Path(__file__).parent))
    from discovery_compare import discover_via_bfs

    known, eligible_count = load_known(DB)
    print(f"[setup] {eligible_count} eligible + {len(known)-eligible_count} rejected = {len(known)} known IDs")

    # Three cohorts
    mid_seeds = pick_seeds(DB, n=20)
    lang_seeds = pick_lang_recovered_seeds(DB, n=10)
    huge_seeds = pick_huge_seeds(DB, n=10)

    print(f"[setup] mid (10K-1M): {len(mid_seeds)} | lang_rec: {len(lang_seeds)} | huge (>=1M): {len(huge_seeds)}")

    def run_one(row, cohort):
        cid, name, subs, country = row
        t0 = time.time()
        try:
            ids, meta = discover_via_bfs(cid, limit=100)
        except Exception as e:
            return {"cohort": cohort, "seed_cid": cid, "name": name, "subs": subs,
                    "error": f"{type(e).__name__}: {e}", "elapsed": time.time()-t0}
        new_ids = [c for c in ids if c not in known]
        return {
            "cohort": cohort,
            "seed_cid": cid,
            "name": name,
            "subs": subs,
            "country": country,
            "n_returned": len(ids),
            "n_new": len(new_ids),
            "overlap_pct": round(100 * (1 - len(new_ids)/max(1,len(ids))), 1),
            "new_sample": new_ids[:5],
            "elapsed_s": round(meta["elapsed_s"], 2),
            "resp_bytes": meta["response_bytes"],
        }

    results = []

    # Run mid cohort sequentially-ish (use small pool to avoid hammering YouTube)
    print("\n=== MID cohort (10K-1M BR) ===")
    with ThreadPoolExecutor(max_workers=4) as pool:
        for r in pool.map(lambda x: run_one(x, "mid"), mid_seeds):
            print(f"  {r.get('seed_cid','?')}  {r.get('name','?')[:30]:30s}  "
                  f"subs={r.get('subs','?'):>9}  ret={r.get('n_returned',0):>3}  "
                  f"new={r.get('n_new',0):>3}  overlap={r.get('overlap_pct','?'):>5}%  "
                  f"{r.get('elapsed_s',0)}s")
            results.append(r)

    print("\n=== LANG_RECOVERED cohort (country=None, lang=pt) ===")
    with ThreadPoolExecutor(max_workers=4) as pool:
        for r in pool.map(lambda x: run_one(x, "lang_rec"), lang_seeds):
            print(f"  {r.get('seed_cid','?')}  {r.get('name','?')[:30]:30s}  "
                  f"subs={r.get('subs','?'):>9}  ret={r.get('n_returned',0):>3}  "
                  f"new={r.get('n_new',0):>3}  overlap={r.get('overlap_pct','?'):>5}%  "
                  f"{r.get('elapsed_s',0)}s")
            results.append(r)

    print("\n=== HUGE cohort (>=1M BR) ===")
    with ThreadPoolExecutor(max_workers=4) as pool:
        for r in pool.map(lambda x: run_one(x, "huge"), huge_seeds):
            print(f"  {r.get('seed_cid','?')}  {r.get('name','?')[:30]:30s}  "
                  f"subs={r.get('subs','?'):>9}  ret={r.get('n_returned',0):>3}  "
                  f"new={r.get('n_new',0):>3}  overlap={r.get('overlap_pct','?'):>5}%  "
                  f"{r.get('elapsed_s',0)}s")
            results.append(r)

    # Aggregate
    def cohort_stats(label, cohort):
        rows = [r for r in results if r.get("cohort")==cohort and "n_returned" in r]
        if not rows:
            return None
        n = len(rows)
        avg_ret = sum(r["n_returned"] for r in rows) / n
        avg_new = sum(r["n_new"] for r in rows) / n
        avg_overlap = sum(r["overlap_pct"] for r in rows) / n
        avg_elapsed = sum(r["elapsed_s"] for r in rows) / n
        return {
            "label": label, "n_seeds": n,
            "avg_returned": round(avg_ret, 1),
            "avg_new": round(avg_new, 1),
            "avg_overlap_pct": round(avg_overlap, 1),
            "avg_elapsed_s": round(avg_elapsed, 2),
            "yield_new_per_call": round(avg_new, 1),
        }

    print("\n" + "="*80)
    print("AGGREGATE STATISTICS")
    print("="*80)
    for lbl, ck in [("mid 10K-1M BR", "mid"), ("lang_recovered pt", "lang_rec"), ("huge >=1M BR", "huge")]:
        st = cohort_stats(lbl, ck)
        if st:
            print(json.dumps(st, indent=2))

    # Save raw results
    out_path = Path(__file__).parent / "bfs_experiment_results.json"
    with open(out_path, "w") as f:
        json.dump({
            "timestamp": int(time.time()),
            "total_known_ids": len(known),
            "results": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\n[saved] {out_path}")

    # Collect all new IDs for further validation (BR spot-check)
    all_new = set()
    for r in results:
        for cid in r.get("new_sample", []):
            all_new.add(cid)
    print(f"[new IDs to spot-check] {len(all_new)}")
    return results, all_new


if __name__ == "__main__":
    main()

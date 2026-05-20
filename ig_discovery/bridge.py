"""
bridge.py — feed yt_candidates from ig.db into results.db so the main
production pipeline (`production_v2.py`) processes them.

Mechanism:
    - yt_candidates with URL pattern /channel/UC... → channel_id is trivial
    - yt_candidates with URL pattern /@handle      → handle, channel_id resolution
      is deferred (Phase 0 next: lookup handle via /resolve_url InnerTube)
    - For each new UC cid not already in results.db channels OR bfs_visited:
        INSERT INTO bfs_visited (seed_cid, visited_at, strategy='ig_bridge', n_yielded=NULL)
      This makes the seed_loader pick it up like any other bfs seed.

After bridging, mark yt_candidates.bridged_at = now.

Run:
    ./.venv/bin/python -m ig_discovery.bridge [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DB = REPO_ROOT / "results.db"
IG_DB = REPO_ROOT / "data" / "ig.db"

# Pattern: https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxx
_CID_RE = re.compile(r"youtube\.com/channel/(UC[A-Za-z0-9_-]{22})", re.IGNORECASE)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--source",
        default=None,
        help="restrict to candidates from specific source (e.g. 'linktree')",
    )
    args = p.parse_args()

    if not RESULTS_DB.exists():
        sys.exit(f"results.db not found at {RESULTS_DB}")
    if not IG_DB.exists():
        sys.exit(f"ig.db not found at {IG_DB}")

    ig_conn = sqlite3.connect(IG_DB, timeout=30)
    ig_conn.execute("PRAGMA busy_timeout = 30000")
    ig_conn.row_factory = sqlite3.Row

    res_conn = sqlite3.connect(RESULTS_DB, timeout=60)
    res_conn.execute("PRAGMA busy_timeout = 60000")

    # Known cids from results.db (channels + bfs_visited)
    print("[bridge] loading known cids from results.db...")
    known_cids: set[str] = set()
    for (cid,) in res_conn.execute("SELECT channel_id FROM channels"):
        known_cids.add(cid)
    for (cid,) in res_conn.execute("SELECT seed_cid FROM bfs_visited"):
        known_cids.add(cid)
    print(f"[bridge] known cids in results.db: {len(known_cids):,}")

    # Pull unbridged yt_candidates with /channel/UC URLs
    where = ["bridged_at IS NULL"]
    params: list = []
    if args.source:
        where.append("source = ?")
        params.append(args.source)
    sql = (
        "SELECT yt_url, source, source_url FROM yt_candidates "
        "WHERE " + " AND ".join(where)
    )
    rows = list(ig_conn.execute(sql, params))
    print(f"[bridge] unbridged candidates: {len(rows):,}")

    n_uc_extracted = 0
    n_new_seeds = 0
    n_already_known = 0
    n_handle_only = 0
    now = int(time.time())

    # 1) Group by extracted cid (some yt_candidates may produce no cid, e.g. /@handle)
    to_insert: list[tuple[str, int, str, str, str]] = []  # (cid, ts, strategy, source, source_url)
    yt_url_to_cid: dict[str, str] = {}  # yt_url -> cid for marking bridged_at later
    rows_processed = []

    for r in rows:
        yt_url = r["yt_url"]
        m = _CID_RE.search(yt_url)
        if not m:
            n_handle_only += 1
            # still mark bridged_at = now with channel_id=NULL so we don't re-process
            rows_processed.append(yt_url)
            continue
        cid = m.group(1)
        n_uc_extracted += 1
        yt_url_to_cid[yt_url] = cid
        rows_processed.append(yt_url)
        if cid in known_cids:
            n_already_known += 1
            continue
        # New seed!
        to_insert.append(
            (cid, now, "ig_bridge", r["source"], r["source_url"] or "")
        )
        known_cids.add(cid)  # avoid duplicate inserts within this run
        n_new_seeds += 1

    print(f"[bridge] yt_url → UC cid extracted:     {n_uc_extracted:,}")
    print(f"[bridge] cids already in results.db:    {n_already_known:,}")
    print(f"[bridge] NEW seeds for production_v2:   {n_new_seeds:,}")
    print(f"[bridge] handle-only (deferred):        {n_handle_only:,}")

    if args.dry_run:
        print("[bridge] dry-run: no changes written.")
        return

    if to_insert:
        # bfs_visited schema: (seed_cid, visited_at, n_yielded, n_new, strategy)
        # We insert with n_yielded=NULL so seed_loader picks them up.
        print(f"[bridge] inserting {len(to_insert)} new seeds into bfs_visited...")
        res_conn.executemany(
            "INSERT OR IGNORE INTO bfs_visited (seed_cid, visited_at, n_yielded, n_new, strategy) "
            "VALUES (?, ?, NULL, NULL, ?)",
            [(cid, ts, strat) for (cid, ts, strat, _src, _surl) in to_insert],
        )
        res_conn.commit()

    if rows_processed:
        ig_conn.execute("BEGIN")
        for yt_url in rows_processed:
            cid = yt_url_to_cid.get(yt_url)
            if cid:
                ig_conn.execute(
                    "UPDATE yt_candidates SET bridged_at = ?, channel_id = ? WHERE yt_url = ?",
                    (now, cid, yt_url),
                )
            else:
                ig_conn.execute(
                    "UPDATE yt_candidates SET bridged_at = ? WHERE yt_url = ?",
                    (now, yt_url),
                )
        ig_conn.commit()

    # Mark in_results_db = 1 for any candidate whose cid is now known
    if not args.dry_run:
        ig_conn.execute(
            "UPDATE yt_candidates SET in_results_db = 1 "
            "WHERE channel_id IS NOT NULL AND channel_id IN ("
            + ",".join("?" * len(known_cids - {x[0] for x in to_insert}))
            + ")"
        ) if False else None  # too many params; do alternative below
        # Alternative: use temp table
        ig_conn.execute("CREATE TEMP TABLE IF NOT EXISTS _known_cids (cid TEXT PRIMARY KEY)")
        ig_conn.execute("DELETE FROM _known_cids")
        ig_conn.executemany("INSERT OR IGNORE INTO _known_cids VALUES (?)", [(c,) for c in known_cids])
        ig_conn.execute(
            "UPDATE yt_candidates SET in_results_db = 1 "
            "WHERE channel_id IN (SELECT cid FROM _known_cids) "
            "  AND in_results_db = 0"
        )
        ig_conn.commit()

    # Final summary
    cur = ig_conn.execute("SELECT * FROM v_phase0_summary")
    cols = [d[0] for d in cur.description]
    print()
    print("=" * 60)
    print("FINAL ig.db SNAPSHOT")
    print("=" * 60)
    vals = cur.fetchone()
    if vals:
        for c, v in zip(cols, vals):
            print(f"  {c:<26} = {v}")

    print()
    print("results.db bfs_visited counts:")
    for (strat, n) in res_conn.execute(
        "SELECT strategy, COUNT(*) FROM bfs_visited "
        "GROUP BY strategy ORDER BY 2 DESC"
    ):
        print(f"  {strat:<24} {n:,}")

    ig_conn.close()
    res_conn.close()


if __name__ == "__main__":
    main()

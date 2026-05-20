"""
phase0_ingest.py — populate ig.db with aggregator URLs already present in
results.db channel descriptions.

This is Phase 0.2 of the Instagram-driven discovery plan
(see long_term_research/09_instagram_discovery.md §9.3).

Run once (idempotent — uses INSERT OR IGNORE):

    ./.venv/bin/python -m ig_discovery.phase0_ingest

It performs:
    1. Read all eligible BR channels (is_target=1) from results.db
    2. For each description, extract aggregator URLs + IG handles + YT URLs
    3. INSERT OR IGNORE into ig.db:
        - aggregators       (Linktree / Beacons / ...)
        - ig_users          (handles seen, no scrape yet)
        - yt_candidates     (any external YT URL already known)

After this, run phase0_fetch.py to actually GET each Linktree page and
harvest more YouTube URLs.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

# Make the package importable when this script is run directly (not -m)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ig_discovery.bio_extractor import (  # noqa: E402  pylint: disable=wrong-import-position
    extract_aggregators,
    extract_instagram,
    extract_youtube,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DB = REPO_ROOT / "results.db"
IG_DB = REPO_ROOT / "data" / "ig.db"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="cap rows scanned from results.db (0 = no limit)",
    )
    parser.add_argument(
        "--min-subs",
        type=int,
        default=0,
        help="only scan channels with >=N subs (0 = no filter)",
    )
    parser.add_argument(
        "--include-rejected",
        action="store_true",
        help="also scan rejected channels (not just is_target=1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print stats but don't write to ig.db",
    )
    args = parser.parse_args()

    if not RESULTS_DB.exists():
        sys.exit(f"results.db not found at {RESULTS_DB}")
    if not IG_DB.exists():
        sys.exit(
            f"ig.db not found at {IG_DB} — initialize it first:\n"
            f"  sqlite3 {IG_DB} < {REPO_ROOT}/ig_discovery/schema.sql"
        )

    now = int(time.time())
    src = sqlite3.connect(RESULTS_DB)
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(IG_DB)

    # Build the query
    where = ["description IS NOT NULL", "description != ''"]
    params: list = []
    if not args.include_rejected:
        where.append("is_target = 1")
    if args.min_subs > 0:
        where.append("subscribers >= ?")
        params.append(args.min_subs)
    where_sql = " AND ".join(where)
    limit_sql = f" LIMIT {args.limit}" if args.limit > 0 else ""

    sql = (
        f"SELECT channel_id, name, subscribers, description "
        f"FROM channels WHERE {where_sql} ORDER BY subscribers DESC{limit_sql}"
    )
    print(f"[query] {sql}  params={params}")

    rows = list(src.execute(sql, params))
    print(f"[scan]  {len(rows):,} candidate channels with non-empty description")

    n_agg_inserted = 0
    n_ig_inserted = 0
    n_yt_inserted = 0
    n_channels_with_agg = 0
    n_channels_with_ig = 0
    n_channels_with_yt = 0
    n_scanned = 0
    by_host: dict[str, int] = {}

    for r in rows:
        n_scanned += 1
        cid = r["channel_id"]
        desc = r["description"] or ""

        aggs = extract_aggregators(desc)
        igs = extract_instagram(desc)
        yts = extract_youtube(desc)

        if aggs:
            n_channels_with_agg += 1
        if igs:
            n_channels_with_ig += 1
        if yts:
            n_channels_with_yt += 1

        if args.dry_run:
            continue

        # Aggregators
        for agg in aggs:
            host = agg.split("/")[2].lower()  # https://host/slug → host
            by_host[host] = by_host.get(host, 0) + 1
            cur = dst.execute(
                "INSERT OR IGNORE INTO aggregators "
                "  (agg_url, host, source, source_ref, discovered_at) "
                "VALUES (?, ?, 'yt_about', ?, ?)",
                (agg, host, cid, now),
            )
            n_agg_inserted += cur.rowcount

        # IG handles
        for h in igs:
            cur = dst.execute(
                "INSERT OR IGNORE INTO ig_users "
                "  (ig_handle, discovered_via, source_ref, discovered_at) "
                "VALUES (?, 'yt_about', ?, ?)",
                (h.lower(), cid, now),
            )
            n_ig_inserted += cur.rowcount

        # YT candidates (already-known channels are still inserted so we can
        # later mark in_results_db=1 in bulk)
        for yt in yts:
            cur = dst.execute(
                "INSERT OR IGNORE INTO yt_candidates "
                "  (yt_url, source, source_url, discovered_at) "
                "VALUES (?, 'yt_about', ?, ?)",
                (yt, f"https://www.youtube.com/channel/{cid}", now),
            )
            n_yt_inserted += cur.rowcount

        if n_scanned % 20_000 == 0:
            print(
                f"[progress] scanned={n_scanned:,}  "
                f"with_agg={n_channels_with_agg:,}  "
                f"with_ig={n_channels_with_ig:,}  "
                f"with_yt={n_channels_with_yt:,}"
            )

    if not args.dry_run:
        dst.commit()

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"channels scanned:                  {n_scanned:,}")
    print(f"  with >=1 aggregator URL:         {n_channels_with_agg:,}  ({100*n_channels_with_agg/max(n_scanned,1):.2f}%)")
    print(f"  with >=1 IG handle:              {n_channels_with_ig:,}  ({100*n_channels_with_ig/max(n_scanned,1):.2f}%)")
    print(f"  with >=1 external YT URL:        {n_channels_with_yt:,}  ({100*n_channels_with_yt/max(n_scanned,1):.2f}%)")
    print()
    print(f"NEW rows inserted into ig.db:")
    print(f"  aggregators:                     {n_agg_inserted:,}")
    print(f"  ig_users:                        {n_ig_inserted:,}")
    print(f"  yt_candidates:                   {n_yt_inserted:,}")
    print()
    print("Aggregator host breakdown:")
    for host, n in sorted(by_host.items(), key=lambda kv: -kv[1]):
        print(f"  {host:<24} {n:>6,}")

    # Mark known yt_candidates as in_results_db=1
    if not args.dry_run:
        print()
        print("[bridge] marking already-known YT candidates...")
        # extract channel_id from yt_url and check against channels(channel_id)
        # we only do this for /channel/UC... URLs (the others need extract_v4 to resolve)
        dst.execute("DROP TABLE IF EXISTS _tmp_known_cids")
        dst.execute("CREATE TEMP TABLE _tmp_known_cids (cid TEXT PRIMARY KEY)")
        known_cids = [(row[0],) for row in src.execute("SELECT channel_id FROM channels")]
        dst.executemany("INSERT OR IGNORE INTO _tmp_known_cids VALUES (?)", known_cids)
        cur = dst.execute(
            "UPDATE yt_candidates "
            "SET in_results_db = 1 "
            "WHERE channel_id IN (SELECT cid FROM _tmp_known_cids) "
            "  AND in_results_db = 0"
        )
        n_marked = cur.rowcount
        # also for yt_url containing /channel/UCxxxx
        cur = dst.execute(
            "UPDATE yt_candidates "
            "SET in_results_db = 1 "
            "WHERE channel_id IS NULL "
            "  AND yt_url LIKE 'https://www.youtube.com/channel/%' "
            "  AND substr(yt_url, 35) IN (SELECT cid FROM _tmp_known_cids) "
            "  AND in_results_db = 0"
        )
        n_marked += cur.rowcount
        dst.commit()
        print(f"  marked {n_marked:,} yt_candidates as in_results_db=1")

        print()
        print("Final phase 0 snapshot:")
        for r in dst.execute("SELECT * FROM v_phase0_summary"):
            print("  " + " | ".join(f"{c}={v}" for c, v in zip(r.keys() if hasattr(r, 'keys') else [], r)))
        # row_factory not set on dst; do it the old way
        cur = dst.execute("SELECT * FROM v_phase0_summary")
        cols = [d[0] for d in cur.description]
        vals = cur.fetchone()
        if vals:
            for c, v in zip(cols, vals):
                print(f"    {c:<26} = {v}")

    src.close()
    dst.close()


if __name__ == "__main__":
    main()

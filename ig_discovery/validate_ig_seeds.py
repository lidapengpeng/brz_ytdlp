"""
validate_ig_seeds.py — take cids from ig.db (resolved via bridge / handle
resolver) and run them through extract_v4 to populate results.db channels.

Why this exists: production_v2.bfs_seed_loader only picks seeds from
channels table where is_target=1. IG-bridged cids aren't in channels
yet, so this script validates them BEFORE production_v2 can pick them
up as BFS expansion seeds.

After this script runs, any cid that passes (is_target=1) will become
visible to bfs_seed_loader on its next pass.

Run:
    ./.venv/bin/python -m ig_discovery.validate_ig_seeds [--limit N]
                                                         [--workers W]
                                                         [--source FILTER]

The script will use the same extract_v4 machinery as production_v2.
It re-uses Clash routing if the env is configured.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import sqlite3
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extract_v4 import extract  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DB = REPO_ROOT / "results.db"
IG_DB = REPO_ROOT / "data" / "ig.db"


def fetch_pending_cids(args) -> list[tuple[str, str, str]]:
    """Return (channel_id, source, source_url) tuples for cids to validate."""
    ig_conn = sqlite3.connect(IG_DB, timeout=30)
    ig_conn.execute("PRAGMA busy_timeout = 30000")
    ig_conn.row_factory = sqlite3.Row

    where = [
        "channel_id IS NOT NULL",
        "in_results_db = 0",
    ]
    params: list = []
    if args.source:
        where.append("source = ?")
        params.append(args.source)
    where_sql = " AND ".join(where)
    limit_sql = f" LIMIT {args.limit}" if args.limit > 0 else ""

    rows = [
        (r["channel_id"], r["source"], r["source_url"])
        for r in ig_conn.execute(
            f"SELECT channel_id, source, source_url FROM yt_candidates "
            f"WHERE {where_sql} ORDER BY discovered_at ASC{limit_sql}",
            params,
        )
    ]
    ig_conn.close()
    return rows


def filter_already_known(cids: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    """Remove cids already in results.db.channels (extract has already been tried)."""
    if not cids:
        return cids
    res_conn = sqlite3.connect(RESULTS_DB, timeout=30)
    known = {row[0] for row in res_conn.execute("SELECT channel_id FROM channels")}
    res_conn.close()
    new = [r for r in cids if r[0] not in known]
    n_skipped = len(cids) - len(new)
    if n_skipped > 0:
        print(f"[validate] skip {n_skipped} cids already in results.db.channels")
    return new


def write_result(res_conn: sqlite3.Connection, info, source: str, source_url: str) -> None:
    """Insert one extract_v4 result into results.db.channels."""
    # ChannelInfoV4 dataclass fields: channel_id, url, name, handle, subscribers,
    #   country, is_target, target_reason, short_circuited, error, description, ...
    is_target = 1 if info.is_target else 0
    short_circuit = 1 if info.short_circuited else 0
    res_conn.execute(
        "INSERT OR IGNORE INTO channels "
        "  (channel_id, url, name, handle, subscribers, country, "
        "   is_target, target_reason, short_circuit, error, description, discovered_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            info.channel_id,
            f"https://www.youtube.com/channel/{info.channel_id}",
            info.name,
            info.handle,
            info.subscribers,
            info.country,
            is_target,
            info.target_reason,
            short_circuit,
            info.error,
            info.description,
            int(time.time()),
        ),
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--workers", type=int, default=4, help="extract_v4 concurrency")
    p.add_argument("--source", default=None, help="filter by yt_candidates.source")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not RESULTS_DB.exists() or not IG_DB.exists():
        sys.exit("DBs not found")

    cids = fetch_pending_cids(args)
    print(f"[validate] {len(cids):,} cids in yt_candidates with channel_id set, in_results_db=0")
    cids = filter_already_known(cids)
    print(f"[validate] {len(cids):,} cids actually need extract_v4 run")

    if not cids:
        return

    if args.dry_run:
        print("[validate] dry-run, exiting.")
        for cid, src, surl in cids[:10]:
            print(f"  sample: {cid}  ({src})")
        return

    res_conn = sqlite3.connect(RESULTS_DB, timeout=60)
    res_conn.execute("PRAGMA busy_timeout = 60000")

    n_done = 0
    n_target = 0
    n_reject = 0
    n_error = 0
    t0 = time.time()
    last_log = t0

    def run_one(item):
        cid, src, surl = item
        try:
            info = extract(None, cid, min_subs=1000)
            return (item, info, None)
        except Exception as e:  # pylint: disable=broad-except
            return (item, None, f"{type(e).__name__}:{e}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, item) for item in cids]
        for fut in concurrent.futures.as_completed(futures):
            (item, info, err) = fut.result()
            cid, src, surl = item
            n_done += 1
            if info is None:
                n_error += 1
            else:
                write_result(res_conn, info, src, surl)
                if info.is_target:
                    n_target += 1
                else:
                    n_reject += 1
                # also mark in_results_db=1 in ig.db (atomic per-cid)
                with sqlite3.connect(IG_DB, timeout=30) as ig_c:
                    ig_c.execute("PRAGMA busy_timeout = 30000")
                    ig_c.execute(
                        "UPDATE yt_candidates SET in_results_db = 1 WHERE channel_id = ?",
                        (cid,),
                    )
            if n_done % 10 == 0:
                res_conn.commit()

            now = time.time()
            if now - last_log >= 3 or n_done == len(cids):
                rate = n_done / max(now - t0, 1e-9)
                eta = (len(cids) - n_done) / max(rate, 1e-9)
                print(
                    f"[validate] {n_done}/{len(cids)}  target={n_target}  "
                    f"reject={n_reject}  err={n_error}  rate={rate:.2f}/s  eta={eta:.0f}s",
                    flush=True,
                )
                last_log = now

    res_conn.commit()
    res_conn.close()

    print()
    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"  total processed:    {n_done}")
    print(f"  eligible (target):  {n_target}")
    print(f"  rejected:           {n_reject}")
    print(f"  errors:             {n_error}")
    if n_done:
        print(f"  hit rate:           {100*n_target/n_done:.1f}%")


if __name__ == "__main__":
    main()

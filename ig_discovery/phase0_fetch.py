"""
phase0_fetch.py — fetch pending aggregator URLs from ig.db, parse outbound
links, write back to aggregators + yt_candidates + ig_users tables.

Run:
    ./.venv/bin/python -m ig_discovery.phase0_fetch [--limit N] [--workers K]
                                                    [--rps R] [--retry-failed]

This is Phase 0 of the Instagram-driven discovery plan.  It expects
phase0_ingest.py to have populated `aggregators` with `fetched_at IS NULL`
rows.
"""
from __future__ import annotations

import argparse
import json
import queue
import sqlite3
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ig_discovery.linktree_parser import fetch_aggregator  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
IG_DB = REPO_ROOT / "data" / "ig.db"

# ---------------------------------------------------------------------------
# Single-writer DB pattern: workers push results to a queue; one DB thread writes.
# ---------------------------------------------------------------------------


class RateLimiter:
    """Simple token-bucket rate limiter (rps requests per second, global)."""

    def __init__(self, rps: float):
        self.interval = 1.0 / rps if rps > 0 else 0
        self.lock = threading.Lock()
        self.next_allowed = 0.0

    def wait(self) -> None:
        if self.interval == 0:
            return
        with self.lock:
            now = time.time()
            if now < self.next_allowed:
                sleep_for = self.next_allowed - now
            else:
                sleep_for = 0
            self.next_allowed = max(now, self.next_allowed) + self.interval
        if sleep_for > 0:
            time.sleep(sleep_for)


def fetcher_worker(
    in_q: "queue.Queue[str|None]",
    out_q: "queue.Queue[dict|None]",
    rate: RateLimiter,
    timeout: int,
    worker_id: int,
) -> None:
    while True:
        url = in_q.get()
        if url is None:
            return
        rate.wait()
        t0 = time.time()
        result = fetch_aggregator(url, timeout=timeout)
        result["_worker"] = worker_id
        result["_elapsed_ms"] = int((time.time() - t0) * 1000)
        out_q.put(result)


def db_writer(
    out_q: "queue.Queue[dict|None]",
    db_path: Path,
    total: int,
    stop_event: threading.Event,
) -> None:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    n_done = 0
    n_ok = 0
    n_err = 0
    n_yt_inserted = 0
    n_ig_inserted = 0
    t_start = time.time()
    last_log = t_start

    while True:
        item = out_q.get()
        if item is None:
            break
        n_done += 1

        # Update aggregators row
        conn.execute(
            "UPDATE aggregators SET "
            "  fetched_at = ?, fetch_status = ?, fetch_error = ?, "
            "  total_links = ?, n_youtube = ?, n_instagram = ? "
            "WHERE agg_url = ?",
            (
                int(time.time()),
                item.get("status") or -1,
                item.get("error"),
                len(item.get("links", [])),
                len(item.get("youtube_channels", [])),
                len(item.get("instagram_handles", [])),
                item["url"],
            ),
        )

        if item.get("error"):
            n_err += 1
        else:
            n_ok += 1

        # Insert harvested YT channels
        now = int(time.time())
        for yt in item.get("youtube_channels", []):
            cur = conn.execute(
                "INSERT OR IGNORE INTO yt_candidates "
                "  (yt_url, source, source_url, discovered_at) "
                "VALUES (?, 'linktree', ?, ?)",
                (yt, item["url"], now),
            )
            n_yt_inserted += cur.rowcount

        # Insert harvested IG handles
        for h in item.get("instagram_handles", []):
            cur = conn.execute(
                "INSERT OR IGNORE INTO ig_users "
                "  (ig_handle, discovered_via, source_ref, discovered_at) "
                "VALUES (?, 'linktree', ?, ?)",
                (h.lower(), item["url"], now),
            )
            n_ig_inserted += cur.rowcount

        # Commit every 50 records
        if n_done % 50 == 0:
            conn.commit()

        now_t = time.time()
        if now_t - last_log >= 3.0 or n_done == total:
            elapsed = now_t - t_start
            rate = n_done / max(elapsed, 1e-9)
            eta = (total - n_done) / max(rate, 1e-9)
            print(
                f"[fetch] {n_done}/{total}  ok={n_ok}  err={n_err}  "
                f"yt+={n_yt_inserted}  ig+={n_ig_inserted}  "
                f"rate={rate:.1f}/s  eta={eta:.0f}s",
                flush=True,
            )
            last_log = now_t

    conn.commit()
    conn.close()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=0, help="max aggregators to fetch")
    p.add_argument("--workers", type=int, default=4, help="concurrent HTTP workers")
    p.add_argument("--rps", type=float, default=4.0, help="global rate limit (req/s)")
    p.add_argument("--timeout", type=int, default=10, help="per-request timeout sec")
    p.add_argument(
        "--retry-failed",
        action="store_true",
        help="also re-fetch rows where fetch_status != 200 or error is set",
    )
    p.add_argument(
        "--host",
        action="append",
        default=None,
        help="restrict to specific aggregator host (repeatable, e.g. --host linktr.ee)",
    )
    args = p.parse_args()

    if not IG_DB.exists():
        sys.exit(f"ig.db not found at {IG_DB}")

    conn = sqlite3.connect(IG_DB)
    conn.row_factory = sqlite3.Row

    where = ["fetched_at IS NULL"]
    params: list = []
    if args.retry_failed:
        where = ["(fetched_at IS NULL OR fetch_status != 200 OR fetch_error IS NOT NULL)"]
    if args.host:
        placeholders = ",".join("?" * len(args.host))
        where.append(f"host IN ({placeholders})")
        params.extend(args.host)
    where_sql = " AND ".join(where)
    limit_sql = f" LIMIT {args.limit}" if args.limit > 0 else ""

    urls = [
        row["agg_url"]
        for row in conn.execute(
            f"SELECT agg_url FROM aggregators WHERE {where_sql} ORDER BY discovered_at ASC{limit_sql}",
            params,
        )
    ]
    conn.close()

    if not urls:
        print("[fetch] nothing to fetch — all aggregators already processed.")
        return

    print(
        f"[fetch] {len(urls)} aggregator URLs queued  "
        f"workers={args.workers}  rps={args.rps}  timeout={args.timeout}s"
    )

    in_q: "queue.Queue[str|None]" = queue.Queue()
    out_q: "queue.Queue[dict|None]" = queue.Queue()
    rate = RateLimiter(args.rps)
    stop_event = threading.Event()

    workers: list[threading.Thread] = []
    for i in range(args.workers):
        t = threading.Thread(
            target=fetcher_worker,
            args=(in_q, out_q, rate, args.timeout, i),
            daemon=True,
        )
        t.start()
        workers.append(t)

    writer = threading.Thread(
        target=db_writer, args=(out_q, IG_DB, len(urls), stop_event), daemon=True
    )
    writer.start()

    for url in urls:
        in_q.put(url)
    for _ in workers:
        in_q.put(None)

    for t in workers:
        t.join()
    out_q.put(None)
    writer.join()

    # Final summary
    conn = sqlite3.connect(IG_DB)
    cur = conn.execute("SELECT * FROM v_phase0_summary")
    cols = [d[0] for d in cur.description]
    vals = cur.fetchone()
    print()
    print("=" * 60)
    print("FINAL ig.db SNAPSHOT")
    print("=" * 60)
    if vals:
        for c, v in zip(cols, vals):
            print(f"  {c:<26} = {v}")

    # Host-level fetch stats
    print()
    print("Per-host fetch results:")
    for r in conn.execute(
        "SELECT host, "
        "       SUM(CASE WHEN fetch_status = 200 THEN 1 ELSE 0 END) AS ok, "
        "       SUM(CASE WHEN fetch_status != 200 OR fetch_error IS NOT NULL THEN 1 ELSE 0 END) AS err, "
        "       COUNT(*) AS total, "
        "       SUM(COALESCE(n_youtube, 0)) AS yt_total "
        "FROM aggregators WHERE fetched_at IS NOT NULL "
        "GROUP BY host ORDER BY total DESC"
    ):
        host, ok, err, total, yt = r
        print(f"  {host:<24} ok={ok:>4}  err={err:>4}  total={total:>4}  yt_harvested={yt}")

    # Top error reasons
    print()
    print("Top error reasons:")
    for r in conn.execute(
        "SELECT COALESCE(fetch_error, 'http_' || fetch_status) AS reason, COUNT(*) AS n "
        "FROM aggregators WHERE fetched_at IS NOT NULL "
        "  AND (fetch_status != 200 OR fetch_error IS NOT NULL) "
        "GROUP BY reason ORDER BY n DESC LIMIT 10"
    ):
        print(f"  {r[0]:<30} {r[1]}")

    # Sample harvested YT URLs
    print()
    print("Sample harvested YT URLs from Linktree pages:")
    for r in conn.execute(
        "SELECT yt_url, source_url FROM yt_candidates "
        "WHERE source = 'linktree' ORDER BY discovered_at DESC LIMIT 10"
    ):
        print(f"  {r[0]:<55}  ← {r[1]}")

    conn.close()


if __name__ == "__main__":
    main()

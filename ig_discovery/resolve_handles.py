"""
resolve_handles.py — resolve YouTube /@handle, /c/customname, /user/oldname
URLs in yt_candidates to their UC channel_id, then call bridge.py.

Strategy: fetch the public channel page HTML and parse:
    1.  meta name="rss" / link canonical → "/channel/UCxxxx"
    2.  fallback: regex on raw HTML for "externalId":"UCxxxx"
    3.  fallback: regex on "browseId":"UCxxxx"  in ytInitialData

Workers: 4 concurrent; rate-limited via global token bucket.

CAUTION: hitting youtube.com directly without proxy might consume some of
the main pipeline's per-IP quota.  Default rps is conservative (1.0).  If
running alongside production_v2.py, lower it further or run during a
production pause.

Run:
    ./.venv/bin/python -m ig_discovery.resolve_handles [--workers N] [--rps R]
"""
from __future__ import annotations

import argparse
import gzip
import json
import queue
import re
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO_ROOT = Path(__file__).resolve().parent.parent
IG_DB = REPO_ROOT / "data" / "ig.db"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

_CANONICAL_RE = re.compile(
    r'<link\s+rel="canonical"\s+href="https://www\.youtube\.com/channel/(UC[A-Za-z0-9_-]{22})"',
    re.IGNORECASE,
)
_EXTERNAL_ID_RE = re.compile(r'"externalId"\s*:\s*"(UC[A-Za-z0-9_-]{22})"')
_BROWSE_ID_RE = re.compile(r'"browseId"\s*:\s*"(UC[A-Za-z0-9_-]{22})"')


class RateLimiter:
    def __init__(self, rps: float):
        self.interval = 1.0 / rps if rps > 0 else 0
        self.lock = threading.Lock()
        self.next_allowed = 0.0

    def wait(self) -> None:
        if self.interval == 0:
            return
        with self.lock:
            now = time.time()
            sleep_for = max(0.0, self.next_allowed - now)
            self.next_allowed = max(now, self.next_allowed) + self.interval
        if sleep_for > 0:
            time.sleep(sleep_for)


def fetch_html(url: str, timeout: int = 12) -> tuple[int, str, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip",
            "Cookie": "PREF=hl=pt&gl=BR; SOCS=CAI",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(1024 * 1024)  # cap at 1MB; canonical link is in head
        if r.headers.get("Content-Encoding") == "gzip":
            try:
                raw = gzip.decompress(raw)
            except OSError:
                pass
        text = raw.decode("utf-8", errors="replace")
        return r.status, r.geturl(), text


def resolve(url: str) -> dict:
    """Resolve a non-UC YouTube URL to UC channel_id."""
    out = {"url": url, "channel_id": None, "status": None, "error": None}
    try:
        status, final, body = fetch_html(url)
        out["status"] = status
    except urllib.error.HTTPError as e:
        out["status"] = e.code
        out["error"] = f"http_{e.code}"
        return out
    except urllib.error.URLError as e:
        out["error"] = f"url_error:{e.reason}"
        return out
    except TimeoutError:
        out["error"] = "timeout"
        return out
    except Exception as e:  # pylint: disable=broad-except
        out["error"] = f"unexpected:{type(e).__name__}"
        return out

    m = _CANONICAL_RE.search(body) or _EXTERNAL_ID_RE.search(body) or _BROWSE_ID_RE.search(body)
    if m:
        out["channel_id"] = m.group(1)
    else:
        out["error"] = "no_uc_found"
    return out


def worker(in_q, out_q, rate, timeout, wid):
    while True:
        item = in_q.get()
        if item is None:
            return
        rate.wait()
        r = resolve(item)
        r["_worker"] = wid
        out_q.put(r)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--rps", type=float, default=1.0)
    p.add_argument("--timeout", type=int, default=10)
    p.add_argument(
        "--source",
        default=None,
        help="restrict to candidates from specific source (linktree/wikipedia/yt_about)",
    )
    args = p.parse_args()

    if not IG_DB.exists():
        sys.exit(f"ig.db not found at {IG_DB}")

    conn = sqlite3.connect(IG_DB, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.row_factory = sqlite3.Row

    where = [
        "channel_id IS NULL",
        # only non-UC URLs need resolution
        "yt_url NOT LIKE '%/channel/UC%'",
    ]
    params: list = []
    if args.source:
        where.append("source = ?")
        params.append(args.source)
    where_sql = " AND ".join(where)
    limit_sql = f" LIMIT {args.limit}" if args.limit > 0 else ""

    rows = [
        r["yt_url"]
        for r in conn.execute(
            f"SELECT yt_url FROM yt_candidates WHERE {where_sql} ORDER BY discovered_at ASC{limit_sql}",
            params,
        )
    ]
    conn.close()

    if not rows:
        print("[resolve] nothing to do — all candidates have channel_id or are UC-format.")
        return

    print(
        f"[resolve] {len(rows)} URLs to resolve  workers={args.workers}  "
        f"rps={args.rps}  timeout={args.timeout}s"
    )

    in_q = queue.Queue()
    out_q = queue.Queue()
    rate = RateLimiter(args.rps)
    threads = []
    for i in range(args.workers):
        t = threading.Thread(
            target=worker, args=(in_q, out_q, rate, args.timeout, i), daemon=True
        )
        t.start()
        threads.append(t)

    for u in rows:
        in_q.put(u)
    for _ in threads:
        in_q.put(None)

    # writer loop
    conn = sqlite3.connect(IG_DB, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")

    n_done = 0
    n_ok = 0
    n_err = 0
    t0 = time.time()
    last_log = t0
    total = len(rows)
    expected_results = total

    # collect results until all workers exit and queue is drained
    # Strategy: collect `total` results
    while n_done < expected_results:
        try:
            r = out_q.get(timeout=60)
        except queue.Empty:
            print(f"[resolve] WARN: timeout waiting for results at {n_done}/{total}")
            break

        cid = r.get("channel_id")
        if cid:
            conn.execute(
                "UPDATE yt_candidates SET channel_id = ? WHERE yt_url = ?",
                (cid, r["url"]),
            )
            n_ok += 1
        else:
            n_err += 1
            # record error so we don't retry on next run
            err = r.get("error") or "unknown"
            # We re-purpose channel_id to NULL; store error in source_url? No, source_url is sacred.
            # Just leave channel_id NULL but mark bridged_at to skip in next bridge.py run.
            conn.execute(
                "UPDATE yt_candidates SET bridged_at = ? WHERE yt_url = ?",
                (int(time.time()) * -1, r["url"]),  # negative timestamp = failure marker
            )
        n_done += 1
        if n_done % 25 == 0:
            conn.commit()

        now = time.time()
        if now - last_log >= 3.0 or n_done == total:
            elapsed = now - t0
            rate_now = n_done / max(elapsed, 1e-9)
            eta = (total - n_done) / max(rate_now, 1e-9)
            print(
                f"[resolve] {n_done}/{total}  ok={n_ok}  err={n_err}  "
                f"rate={rate_now:.1f}/s  eta={eta:.0f}s",
                flush=True,
            )
            last_log = now

    conn.commit()

    for t in threads:
        t.join()

    print()
    print("=" * 60)
    print("RESOLUTION SUMMARY")
    print("=" * 60)
    print(f"resolved (UC found):       {n_ok}")
    print(f"failed (no UC / error):    {n_err}")
    print(f"total processed:           {n_done}")

    # How many of the resolved are NEW vs already known?
    # Quick query: load results.db known cids and compare
    results_db = REPO_ROOT / "results.db"
    if results_db.exists():
        r_conn = sqlite3.connect(results_db, timeout=30)
        known = {row[0] for row in r_conn.execute("SELECT channel_id FROM channels")}
        known |= {row[0] for row in r_conn.execute("SELECT seed_cid FROM bfs_visited")}
        r_conn.close()
        resolved_cids = [
            r[0]
            for r in conn.execute(
                "SELECT channel_id FROM yt_candidates WHERE channel_id IS NOT NULL"
            )
        ]
        new_count = sum(1 for c in resolved_cids if c not in known)
        already_known = sum(1 for c in resolved_cids if c in known)
        print()
        print(f"Of {len(resolved_cids)} total resolved cids:")
        print(f"  already in results.db:   {already_known}")
        print(f"  NEW (bridgeable):        {new_count}")

    conn.close()


if __name__ == "__main__":
    main()

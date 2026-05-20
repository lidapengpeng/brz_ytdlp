"""Production v2 — 3-hour run with persistence + query bank.

Differences from production_run.py:
  - Reads queries from query_bank.txt (full 36K bank, shuffled)
  - Persists ALL extraction results to results.db (eligible AND rejected)
  - Cycles queries if exhausted (with fresh visitor_data → diverse results)
  - --minutes flag (default 180)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

import extract_v3  # monkey-patch side-effect
from discovery_compare import (
    discover_via_video_owners, discover_via_channel_filter,
    discover_via_bfs, discover_via_watchnext,
)
from extract_v4 import extract as extract_v4_fn, is_brazil
import music_scanner


RESULTS_DB = Path(__file__).resolve().parent / "results.db"


# ----- SQLite persistence ------------------------------------------------

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

-- channels: ONLY rows that passed eligibility (is_target=1 AND subs>=1000).
-- Errors and rejections are NOT stored here.
CREATE TABLE IF NOT EXISTS channels (
    channel_id     TEXT PRIMARY KEY,
    url            TEXT NOT NULL,
    name           TEXT,
    handle         TEXT,
    subscribers    INTEGER,
    country        TEXT,
    is_target      INTEGER,
    target_reason  TEXT,
    short_circuit  INTEGER,
    error          TEXT,
    description    TEXT,
    discovered_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_target ON channels(is_target);
CREATE INDEX IF NOT EXISTS idx_country ON channels(country);
CREATE INDEX IF NOT EXISTS idx_subs ON channels(subscribers);

-- rejected_channel_ids: just IDs we've confirmed are NOT eligible
-- (subs < 1000 or non-Brazil). Used for dedup so we don't waste API calls
-- re-validating the same dead leads in subsequent runs.
CREATE TABLE IF NOT EXISTS rejected_channel_ids (
    channel_id TEXT PRIMARY KEY,
    reason     TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    kind TEXT NOT NULL,
    msg TEXT
);

-- BFS visited seeds: prevents re-running BFS on the same seed across sessions.
-- See long_term_research/06_bfs_discovery.md §6 for design.
CREATE TABLE IF NOT EXISTS bfs_visited (
    seed_cid    TEXT PRIMARY KEY,
    visited_at  INTEGER NOT NULL,
    n_yielded   INTEGER,      -- total cids returned by this BFS call
    n_new       INTEGER,      -- of those, how many were new vs known_ids
    strategy    TEXT          -- 'grid_channel' | 'watchnext'
);
CREATE INDEX IF NOT EXISTS idx_bfs_visited_at ON bfs_visited(visited_at);
"""


def init_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def persist_result(conn: sqlite3.Connection, info, lock: asyncio.Lock):
    """Insert ONLY clean eligibles into channels; rejections into
    rejected_channel_ids; errors are NOT persisted (transient — can be
    retried in a future discovery pass)."""
    if info.error:
        return   # transient — skip

    eligible = (info.is_target
                and info.subscribers is not None
                and info.subscribers >= 1000)

    if eligible:
        conn.execute(
            """INSERT OR IGNORE INTO channels
               (channel_id, url, name, handle, subscribers, country,
                is_target, target_reason, short_circuit, error, description, discovered_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                info.channel_id,
                f"https://www.youtube.com/channel/{info.channel_id}",
                info.name,
                info.handle,
                info.subscribers,
                info.country,
                1 if info.is_target else 0,
                info.target_reason,
                1 if info.short_circuited else 0,
                None,
                (info.description or "")[:500] if hasattr(info, "description") else None,
                int(time.time()),
            ),
        )
    else:
        # Reject reason for audit
        if info.short_circuited:
            # Handle the new "no_subs_metadata" case (subs unparseable from stage1)
            if info.target_reason == "no_subs_metadata":
                reason = "no_subs_metadata"
            else:
                reason = f"subs={info.subscribers}<1000"
        elif info.country and not is_brazil(info.country):
            reason = f"country={info.country}"
        elif info.country is None:
            reason = "country=None,lang!=pt"
        else:
            reason = "other"
        conn.execute(
            "INSERT OR IGNORE INTO rejected_channel_ids (channel_id, reason) VALUES (?, ?)",
            (info.channel_id, reason),
        )


@dataclass
class Counters:
    discovered: int = 0
    validated: int = 0
    errors: int = 0
    short_circuited: int = 0
    target: int = 0
    eligible: int = 0
    big: int = 0
    huge: int = 0
    lang_recovered: int = 0
    api_calls: int = 0
    started_at: float = field(default_factory=time.time)


async def run_pipeline(
    queries: List[str],
    db_path: Path,
    discovery_workers: int = 10,
    validation_workers: int = 80,
    bfs_workers: int = 2,            # NEW: BFS discoverers (uses BR seeds from DB)
    music_scan_interval: float = 1800.0,  # 30 min between music scans (0 = disabled)
    max_seconds: float = 10800.0,
    status_every: float = 30.0,
    queue_max: int = 5000,
):
    counters = Counters()
    seen_channels: Set[str] = set()
    seen_lock = asyncio.Lock()
    ch_queue: asyncio.Queue = asyncio.Queue(maxsize=queue_max)
    stop_event = asyncio.Event()

    # NOTE: SQLite needs a SHORTER timeout because we batch via persist_flusher
    # which acquires db_lock briefly every ~2s — but we want operations like
    # event INSERT and bfs_visited UPDATE to coexist without blocking.
    db_conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None,
                              timeout=30.0)
    db_conn.execute("PRAGMA journal_mode=WAL")
    db_conn.execute("PRAGMA synchronous=NORMAL")
    db_conn.execute("PRAGMA temp_store=MEMORY")
    db_lock = asyncio.Lock()

    # Persistence buffer (Task #5 batching). Append per validation; flush every
    # PERSIST_FLUSH_INTERVAL or when buffer exceeds PERSIST_FLUSH_THRESHOLD.
    persist_buffer: List = []
    PERSIST_FLUSH_INTERVAL = 2.0      # seconds
    PERSIST_FLUSH_THRESHOLD = 100     # items

    # ----- preload known channel_ids (eligible + rejected) for dedup -----
    # Discoverers filter against these so we don't waste API calls
    # re-validating channels we've already settled.
    known_ids: Set[str] = set()
    for (cid,) in db_conn.execute("SELECT channel_id FROM channels"):
        known_ids.add(cid)
    eligible_count_at_start = len(known_ids)
    for (cid,) in db_conn.execute("SELECT channel_id FROM rejected_channel_ids"):
        known_ids.add(cid)
    print(f"[init] dedup preload: {eligible_count_at_start} eligible + "
          f"{len(known_ids) - eligible_count_at_start} rejected = "
          f"{len(known_ids)} known channel_ids", flush=True)

    loop = asyncio.get_running_loop()
    disc_pool = ThreadPoolExecutor(max_workers=discovery_workers, thread_name_prefix="disc")
    val_pool = ThreadPoolExecutor(max_workers=validation_workers, thread_name_prefix="val")
    bfs_pool = ThreadPoolExecutor(max_workers=max(1, bfs_workers), thread_name_prefix="bfs")

    # BFS seed queue — loaded periodically from DB
    bfs_seed_queue: asyncio.Queue = asyncio.Queue(maxsize=200)

    # Endless query iterator (cycles through, reshuffling each pass).
    # CRITICAL: shuffle at STARTUP — query_bank.txt is sorted in alphabetical-pair
    # order (e.g. "bordão brasileiro" + "bordão brasileiro canal"), so processing
    # in original order causes 99%+ dedup overlap. Without this shuffle, validators
    # starve at <0.1 ch/s. (Bug found 2026-05-19 via traced run.)
    query_idx = [0]
    query_lock = asyncio.Lock()
    queries_local = list(queries)
    random.shuffle(queries_local)

    async def next_query() -> Optional[str]:
        async with query_lock:
            if query_idx[0] >= len(queries_local):
                # Reshuffle for next pass
                random.shuffle(queries_local)
                query_idx[0] = 0
                # Log cycle event
                async with db_lock:
                    db_conn.execute(
                        "INSERT INTO events (ts, kind, msg) VALUES (?, ?, ?)",
                        (int(time.time()), "queries_cycle", f"reshuffled {len(queries_local)}"),
                    )
            q = queries_local[query_idx[0]]
            query_idx[0] += 1
            return q

    # Per-worker state for watchdog: {worker_id: (state, since_ts, cid_or_query)}
    worker_states: dict = {}

    def _set_state(wid, state: str, ctx: str = ""):
        worker_states[wid] = (state, time.time(), ctx)

    # Discovery strategies — round-robin per query for fingerprint + result-set diversity.
    # Benchmark 2026-05-19 showed channel-filter yields 3.5x more new cids per query
    # vs video-owners (109 new vs 40 new across 5 queries) with <4% overlap between
    # the two pools — combining both is essentially independent yield per call.
    DISC_STRATEGIES = [
        ("video_owners",   discover_via_video_owners),
        ("channel_filter", discover_via_channel_filter),
    ]

    async def discoverer(worker_id: int):
        wid = ("disc", worker_id)
        _set_state(wid, "spawned", "")
        strategy_idx = worker_id   # each worker starts on a different strategy
        while not stop_event.is_set():
            _set_state(wid, "next_query", "")
            q = await next_query()
            if q is None: return
            # Round-robin strategy each call
            strat_name, strat_fn = DISC_STRATEGIES[strategy_idx % len(DISC_STRATEGIES)]
            strategy_idx += 1
            _set_state(wid, f"disc_{strat_name}", q[:30])
            try:
                ids, _meta = await loop.run_in_executor(disc_pool, strat_fn, q, 30)
            except Exception:
                continue
            _set_state(wid, "dedup", q[:30])
            async with seen_lock:
                # Filter: skip channel_ids we already know (eligible or rejected
                # from prior runs) AND ones we already queued this session.
                new_ids = [c for c in ids
                           if c not in seen_channels and c not in known_ids]
                for c in new_ids:
                    seen_channels.add(c)
            counters.discovered += len(new_ids)
            _set_state(wid, "queueing", f"{len(new_ids)} cids")
            for cid in new_ids:
                if stop_event.is_set(): return
                try:
                    await asyncio.wait_for(ch_queue.put(cid), timeout=10.0)
                except asyncio.TimeoutError:
                    break

    async def validator(worker_id: int):
        wid = ("val", worker_id)
        _set_state(wid, "spawned", "")
        while not stop_event.is_set():
            _set_state(wid, "waiting_queue", "")
            try:
                cid = await asyncio.wait_for(ch_queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue
            _set_state(wid, "extracting", cid)
            try:
                info = await loop.run_in_executor(val_pool, extract_v4_fn, None, cid)
            except Exception:
                counters.errors += 1
                ch_queue.task_done()
                continue

            counters.validated += 1
            counters.api_calls += info.stages_called
            if info.error:
                counters.errors += 1
            elif info.short_circuited:
                counters.short_circuited += 1
            else:
                if info.is_target:
                    counters.target += 1
                    if info.target_reason == "country=None,lang=pt":
                        counters.lang_recovered += 1
                    if (info.subscribers or 0) >= 1000:
                        counters.eligible += 1
                    if (info.subscribers or 0) >= 10_000:
                        counters.big += 1
                    if (info.subscribers or 0) >= 1_000_000:
                        counters.huge += 1
            # Persist: only clean eligibles into channels;
            # rejections go to rejected_channel_ids; errors not persisted.
            # OPTIMIZATION (Task #5 2026-05-19): buffer instead of writing per-cid.
            # The flusher task drains the buffer every 2s or on stop_event, doing
            # one bulk transaction. Reduces db_lock contention 50x at the cost of
            # at most 2s persistence latency (acceptable — recovered on restart
            # via discovery re-finding the cid; persist is idempotent on PK).
            _set_state(wid, "buffering", cid)
            persist_buffer.append(info)
            # Track in known_ids so we don't re-validate within this session
            if not info.error:
                async with seen_lock:
                    known_ids.add(info.channel_id)
            ch_queue.task_done()

    # ----- BFS strategies (uses BR seeds from DB, not query bank) -----
    # OPTIMIZED 2026-05-20: dropped bfs_grid_channel after measuring 7549 visited
    # seeds with avg 0.55 new/seed (vs bfs_watchnext's 5.13 new/seed across 7834
    # visited — 9.3x better). Same BFS pool throughput now produces 4-5x more new
    # cids by spending all budget on watchnext.
    BFS_STRATEGIES = [
        ("bfs_watchnext",    discover_via_watchnext),
    ]

    async def bfs_seed_loader():
        """Refill bfs_seed_queue with unvisited BR seeds (subs>=10K, ORDER BY subs DESC)."""
        while not stop_event.is_set():
            if bfs_seed_queue.qsize() < 30:
                async with db_lock:
                    rows = list(db_conn.execute("""
                        SELECT c.channel_id
                        FROM channels c
                        LEFT JOIN bfs_visited v ON c.channel_id = v.seed_cid
                        WHERE c.is_target = 1
                          AND c.subscribers >= 10000
                          AND c.country IN ('Brazil','Brasil')
                          AND v.seed_cid IS NULL
                        ORDER BY c.subscribers DESC
                        LIMIT 100
                    """).fetchall())
                for (cid,) in rows:
                    # Claim atomically (row in bfs_visited prevents double-process)
                    async with db_lock:
                        cur = db_conn.execute(
                            "INSERT OR IGNORE INTO bfs_visited (seed_cid, visited_at, strategy) "
                            "VALUES (?, ?, ?)",
                            (cid, int(time.time()), "queued"))
                        claimed = cur.rowcount > 0
                    if claimed:
                        await bfs_seed_queue.put(cid)
                if not rows:
                    await asyncio.sleep(60)  # DB exhausted, wait before retry
            await asyncio.sleep(3)

    async def bfs_worker(worker_id: int):
        wid = ("bfs", worker_id)
        _set_state(wid, "spawned", "")
        strategy_idx = worker_id  # different starting strategy per worker
        while not stop_event.is_set():
            _set_state(wid, "waiting_seed", "")
            try:
                seed = await asyncio.wait_for(bfs_seed_queue.get(), timeout=10.0)
            except asyncio.TimeoutError:
                continue
            strat_name, strat_fn = BFS_STRATEGIES[strategy_idx % len(BFS_STRATEGIES)]
            strategy_idx += 1
            _set_state(wid, f"bfs_{strat_name}", seed)
            try:
                ids, _meta = await loop.run_in_executor(bfs_pool, strat_fn, seed, 50)
            except Exception:
                continue
            _set_state(wid, "bfs_dedup", seed)
            async with seen_lock:
                new_ids = [c for c in ids
                           if c not in seen_channels and c not in known_ids]
                for c in new_ids: seen_channels.add(c)
            counters.discovered += len(new_ids)
            # Update bfs_visited with strategy + yield stats
            async with db_lock:
                db_conn.execute(
                    "UPDATE bfs_visited SET n_yielded=?, n_new=?, strategy=? WHERE seed_cid=?",
                    (len(ids), len(new_ids), strat_name, seed))
            _set_state(wid, "bfs_enqueue", f"{len(new_ids)} new")
            for cid in new_ids:
                if stop_event.is_set(): return
                try:
                    await asyncio.wait_for(ch_queue.put(cid), timeout=10.0)
                except asyncio.TimeoutError:
                    break

    # ----- Music Scanner (independent BR music discovery, no IP cost overlap) -----
    # Runs every music_scan_interval seconds. Each scan hits FEmusic_{charts,explore,
    # new_releases,home} on music.youtube.com via web_music client — separate from
    # main pipeline's IP throttle bucket. Verified yield ~80-100 unique cid/scan.
    # See long_term_research/06_bfs_discovery.md §12.2 for benchmark.
    async def music_scanner_task():
        if music_scan_interval <= 0:
            return
        # Wait briefly at startup so first scan doesn't compete with warmup
        await asyncio.sleep(30)
        wid = ("music_scanner", 0)
        while not stop_event.is_set():
            _set_state(wid, "scanning_music", "")
            try:
                cids, meta = await loop.run_in_executor(None, music_scanner.scan_all_music)
            except Exception as e:
                print(f"  [music_scanner] ✗ {type(e).__name__}: {str(e)[:60]}", flush=True)
                await asyncio.sleep(min(60, music_scan_interval))
                continue
            async with seen_lock:
                new_ids = [c for c in cids
                           if c not in seen_channels and c not in known_ids]
                for c in new_ids: seen_channels.add(c)
            counters.discovered += len(new_ids)
            print(f"  [music_scanner] {meta['total_cids']} cids returned, "
                  f"{len(new_ids)} new — enqueueing", flush=True)
            _set_state(wid, "enqueueing_music", f"{len(new_ids)} cids")
            for cid in new_ids:
                if stop_event.is_set(): return
                try:
                    await asyncio.wait_for(ch_queue.put(cid), timeout=10.0)
                except asyncio.TimeoutError:
                    break
            _set_state(wid, "sleeping", f"{int(music_scan_interval)}s")
            # Sleep in chunks so we can respond to stop_event quickly
            for _ in range(int(music_scan_interval / 5)):
                if stop_event.is_set(): return
                await asyncio.sleep(5)

    # ----- Persistence flusher (Task #5) -----
    # Drains persist_buffer every PERSIST_FLUSH_INTERVAL or when threshold hit.
    # Writes are wrapped in BEGIN/COMMIT for one-shot transaction → much less
    # SQLite synchronous fsync overhead, and only ONE db_lock acquire per batch.
    async def persist_flusher():
        wid = ("flusher", 0)
        _set_state(wid, "spawned", "")
        while not stop_event.is_set():
            # Reset state to indicate we're idle between flushes (fixes watchdog
            # false-positive that reported "flushing for Ns" when actually waiting)
            _set_state(wid, "idle", f"buf={len(persist_buffer)}")
            # Wait for either threshold-hit or timeout
            t0 = time.time()
            while (time.time() - t0 < PERSIST_FLUSH_INTERVAL
                   and len(persist_buffer) < PERSIST_FLUSH_THRESHOLD
                   and not stop_event.is_set()):
                await asyncio.sleep(0.2)
            await _flush_persist_buffer()

        # Final drain at shutdown
        await _flush_persist_buffer()

    async def _flush_persist_buffer():
        if not persist_buffer:
            return
        _set_state(("flusher", 0), "flushing", f"{len(persist_buffer)} items")
        # Snapshot + clear under no lock — list.append in CPython is atomic
        batch = persist_buffer[:]
        persist_buffer.clear()
        async with db_lock:
            try:
                db_conn.execute("BEGIN")
                for info in batch:
                    try:
                        persist_result(db_conn, info, db_lock)
                    except Exception:
                        pass
                db_conn.execute("COMMIT")
            except Exception as e:
                try: db_conn.execute("ROLLBACK")
                except Exception: pass
                print(f"  [flusher] ✗ batch failed: {type(e).__name__}", flush=True)

    async def monitor():
        last = (0, 0, time.time())
        while not stop_event.is_set():
            await asyncio.sleep(status_every)
            now = time.time()
            elapsed = now - counters.started_at
            dv = counters.validated - last[0]
            de = counters.eligible - last[1]
            recent = now - last[2]
            print(
                f"[{elapsed:7.0f}s]  "
                f"disc={counters.discovered:>7d}  val={counters.validated:>7d}  "
                f"eligible={counters.eligible:>6d} (+{de})  "
                f"target={counters.target:>6d}  lang_rec={counters.lang_recovered:>5d}  "
                f"short={counters.short_circuited:>5d}  err={counters.errors:>5d}  "
                f"q={ch_queue.qsize():>4d}  "
                f"vr={dv/max(0.001,recent):5.2f}/s  er={de/max(0.001,recent):5.2f}/s",
                flush=True,
            )
            # Watchdog: print stuck workers (anyone in same state > 15s)
            stuck = []
            BENIGN_STATES = ("waiting_queue", "next_query", "spawned",
                             "waiting_seed", "sleeping", "idle")  # flusher idle = OK
            for wid, (state, since_ts, ctx) in worker_states.items():
                age = now - since_ts
                if age > 15.0 and state not in BENIGN_STATES:
                    stuck.append((wid, state, age, ctx))
            if stuck:
                stuck.sort(key=lambda x: -x[2])
                print(f"  ⚠️ STUCK WORKERS ({len(stuck)}):", flush=True)
                for wid, state, age, ctx in stuck[:10]:
                    kind, idx = wid
                    print(f"     {kind}{idx:>2d}  state={state:<14s} for {age:>5.1f}s  ctx={ctx[:40]}", flush=True)
            last = (counters.validated, counters.eligible, now)
            if elapsed >= max_seconds:
                stop_event.set()
                return

    print(f"queries={len(queries_local)} disc_workers={discovery_workers} "
          f"val_workers={validation_workers} bfs_workers={bfs_workers} "
          f"max_seconds={max_seconds}", flush=True)
    print(f"db={db_path}\nstarting pipeline...\n", flush=True)

    disc_tasks = [asyncio.create_task(discoverer(i)) for i in range(discovery_workers)]
    val_tasks = [asyncio.create_task(validator(i)) for i in range(validation_workers)]
    bfs_tasks = [asyncio.create_task(bfs_worker(i)) for i in range(bfs_workers)]
    bfs_seed_loader_task = asyncio.create_task(bfs_seed_loader())
    music_task = asyncio.create_task(music_scanner_task())
    flusher_task = asyncio.create_task(persist_flusher())
    mon_task = asyncio.create_task(monitor())

    try:
        while not stop_event.is_set():
            await asyncio.sleep(2)
            if time.time() - counters.started_at >= max_seconds:
                stop_event.set()
                break
    finally:
        # Order matters: stop discoverers/validators FIRST, then drain persist buffer,
        # then cancel flusher to avoid losing in-flight writes.
        mon_task.cancel()
        bfs_seed_loader_task.cancel()
        music_task.cancel()
        for t in disc_tasks + val_tasks + bfs_tasks: t.cancel()
        await asyncio.gather(*disc_tasks, *val_tasks, *bfs_tasks, return_exceptions=True)
        # Final drain (flusher itself does this at exit, but be defensive)
        try: await _flush_persist_buffer()
        except Exception: pass
        flusher_task.cancel()
        await asyncio.gather(mon_task, bfs_seed_loader_task, music_task,
                             flusher_task, return_exceptions=True)
        disc_pool.shutdown(wait=False)
        val_pool.shutdown(wait=False)
        bfs_pool.shutdown(wait=False)
        try: db_conn.close()
        except: pass

    return counters


def print_summary(c: Counters):
    elapsed = time.time() - c.started_at
    print("\n" + "=" * 70)
    print("PRODUCTION-RUN SUMMARY")
    print("=" * 70)
    print(f"  elapsed:           {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"  discovered:        {c.discovered}")
    print(f"  validated:         {c.validated}")
    print(f"    short-circuited: {c.short_circuited}  (subs<1k, skipped stage 2)")
    print(f"    errors:          {c.errors}")
    print(f"    target (full):   {c.target}")
    print(f"      lang-recovered:{c.lang_recovered}")
    print(f"    eligible (≥1k):  {c.eligible}")
    print(f"    big (≥10k):      {c.big}")
    print(f"    huge (≥1M):      {c.huge}")
    print(f"  api_calls:         {c.api_calls}  (avg {c.api_calls/max(1,c.validated):.2f}/channel)")
    print(f"  validation rate:   {c.validated/max(0.001,elapsed):.2f} ch/s")
    print(f"  eligible rate:     {c.eligible/max(0.001,elapsed):.2f} ch/s")
    print(f"  conversion rate:   {c.eligible/max(1,c.validated)*100:.1f}%")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=180.0)
    ap.add_argument("--disc-workers", type=int, default=10)
    ap.add_argument("--val-workers", type=int, default=80)
    ap.add_argument("--bfs-workers", type=int, default=2)
    ap.add_argument("--music-scan-interval", type=float, default=1800.0,
                    help="seconds between Music BR scans (0 to disable)")
    ap.add_argument("--status-every", type=float, default=30.0)
    ap.add_argument("--queries-file", type=str, default="query_bank.txt")
    ap.add_argument("--db", type=str, default=str(RESULTS_DB))
    args = ap.parse_args()

    db_path = Path(args.db)
    init_db(db_path)

    queries_path = Path(args.queries_file)
    queries = [l.strip() for l in queries_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"loaded {len(queries)} queries from {queries_path}", flush=True)

    counters = await run_pipeline(
        queries=queries,
        db_path=db_path,
        discovery_workers=args.disc_workers,
        validation_workers=args.val_workers,
        bfs_workers=args.bfs_workers,
        music_scan_interval=args.music_scan_interval,
        max_seconds=args.minutes * 60,
        status_every=args.status_every,
    )
    print_summary(counters)


if __name__ == "__main__":
    asyncio.run(main())

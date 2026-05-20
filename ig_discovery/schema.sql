-- ig_discovery/schema.sql
-- Independent SQLite schema for the Instagram-driven discovery pipeline.
-- Stored at `data/ig.db` (root-relative).
--
-- Decoupled from results.db: bridge script periodically reads candidate YT
-- channel IDs and INSERT OR IGNORE into results.db ch_queue.

PRAGMA journal_mode = WAL;
PRAGMA synchronous  = NORMAL;
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- 1.  Aggregators (Linktree / Beacons / Bio.link / ...)
-- ---------------------------------------------------------------------------
-- One row per aggregator URL we discover or fetch.
CREATE TABLE IF NOT EXISTS aggregators (
    agg_url       TEXT PRIMARY KEY,           -- canonical e.g. https://linktr.ee/whindersson
    host          TEXT NOT NULL,              -- 'linktr.ee' | 'beacons.ai' | ...
    source        TEXT NOT NULL,              -- 'yt_about' | 'wikipedia' | 'manual' | 'ig_bio'
    source_ref    TEXT,                       -- e.g. yt channel_id that linked here
    fetched_at    INTEGER,                    -- unix ts; NULL = not fetched yet
    fetch_status  INTEGER,                    -- HTTP status; -1 = transport error
    fetch_error   TEXT,                       -- error str if non-null
    total_links   INTEGER,                    -- count of outbound links
    n_youtube     INTEGER,                    -- # YouTube links extracted
    n_instagram   INTEGER,                    -- # IG handles extracted
    discovered_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agg_host    ON aggregators(host);
CREATE INDEX IF NOT EXISTS idx_agg_status  ON aggregators(fetch_status);
CREATE INDEX IF NOT EXISTS idx_agg_pending ON aggregators(fetched_at) WHERE fetched_at IS NULL;

-- ---------------------------------------------------------------------------
-- 2.  YouTube channels harvested from aggregators / bios
-- ---------------------------------------------------------------------------
-- One row per YT channel candidate discovered through an out-of-band source.
CREATE TABLE IF NOT EXISTS yt_candidates (
    yt_url        TEXT PRIMARY KEY,           -- canonical /@handle or /channel/UC...
    source        TEXT NOT NULL,              -- 'linktree' | 'wikipedia' | 'ig_bio' | 'beacons' | ...
    source_url    TEXT,                       -- aggregator URL / wiki page / ig handle
    channel_id    TEXT,                       -- resolved UC... (NULL until we run extract_v4)
    in_results_db INTEGER DEFAULT 0,          -- 1 if already present in results.db channels
    bridged_at    INTEGER,                    -- unix ts when sent to ch_queue
    discovered_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ytcand_source     ON yt_candidates(source);
CREATE INDEX IF NOT EXISTS idx_ytcand_bridged    ON yt_candidates(bridged_at);
CREATE INDEX IF NOT EXISTS idx_ytcand_cid        ON yt_candidates(channel_id);
CREATE INDEX IF NOT EXISTS idx_ytcand_resultsdb  ON yt_candidates(in_results_db);

-- ---------------------------------------------------------------------------
-- 3.  Instagram handles seen
-- ---------------------------------------------------------------------------
-- One row per IG handle.  Phase 0 only collects; Phase 1+ does bio scrape.
CREATE TABLE IF NOT EXISTS ig_users (
    ig_handle      TEXT PRIMARY KEY,          -- lowercase
    discovered_via TEXT NOT NULL,             -- 'yt_about' | 'linktree' | 'wikipedia' | 'follower_bfs'
    source_ref     TEXT,                      -- yt cid / linktree url / wiki page
    full_name      TEXT,
    bio            TEXT,
    external_url   TEXT,
    follower_count INTEGER,
    following_count INTEGER,
    is_business    INTEGER,
    bio_scraped_at INTEGER,                   -- unix ts of last bio fetch
    bio_scrape_error TEXT,
    discovered_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_iguser_discovered ON ig_users(discovered_via);
CREATE INDEX IF NOT EXISTS idx_iguser_scraped    ON ig_users(bio_scraped_at);
CREATE INDEX IF NOT EXISTS idx_iguser_followers  ON ig_users(follower_count);

-- ---------------------------------------------------------------------------
-- 4.  IG follower BFS visit log (Phase 2+)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ig_follower_visited (
    ig_handle      TEXT PRIMARY KEY,
    visited_at     INTEGER NOT NULL,
    n_followers_fetched INTEGER,
    new_handles_found  INTEGER
);

-- ---------------------------------------------------------------------------
-- 5.  Per-IG-account session log (Phase 1+)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ig_account_sessions (
    session_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    account        TEXT NOT NULL,              -- our IG username
    started_at     INTEGER NOT NULL,
    ended_at       INTEGER,
    api_calls      INTEGER DEFAULT 0,
    error_count    INTEGER DEFAULT 0,
    last_error     TEXT,
    proxy_used     TEXT
);
CREATE INDEX IF NOT EXISTS idx_iasess_account ON ig_account_sessions(account);

-- ---------------------------------------------------------------------------
-- 6.  Convenient views
-- ---------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS v_pending_aggregators AS
    SELECT agg_url, host, source, discovered_at
    FROM aggregators
    WHERE fetched_at IS NULL
    ORDER BY discovered_at ASC;

CREATE VIEW IF NOT EXISTS v_pending_bridge AS
    SELECT yt_url, source, channel_id, discovered_at
    FROM yt_candidates
    WHERE bridged_at IS NULL
      AND in_results_db = 0
    ORDER BY discovered_at ASC;

CREATE VIEW IF NOT EXISTS v_phase0_summary AS
    SELECT
        (SELECT COUNT(*) FROM aggregators) AS aggs_total,
        (SELECT COUNT(*) FROM aggregators WHERE fetched_at IS NOT NULL) AS aggs_fetched,
        (SELECT COUNT(*) FROM aggregators WHERE fetch_status = 200) AS aggs_ok,
        (SELECT COUNT(*) FROM yt_candidates) AS yt_candidates_total,
        (SELECT COUNT(*) FROM yt_candidates WHERE in_results_db = 1) AS yt_already_known,
        (SELECT COUNT(*) FROM yt_candidates WHERE bridged_at IS NOT NULL) AS yt_bridged,
        (SELECT COUNT(*) FROM ig_users) AS ig_users_total;

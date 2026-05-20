# brz_ytdlp — Brazilian YouTube Channel Scraper

Goal: discover 700K Brazilian (pt-BR) YouTube channels with ≥1000 subscribers.

## Architecture

```
                   ┌─────────────────────┐
                   │  query_bank (46K)   │  (curated BR queries +
                   │                     │   YouTube Suggest API BFS)
                   └──────────┬──────────┘
                              │
        ┌─────────────────────┴──────────────────────┐
        │           production_v2.py                  │
        │                                             │
        │  3 discoverers ──┐                          │
        │  2 BFS workers ──┼─→ ch_queue(5K) ──→ 15 validators
        │  1 music scanner ┘                          │
        │                          │                  │
        │  yt-dlp _call_api → InnerTube /browse, /search, /next
        │                                             │
        │            ↓ batched persist (every 2s)     │
        │       SQLite WAL (results.db)               │
        └─────────────────────────────────────────────┘
                              ↓
                   ┌─────────────────────┐
                   │  channels (eligible)│
                   │  rejected_channel_ids│
                   │  bfs_visited        │
                   └─────────────────────┘
```

## Network

- Local Mac + Clash Verge TUN mode + 100+ subscription nodes
- Auto-rotation: every 300 channels (proactive) or 2 min sustained red (reactive)
- Single hop preferred over chained (chained 10x slower per call)

## Files

| File | Purpose |
|---|---|
| `production_v2.py` | Main async pipeline orchestrator |
| `extract_v4.py` | 2-stage InnerTube extraction (browse → about panel) |
| `extract_v3.py` | InnerTube context monkey-patch (gl=BR, visitor_data) |
| `discovery_compare.py` | 4 discovery strategies (video_owners, channel_filter, bfs_grid, bfs_watchnext) |
| `music_scanner.py` | YouTube Music BR endpoint scanner |
| `clash_control.py` | Clash Verge mihomo Unix-socket API client |
| `terminal_runner.py` | Watchdog UI + auto-rotation orchestrator |
| `expand_via_suggest.py` | YouTube Suggest API BFS query bank generator |
| `query_bank.txt` | 36K BR pt-BR search queries (cartesian product) |
| `query_bank_extended.txt` | 46K queries (36K + 10K novel from Suggest BFS) |
| `RATE_LIMIT_INVESTIGATION.md` | 800-line write-up of throttling investigation |
| `long_term_research/` | 4 deep-dive docs (query bank, BFS, cookies, IPv6 VPS) |
| `colab/spike_colab.ipynb` | Google Colab spike notebook for cloud-IP scraping |
| `ig_discovery/` | Instagram-driven YouTube discovery (Phase 0 spike, see §09 long_term_research) |

## Setup

```bash
git clone <this-repo>
cd brz_ytdlp
python3.14 -m venv .venv
./.venv/bin/pip install yt-dlp langdetect langid

# Initialize SQLite schema (creates results.db)
./.venv/bin/python -c "from production_v2 import init_db; from pathlib import Path; init_db(Path('results.db'))"

# Local Clash Verge running on Unix socket /tmp/verge/verge-mihomo.sock
# (or modify clash_control.SOCK_PATH for your setup)

# Run
bash run.sh
# Prompted: auto-rotate? (default Y) and chained proxy? (default N)
```

## Performance benchmarks (2026-05)

| Stage of optimization | val rate | eligible rate |
|---|---|---|
| Broken (shuffle bug) | 0.08/s | 0.07/s |
| Shuffle fix + client rotation | 5.20/s | 2.47/s |
| + Discovery dual-track (video_owners + channel_filter) | 8.32/s | 2.66/s |
| + Mode B subscriber pre-filter | 6.90/s | 4.86/s ⭐ |
| + BFS gridChannel + watchnext | 8/s | 2-3/s |
| (After DB grew to 380K, dedup ~96%) | 1-2/s | 0.5-1/s |

## Long-term research

See `long_term_research/INDEX.md` for 5 deep investigations:
- 05 Query bank diversity (Suggest API BFS — IMPLEMENTED)
- 06 BFS discovery (grid + watchnext — IMPLEMENTED, depth-2 — natural via DB growth)
- 07 Cookie pool (4x quota — pending, requires BR YouTube accounts + 24h aging)
- 08 IPv6 VPS rotation (Hetzner + TREVORproxy — pending, €3.79/mo)
- 09 Instagram discovery (Phase 0 spike — IMPLEMENTED, 60% hit rate vs 15-20% for YT algo)

## Phase 0 Instagram spike (run order)

```bash
# 1. Init ig.db
sqlite3 data/ig.db < ig_discovery/schema.sql

# 2. Mine aggregators from existing channel descriptions
./.venv/bin/python -m ig_discovery.phase0_ingest

# 3. Fetch Linktree pages (4 workers, 4 rps)
./.venv/bin/python -m ig_discovery.phase0_fetch --workers 4 --rps 4

# 4. Harvest PT-Wikipedia BR YouTuber categories
./.venv/bin/python -m ig_discovery.phase0_wikipedia --rps 3

# 5. Resolve /@handle URLs to UC channel_id (hits youtube.com — pause production)
./.venv/bin/python -m ig_discovery.resolve_handles --rps 1 --workers 4

# 6. Bridge UC cids into results.db.bfs_visited
./.venv/bin/python -m ig_discovery.bridge

# 7. Validate ig_bridge seeds via extract_v4
./.venv/bin/python -m ig_discovery.validate_ig_seeds --workers 2
```

## Cloud experiment

See `colab/spike_colab.ipynb` for a Google Colab spike testing whether free GCP IPs are throttled less than home IPs.

## License

MIT (this project) — yt-dlp itself is Unlicense.

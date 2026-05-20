"""
ig_discovery — Instagram-driven YouTube channel discovery for BR creators.

See `long_term_research/09_instagram_discovery.md` for the architecture and
phase plan. This module is kept deliberately decoupled from the main
production_v2.py pipeline:

    - data/ig.db        independent sqlite store (own schema)
    - bridge script     periodically reads new YT channel IDs from ig.db
                        and feeds them into results.db ch_queue

Phase 0 (no IG account, $0):
    - bio_extractor.py   regex extraction of YouTube / Linktree / Beacons URLs
                         from arbitrary text (YouTube about panel, IG bio, etc.)
    - linktree_parser.py fetch + parse public Linktree / Beacons / Bio.link
                         HTML pages -> outbound URLs

Phase 1+ (single / multi IG account):
    - account_pool.py    rotating IG login + cooldown management
    - ig_scraper.py      instagrapi-driven bio + followers traversal
"""

__version__ = "0.1.0"

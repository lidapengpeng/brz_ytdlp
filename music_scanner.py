"""Music Scanner — YouTube Music BR independent discovery surface.

Periodically scans FEmusic_charts / FEmusic_explore / FEmusic_new_releases
endpoints with the web_music client. Each scan yields ~100 unique cids
(verified 2026-05-19, see long_term_research/06_bfs_discovery.md §12.2).

Used as a SEPARATE async task inside production_v2.run_pipeline. Does NOT
share IP traffic profile with query/BFS discoverers — Music endpoints are on
music.youtube.com path which YouTube treats as a different service.
"""
from __future__ import annotations

import random
import time
from typing import List, Set, Tuple

import yt_dlp
from extract_v3 import generate_visitor_data, random_brazil_ip


# Endpoints verified to work (HTTP 200 + return channelIds):
MUSIC_BROWSE_IDS = [
    "FEmusic_charts",        # 40 cids/scan
    "FEmusic_explore",       # 63 cids/scan
    "FEmusic_new_releases",  # 63 cids/scan
    "FEmusic_home",          # 0-10 cids/scan (variable)
]


def _make_music_ydl() -> yt_dlp.YoutubeDL:
    """YoutubeDL configured for music.youtube.com via web_music (WEB_REMIX) client."""
    return yt_dlp.YoutubeDL({
        "quiet": True, "no_warnings": True, "skip_download": True,
        "socket_timeout": 30,
        "geo_bypass": True, "geo_bypass_country": "BR",
        "extractor_args": {
            "youtube": {
                "player_client": ["web_music"],
                "player_skip": ["js", "configs"],
                "visitor_data": [generate_visitor_data()],
            },
        },
        "http_headers": {
            "Accept-Language": "pt-BR,pt;q=0.9",
            "X-Forwarded-For": random_brazil_ip(),
            "Origin": "https://music.youtube.com",
            "Referer": "https://music.youtube.com/",
        },
    })


def _extract_all_uc_cids(node, out=None):
    """Recursively extract all valid 24-char UC* channel ids from JSON tree."""
    if out is None:
        out = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and v.startswith("UC") and len(v) >= 24:
                out.add(v)
            _extract_all_uc_cids(v, out)
    elif isinstance(node, list):
        for x in node:
            _extract_all_uc_cids(x, out)
    return out


def scan_music_endpoint(browse_id: str) -> Tuple[Set[str], dict]:
    """Hit one FEmusic_* endpoint, harvest all channel IDs from response.

    Returns: (set of cids, meta dict).
    Failures return empty set + error meta — caller can ignore.
    """
    ydl = _make_music_ydl()
    t0 = time.time()
    try:
        ie = ydl.get_info_extractor("YoutubeTab")
        resp = ie._call_api(
            ep="browse", video_id="seed",
            query={"browseId": browse_id},
            default_client="web_music",
        )
        cids = _extract_all_uc_cids(resp)
        return cids, {
            "elapsed_s": time.time() - t0,
            "browse_id": browse_id,
            "n_cids": len(cids),
        }
    except Exception as e:
        return set(), {
            "elapsed_s": time.time() - t0,
            "browse_id": browse_id,
            "error": f"{type(e).__name__}: {str(e)[:60]}",
        }
    finally:
        try: ydl.close()
        except: pass


def scan_all_music(shuffle_clients: bool = True) -> Tuple[Set[str], dict]:
    """Run all known music endpoints, return union of cids + per-endpoint stats."""
    all_cids: Set[str] = set()
    per_endpoint = {}
    endpoints = list(MUSIC_BROWSE_IDS)
    if shuffle_clients:
        random.shuffle(endpoints)   # diversify visitor profile order
    for bid in endpoints:
        cids, meta = scan_music_endpoint(bid)
        per_endpoint[bid] = meta
        all_cids.update(cids)
    return all_cids, {
        "endpoints_scanned": len(endpoints),
        "total_cids": len(all_cids),
        "per_endpoint": per_endpoint,
    }


# ===== CLI smoke test =====
if __name__ == "__main__":
    print("=== Music Scanner smoke test ===")
    cids, meta = scan_all_music()
    print(f"Total unique cids: {len(cids)}")
    for bid, m in meta["per_endpoint"].items():
        if "error" in m:
            print(f"  {bid}: ✗ {m['error']}")
        else:
            print(f"  {bid}: ✓ {m['n_cids']} cids in {m['elapsed_s']*1000:.0f}ms")
    print(f"\nSample 10 cids: {list(cids)[:10]}")

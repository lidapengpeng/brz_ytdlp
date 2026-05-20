"""Shared helpers for bfs_v2 experiments — keep each test script lean."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import sqlite3, json, random
import yt_dlp
from extract_v3 import generate_visitor_data, random_brazil_ip

DB_PATH = "/Users/dapeng/Desktop/word/brz_ytdlp/results.db"

SAFE_CLIENTS = ("tv", "web_safari", "ios", "android_vr", "mweb")


def make_ydl(client="tv", locale="pt-BR,pt;q=0.9", gl="BR"):
    """Build a YoutubeDL with chosen client + locale + region."""
    return yt_dlp.YoutubeDL({
        "quiet": True, "no_warnings": True, "skip_download": True,
        "socket_timeout": 30,
        "geo_bypass": True, "geo_bypass_country": gl,
        "extractor_args": {
            "youtube": {
                "player_client": [client],
                "player_skip": ["js", "configs"],
                "visitor_data": [generate_visitor_data()],
            },
            "youtubetab": {"skip": ["webpage"]},
        },
        "http_headers": {
            "Accept-Language": locale,
            "X-Forwarded-For": random_brazil_ip(),
            "Cookie": f"PREF=hl=pt&gl={gl}&tz=America%2FSao_Paulo; SOCS=CAI",
        },
    })


def load_known_ids():
    """Load all known channel_ids from DB (eligible + rejected)."""
    conn = sqlite3.connect(DB_PATH)
    known = set()
    for (c,) in conn.execute("SELECT channel_id FROM channels"):
        known.add(c)
    for (c,) in conn.execute("SELECT channel_id FROM rejected_channel_ids"):
        known.add(c)
    conn.close()
    return known


def find_all(node, key, limit=None):
    """Recursively find all dicts containing `key` field."""
    out = []
    def walk(n):
        if limit is not None and len(out) >= limit:
            return True
        if isinstance(n, dict):
            if key in n:
                out.append(n[key])
                if limit is not None and len(out) >= limit:
                    return True
            for v in n.values():
                if walk(v): return True
        elif isinstance(n, list):
            for x in n:
                if walk(x): return True
        return False
    walk(node)
    return out


def find_all_renderers(node, key):
    """Find all dicts where key starts a renderer (e.g., 'channelRenderer')."""
    out = []
    def walk(n):
        if isinstance(n, dict):
            if key in n and isinstance(n[key], dict):
                out.append(n[key])
            for v in n.values(): walk(v)
        elif isinstance(n, list):
            for x in n: walk(x)
    walk(node)
    return out


def extract_all_cids(node):
    """Recursively extract all UC* channel ids."""
    out = set()
    def walk(n):
        if isinstance(n, dict):
            for k, v in n.items():
                if isinstance(v, str) and v.startswith("UC") and len(v) >= 24:
                    out.add(v)
                walk(v)
        elif isinstance(n, list):
            for x in n: walk(x)
    walk(node)
    return out


def pick_seeds(cohort, n=5):
    """Pick N random seeds from a cohort. cohort options:
       'huge'  : subs >= 1M BR
       'large' : 100K-1M BR
       'mid'   : 10K-100K BR
    """
    conn = sqlite3.connect(DB_PATH)
    if cohort == "huge":
        sql = """SELECT channel_id FROM channels
                 WHERE is_target=1 AND subscribers>=1000000 AND country IN ('Brasil','Brazil')
                 ORDER BY RANDOM() LIMIT ?"""
    elif cohort == "large":
        sql = """SELECT channel_id FROM channels
                 WHERE is_target=1 AND subscribers BETWEEN 100000 AND 999999 AND country IN ('Brasil','Brazil')
                 ORDER BY RANDOM() LIMIT ?"""
    elif cohort == "mid":
        sql = """SELECT channel_id FROM channels
                 WHERE is_target=1 AND subscribers BETWEEN 10000 AND 99999 AND country IN ('Brasil','Brazil')
                 ORDER BY RANDOM() LIMIT ?"""
    else:
        raise ValueError(cohort)
    seeds = [r[0] for r in conn.execute(sql, (n,)).fetchall()]
    conn.close()
    return seeds


def dump_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=str)

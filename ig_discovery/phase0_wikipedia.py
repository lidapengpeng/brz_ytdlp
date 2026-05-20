"""
phase0_wikipedia.py — harvest BR YouTuber YouTube channel URLs from
Portuguese Wikipedia.

Strategy:
    1. Fetch the seed list pages on pt.wikipedia.org:
        - Category: "Categoria:YouTubers do Brasil"  (paged)
        - Article:  "Lista de YouTubers brasileiros" (if exists)
       Each page lists individual BR YouTuber Wikipedia articles.
    2. For each individual article page, parse the right-rail "Infobox"
       and the body for external links → YouTube / Linktree / IG.
    3. Write everything to ig.db:
        - aggregators (Linktree found on wiki)
        - yt_candidates (YouTube channel URLs)
        - ig_users (IG handles)

This is Phase 0.1 of 09_instagram_discovery.md §9.2.
"""
from __future__ import annotations

import argparse
import gzip
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ig_discovery.bio_extractor import (  # noqa: E402
    extract_aggregators,
    extract_instagram,
    extract_youtube,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
IG_DB = REPO_ROOT / "data" / "ig.db"

USER_AGENT = (
    "brz_ytdlp-research-bot/0.1 (research; contact: research@example.com) "
    "Python/urllib"
)

# Wikipedia REST API base
WIKI_BASE = "https://pt.wikipedia.org"

# Seed pages.  PT-Wikipedia uses lowercase 'Youtubers' (not 'YouTubers').
SEED_CATEGORIES = [
    "Categoria:Youtubers do Brasil",
    "Categoria:Youtubers de Minas Gerais",
    "Categoria:Youtubers do Rio de Janeiro",
    "Categoria:Youtubers do estado do Rio de Janeiro",
    "Categoria:Youtubers do Distrito Federal (Brasil)",
    "Categoria:Youtubers de Pernambuco",
    "Categoria:Youtubers de Santa Catarina",
    # Add more sub-categories as discovered:
    # Categoria:Influenciadores digitais do Brasil
]
SEED_PAGE_LISTS = [
    "Lista de YouTubers brasileiros",
    "Lista de canais brasileiros no YouTube",
]


def _http_get(url: str, timeout: int = 15) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Accept-Encoding": "gzip",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return r.status, raw.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Category traversal via MediaWiki API
# ---------------------------------------------------------------------------


def list_category_members(category: str, limit_per_call: int = 500) -> list[str]:
    """Return article titles in a Wikipedia category (recursively page-by-page)."""
    import json

    titles: list[str] = []
    cont: str | None = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": str(limit_per_call),
            "cmnamespace": "0",  # main namespace only (articles, not sub-cats)
            "format": "json",
        }
        if cont:
            params["cmcontinue"] = cont
        url = f"{WIKI_BASE}/w/api.php?" + urllib.parse.urlencode(params)
        try:
            _, body = _http_get(url)
            data = json.loads(body)
        except (urllib.error.URLError, ValueError) as e:
            print(f"[wiki] error fetching category {category}: {e}")
            break
        members = data.get("query", {}).get("categorymembers", []) or []
        for m in members:
            titles.append(m["title"])
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        time.sleep(0.5)  # polite to wiki
    return titles


def list_subcategories(category: str) -> list[str]:
    """Return sub-category titles within a Wikipedia category."""
    import json
    subcats: list[str] = []
    cont: str | None = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": "500",
            "cmnamespace": "14",  # Category namespace
            "format": "json",
        }
        if cont:
            params["cmcontinue"] = cont
        url = f"{WIKI_BASE}/w/api.php?" + urllib.parse.urlencode(params)
        try:
            _, body = _http_get(url)
            data = json.loads(body)
        except Exception as e:
            print(f"[wiki] error fetching subcats {category}: {e}")
            break
        for m in data.get("query", {}).get("categorymembers", []) or []:
            subcats.append(m["title"])
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        time.sleep(0.5)
    return subcats


# ---------------------------------------------------------------------------
# Article page parsing
# ---------------------------------------------------------------------------


def fetch_article_external_links(title: str) -> dict:
    """Fetch an article's external links via the MediaWiki API."""
    import json

    params = {
        "action": "query",
        "prop": "extlinks",
        "titles": title,
        "ellimit": "500",
        "format": "json",
    }
    url = f"{WIKI_BASE}/w/api.php?" + urllib.parse.urlencode(params)
    try:
        _, body = _http_get(url)
        data = json.loads(body)
    except Exception as e:
        return {"title": title, "links": [], "error": str(e)}

    links: list[str] = []
    for pid, page in data.get("query", {}).get("pages", {}).items():
        for el in page.get("extlinks", []) or []:
            # API returns either {"*": url} or {"url": url} depending on version
            link = el.get("*") or el.get("url")
            if link:
                links.append(link)
    return {"title": title, "links": links, "error": None}


def harvest_one_article(title: str, conn: sqlite3.Connection) -> dict:
    """Fetch one Wikipedia article, extract & store YT/Linktree/IG links."""
    art = fetch_article_external_links(title)
    if art["error"]:
        return {"title": title, "yt": 0, "agg": 0, "ig": 0, "error": art["error"]}
    all_links = "\n".join(art["links"])

    yts = extract_youtube(all_links)
    aggs = extract_aggregators(all_links)
    igs = extract_instagram(all_links)

    now = int(time.time())

    n_yt = 0
    for yt in yts:
        cur = conn.execute(
            "INSERT OR IGNORE INTO yt_candidates "
            "  (yt_url, source, source_url, discovered_at) "
            "VALUES (?, 'wikipedia', ?, ?)",
            (yt, f"{WIKI_BASE}/wiki/{urllib.parse.quote(title.replace(' ', '_'))}", now),
        )
        n_yt += cur.rowcount

    n_agg = 0
    for agg in aggs:
        host = agg.split("/")[2].lower()
        cur = conn.execute(
            "INSERT OR IGNORE INTO aggregators "
            "  (agg_url, host, source, source_ref, discovered_at) "
            "VALUES (?, ?, 'wikipedia', ?, ?)",
            (agg, host, title, now),
        )
        n_agg += cur.rowcount

    n_ig = 0
    for h in igs:
        cur = conn.execute(
            "INSERT OR IGNORE INTO ig_users "
            "  (ig_handle, discovered_via, source_ref, discovered_at) "
            "VALUES (?, 'wikipedia', ?, ?)",
            (h.lower(), title, now),
        )
        n_ig += cur.rowcount

    return {"title": title, "yt": n_yt, "agg": n_agg, "ig": n_ig, "error": None}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=0, help="cap articles processed")
    p.add_argument("--rps", type=float, default=2.0, help="requests/sec to wiki API")
    p.add_argument(
        "--recursive",
        action="store_true",
        help="also recurse 1 level into sub-categories of YouTubers_do_Brasil",
    )
    args = p.parse_args()

    if not IG_DB.exists():
        sys.exit(f"ig.db not found at {IG_DB}")

    titles: list[str] = []
    for cat in SEED_CATEGORIES:
        members = list_category_members(cat)
        print(f"[wiki] {cat}: {len(members)} articles")
        titles.extend(members)

    if args.recursive:
        # also fetch sub-categories of each seed (single-level)
        for cat in SEED_CATEGORIES:
            subcats = list_subcategories(cat)
            for sc in subcats:
                if sc in SEED_CATEGORIES:
                    continue
                members = list_category_members(sc)
                print(f"[wiki]   {sc}: +{len(members)}")
                titles.extend(members)

    # de-dup
    titles = list(dict.fromkeys(titles))
    print(f"[wiki] total unique articles: {len(titles)}")

    if args.limit > 0:
        titles = titles[: args.limit]
        print(f"[wiki] limiting to first {len(titles)}")

    interval = 1.0 / args.rps if args.rps > 0 else 0
    conn = sqlite3.connect(IG_DB, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")

    tot_yt = tot_agg = tot_ig = tot_err = 0
    t0 = time.time()
    last_log = t0

    for i, title in enumerate(titles, 1):
        # rate limit
        time.sleep(interval)
        r = harvest_one_article(title, conn)
        if r["error"]:
            tot_err += 1
        tot_yt += r["yt"]
        tot_agg += r["agg"]
        tot_ig += r["ig"]
        if i % 10 == 0:
            conn.commit()

        now_t = time.time()
        if now_t - last_log >= 3.0 or i == len(titles):
            elapsed = now_t - t0
            rate = i / max(elapsed, 1e-9)
            eta = (len(titles) - i) / max(rate, 1e-9)
            print(
                f"[wiki] {i}/{len(titles)}  yt+={tot_yt}  agg+={tot_agg}  ig+={tot_ig}  "
                f"err={tot_err}  rate={rate:.1f}/s  eta={eta:.0f}s"
            )
            last_log = now_t

    conn.commit()

    # Summary
    print()
    print("=" * 60)
    print("WIKIPEDIA HARVEST SUMMARY")
    print("=" * 60)
    print(f"articles processed:                {len(titles)}")
    print(f"new yt_candidates (source=wikipedia): {tot_yt}")
    print(f"new aggregators (source=wikipedia):   {tot_agg}")
    print(f"new ig_users (discovered_via=wiki):   {tot_ig}")
    print(f"fetch errors:                        {tot_err}")

    print()
    print("Sample YT URLs harvested:")
    for r in conn.execute(
        "SELECT yt_url, source_url FROM yt_candidates "
        "WHERE source = 'wikipedia' ORDER BY discovered_at DESC LIMIT 10"
    ):
        print(f"  {r[0]:<55}  ← {r[1].split('/')[-1].replace('_', ' ')}")

    conn.close()


if __name__ == "__main__":
    main()

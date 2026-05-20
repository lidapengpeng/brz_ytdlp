"""
linktree_parser.py — fetch + parse public link-aggregator pages and return
outbound URLs.  Supported hosts:

    - linktr.ee/<slug>
    - beacons.ai/<slug>
    - bio.link/<slug>
    - lnk.bio/<slug>
    - linkin.bio/<slug>
    - campsite.bio/<slug>
    - solo.to/<slug>

Strategy:
    1. HEAD-less GET via urllib (yt-dlp is already a dep, but urllib is stdlib).
    2. Two extraction paths:
        a. <a href="..."> tags  -- covers static HTML pages
        b. Linktree's __NEXT_DATA__ JSON  -- modern Linktree renders client-side
    3. Resolve final URL for short-link redirects (lnk.bio, etc.) by following
       redirects (max 3 hops) and capturing the final Location.
    4. De-dup + return only YouTube / Instagram / canonical channel URLs (the
       caller decides which to keep).

Public API:
    fetch_aggregator(url, timeout=10) -> dict
        Returns: {
            'url': '<canonical url>',
            'host': 'linktr.ee',
            'status': 200 | 404 | ...,
            'links': [{'url': '...', 'text': '...', 'kind': 'youtube'|'instagram'|'other'}],
            'youtube_channels': [...],   # canonicalized YT channel URLs
            'instagram_handles': [...],
            'fetched_at': unix_ts,
            'error': None | 'timeout' | 'http_403' | ...
        }
"""
from __future__ import annotations

import gzip
import html
import io
import json
import re
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urljoin, urlparse

from .bio_extractor import canonicalize_youtube, extract_instagram, extract_youtube

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 10

_HREF_RE = re.compile(r'href="([^"]+)"', re.IGNORECASE)
_NEXT_DATA_RE = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
    re.DOTALL,
)


def _http_get(url: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[int, str, str]:
    """GET a URL.  Returns (status_code, final_url, body_text).  Raises on transport error.

    Handles gzip and follows redirects automatically (urllib default).
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        encoding = resp.headers.get_content_charset() or "utf-8"
        try:
            text = raw.decode(encoding, errors="replace")
        except LookupError:
            text = raw.decode("utf-8", errors="replace")
        return resp.status, resp.geturl(), text


# ---------------------------------------------------------------------------
# Linktree-specific: parse __NEXT_DATA__ JSON for structured link list
# ---------------------------------------------------------------------------


def _parse_linktree_nextdata(html_text: str) -> list[dict[str, str]]:
    """Extract links from Linktree's __NEXT_DATA__ JSON blob.

    Returns: [{'url': str, 'title': str}, ...]
    """
    m = _NEXT_DATA_RE.search(html_text)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    # Linktree JSON shape (as of 2026):
    #   data['props']['pageProps']['links']   -> [{url, title, ...}, ...]
    links: list[dict[str, str]] = []
    try:
        page_props = data.get("props", {}).get("pageProps", {})
        for entry in page_props.get("links", []) or []:
            url = entry.get("url") or entry.get("href")
            title = entry.get("title", "") or ""
            if url:
                links.append({"url": url, "title": title})
        # Some Linktrees also embed 'socialLinks'
        for entry in page_props.get("socialLinks", []) or []:
            url = entry.get("url") or entry.get("href")
            title = entry.get("type", "") or entry.get("title", "") or ""
            if url:
                links.append({"url": url, "title": title})
    except (AttributeError, TypeError):
        pass
    return links


# ---------------------------------------------------------------------------
# Generic href fallback
# ---------------------------------------------------------------------------


_INTERNAL_HOSTS = {
    "linktr.ee", "beacons.ai", "bio.link", "lnk.bio", "linkin.bio",
    "campsite.bio", "solo.to", "linke.to", "stan.store",
}


def _parse_generic_hrefs(html_text: str, base_url: str) -> list[dict[str, str]]:
    """Pull all <a href> URLs; filter out anchors / mailto / internal nav."""
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    base_host = urlparse(base_url).netloc.lower()
    for m in _HREF_RE.finditer(html_text):
        href = html.unescape(m.group(1)).strip()
        if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        if parsed.scheme not in ("http", "https"):
            continue
        host = parsed.netloc.lower()
        # skip internal links to the aggregator itself & its own paths
        if host == base_host:
            continue
        # skip linktree login/about/etc.
        if host in _INTERNAL_HOSTS and parsed.path in ("", "/", "/about", "/login"):
            continue
        if full in seen:
            continue
        seen.add(full)
        out.append({"url": full, "title": ""})
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_aggregator(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """Fetch an aggregator page and return parsed outbound links."""
    result: dict[str, Any] = {
        "url": url,
        "host": urlparse(url).netloc.lower(),
        "status": None,
        "links": [],
        "youtube_channels": [],
        "instagram_handles": [],
        "fetched_at": int(time.time()),
        "error": None,
    }
    try:
        status, final_url, body = _http_get(url, timeout=timeout)
        result["status"] = status
        result["final_url"] = final_url
    except urllib.error.HTTPError as e:
        result["status"] = e.code
        result["error"] = f"http_{e.code}"
        return result
    except urllib.error.URLError as e:
        result["error"] = f"url_error:{e.reason}"
        return result
    except TimeoutError:
        result["error"] = "timeout"
        return result
    except Exception as e:  # pylint: disable=broad-except
        result["error"] = f"unexpected:{type(e).__name__}:{e}"
        return result

    host = result["host"]
    raw_links: list[dict[str, str]] = []

    # Prefer Linktree's structured JSON if present
    if "linktr.ee" in host:
        raw_links = _parse_linktree_nextdata(body)
    # Fallback / supplement: generic <a href>
    if not raw_links:
        raw_links = _parse_generic_hrefs(body, url)
    else:
        # union with hrefs in case JSON missed any custom-embedded link
        href_links = _parse_generic_hrefs(body, url)
        seen_urls = {l["url"].lower() for l in raw_links}
        for l in href_links:
            if l["url"].lower() not in seen_urls:
                raw_links.append(l)

    # Classify each link
    yt_seen: set[str] = set()
    ig_seen: set[str] = set()
    classified: list[dict[str, str]] = []
    for l in raw_links:
        link_url = l["url"]
        title = l.get("title", "")
        kind = "other"

        yts = extract_youtube(link_url) or extract_youtube(title)
        igs = extract_instagram(link_url)
        if yts:
            kind = "youtube"
            for yt in yts:
                if yt.lower() not in yt_seen:
                    yt_seen.add(yt.lower())
                    result["youtube_channels"].append(yt)
        elif igs:
            kind = "instagram"
            for h in igs:
                if h.lower() not in ig_seen:
                    ig_seen.add(h.lower())
                    result["instagram_handles"].append(h)
        classified.append({"url": link_url, "title": title, "kind": kind})

    result["links"] = classified
    return result


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    targets = sys.argv[1:] or [
        # well-known BR creator linktrees (verify these still resolve)
        "https://linktr.ee/felipeneto",
        "https://linktr.ee/whindersson",
        "https://beacons.ai/anitta",
    ]
    for t in targets:
        print("=" * 70)
        print(f"FETCH: {t}")
        r = fetch_aggregator(t)
        print(f"  status={r['status']}  error={r['error']}")
        print(f"  total_links={len(r['links'])}  yt={len(r['youtube_channels'])}  ig={len(r['instagram_handles'])}")
        for yt in r["youtube_channels"]:
            print(f"    YT  {yt}")
        for ig in r["instagram_handles"][:5]:
            print(f"    IG  {ig}")
        print()

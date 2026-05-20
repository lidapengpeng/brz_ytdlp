"""
bio_extractor.py — extract YouTube + IG + link-aggregator URLs from arbitrary
text (YouTube about-panel description, IG bio, Linktree page, etc.).

Public API:
    extract_youtube(text) -> list[str]            # canonical YT URLs / handles
    extract_instagram(text) -> list[str]          # IG handles (no '@')
    extract_aggregators(text) -> list[str]        # linktr.ee/beacons.ai/bio.link URLs
    extract_all(text) -> dict                     # {'youtube': [...], 'instagram': [...], 'aggregators': [...]}
    canonicalize_youtube(url) -> str | None       # normalize to /@handle or /channel/UC...

The regexes are intentionally permissive (we'd rather over-include and filter
downstream than miss valid links).  All matches are de-duplicated case-insensitively
within a single text blob.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit, unquote

# ---------------------------------------------------------------------------
# 1.  YouTube URL extraction
# ---------------------------------------------------------------------------

# Matches:
#   youtube.com/@handle
#   youtube.com/c/customname
#   youtube.com/user/oldusername
#   youtube.com/channel/UC...     (24-char base64-ish)
#   youtu.be/<video_id>  -- intentionally skipped (video, not channel)
_YT_RE = re.compile(
    r"""(?ix)                                       # case-insensitive, verbose
    (?:https?://)?                                  # optional scheme
    (?:www\.|m\.|music\.)?                          # optional sub
    youtube\.com
    /(?:
        @(?P<handle>[A-Za-z0-9_.\-]{3,30})          # @handle (3-30 chars)
      | c/(?P<custom>[A-Za-z0-9_.\-]{1,50})         # /c/customname
      | user/(?P<user>[A-Za-z0-9_.\-]{1,50})        # /user/oldname
      | channel/(?P<cid>UC[A-Za-z0-9_-]{22})        # /channel/UC...
    )
    """
)

# Sometimes channels write bare handles like "@mychannel" without a URL
_BARE_HANDLE_RE = re.compile(
    r"(?ix)(?<![A-Za-z0-9._])@([A-Za-z0-9_.\-]{3,30})(?=\s|$|[^\w.])"
)


def extract_youtube(text: str) -> list[str]:
    """Return canonicalized YouTube URLs / handles found in text.

    Returns a list of strings of the form:
        https://www.youtube.com/@handle
        https://www.youtube.com/channel/UCxxxx...
    Duplicates removed (case-insensitive).
    """
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for m in _YT_RE.finditer(text):
        if m.group("cid"):
            canon = f"https://www.youtube.com/channel/{m.group('cid')}"
        elif m.group("handle"):
            canon = f"https://www.youtube.com/@{m.group('handle')}"
        elif m.group("custom"):
            canon = f"https://www.youtube.com/c/{m.group('custom')}"
        elif m.group("user"):
            canon = f"https://www.youtube.com/user/{m.group('user')}"
        else:
            continue
        key = canon.lower()
        if key not in seen:
            seen.add(key)
            out.append(canon)
    return out


def canonicalize_youtube(url: str) -> str | None:
    """Normalize a single YouTube URL to canonical form, or None if not a channel URL."""
    matches = extract_youtube(url)
    return matches[0] if matches else None


# ---------------------------------------------------------------------------
# 2.  Instagram handle extraction
# ---------------------------------------------------------------------------

# Matches instagram.com/<handle>, www.instagram.com/<handle>/, etc.
# IG handles: 1-30 chars, letters / digits / _ / . (no consecutive dots, but
# we accept anything matching the broad pattern and let IG decide).
_IG_URL_RE = re.compile(
    r"(?ix)"
    r"(?:https?://)?(?:www\.|m\.)?instagram\.com/"
    r"(?!p/|reel/|stories/|tv/|explore/|accounts/|direct/|web/)"  # not media paths
    r"([A-Za-z0-9_.][A-Za-z0-9_.]{0,29})"                          # handle
    r"/?"
)


def extract_instagram(text: str) -> list[str]:
    """Return IG handles (without @) found in text. Case-preserved as in source."""
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for m in _IG_URL_RE.finditer(text):
        handle = m.group(1).rstrip(".")
        # filter out obvious noise
        if handle.lower() in {"about", "explore", "developer", "p", "reel"}:
            continue
        if len(handle) < 2:
            continue
        key = handle.lower()
        if key not in seen:
            seen.add(key)
            out.append(handle)
    return out


# ---------------------------------------------------------------------------
# 3.  Link-aggregators (Linktree / Beacons / Bio.link / Lnk.bio / etc.)
# ---------------------------------------------------------------------------

_AGG_RE = re.compile(
    r"(?ix)"
    r"(?:https?://)?(?:www\.)?"
    r"("
    r"  linktr\.ee/[A-Za-z0-9_.\-]+"
    r"| beacons\.ai/[A-Za-z0-9_.\-]+"
    r"| bio\.link/[A-Za-z0-9_.\-]+"
    r"| lnk\.bio/[A-Za-z0-9_.\-]+"
    r"| linkin\.bio/[A-Za-z0-9_.\-]+"
    r"| campsite\.bio/[A-Za-z0-9_.\-]+"
    r"| solo\.to/[A-Za-z0-9_.\-]+"
    r"| linke\.to/[A-Za-z0-9_.\-]+"
    r"| stan\.store/[A-Za-z0-9_.\-]+"
    r"| linke\.tr/[A-Za-z0-9_.\-]+"
    r")"
    r"/?"
)


def extract_aggregators(text: str) -> list[str]:
    """Return aggregator URLs (Linktree / Beacons / Bio.link / Lnk.bio / ...)."""
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for m in _AGG_RE.finditer(text):
        raw = m.group(1).rstrip("/")
        # normalize: ensure https://, no www., lowercase host
        host, _, path = raw.partition("/")
        canon = f"https://{host.lower()}/{path}"
        key = canon.lower()
        if key not in seen:
            seen.add(key)
            out.append(canon)
    return out


# ---------------------------------------------------------------------------
# 4.  Combined extraction
# ---------------------------------------------------------------------------


def extract_all(text: str) -> dict[str, list[str]]:
    """Extract every kind of link from text. Returns dict with three lists."""
    return {
        "youtube": extract_youtube(text),
        "instagram": extract_instagram(text),
        "aggregators": extract_aggregators(text),
    }


# ---------------------------------------------------------------------------
# 5.  CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    samples = [
        "Inscreva-se! https://www.youtube.com/@felipeneto e veja meu Linktree: https://linktr.ee/felipeneto",
        "Sigam-me no IG: instagram.com/whindersson  e canal https://youtube.com/channel/UC1234567890abcdefghijkl",
        "All my links: beacons.ai/anaclara | YouTube /c/AnaClaraOficial",
        "Contact @canalbrasil pelo instagram, ou youtube.com/user/oldhandle",
        "https://www.youtube.com/@canalA   https://www.youtube.com/@canalB    linktr.ee/multi",
        "no links here just text",
    ]
    for s in samples:
        print("-" * 60)
        print("INPUT:", s)
        print("YT  :", extract_youtube(s))
        print("IG  :", extract_instagram(s))
        print("AGG :", extract_aggregators(s))

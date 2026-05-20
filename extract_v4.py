"""extract_v4.py — Conversion-rate-optimized extractor (PDF "conversion_rate_fix").

Three changes vs v3:
  A. Parse subscribers from Stage1's `contentMetadataViewModel`. If <1000, skip
     Stage2 entirely. Cuts API calls ~50%.
  B. When Stage2 returns country=None (PDF observed ~16.6% of real BR channels),
     run langdetect/langid on (name + description). If pt, count as Brazil.
  C. Robust pt-BR parse_count (already implemented in v3, kept here).

Also tracks stages_called so we can verify the API-call saving.
"""
from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

import yt_dlp
from yt_dlp.extractor.youtube._base import YoutubeBaseInfoExtractor

from extract_v3 import (
    _find_first, _text, _get_about_panel_token,
    generate_visitor_data, random_brazil_ip, parse_count, is_brazil,
)

# Rotate per call to spread fingerprint across 5 distinct user-agents.
# mweb is intentionally kept LAST + with lower weight because of known 2025-2026
# issues (yt-dlp #14610, #14421, #16212). All five succeed on browse endpoint,
# none require PO token or auth — verified by smoke test 2026-05.
SAFE_CLIENTS = (
    "tv",          # Cobalt SmartTV UA — uncommon, low throttle
    "web_safari",  # Mac Safari UA — standard web user
    "ios",         # iPhone YouTube app UA
    "android_vr",  # Oculus VR app UA — very rare, light throttle
    "mweb",        # iPad mobile-web (kept for diversity, not as default)
)

# Apply the same Monkey Patch as v3 (gl=BR in InnerTube context)
# (already applied when extract_v3 is imported)


# Lazy import language detectors — heavy on first call
_DETECT = None
_LANGID = None
def _ensure_langs():
    global _DETECT, _LANGID
    if _DETECT is None:
        from langdetect import detect, LangDetectException, DetectorFactory
        DetectorFactory.seed = 0  # deterministic
        _DETECT = (detect, LangDetectException)
    if _LANGID is None:
        import langid
        # Restrict to relevant European languages for speed + accuracy
        langid.set_languages(['pt', 'es', 'en', 'it', 'fr', 'de'])
        _LANGID = langid


def detect_pt(text: str) -> bool:
    """Return True iff text is Portuguese (uses langdetect + langid).

    Requires both detectors to AGREE on 'pt' for high confidence (was OR before
    — that produced ~1.4% false positives on channels with marginal text).
    Also raises min length 12 → 30 chars (langdetect is unreliable on short text).
    """
    if not text or len(text) < 30:
        return False
    _ensure_langs()
    detect, LangDetectException = _DETECT
    try:
        langdetect_pt = (detect(text) == 'pt')
    except LangDetectException:
        return False
    try:
        langid_pt = (_LANGID.classify(text)[0] == 'pt')
    except Exception:
        return False
    return langdetect_pt and langid_pt   # AND, not OR


@dataclass
class ChannelInfoV4:
    channel_id: str
    name: Optional[str] = None
    handle: Optional[str] = None
    country: Optional[str] = None
    subscribers: Optional[int] = None
    description: Optional[str] = None
    lang_detect: Optional[str] = None     # 'pt' / 'other' / None
    # PDF plan B: combined verdict
    is_target: bool = False
    target_reason: Optional[str] = None   # 'country=Brazil', 'lang=pt', etc.
    # bookkeeping
    stages_called: int = 0
    short_circuited: bool = False         # True if Stage2 was skipped (subs<1000)
    stage1_bytes: int = 0
    stage2_bytes: int = 0
    elapsed_s: float = 0.0
    error: Optional[str] = None


def make_ydl_v4(client: Optional[str] = None) -> yt_dlp.YoutubeDL:
    """Build a fresh YoutubeDL with a chosen (or random) player_client.

    Rotating clients per channel spreads the request fingerprint across multiple
    User-Agents (Cobalt TV, Safari, iPhone, Oculus VR, iPad). This avoids the
    "40 identical mweb workers from one IP" signature that triggers YouTube
    bot detection — without changing what data we extract (browse endpoint is
    identical across clients; verified by A/B smoke test).
    """
    if client is None:
        client = random.choice(SAFE_CLIENTS)
    return yt_dlp.YoutubeDL({
        "quiet": True, "no_warnings": True,
        "skip_download": True,
        "socket_timeout": 30,
        "geo_bypass": True,
        "geo_bypass_country": "BR",
        "extractor_args": {
            "youtube": {
                "player_client": [client],
                "player_skip": ["js", "configs"],
                "visitor_data": [generate_visitor_data()],
            },
            "youtubetab": {"skip": ["webpage"]},
        },
        "http_headers": {
            "Accept-Language": "pt-BR,pt;q=0.9",
            "X-Forwarded-For": random_brazil_ip(),
            "Cookie": "PREF=hl=pt&gl=BR&tz=America%2FSao_Paulo; SOCS=CAI",
        },
    })


def _extract_subs_from_stage1(resp1: dict) -> Optional[int]:
    """PDF plan A: pluck subs from contentMetadataViewModel."""
    phvm = (resp1.get('header', {})
                  .get('pageHeaderRenderer', {})
                  .get('content', {})
                  .get('pageHeaderViewModel', {}))
    if not isinstance(phvm, dict):
        return None
    cmvm = phvm.get('metadata', {}).get('contentMetadataViewModel', {})
    if not isinstance(cmvm, dict):
        return None
    for row in cmvm.get('metadataRows', []):
        if not isinstance(row, dict):
            continue
        for part in row.get('metadataParts', []):
            text = part.get('text', {})
            content = text.get('content', '') if isinstance(text, dict) else ''
            low = content.lower()
            if 'subscriber' in low or 'inscrit' in low or 'subscritor' in low:
                n = parse_count(content)
                if n is not None:
                    return n
    return None


def _extract_handle_name(resp1: dict) -> tuple[Optional[str], Optional[str]]:
    phvm = (resp1.get('header', {})
                  .get('pageHeaderRenderer', {})
                  .get('content', {})
                  .get('pageHeaderViewModel', {}))
    name = None
    if isinstance(phvm, dict):
        title = phvm.get('title', {})
        if isinstance(title, dict):
            tdv = title.get('dynamicTextViewModel', {}) if isinstance(title.get('dynamicTextViewModel'), dict) else {}
            name = _text(tdv.get('text'))
    handle = None
    cb = _find_first(resp1, "canonicalBaseUrl")
    if isinstance(cb, str) and cb.startswith("/@"):
        handle = cb.lstrip("/")
    return handle, name


def _extract_stage1_description(resp1: dict) -> Optional[str]:
    """Extract SEO description from microformat (Stage 1).

    YouTube embeds a ~150-char SEO summary of the channel description in
    Stage 1 response under microformat.microformatDataRenderer.description.
    Used as fallback signal when Stage 2 aboutChannelViewModel.description is
    too short for reliable langdetect (PDF plan B / strict pt rule needs ≥30 chars).
    """
    micro = resp1.get('microformat', {})
    if isinstance(micro, dict):
        mdr = micro.get('microformatDataRenderer', {})
        if isinstance(mdr, dict):
            d = mdr.get('description')
            if isinstance(d, str) and d.strip():
                return d.strip()
    return None


def extract(_ignored, channel_id: str, min_subs: int = 1000) -> ChannelInfoV4:
    """v4 two-stage with PDF plan A (early exit) + plan B (lang detect fallback).

    Each call mints + closes a fresh YoutubeDL so file descriptors don't leak
    (avoids OSError: [Errno 24] Too many open files under high concurrency).
    """
    info = ChannelInfoV4(channel_id=channel_id)
    ydl = make_ydl_v4()
    try:
        return _extract_inner(ydl, info, channel_id, min_subs)
    finally:
        try:
            ydl.close()           # release sockets / temp files
        except Exception:
            pass


def _extract_inner(ydl, info: "ChannelInfoV4", channel_id: str, min_subs: int) -> "ChannelInfoV4":
    ie = ydl.get_info_extractor("YoutubeTab")
    t0 = time.time()

    # ---- Stage 1 ----
    info.stages_called = 1
    try:
        resp1 = ie._call_api(ep="browse", video_id=channel_id, query={"browseId": channel_id})
    except Exception as e:
        info.error = f"stage1: {type(e).__name__}: {e}"
        info.elapsed_s = time.time() - t0
        return info
    info.stage1_bytes = len(json.dumps(resp1))

    info.subscribers = _extract_subs_from_stage1(resp1)
    info.handle, info.name = _extract_handle_name(resp1)
    # NEW: capture stage1 SEO description for langdetect fallback
    stage1_desc = _extract_stage1_description(resp1)

    # PDF plan A: early exit if subs < min OR subs unparseable.
    # IMPORTANT (2026-05-19 fix): if subscribers is None it means the channel home
    # page has no contentMetadataViewModel — typically auto-generated/deleted/
    # topic channels. These are PERMANENTLY unprocessable, not transient errors.
    # Mark as short_circuited so they go to rejected_channel_ids and don't get
    # re-validated next session. Previously these were dumped as info.error which
    # (a) inflated err rate to 14% and (b) caused re-discovery+re-validation
    # every session (wasted API calls).
    if info.subscribers is None:
        info.short_circuited = True
        info.target_reason = "no_subs_metadata"
        info.elapsed_s = time.time() - t0
        return info
    if info.subscribers < min_subs:
        info.short_circuited = True
        info.elapsed_s = time.time() - t0
        return info  # is_target stays False; caller can see short_circuited

    # ---- Stage 2 (only for >= min_subs channels) ----
    token = _get_about_panel_token(resp1)
    if not token:
        info.error = "no about-panel token in stage1"
        info.elapsed_s = time.time() - t0
        return info

    info.stages_called = 2
    try:
        resp2 = ie._call_api(ep="browse", video_id=channel_id,
                             query={"continuation": token})
    except Exception as e:
        info.error = f"stage2: {type(e).__name__}: {e}"
        info.elapsed_s = time.time() - t0
        return info
    info.stage2_bytes = len(json.dumps(resp2))

    avm = _find_first(resp2, "aboutChannelViewModel")
    if isinstance(avm, dict):
        c = avm.get("country")
        if isinstance(c, str) and c.strip():
            info.country = c.strip()
        # description is what plan B feeds into langdetect
        info.description = _text(avm.get("description"))
        # Also refresh subs from stage 2 if it's more accurate
        stage2_subs = parse_count(_text(avm.get("subscriberCountText")))
        if stage2_subs is not None:
            info.subscribers = stage2_subs  # stage 2 is canonical

    # ---- PDF plan B: language-detect fallback ----
    # Strict rule: only the DESCRIPTION counts, not the channel name. Name is a
    # weak signal (a non-BR channel can have a pt-looking handle like "@brasil_x").
    # Combined with detect_pt's AND-of-two-detectors rule, this should yield
    # ~99.9% precision on lang_recovered.
    #
    # 2026-05-19 enhancement: when Stage 2 description is missing or too short
    # (<30 chars — detect_pt's threshold), fall back to Stage 1's SEO description
    # (microformatDataRenderer.description, typically ~150 chars). This recovers
    # additional lang_recovered eligibles that previously failed silently.
    if is_brazil(info.country):
        info.is_target = True
        info.target_reason = "country=Brazil"
    elif info.country is None:
        stage2_desc = (info.description or "").strip()
        # Pick best description for langdetect: prefer stage2 if >=30 chars,
        # else use stage1 SEO desc (still has ~150 chars), else concatenate both.
        if len(stage2_desc) >= 30:
            desc_for_detect = stage2_desc
        elif stage1_desc and len(stage1_desc) >= 30:
            desc_for_detect = stage1_desc
            # Also expose this in info.description so downstream sees the signal used
            if not info.description:
                info.description = stage1_desc
        else:
            # Concatenate any partial text to push past the 30-char threshold
            combined = " ".join(filter(None, [stage2_desc, stage1_desc])).strip()
            desc_for_detect = combined if len(combined) >= 30 else None

        if desc_for_detect and detect_pt(desc_for_detect):
            info.is_target = True
            info.target_reason = "country=None,lang=pt"
            info.lang_detect = "pt"
        else:
            info.lang_detect = "other_or_unknown"
    else:
        # Non-BR confirmed country
        info.is_target = False

    info.elapsed_s = time.time() - t0
    return info


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

def main():
    # PDF-cited examples + our usual mix
    tests = [
        ("UCr4ARxgElIO21GWfIraZezg", "Brazil",          10_200_000,  "Garena FF Brasil"),
        ("UCJ0-OtVpF0wOKEqT2Z1HEtA", "Canada",           8_710_000,  "ElectroBOOM (non-BR)"),
        ("UCTl3QQTvqHFjurroKxexy2Q", "PDF: BR-but-country=None", 16_000_000, "Olympics (PDF cited)"),
        ("UCLFfhSlpG3BO-FaUUg-k0OQ", "PDF: BR-but-country=None",    127_000, "PDF cited recovery"),
        ("UCFCUSOunpAQFpFl-M94sX_Q", "Brazil",                       45_700,  "MONTORO BR small"),
    ]
    print(f"yt-dlp {yt_dlp.version.__version__} — extract_v4 (PDF plan A+B+C)\n")
    print(f"{'channel':32s} {'expected':28s} {'stage1_subs':>11s} {'country':>14s} {'lang':>5s} {'target?':>8s} {'reason':>22s} {'stages':>3s}")
    print("-" * 145)
    for cid, expected_country, expected_subs, label in tests:
        info = extract(None, cid)
        if info.error:
            print(f"{label[:32]:32s} ERR: {info.error[:80]}")
            continue
        target_mark = "✓" if info.is_target else "✗"
        print(f"{label[:32]:32s} {expected_country[:28]:28s} "
              f"{info.subscribers!s:>11s} {info.country!s:>14s} "
              f"{info.lang_detect or '-':>5s} {target_mark:>8s} "
              f"{(info.target_reason or '-'):>22s} {info.stages_called:>3d}")


if __name__ == "__main__":
    main()

"""Two-stage InnerTube channel metadata extractor.

Flow per channel:
   1. POST /youtubei/v1/browse  {browseId: UC...}              ~1.1MB
        → parse header.pageHeaderRenderer....descriptionPreviewViewModel
           ....showEngagementPanelEndpoint.....continuationCommand.token
   2. POST /youtubei/v1/browse  {continuation: <token>}         ~18KB
        → parse aboutChannelViewModel.{country, subscriberCountText, ...}

Returns ChannelInfo with verified country + subscriber count.

Inspired by yt-dlp issue #8634 (coletdjnz's hint: "the token is in the channel header data").
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Optional

import yt_dlp


@dataclass
class ChannelInfo:
    channel_id: str
    name: Optional[str] = None
    handle: Optional[str] = None
    country: Optional[str] = None
    subscribers: Optional[int] = None
    view_count: Optional[int] = None
    video_count: Optional[int] = None
    joined_date: Optional[str] = None
    elapsed_total_s: float = 0.0
    bytes_total: int = 0
    error: Optional[str] = None


_SUB_RE = re.compile(r"(\d[\d.,]*)\s*(thousand|millions?|million|mil|mi|bilhão|bilhões|billion|bi|m|k|b)?",
                     re.IGNORECASE)


def parse_count(text: str) -> Optional[int]:
    """Parse 'X subscribers' / 'X.YM' / 'X mil' / 'X mi'."""
    if not text:
        return None
    s = text.lower().replace("\xa0", " ").replace(",", "")
    # strip noise
    for noise in ("subscribers", "subscriber", "inscritos", "views", "videos",
                  "visualizações", "vídeos", "se inscreveram"):
        s = s.replace(noise, "")
    s = s.strip()
    m = _SUB_RE.search(s)
    if not m:
        return None
    try:
        num = float(m.group(1))
    except ValueError:
        return None
    unit = (m.group(2) or "").lower()
    mult = 1
    if unit in ("mil", "k", "thousand"):
        mult = 1_000
    elif unit in ("mi", "m", "million", "millions"):
        mult = 1_000_000
    elif unit in ("bi", "b", "billion", "bilhão", "bilhões"):
        mult = 1_000_000_000
    return int(num * mult)


def _find_first(node: Any, key: str) -> Any:
    """DFS for the first occurrence of `key` in a nested dict/list."""
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for v in node.values():
            r = _find_first(v, key)
            if r is not None:
                return r
    elif isinstance(node, list):
        for x in node:
            r = _find_first(x, key)
            if r is not None:
                return r
    return None


def _text(obj: Any) -> str:
    """Extract text from a simpleText / runs / {content} structure."""
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        if "simpleText" in obj:
            return str(obj["simpleText"] or "")
        if "content" in obj and isinstance(obj["content"], str):
            return obj["content"]
        runs = obj.get("runs")
        if isinstance(runs, list):
            return "".join(str(r.get("text", "")) for r in runs if isinstance(r, dict))
    return ""


def _get_about_panel_token(channel_resp: dict) -> Optional[str]:
    """Navigate channel_resp → the description-preview's continuation token (about panel loader)."""
    try:
        desc = (channel_resp["header"]["pageHeaderRenderer"]["content"]
                ["pageHeaderViewModel"]["description"]["descriptionPreviewViewModel"])
    except (KeyError, TypeError):
        return None
    try:
        sep = (desc["rendererContext"]["commandContext"]["onTap"]
               ["innertubeCommand"]["showEngagementPanelEndpoint"])
        contents = sep["engagementPanel"]["engagementPanelSectionListRenderer"]["content"]["sectionListRenderer"]["contents"]
        for c in contents:
            isr = c.get("itemSectionRenderer", {})
            for inner in isr.get("contents", []):
                cir = inner.get("continuationItemRenderer")
                if cir:
                    return cir["continuationEndpoint"]["continuationCommand"]["token"]
    except (KeyError, TypeError):
        pass
    return None


def extract(ydl: yt_dlp.YoutubeDL, channel_id: str) -> ChannelInfo:
    """Two-stage InnerTube extraction; returns a ChannelInfo (with `.error` set on failure)."""
    info = ChannelInfo(channel_id=channel_id)
    ie = ydl.get_info_extractor("YoutubeTab")
    t0 = time.time()
    total_bytes = 0

    # ---- Stage 1: channel page ----
    try:
        resp1 = ie._call_api(ep="browse", video_id=channel_id, query={"browseId": channel_id})
    except Exception as e:
        info.error = f"stage1: {type(e).__name__}: {e}"
        info.elapsed_total_s = time.time() - t0
        return info
    try:
        import json
        total_bytes += len(json.dumps(resp1))
    except Exception:
        pass

    # Extract immediate metadata from channel header
    hdr = _find_first(resp1, "pageHeaderViewModel") or {}
    if isinstance(hdr, dict):
        info.name = _text(hdr.get("title", {}).get("dynamicTextViewModel", {}).get("text"))
    meta = _find_first(resp1, "channelMetadataRenderer") or {}
    if isinstance(meta, dict):
        info.name = info.name or meta.get("title")
    handle = _find_first(resp1, "canonicalBaseUrl")
    if isinstance(handle, str) and handle.startswith("/@"):
        info.handle = handle.lstrip("/")

    # ---- Stage 2: about panel via continuation token ----
    token = _get_about_panel_token(resp1)
    if not token:
        info.error = "no about-panel token in channel response"
        info.elapsed_total_s = time.time() - t0
        info.bytes_total = total_bytes
        return info

    try:
        resp2 = ie._call_api(ep="browse", video_id=channel_id, query={"continuation": token})
    except Exception as e:
        info.error = f"stage2: {type(e).__name__}: {e}"
        info.elapsed_total_s = time.time() - t0
        info.bytes_total = total_bytes
        return info
    try:
        import json
        total_bytes += len(json.dumps(resp2))
    except Exception:
        pass

    avm = _find_first(resp2, "aboutChannelViewModel")
    if not isinstance(avm, dict):
        info.error = "no aboutChannelViewModel in panel response"
        info.elapsed_total_s = time.time() - t0
        info.bytes_total = total_bytes
        return info

    # The juicy fields
    if isinstance(avm.get("country"), str):
        info.country = avm["country"].strip()
    info.subscribers = parse_count(_text(avm.get("subscriberCountText")))
    info.view_count  = parse_count(_text(avm.get("viewCountText")))
    info.video_count = parse_count(_text(avm.get("videoCountText")))
    info.joined_date = _text(avm.get("joinedDateText"))
    info.name        = info.name or _text(avm.get("titleText"))

    info.elapsed_total_s = time.time() - t0
    info.bytes_total = total_bytes
    return info


def main():
    """Smoke test on a known mix of BR + non-BR channels."""
    tests = [
        ("UCr4ARxgElIO21GWfIraZezg", "Garena Free Fire Brasil", "Brazil"),
        ("UCJ0-OtVpF0wOKEqT2Z1HEtA", "ElectroBOOM",             "Canada"),
        ("UC295-Dw_tDNtZXFeAPAW6Aw", "5-Minute Crafts",         "United States"),
        ("UCY30JRSgfhYXA6i6xX1erWg", "Smosh",                   "United States"),
        ("UCFCUSOunpAQFpFl-M94sX_Q", "(unknown BR channel)",    "Brazil"),
    ]
    ydl = yt_dlp.YoutubeDL({
        "quiet": True, "no_warnings": True,
        "extractor_args": {"youtube": {"player_client": ["mweb"]}},
    })
    print(f"yt-dlp {yt_dlp.version.__version__}")
    print("=" * 92)
    print(f"{'channel':28s}  {'subs':>10s}  {'country':>16s}  {'time':>5s}  {'bytes':>8s}  {'expected':>15s}")
    print("=" * 92)
    for cid, label, expected in tests:
        info = extract(ydl, cid)
        if info.error:
            print(f"{label[:28]:28s}  ERR: {info.error}")
            continue
        marker = "✓" if info.country == expected else "✗"
        print(f"{(info.name or label)[:28]:28s}  "
              f"{(info.subscribers or 0):>10,d}  "
              f"{(info.country or ''):>16s}  "
              f"{info.elapsed_total_s:>4.1f}s  "
              f"{info.bytes_total:>8,d}  "
              f"{expected:>15s} {marker}")


if __name__ == "__main__":
    main()

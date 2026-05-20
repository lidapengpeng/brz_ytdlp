"""extract_v3.py — applies the three new tricks from the deep-solution PDF.

Changes vs extract_v2:
  1. **Per-request dynamic visitor_data** (PDF §2.2) — instead of harvesting one
     vd and reusing it across all calls, generate a fresh Protobuf-encoded vd
     for every channel. PDF claims this is the dominant cause of bot detection
     when concurrent workers share a single vd.

  2. **InnerTube context gl='BR' injection** (PDF §2.3) — yt-dlp's _extract_context
     only sets hl/timeZone, not gl. We Monkey-Patch it to also set gl='BR' so
     YouTube treats every call as coming from a Brazilian session.

  3. **Random Brazil X-Forwarded-For** (PDF §2.4) — inject a random IP from
     Brazil ISP ranges (Claro, Vivo, NET, etc.) on every request.

If the PDF's hypothesis is right, these should let us push 20+ concurrent
workers without the cascade-block we saw in v2.
"""
from __future__ import annotations

import base64
import ipaddress
import json
import random
import string
import time
from dataclasses import dataclass
from typing import Any, List, Optional

import yt_dlp
from yt_dlp.extractor.youtube._base import YoutubeBaseInfoExtractor


# ---------------------------------------------------------------------------
# Monkey-patch: inject gl='BR' into every InnerTube context
# ---------------------------------------------------------------------------

_original_extract_context = YoutubeBaseInfoExtractor._extract_context


def _patched_extract_context(self, ytcfg=None, default_client="web"):
    """Add gl/hl/timeZone/utcOffsetMinutes to every InnerTube call's context."""
    ctx = _original_extract_context(self, ytcfg, default_client)
    if isinstance(ctx, dict) and isinstance(ctx.get("client"), dict):
        ctx["client"].update({
            "gl": "BR",
            "hl": "pt",
            "timeZone": "America/Sao_Paulo",
            "utcOffsetMinutes": -180,
        })
    return ctx


YoutubeBaseInfoExtractor._extract_context = _patched_extract_context


# ---------------------------------------------------------------------------
# Per-request visitor_data + Brazil XFF helpers
# ---------------------------------------------------------------------------

def generate_visitor_data() -> str:
    """Fresh Protobuf-encoded visitor_data, exactly as PDF §2.2 spec."""
    chars = string.ascii_letters + string.digits + "_-"
    visitor_id = "".join(random.choices(chars, k=11))
    ts = int(time.time())

    id_bytes = visitor_id.encode()
    field1 = bytes([0x0a, len(id_bytes)]) + id_bytes

    def varint(n: int) -> bytes:
        out = []
        while n > 0x7F:
            out.append((n & 0x7F) | 0x80)
            n >>= 7
        out.append(n)
        return bytes(out)

    field5 = bytes([0x28]) + varint(ts)
    return base64.urlsafe_b64encode(field1 + field5).decode().rstrip("=")


BRAZIL_IP_RANGES = [
    "177.0.0.0/8",       # Claro
    "179.0.0.0/8",       # Vivo
    "189.0.0.0/8",       # NET / Claro
    "191.128.0.0/12",    # general BR
    "200.128.0.0/9",     # ANATEL allocations
]


def random_brazil_ip() -> str:
    cidr = random.choice(BRAZIL_IP_RANGES)
    network = ipaddress.IPv4Network(cidr)
    return str(ipaddress.IPv4Address(
        random.randint(int(network.network_address), int(network.broadcast_address))
    ))


# ---------------------------------------------------------------------------
# Data shapes (mirror extract_v2 for drop-in compatibility)
# ---------------------------------------------------------------------------

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
    stage1_bytes: int = 0
    stage2_bytes: int = 0
    stage1_s: float = 0.0
    stage2_s: float = 0.0
    error: Optional[str] = None


@dataclass
class ExtractorConfigV3:
    use_cookies_from_chrome: bool = False
    label: str = "v3"


# ---------------------------------------------------------------------------
# Parsing helpers (copied from v2 — same logic)
# ---------------------------------------------------------------------------

import re
_SUB_RE = re.compile(r"(\d[\d.,]*)\s*(thousand|millions?|million|mil|mi|bilhão|bilhões|billion|bi|m|k|b)?",
                     re.IGNORECASE)


def parse_count(text: str) -> Optional[int]:
    """Parse '10,2 mi inscritos' (pt-BR) and '10.2M subscribers' (en) correctly.

    pt-BR: comma is decimal, period is thousands.  '10,2 mi' = 10.2M
    en   : comma is thousands, period is decimal.  '10.2M' = 10.2M
    """
    if not text:
        return None
    s = text.lower().replace("\xa0", " ")
    for noise in ("subscribers", "subscriber", "inscritos", "views", "videos",
                  "visualizações", "vídeos", "se inscreveram",
                  "visualizacoes", "subscritores"):
        s = s.replace(noise, "")
    s = s.strip()
    m = _SUB_RE.search(s)
    if not m:
        return None
    num_s = m.group(1)
    unit = (m.group(2) or "").lower()

    try:
        if "," in num_s and "." in num_s:
            # Mixed — assume the rightmost separator is decimal
            if num_s.rfind(",") > num_s.rfind("."):
                num = float(num_s.replace(".", "").replace(",", "."))  # pt
            else:
                num = float(num_s.replace(",", ""))  # en
        elif "," in num_s:
            # Only comma. If unit present AND last chunk has ≤2 digits → pt decimal
            # ("10,2 mi"). Otherwise treat as en thousands ("1,234 subs").
            last_chunk = num_s.split(",")[-1]
            if unit and len(last_chunk) <= 2:
                num = float(num_s.replace(",", "."))
            elif not unit and len(last_chunk) == 3:
                num = float(num_s.replace(",", ""))
            else:
                num = float(num_s.replace(",", "."))
        else:
            # No comma. If unit present and exactly one period → en decimal ("1.5M").
            # Otherwise period is thousands ("1.234 inscritos" pt).
            if unit and num_s.count(".") == 1:
                num = float(num_s)
            else:
                num = float(num_s.replace(".", ""))
    except ValueError:
        return None

    mult = 1
    if unit in ("mil", "k", "thousand"):
        mult = 1_000
    elif unit in ("mi", "m", "million", "millions"):
        mult = 1_000_000
    elif unit in ("bi", "b", "billion", "bilhão", "bilhões"):
        mult = 1_000_000_000
    try:
        return int(num * mult)
    except (ValueError, OverflowError):
        return None


_BRAZIL_NAMES = frozenset({"Brasil", "Brazil"})  # gl=BR returns either depending on hl


def is_brazil(country: Optional[str]) -> bool:
    return country in _BRAZIL_NAMES if country else False


def _find_first(node: Any, key: str) -> Any:
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


def _get_about_panel_token(resp1: dict) -> Optional[str]:
    try:
        desc = (resp1["header"]["pageHeaderRenderer"]["content"]
                ["pageHeaderViewModel"]["description"]["descriptionPreviewViewModel"])
        sep = (desc["rendererContext"]["commandContext"]["onTap"]
               ["innertubeCommand"]["showEngagementPanelEndpoint"])
        contents = sep["engagementPanel"]["engagementPanelSectionListRenderer"]["content"]["sectionListRenderer"]["contents"]
        for c in contents:
            for inner in c.get("itemSectionRenderer", {}).get("contents", []):
                cir = inner.get("continuationItemRenderer")
                if cir:
                    return cir["continuationEndpoint"]["continuationCommand"]["token"]
    except (KeyError, TypeError, AttributeError):
        return None
    return None


# ---------------------------------------------------------------------------
# Build a fresh yt-dlp per call (so each call gets a fresh visitor_data)
# ---------------------------------------------------------------------------

def make_ydl_v3(cfg: ExtractorConfigV3) -> yt_dlp.YoutubeDL:
    """Each call mints a new visitor_data + random Brazil XFF header."""
    vd = generate_visitor_data()
    xff = random_brazil_ip()

    opts = {
        "quiet": True, "no_warnings": True,
        "skip_download": True,
        "socket_timeout": 30,
        "geo_bypass": True,
        "geo_bypass_country": "BR",
        "extractor_args": {
            "youtube": {
                "player_client": ["mweb"],
                "player_skip": ["js", "configs"],
                "visitor_data": [vd],
            },
            "youtubetab": {"skip": ["webpage"]},
        },
        "http_headers": {
            "Accept-Language": "pt-BR,pt;q=0.9",
            "X-Forwarded-For": xff,
            "Cookie": "PREF=hl=pt&gl=BR&tz=America%2FSao_Paulo; SOCS=CAI",
        },
    }
    if cfg.use_cookies_from_chrome:
        opts["cookiesfrombrowser"] = ("chrome", None, None, None)
    return yt_dlp.YoutubeDL(opts)


def extract(ydl_unused: yt_dlp.YoutubeDL, channel_id: str,
            cfg: Optional[ExtractorConfigV3] = None) -> ChannelInfo:
    """Two-stage InnerTube extraction with v3 mitigations.

    NOTE: We ignore `ydl_unused` to mimic the v2 signature for drop-in. Each
    call builds its own yt-dlp with fresh visitor_data + XFF.
    """
    if cfg is None:
        cfg = ExtractorConfigV3()
    ydl = make_ydl_v3(cfg)
    info = ChannelInfo(channel_id=channel_id)
    ie = ydl.get_info_extractor("YoutubeTab")

    # ---- Stage 1: channel page ----
    t0 = time.time()
    try:
        resp1 = ie._call_api(ep="browse", video_id=channel_id,
                             query={"browseId": channel_id})
    except Exception as e:
        info.error = f"stage1: {type(e).__name__}: {e}"
        info.stage1_s = time.time() - t0
        return info
    info.stage1_s = time.time() - t0
    info.stage1_bytes = len(json.dumps(resp1))

    hdr = _find_first(resp1, "pageHeaderViewModel") or {}
    if isinstance(hdr, dict):
        info.name = _text(hdr.get("title", {}).get("dynamicTextViewModel", {}).get("text"))
    handle = _find_first(resp1, "canonicalBaseUrl")
    if isinstance(handle, str) and handle.startswith("/@"):
        info.handle = handle.lstrip("/")

    # ---- Stage 2: about panel ----
    token = _get_about_panel_token(resp1)
    if not token:
        info.error = "no about-panel token in stage1 response"
        return info

    t0 = time.time()
    try:
        resp2 = ie._call_api(ep="browse", video_id=channel_id,
                             query={"continuation": token})
    except Exception as e:
        info.error = f"stage2: {type(e).__name__}: {e}"
        info.stage2_s = time.time() - t0
        return info
    info.stage2_s = time.time() - t0
    info.stage2_bytes = len(json.dumps(resp2))

    avm = _find_first(resp2, "aboutChannelViewModel")
    if not isinstance(avm, dict):
        info.error = "no aboutChannelViewModel in stage2"
        return info

    if isinstance(avm.get("country"), str):
        info.country = avm["country"].strip()
    info.subscribers = parse_count(_text(avm.get("subscriberCountText")))
    info.view_count = parse_count(_text(avm.get("viewCountText")))
    info.video_count = parse_count(_text(avm.get("videoCountText")))
    info.joined_date = _text(avm.get("joinedDateText"))
    return info


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

def main():
    # accept both pt-BR and en country names ("Brasil" == "Brazil" etc.)
    EQUIV = {
        "Brasil": "Brazil", "Brazil": "Brazil",
        "Canadá": "Canada", "Canada": "Canada",
        "Estados Unidos": "United States", "United States": "United States",
    }
    tests = [
        ("UCr4ARxgElIO21GWfIraZezg", "Brazil",        10_200_000),
        ("UCJ0-OtVpF0wOKEqT2Z1HEtA", "Canada",         8_710_000),
        ("UC295-Dw_tDNtZXFeAPAW6Aw", "United States", 80_700_000),
        ("UCY30JRSgfhYXA6i6xX1erWg", "United States", 27_100_000),
        ("UCFCUSOunpAQFpFl-M94sX_Q", "Brazil",            45_700),
    ]
    print(f"yt-dlp {yt_dlp.version.__version__} — extract_v3 (PDF mitigations)")
    print(f"Monkey-patched _extract_context to inject gl=BR/hl=pt\n")
    for cid, expected_country, expected_subs in tests:
        info = extract(None, cid)
        if info.error:
            print(f"  ERR {cid}: {info.error}")
            continue
        country_ok = EQUIV.get(info.country) == expected_country
        # ±10% tolerance for subscriber count
        subs_ok = info.subscribers and abs(info.subscribers - expected_subs) / expected_subs < 0.10
        mark = "✓" if country_ok and subs_ok else "✗"
        print(f"  {mark} {cid}  subs={info.subscribers!s:>10}  "
              f"country={info.country!s:>14}  expected={expected_country:>14}/{expected_subs:>9,}  "
              f"t1={info.stage1_s:.2f}s  t2={info.stage2_s:.2f}s")


if __name__ == "__main__":
    main()

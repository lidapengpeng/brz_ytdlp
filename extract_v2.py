"""Two-stage InnerTube extractor — v2 with:
  - configurable cookies-from-browser
  - visitor_data reuse across channels (single InnerTube identity)
  - youtubetab:skip=webpage to bypass HTML
  - structured per-call timing + bytes accounting + 429 detection
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import yt_dlp


# ----- data shapes -----

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
class ExtractorConfig:
    """Knobs you can dial."""
    use_cookies_from_chrome: bool = False
    fixed_visitor_data: Optional[str] = None  # pre-obtained or persisted
    player_client: Tuple[str, ...] = ("mweb",)
    skip_webpage: bool = True
    sleep_between_calls: float = 0.0
    label: str = "default"


# ----- helpers -----

_SUB_RE = re.compile(r"(\d[\d.,]*)\s*(thousand|millions?|million|mil|mi|bilhão|bilhões|billion|bi|m|k|b)?",
                     re.IGNORECASE)


def parse_count(text: str) -> Optional[int]:
    if not text:
        return None
    s = text.lower().replace("\xa0", " ").replace(",", "")
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


# ----- the extractor itself -----

def make_ydl(cfg: ExtractorConfig) -> yt_dlp.YoutubeDL:
    """Build a yt-dlp instance honouring the config."""
    ya = {
        "youtube": {
            "player_client": list(cfg.player_client),
            "player_skip": ["js"],
        },
    }
    if cfg.skip_webpage:
        ya["youtubetab"] = {"skip": ["webpage"]}
    if cfg.fixed_visitor_data:
        ya["youtube"]["visitor_data"] = [cfg.fixed_visitor_data]

    opts = {
        "quiet": True, "no_warnings": True,
        "skip_download": True,
        "socket_timeout": 30,
        "extractor_args": ya,
    }
    if cfg.use_cookies_from_chrome:
        # macOS: yt-dlp will read from ~/Library/Application Support/Google/Chrome/Default/Cookies
        opts["cookiesfrombrowser"] = ("chrome", None, None, None)
    return yt_dlp.YoutubeDL(opts)


def harvest_visitor_data(ydl: yt_dlp.YoutubeDL) -> Optional[str]:
    """Make a single InnerTube call to obtain a fresh visitor_data for later reuse."""
    ie = ydl.get_info_extractor("YoutubeTab")
    try:
        # Cheapest call: ytcfg — but yt-dlp's helper is _call_api which always needs a payload.
        # Use a tiny browse call (channel root for a well-known channel).
        resp = ie._call_api(ep="browse", video_id="seed",
                            query={"browseId": "UCBR8-60-B28hp2BmDPdntcQ"})  # YouTube's own channel, tiny seed
        vd = _find_first(resp, "visitorData")
        if isinstance(vd, str) and vd:
            return vd
    except Exception:
        return None
    return None


def extract(ydl: yt_dlp.YoutubeDL, channel_id: str) -> ChannelInfo:
    info = ChannelInfo(channel_id=channel_id)
    ie = ydl.get_info_extractor("YoutubeTab")

    # ---- Stage 1: channel page via InnerTube ----
    t0 = time.time()
    try:
        resp1 = ie._call_api(ep="browse", video_id=channel_id, query={"browseId": channel_id})
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
        resp2 = ie._call_api(ep="browse", video_id=channel_id, query={"continuation": token})
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


# ----- bulk runner -----

def run_batch(channels: List[str], cfg: ExtractorConfig, expected: dict = None) -> dict:
    """Sequentially extract a batch of channels and return aggregate stats."""
    expected = expected or {}
    ydl = make_ydl(cfg)

    # If user wanted visitor_data reuse but didn't provide one, harvest one
    if cfg.fixed_visitor_data is None and cfg.skip_webpage:
        # If skip_webpage and no visitor_data, yt-dlp may fail because the InnerTube
        # context has no client identity. Try harvesting one first.
        vd = harvest_visitor_data(ydl)
        if vd:
            print(f"  [{cfg.label}] harvested visitor_data: {vd[:32]}...")
            cfg.fixed_visitor_data = vd
            ydl = make_ydl(cfg)  # rebuild with the new vd

    results: list[ChannelInfo] = []
    blocks = 0
    errors = 0
    t_start = time.time()
    for i, cid in enumerate(channels):
        info = extract(ydl, cid)
        results.append(info)
        if info.error:
            errors += 1
            if "429" in info.error or "Too Many" in info.error:
                blocks += 1
        if cfg.sleep_between_calls > 0:
            time.sleep(cfg.sleep_between_calls)

    elapsed = time.time() - t_start

    ok = [r for r in results if not r.error]
    correct = [r for r in ok if expected.get(r.channel_id) and r.country == expected[r.channel_id]]
    bytes_total = sum(r.stage1_bytes + r.stage2_bytes for r in ok)
    stage1_s = sum(r.stage1_s for r in ok)
    stage2_s = sum(r.stage2_s for r in ok)
    return {
        "label": cfg.label,
        "channels": len(channels),
        "ok": len(ok),
        "errors": errors,
        "blocks": blocks,
        "correct_country": len(correct),
        "total_s": elapsed,
        "channels_per_s": len(ok) / max(0.001, elapsed),
        "avg_bytes": bytes_total / max(1, len(ok)),
        "avg_stage1_s": stage1_s / max(1, len(ok)),
        "avg_stage2_s": stage2_s / max(1, len(ok)),
        "results": results,
    }


# ----- the test plan -----

TEST_CHANNELS = [
    ("UCr4ARxgElIO21GWfIraZezg", "Brazil"),         # Garena Free Fire Brasil
    ("UCJ0-OtVpF0wOKEqT2Z1HEtA", "Canada"),         # ElectroBOOM
    ("UC295-Dw_tDNtZXFeAPAW6Aw", "United States"),  # 5-Minute Crafts
    ("UCY30JRSgfhYXA6i6xX1erWg", "United States"),  # Smosh
    ("UCFCUSOunpAQFpFl-M94sX_Q", "Brazil"),         # MONTORO
    # 5 more random Brazilian-ish channels (real channel ids picked at random)
    ("UCBjURrPoezykLs9EqgamOBg", None),
    ("UCnB-PDxnaYz5MIfUq_4Olnw", None),
    ("UC7e2PtnzVqEoEi-PR_n_iAQ", None),
    ("UCqYPhGiB9tkShZorfgcL2lA", None),
    ("UCx6V5RNZpb0R9_xa8DvR2-w", None),
]


def main():
    channels = [c for c, _ in TEST_CHANNELS]
    expected = {c: e for c, e in TEST_CHANNELS if e}

    print(f"yt-dlp {yt_dlp.version.__version__} — extract_v2 bulk-test\n")

    configs = [
        ExtractorConfig(label="A_baseline_mweb"),
        ExtractorConfig(label="B_skip_webpage_+_fresh_visitor",
                        skip_webpage=True),
        ExtractorConfig(label="C_chrome_cookies",
                        use_cookies_from_chrome=True),
        ExtractorConfig(label="D_chrome_cookies_+_visitor",
                        use_cookies_from_chrome=True,
                        skip_webpage=True),
    ]

    for cfg in configs:
        print(f"\n=== {cfg.label} ===")
        try:
            stats = run_batch(channels, cfg, expected)
        except Exception as e:
            print(f"   FATAL: {type(e).__name__}: {e}")
            continue
        print(f"   ok={stats['ok']}/{stats['channels']}  errors={stats['errors']}  blocks={stats['blocks']}"
              f"  country_correct={stats['correct_country']}/{len(expected)}")
        print(f"   total={stats['total_s']:.1f}s  rate={stats['channels_per_s']:.2f}/s"
              f"  avg_bytes={stats['avg_bytes']:,.0f}"
              f"  avg_stage1={stats['avg_stage1_s']:.2f}s  avg_stage2={stats['avg_stage2_s']:.2f}s")
        # Spot-check failures
        for r in stats["results"]:
            if r.error:
                print(f"     ERR {r.channel_id}: {r.error}")


if __name__ == "__main__":
    main()

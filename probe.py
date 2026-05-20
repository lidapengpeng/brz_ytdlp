"""Probe: validate the yt-dlp + mobile-client approach against known channels.

Goals:
  1. Confirm we can extract subscriber_count from yt-dlp's info_dict.
  2. Confirm we can extract country (NOT in default info_dict) via _call_api.
  3. Benchmark bandwidth + latency across player_client variants.
  4. Compare to the brazil700k aiohttp/HTML baseline (~2 MB per /about).

Test channels (manually chosen — covers BR + non-BR + edge cases):
  - UCr4ARxgElIO21GWfIraZezg   Garena Free Fire Brasil (BR, ~10M)
  - UCe2A3KAuxKbBM-uKgX4UA0w   Felipe Neto                (BR, ~46M)
  - UCJ0-OtVpF0wOKEqT2Z1HEtA   ElectroBOOM                (Canadá, ~6M)
  - UC295-Dw_tDNtZXFeAPAW6Aw   5-Minute Crafts            (EUA, ~80M)
  - UCY30JRSgfhYXA6i6xX1erWg   Smosh                      (EUA, ~26M)
"""
from __future__ import annotations

import json
import statistics
import time
from typing import Any, Optional

import yt_dlp


TEST_CHANNELS = [
    ("UCr4ARxgElIO21GWfIraZezg", "Garena Free Fire Brasil", "BR"),
    ("UCe2A3KAuxKbBM-uKgX4UA0w", "Felipe Neto",             "BR"),
    ("UCJ0-OtVpF0wOKEqT2Z1HEtA", "ElectroBOOM",             "CA"),
    ("UC295-Dw_tDNtZXFeAPAW6Aw", "5-Minute Crafts",         "US"),
    ("UCY30JRSgfhYXA6i6xX1erWg", "Smosh",                   "US"),
]

# Player clients to compare. Order matters: yt-dlp tries them left-to-right.
CLIENT_VARIANTS: dict[str, list[str]] = {
    "mweb":             ["mweb"],
    "ios":              ["ios"],
    "android_producer": ["android_producer"],
    "tv_embedded":      ["tv_embedded"],
    "web":              ["web"],                # baseline (most restricted)
    "fallback_chain":   ["mweb", "ios", "android_producer", "web"],
}


def make_ydl(player_clients: list[str]) -> yt_dlp.YoutubeDL:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",   # don't recurse into the channel's videos
        "extractor_args": {
            "youtube": {
                "player_client": player_clients,
                # Skip operations we don't need — saves time and request count
                "player_skip": ["js"],
            }
        },
        "socket_timeout": 30,
    }
    return yt_dlp.YoutubeDL(opts)


def extract_basic(ydl: yt_dlp.YoutubeDL, channel_id: str) -> dict[str, Any]:
    """Call yt-dlp's standard extractor — returns its normalised info_dict."""
    url = f"https://www.youtube.com/channel/{channel_id}/about"
    return ydl.extract_info(url, download=False, process=False) or {}


def extract_country_via_innertube(ydl: yt_dlp.YoutubeDL, channel_id: str) -> Optional[str]:
    """Use yt-dlp's underlying YoutubeTabIE._call_api to call /youtubei/v1/browse
    directly. Country lives under aboutChannelViewModel.country in the raw response
    — yt-dlp's standard info_dict doesn't expose it."""
    try:
        ie = ydl.get_info_extractor("YoutubeTab")
    except KeyError:
        ie = ydl.get_info_extractor("Youtube")
    # browseId = channel_id, params = the EgVhYm91dA encoded "About tab" pointer
    # (verified from real responses; this is what the browser sends when clicking About)
    try:
        resp = ie._call_api(
            ep="browse",
            video_id=channel_id,
            query={"browseId": channel_id, "params": "EgVhYm91dA%3D%3D"},
        )
    except Exception as e:
        return f"<API error: {type(e).__name__}: {e}>"

    # Walk for aboutChannelViewModel.country
    def find(node: Any, key: str) -> Optional[Any]:
        if isinstance(node, dict):
            if key in node:
                return node[key]
            for v in node.values():
                r = find(v, key)
                if r is not None:
                    return r
        elif isinstance(node, list):
            for x in node:
                r = find(x, key)
                if r is not None:
                    return r
        return None

    avm = find(resp, "aboutChannelViewModel")
    if isinstance(avm, dict):
        c = avm.get("country")
        if isinstance(c, str) and c.strip():
            return c.strip()
    return None


def probe_one(client_label: str, clients: list[str], channel_id: str) -> dict[str, Any]:
    ydl = make_ydl(clients)
    t0 = time.time()
    info: dict[str, Any] = {}
    err: Optional[str] = None
    try:
        info = extract_basic(ydl, channel_id)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    elapsed_info = time.time() - t0

    t1 = time.time()
    country = extract_country_via_innertube(ydl, channel_id) if not err else None
    elapsed_country = time.time() - t1

    return {
        "client": client_label,
        "channel_id": channel_id,
        "elapsed_info_s": round(elapsed_info, 2),
        "elapsed_country_s": round(elapsed_country, 2),
        "title": info.get("title") or info.get("channel"),
        "channel_follower_count": info.get("channel_follower_count"),
        "uploader": info.get("uploader"),
        "channel_url": info.get("channel_url"),
        "country": country,
        "error": err,
    }


def main() -> None:
    print(f"yt-dlp version: {yt_dlp.version.__version__}")
    print("=" * 80)

    # Per-channel matrix: one row per (client, channel)
    all_rows: list[dict[str, Any]] = []
    for client_label, clients in CLIENT_VARIANTS.items():
        print(f"\n[client={client_label}  internal_chain={clients}]")
        for cid, label, expected_country in TEST_CHANNELS:
            r = probe_one(client_label, clients, cid)
            all_rows.append({**r, "expected_country_guess": expected_country, "label": label})
            ok = r["channel_follower_count"] is not None and r["error"] is None
            err_marker = " ERR" if r["error"] else ("    " if ok else "   ?")
            country_str = r["country"] or "(no country)"
            print(
                f"  {err_marker}  {label[:28]:28s}  "
                f"subs={r['channel_follower_count']!s:>9s}  "
                f"country={country_str!s:>16s}  "
                f"t_info={r['elapsed_info_s']:5.2f}s  "
                f"t_country={r['elapsed_country_s']:5.2f}s"
                + (f"  err={r['error']}" if r["error"] else "")
            )

    # Aggregate
    print("\n" + "=" * 80)
    print("AGGREGATE")
    for client_label in CLIENT_VARIANTS:
        rows = [r for r in all_rows if r["client"] == client_label]
        ok_rows = [r for r in rows if r["error"] is None and r["channel_follower_count"] is not None]
        country_rows = [r for r in rows if r["country"] and not r["country"].startswith("<")]
        t_info = [r["elapsed_info_s"] for r in ok_rows]
        t_country = [r["elapsed_country_s"] for r in rows if not r["error"]]
        print(
            f"  {client_label:18s}  "
            f"info_ok={len(ok_rows)}/{len(rows)}  "
            f"country_ok={len(country_rows)}/{len(rows)}  "
            f"avg_t_info={statistics.mean(t_info):.2f}s "  if t_info else
            f"  {client_label:18s}  info_ok=0  "
        )
        # Re-print cleanly to avoid the conditional formatting glitch
    print()
    print("--- clean summary ---")
    for client_label in CLIENT_VARIANTS:
        rows = [r for r in all_rows if r["client"] == client_label]
        ok = [r for r in rows if r["error"] is None and r["channel_follower_count"] is not None]
        co = [r for r in rows if r["country"] and not str(r["country"]).startswith("<")]
        t_info = [r["elapsed_info_s"] for r in ok] or [0]
        t_country = [r["elapsed_country_s"] for r in rows if not r["error"]] or [0]
        print(f"  {client_label:18s}  info_ok={len(ok)}/{len(rows)}  "
              f"country_ok={len(co)}/{len(rows)}  "
              f"avg_t_info={statistics.mean(t_info):.2f}s  "
              f"avg_t_country={statistics.mean(t_country):.2f}s")


if __name__ == "__main__":
    main()

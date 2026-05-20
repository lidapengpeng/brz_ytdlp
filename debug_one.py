"""Debug: dump everything yt-dlp gives us for a single Brazilian channel,
then try several ways to extract country from the underlying InnerTube response."""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import yt_dlp

CHANNEL_ID = "UCr4ARxgElIO21GWfIraZezg"  # Garena Free Fire Brasil — known BR


def walk_find(node: Any, key: str, max_results: int = 5) -> list[tuple[str, Any]]:
    """DFS for a key; return up to max_results (path, value) tuples."""
    results: list[tuple[str, Any]] = []

    def visit(n: Any, path: str) -> None:
        if len(results) >= max_results:
            return
        if isinstance(n, dict):
            for k, v in n.items():
                if k == key:
                    results.append((f"{path}.{k}", v))
                    if len(results) >= max_results:
                        return
                visit(v, f"{path}.{k}")
        elif isinstance(n, list):
            for i, x in enumerate(n):
                if len(results) >= max_results:
                    return
                visit(x, f"{path}[{i}]")

    visit(node, "")
    return results


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    print(f"yt-dlp {yt_dlp.version.__version__}")
    print(f"channel: {CHANNEL_ID}")

    # ---------- Approach 1: vanilla extract_info ----------
    print("\n=== Approach 1: vanilla extract_info ===")
    ydl = yt_dlp.YoutubeDL({
        "quiet": True, "no_warnings": True, "skip_download": True,
        "extract_flat": "in_playlist",
        "extractor_args": {"youtube": {"player_client": ["mweb"], "player_skip": ["js"]}},
    })
    t0 = time.time()
    info = ydl.extract_info(f"https://www.youtube.com/channel/{CHANNEL_ID}/about",
                            download=False, process=False)
    t = time.time() - t0
    print(f"  elapsed: {t:.2f}s")
    print(f"  keys: {sorted(info.keys()) if isinstance(info, dict) else type(info)}")
    if isinstance(info, dict):
        # Print every scalar field
        for k in sorted(info.keys()):
            v = info[k]
            if isinstance(v, (str, int, float, bool)) or v is None:
                short = (v[:80] + '…') if isinstance(v, str) and len(v) > 80 else v
                print(f"    {k} = {short!r}")
        # Save full info for later inspection
        (out_dir / "info_dict.json").write_text(json.dumps(info, indent=2, default=str), encoding="utf-8")
        print(f"  -> wrote info_dict.json")
        # Look for country anywhere in the dict
        for path, val in walk_find(info, "country", 3):
            print(f"  found 'country' at: {path}  = {val!r}")
        for path, val in walk_find(info, "location", 3):
            print(f"  found 'location' at: {path}  = {val!r}")

    # ---------- Approach 2: _call_api directly ----------
    print("\n=== Approach 2: _call_api('browse', browseId+params) ===")
    ie = ydl.get_info_extractor("YoutubeTab")
    print(f"  extractor type: {type(ie).__name__}")
    print(f"  has _call_api: {hasattr(ie, '_call_api')}")
    try:
        t0 = time.time()
        # The "About" tab pointer; EgVhYm91dA== decodes to "about" in protobuf var-string
        # (different YouTube versions use different params strings; this one matches the
        #  desktop-web /about endpoint and works for all clients)
        resp = ie._call_api(
            ep="browse",
            video_id=CHANNEL_ID,
            query={"browseId": CHANNEL_ID, "params": "EgVhYm91dA%3D%3D"},
        )
        t = time.time() - t0
        print(f"  elapsed: {t:.2f}s")
        print(f"  response top-level keys: {list(resp.keys())[:20]}")
        # Save
        (out_dir / "innertube_browse.json").write_text(json.dumps(resp, indent=2, default=str), encoding="utf-8")
        print(f"  -> wrote innertube_browse.json ({len(json.dumps(resp))} bytes serialized)")
        # Hunt for country
        for path, val in walk_find(resp, "country", 5):
            short = (str(val)[:120] + '…') if len(str(val)) > 120 else val
            print(f"  found 'country' at: {path}  = {short!r}")
        for path, val in walk_find(resp, "aboutChannelViewModel", 2):
            if isinstance(val, dict):
                print(f"  aboutChannelViewModel at: {path}")
                print(f"    its country field: {val.get('country')!r}")
                print(f"    its subs field:    {val.get('subscriberCountText')!r}")
    except Exception as e:
        print(f"  _call_api FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()

    # ---------- Approach 3: ie._download_json (lower level) ----------
    print("\n=== Approach 3: _download_json to /youtubei/v1/browse ===")
    try:
        t0 = time.time()
        # _call_api signature (from yt-dlp source): _call_api(ep, query, video_id, fatal=True, headers=None, note=...)
        # The API key + context comes from the active player_client. Default 'web' will work.
        body = {
            "context": {
                "client": {
                    "clientName": "MWEB",
                    "clientVersion": "2.20240101.01.00",
                    "platform": "MOBILE",
                    "gl": "BR",
                    "hl": "pt-BR",
                },
            },
            "browseId": CHANNEL_ID,
            "params": "EgVhYm91dA==",
        }
        resp = ie._download_json(
            "https://www.youtube.com/youtubei/v1/browse",
            video_id=CHANNEL_ID,
            data=json.dumps(body).encode("utf-8"),
            headers={"content-type": "application/json"},
            query={"prettyPrint": "false"},
        )
        t = time.time() - t0
        print(f"  elapsed: {t:.2f}s")
        (out_dir / "innertube_browse_raw.json").write_text(json.dumps(resp, indent=2, default=str), encoding="utf-8")
        # Country search
        for path, val in walk_find(resp, "country", 5):
            short = (str(val)[:120] + '…') if len(str(val)) > 120 else val
            print(f"  found 'country' at: {path}  = {short!r}")
        avm_hits = walk_find(resp, "aboutChannelViewModel", 2)
        if avm_hits:
            for path, val in avm_hits:
                if isinstance(val, dict):
                    print(f"  aboutChannelViewModel at: {path}")
                    print(f"    country:           {val.get('country')!r}")
                    print(f"    subscriberCountText: {val.get('subscriberCountText')!r}")
                    print(f"    joinedDateText:    {val.get('joinedDateText')!r}")
        else:
            print("  NO aboutChannelViewModel found in response")
    except Exception as e:
        print(f"  _download_json FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()

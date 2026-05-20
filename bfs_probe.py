"""Probe what the /channels tab actually returns for known BR seeds.

Dumps the raw response so we can see what's there.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import yt_dlp
import random
from extract_v3 import generate_visitor_data, random_brazil_ip

def probe(channel_id, name):
    ydl = yt_dlp.YoutubeDL({
        "quiet": True, "no_warnings": True, "skip_download": True,
        "socket_timeout": 30,
        "geo_bypass": True, "geo_bypass_country": "BR",
        "extractor_args": {
            "youtube": {
                "player_client": ["web_safari"],   # use a consistent client for the probe
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
    ie = ydl.get_info_extractor("YoutubeTab")

    # Probe 1: /channels tab
    print(f"\n=== {name} ({channel_id}) ===")
    try:
        resp1 = ie._call_api(
            ep="browse", video_id=channel_id,
            query={"browseId": channel_id, "params": "EghjaGFubmVscw%3D%3D"},
        )
        # Inspect tabs
        tabs = resp1.get("contents",{}).get("twoColumnBrowseResultsRenderer",{}).get("tabs",[])
        print(f"  #tabs: {len(tabs)}")
        tab_titles = []
        for t in tabs:
            tr = t.get("tabRenderer", {})
            if tr:
                tab_titles.append(tr.get("title", "?"))
        print(f"  tab titles: {tab_titles}")

        # Look for selected tab content
        for t in tabs:
            tr = t.get("tabRenderer", {})
            if tr.get("selected"):
                print(f"  selected tab: {tr.get('title')}")
                content = tr.get("content", {})
                # Count various renderers in the tab
                def count_renderer(node, key, cnt=[0]):
                    if isinstance(node, dict):
                        if key in node: cnt[0] += 1
                        for v in node.values(): count_renderer(v, key, cnt)
                    elif isinstance(node, list):
                        for x in node: count_renderer(x, key, cnt)
                    return cnt[0]
                for k in ["channelRenderer", "gridChannelRenderer", "shelfRenderer", "channelListSubMenuAvatarRenderer", "elementRenderer", "horizontalListRenderer"]:
                    c = [0]; count_renderer(content, k, c)
                    if c[0]>0:
                        print(f"    {k}: {c[0]}")
        # Try alerts/error
        alerts = resp1.get("alerts", [])
        if alerts:
            print(f"  alerts: {alerts}")
        # Dump first 2000 chars of structure preview
        # print("  STRUCTURE PREVIEW:")
        # print(json.dumps(resp1, indent=1, ensure_ascii=False)[:3000])

    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")

    # Probe 2: home tab — featured channels live here
    print(f"  --- home tab (default browse, no params) ---")
    try:
        resp2 = ie._call_api(
            ep="browse", video_id=channel_id,
            query={"browseId": channel_id},
        )
        tabs = resp2.get("contents",{}).get("twoColumnBrowseResultsRenderer",{}).get("tabs",[])
        print(f"  home #tabs: {len(tabs)}")
        for t in tabs:
            tr = t.get("tabRenderer", {})
            title = tr.get("title", "?")
            endpoint = tr.get("endpoint", {})
            params_ = endpoint.get("browseEndpoint", {}).get("params", "")
            sel = " (selected)" if tr.get("selected") else ""
            print(f"    {title}{sel} params={params_}")

        # Look for featured channels in shelfRenderer
        def find_shelves(node, out=None):
            if out is None: out = []
            if isinstance(node, dict):
                if "shelfRenderer" in node:
                    sr = node["shelfRenderer"]
                    title = sr.get("title", {})
                    title_text = title.get("simpleText", "") if isinstance(title, dict) else ""
                    if not title_text:
                        runs = title.get("runs", []) if isinstance(title, dict) else []
                        title_text = "".join(r.get("text","") for r in runs if isinstance(r, dict))
                    out.append(title_text)
                for v in node.values(): find_shelves(v, out)
            elif isinstance(node, list):
                for x in node: find_shelves(x, out)
            return out
        shelves = find_shelves(resp2)
        if shelves:
            print(f"  home shelves: {shelves[:10]}")

        # Count featured channel renderers in the home content
        def count_renderer(node, key, cnt=[0]):
            if isinstance(node, dict):
                if key in node: cnt[0] += 1
                for v in node.values(): count_renderer(v, key, cnt)
            elif isinstance(node, list):
                for x in node: count_renderer(x, key, cnt)
            return cnt[0]
        for k in ["channelRenderer", "gridChannelRenderer", "channelFeaturedContentRenderer"]:
            c = [0]; count_renderer(resp2, k, c)
            if c[0]>0:
                print(f"    home {k}: {c[0]}")
    except Exception as e:
        print(f"  HOME ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    # PDF cited
    test_channels = [
        ("UCr4ARxgElIO21GWfIraZezg", "Garena FF Brasil (10M)"),
        ("UCJ0-OtVpF0wOKEqT2Z1HEtA", "ElectroBOOM (non-BR)"),
        ("UCTl3QQTvqHFjurroKxexy2Q", "Olympics (16M)"),
        ("UCBR8-60-B28hp2BmDPdntcQ", "YouTube"),
        ("UCCgr0Hp8Rs0ynVD2tjXFnIQ", "Cortes do Mylon (166K BR)"),
        ("UCtzeHEIagYykh_TuwjAS6kA", "IMPERA (215K BR)"),
    ]
    for cid, name in test_channels:
        probe(cid, name)

"""Test B: YouTube Music BR explore — try FEmusic_* browse_ids + WEB_REMIX client."""
import time, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/Users/dapeng/Desktop/word/brz_ytdlp")
import yt_dlp
from extract_v3 import generate_visitor_data, random_brazil_ip
from _bfs_v2_helpers import load_known_ids, extract_all_cids, find_all_renderers, dump_json

print("=" * 70)
print("Test B: YouTube Music BR exploration")
print("=" * 70)

known = load_known_ids()
print(f"loaded {len(known)} known_ids\n")

# WEB_REMIX is the Music client. Try via yt-dlp's web_music
def make_music_ydl():
    return yt_dlp.YoutubeDL({
        "quiet": True, "no_warnings": True, "skip_download": True,
        "socket_timeout": 30,
        "geo_bypass": True, "geo_bypass_country": "BR",
        "extractor_args": {
            "youtube": {
                "player_client": ["web_music"],   # yt-dlp's WEB_REMIX
                "player_skip": ["js", "configs"],
                "visitor_data": [generate_visitor_data()],
            },
        },
        "http_headers": {
            "Accept-Language": "pt-BR,pt;q=0.9",
            "X-Forwarded-For": random_brazil_ip(),
            "Origin": "https://music.youtube.com",
            "Referer": "https://music.youtube.com/",
        },
    })

# Music browse_ids to try
MUSIC_IDS = [
    "FEmusic_home",
    "FEmusic_charts",
    "FEmusic_explore",
    "FEmusic_new_releases",
    "FEmusic_moods_and_genres",
    "FEmusic_trending",
    "FEmusic_listen_again",
    "FEmusic_library_landing",
    "FEmusic_top_charts",
    "FEmusic_hotlist",
]

results = {}
all_cids = set()
for bid in MUSIC_IDS:
    ydl = make_music_ydl()
    try:
        ie = ydl.get_info_extractor("YoutubeTab")
        t0 = time.time()
        # Try with default_client to force music client
        resp = ie._call_api(ep="browse", video_id="seed",
                           query={"browseId": bid},
                           default_client="web_music")
        ms = int((time.time()-t0)*1000)
        cids_this = extract_all_cids(resp)
        # Filter to UC* with 24 chars (proper channelIds)
        cids_this = {c for c in cids_this if len(c) >= 24 and c.startswith("UC")}
        new_this = cids_this - known
        results[bid] = {
            "http": 200, "ms": ms, "size_bytes": len(json.dumps(resp)),
            "cids_total": len(cids_this), "cids_new": len(new_this),
            "sample_new": list(new_this)[:10],
        }
        all_cids.update(cids_this)
        print(f"  {bid:35s}  {ms}ms  total={len(cids_this)} new={len(new_this)}")
    except Exception as e:
        err_str = str(e)
        status = "?"
        if "400" in err_str: status = 400
        elif "404" in err_str: status = 404
        elif "403" in err_str: status = 403
        results[bid] = {"http": status, "err": f"{type(e).__name__}: {err_str[:80]}"}
        print(f"  {bid:35s}  ✗ HTTP {status}: {err_str[:50]}")
    finally:
        try: ydl.close()
        except: pass

# Music search test
print("\n--- Music search test ---")
for query in ["funk brasileiro", "sertanejo", "mpb", "samba"]:
    ydl = make_music_ydl()
    try:
        ie = ydl.get_info_extractor("YoutubeTab")
        t0 = time.time()
        resp = ie._call_api(ep="search", video_id="seed",
                           query={"query": query, "params": "Eg-KAQwIABAAGAAgACgAMABqChAEEAUQAxAKEAk%3D"},  # music filter
                           default_client="web_music")
        ms = int((time.time()-t0)*1000)
        cids_this = extract_all_cids(resp)
        cids_this = {c for c in cids_this if len(c) >= 24 and c.startswith("UC")}
        new_this = cids_this - known
        results[f"search:{query}"] = {
            "ms": ms, "cids_total": len(cids_this), "cids_new": len(new_this),
            "sample_new": list(new_this)[:5],
        }
        all_cids.update(cids_this)
        print(f"  '{query:25s}'  {ms}ms  total={len(cids_this)} new={len(new_this)}")
    except Exception as e:
        results[f"search:{query}"] = {"err": f"{type(e).__name__}: {str(e)[:60]}"}
        print(f"  '{query:25s}'  ✗ {type(e).__name__}")
    finally:
        try: ydl.close()
        except: pass

new_total = all_cids - known
print(f"\n--- Aggregate ---")
print(f"  Total unique cids across all music endpoints: {len(all_cids)}")
print(f"  New (not in DB):                              {len(new_total)}")

results["_aggregate"] = {
    "total_cids": len(all_cids),
    "new_cids": len(new_total),
    "new_sample_50": list(new_total)[:50],
    "verdict": ("WORTH adding music discovery" if len(new_total) >= 50
                else "MARGINAL" if len(new_total) >= 10
                else "NOT WORTH"),
}
dump_json(os.path.join(os.path.dirname(__file__), "test_B_youtube_music_results.json"), results)
print(f"\nresults dumped → test_B_youtube_music_results.json")

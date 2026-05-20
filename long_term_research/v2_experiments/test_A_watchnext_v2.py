"""Test A v2: watchEndpoint Up-Next mining — FIXED for new lockupViewModel layout.

The 2024+ YouTube web layout dropped compactVideoRenderer in favor of lockupViewModel.
Up-next sidebar lives at: contents.twoColumnWatchNextResults.secondaryResults.secondaryResults.results[*].lockupViewModel
"""
import time, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/Users/dapeng/Desktop/word/brz_ytdlp")
import yt_dlp
from extract_v3 import generate_visitor_data, random_brazil_ip
from _bfs_v2_helpers import pick_seeds, load_known_ids, find_all_renderers, extract_all_cids, dump_json

print("=" * 70)
print("Test A v2: watchEndpoint Up-Next mining (FIXED for lockupViewModel)")
print("=" * 70)

known = load_known_ids()
seeds = pick_seeds("huge", n=5)
print(f"5 huge BR seeds: {seeds}\n")

def make_web_ydl():
    return yt_dlp.YoutubeDL({
        "quiet": True, "no_warnings": True, "skip_download": True,
        "socket_timeout": 30,
        "geo_bypass": True, "geo_bypass_country": "BR",
        "extractor_args": {
            "youtube": {"player_client": ["web_safari"], "player_skip": ["js","configs"],
                       "visitor_data": [generate_visitor_data()]},
            "youtubetab": {"skip": ["webpage"]},
        },
        "http_headers": {
            "Accept-Language": "pt-BR,pt;q=0.9",
            "X-Forwarded-For": random_brazil_ip(),
            "Cookie": "PREF=hl=pt&gl=BR&tz=America%2FSao_Paulo; SOCS=CAI",
        },
    })

VIDEOS_TAB_PARAMS = "EgZ2aWRlb3M%3D"
results = {}
total_new_cids = set()
api_calls_total = 0

for seed in seeds:
    print(f"\n=== seed {seed} ===")
    seed_new_cids = set()
    api_calls = 0
    # Step 1: videos tab
    ydl = make_web_ydl()
    try:
        ie = ydl.get_info_extractor("YoutubeTab")
        t0 = time.time()
        resp = ie._call_api(ep="browse", video_id=seed,
                          query={"browseId": seed, "params": VIDEOS_TAB_PARAMS},
                          default_client="web_safari")
        ms_browse = int((time.time()-t0)*1000)
        api_calls += 1
        # Extract video IDs (new layout uses richItemRenderer too)
        video_ids = []
        vrs = find_all_renderers(resp, "videoRenderer")
        gvrs = find_all_renderers(resp, "gridVideoRenderer")
        rirs = find_all_renderers(resp, "richItemRenderer")
        for rir in rirs:
            inner = rir.get("content", {}).get("videoRenderer")
            if inner: vrs.append(inner)
        for vr in vrs + gvrs:
            vid = vr.get("videoId")
            if vid and vid not in video_ids:
                video_ids.append(vid)
        # 新 layout: 视频 ID 也可能在 lockupViewModel 里
        lvms_v = find_all_renderers(resp, "lockupViewModel")
        for lvm in lvms_v:
            content_id = lvm.get("contentId")
            if content_id and len(content_id) == 11 and content_id not in video_ids:
                video_ids.append(content_id)
        print(f"  videos tab: {ms_browse}ms, found {len(video_ids)} videos")
    except Exception as e:
        print(f"  videos tab ✗: {type(e).__name__}: {str(e)[:60]}")
        results[seed] = {"err": "videos tab failed"}
        continue
    finally:
        try: ydl.close()
        except: pass

    if not video_ids:
        print(f"  No videos for {seed}, skipping")
        results[seed] = {"err": "no videos"}
        continue

    # Step 2: call /next on top 5 videos
    per_video = []
    for vid in video_ids[:5]:
        ydl = make_web_ydl()
        try:
            ie = ydl.get_info_extractor("YoutubeTab")
            t0 = time.time()
            n_resp = ie._call_api(ep="next", video_id=vid,
                                  query={"videoId": vid},
                                  default_client="web_safari")
            ms_next = int((time.time()-t0)*1000)
            api_calls += 1
            # Extract from secondaryResults branch
            try:
                sec = n_resp["contents"]["twoColumnWatchNextResults"]["secondaryResults"]["secondaryResults"]["results"]
            except (KeyError, TypeError):
                sec = []

            # Method 1: lockupViewModel 显式路径
            owners_lvm = set()
            for entry in sec:
                lvm = entry.get("lockupViewModel") if isinstance(entry, dict) else None
                if not lvm: continue
                # decoratedAvatarViewModel 路径
                try:
                    cid = (lvm["metadata"]["lockupMetadataViewModel"]["image"]
                           ["decoratedAvatarViewModel"]["rendererContext"]
                           ["commandContext"]["onTap"]["innertubeCommand"]
                           ["browseEndpoint"]["browseId"])
                    if cid and cid.startswith("UC"):
                        owners_lvm.add(cid)
                except (KeyError, TypeError):
                    pass

            # Method 2: 整段 secondaryResults 抽所有 UC* (兜底)
            owners_brute = extract_all_cids(sec) if sec else set()
            owners_brute = {c for c in owners_brute if len(c) >= 24 and c.startswith("UC")}

            owners = owners_lvm | owners_brute
            owners.discard(seed)
            new_owners = owners - known
            seed_new_cids |= new_owners
            per_video.append({
                "video": vid, "ms": ms_next, "sec_count": len(sec),
                "owners_lvm": len(owners_lvm), "owners_brute": len(owners_brute),
                "owners_union": len(owners), "new": len(new_owners),
            })
            print(f"    video {vid}: {ms_next}ms, sec_count={len(sec)}, "
                  f"owners {len(owners)} ({len(new_owners)} new)")
        except Exception as e:
            print(f"    video {vid} ✗: {type(e).__name__}: {str(e)[:50]}")
        finally:
            try: ydl.close()
            except: pass

    api_calls_total += api_calls
    total_new_cids |= seed_new_cids
    results[seed] = {
        "videos_in_tab": len(video_ids),
        "videos_tested": min(5, len(video_ids)),
        "new_cids_for_seed": len(seed_new_cids),
        "api_calls": api_calls,
        "per_video": per_video,
        "sample_new": list(seed_new_cids)[:10],
    }
    print(f"  → seed total: {len(seed_new_cids)} new cids from {api_calls} API calls")

print(f"\n=== Aggregate ===")
print(f"  Seeds tested: 5")
print(f"  Total new cids: {len(total_new_cids)}")
print(f"  Avg new/seed: {len(total_new_cids)/5:.1f}")
print(f"  API calls: {api_calls_total}")
print(f"  Yield per call: {len(total_new_cids)/max(1,api_calls_total):.2f}")
print(f"\n  vs v1 BFS gridChannel (huge seed): 3.25 new/seed")
print(f"  Test A boost: {(len(total_new_cids)/5)/3.25:.2f}x")

results["_aggregate"] = {
    "seeds_tested": 5,
    "total_new_cids": len(total_new_cids),
    "avg_new_per_seed": len(total_new_cids) / 5,
    "api_calls_total": api_calls_total,
    "yield_per_call": len(total_new_cids) / max(1, api_calls_total),
    "vs_v1_bfs_boost": (len(total_new_cids) / 5) / 3.25,
    "verdict": ("EXCELLENT" if len(total_new_cids) >= 50
                else "WORTH at scale" if len(total_new_cids) >= 25
                else "MARGINAL" if len(total_new_cids) >= 10
                else "NOT WORTH"),
    "sample_new_50": list(total_new_cids)[:50],
}
dump_json(os.path.join(os.path.dirname(__file__), "test_A_watchnext_v2_results.json"), results)
print(f"\nresults → test_A_watchnext_v2_results.json")

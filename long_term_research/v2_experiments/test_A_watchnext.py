"""Test A: watchEndpoint "Up Next" mining.

Hypothesis: video.next response's secondaryResults.results[*].compactVideoRenderer
exposes ALGORITHM-curated recommended videos. Their owners form a different cid
pool than gridChannelRenderer (which is owner-curated).
"""
import time, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bfs_v2_helpers import make_ydl, pick_seeds, load_known_ids, find_all_renderers, dump_json

print("=" * 70)
print("Test A: watchEndpoint Up-Next mining")
print("=" * 70)

known = load_known_ids()
seeds = pick_seeds("huge", n=5)
print(f"5 huge BR seeds: {seeds}\n")

VIDEOS_TAB_PARAMS = "EgZ2aWRlb3M%3D"  # base64 for "videos" — the videos tab

results = {}
total_new_cids = set()

for seed in seeds:
    print(f"\n=== seed {seed} ===")
    seed_new_cids = set()
    api_calls = 0

    # Step 1: get top videos from this channel's videos tab
    ydl = make_ydl("tv")
    try:
        ie = ydl.get_info_extractor("YoutubeTab")
        t0 = time.time()
        resp = ie._call_api(ep="browse", video_id=seed,
                          query={"browseId": seed, "params": VIDEOS_TAB_PARAMS})
        ms_browse = int((time.time()-t0)*1000)
        api_calls += 1
        # Extract video IDs from richItemRenderer.content.videoRenderer or gridVideoRenderer
        video_ids = []
        vrs = find_all_renderers(resp, "videoRenderer")
        gvrs = find_all_renderers(resp, "gridVideoRenderer")
        # richItemRenderer is for the new layout
        rirs = find_all_renderers(resp, "richItemRenderer")
        for rir in rirs:
            inner = rir.get("content", {}).get("videoRenderer")
            if inner: vrs.append(inner)
        for vr in vrs + gvrs:
            vid = vr.get("videoId")
            if vid and vid not in video_ids:
                video_ids.append(vid)
        print(f"  videos tab: {ms_browse}ms, found {len(video_ids)} videos")
    except Exception as e:
        print(f"  videos tab ✗: {type(e).__name__}: {str(e)[:50]}")
        results[seed] = {"err": f"videos tab failed"}
        continue
    finally:
        try: ydl.close()
        except: pass

    if not video_ids:
        print(f"  No videos for {seed}, skipping")
        results[seed] = {"err": "no videos in videos tab", "video_ids": 0}
        continue

    # Step 2: call /next on top 5 videos, harvest up-next channels
    per_video_yields = []
    for vid in video_ids[:5]:
        ydl = make_ydl("tv")
        try:
            ie = ydl.get_info_extractor("YoutubeTab")
            t0 = time.time()
            n_resp = ie._call_api(ep="next", video_id=vid,
                                  query={"videoId": vid})
            ms_next = int((time.time()-t0)*1000)
            api_calls += 1

            # Extract owner cids from secondaryResults's compactVideoRenderer
            compacts = find_all_renderers(n_resp, "compactVideoRenderer")
            owners = set()
            for cv in compacts:
                # owner is in shortBylineText.runs[0].navigationEndpoint.browseEndpoint.browseId
                runs = cv.get("shortBylineText", {}).get("runs", [])
                if runs and isinstance(runs[0], dict):
                    cid = runs[0].get("navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId")
                    if cid and cid.startswith("UC"):
                        owners.add(cid)
                # also longBylineText
                runs = cv.get("longBylineText", {}).get("runs", [])
                if runs and isinstance(runs[0], dict):
                    cid = runs[0].get("navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId")
                    if cid and cid.startswith("UC"):
                        owners.add(cid)

            owners.discard(seed)
            new_owners = owners - known
            seed_new_cids |= new_owners
            per_video_yields.append({
                "video_id": vid, "ms": ms_next, "compacts": len(compacts),
                "unique_owners": len(owners), "new_owners": len(new_owners),
            })
            print(f"    video {vid}: {ms_next}ms, {len(compacts)} up-next compacts, "
                  f"{len(owners)} owners, {len(new_owners)} new")
        except Exception as e:
            print(f"    video {vid} ✗: {type(e).__name__}: {str(e)[:50]}")
        finally:
            try: ydl.close()
            except: pass

    total_new_cids |= seed_new_cids
    results[seed] = {
        "videos_in_tab": len(video_ids),
        "videos_tested": min(5, len(video_ids)),
        "new_cids_for_seed": len(seed_new_cids),
        "api_calls": api_calls,
        "per_video": per_video_yields,
        "sample_new": list(seed_new_cids)[:10],
    }
    print(f"  → seed total: {len(seed_new_cids)} new cids from {api_calls} API calls")

print(f"\n=== Aggregate ===")
print(f"  5 seeds × ~5 videos/seed × ~20 up-next per video = ~500 candidate pool")
print(f"  Total new cids:  {len(total_new_cids)}")
print(f"  Avg new/seed:    {len(total_new_cids)/5:.1f}")
api_calls_total = sum(r.get("api_calls", 0) for r in results.values() if isinstance(r, dict))
print(f"  Total API calls: {api_calls_total}")
print(f"  Yield per call:  {len(total_new_cids)/max(1, api_calls_total):.2f} new cid/call")

# Compare against v1 BFS gridChannel: 3.25 new/huge seed
print(f"\n  vs v1 BFS gridChannel:  3.25 new cid / huge seed")
print(f"  Test A boost:           {(len(total_new_cids)/5)/3.25:.2f}x")

results["_aggregate"] = {
    "seeds_tested": 5,
    "total_new_cids": len(total_new_cids),
    "avg_new_per_seed": len(total_new_cids) / 5,
    "total_api_calls": api_calls_total,
    "yield_per_call": len(total_new_cids) / max(1, api_calls_total),
    "vs_v1_bfs_boost": (len(total_new_cids) / 5) / 3.25,
    "verdict": ("EXCELLENT — adopt as second BFS strategy"
                if len(total_new_cids) >= 50
                else "WORTH at scale" if len(total_new_cids) >= 25
                else "MARGINAL" if len(total_new_cids) >= 10
                else "NOT WORTH"),
    "sample_new_50": list(total_new_cids)[:50],
}
dump_json(os.path.join(os.path.dirname(__file__), "test_A_watchnext_results.json"), results)
print(f"\nresults dumped → test_A_watchnext_results.json")

"""Test G: Playlist collaborators — find playlists in channel home, extract owners."""
import time, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bfs_v2_helpers import make_ydl, pick_seeds, load_known_ids, find_all_renderers, dump_json

print("=" * 70)
print("Test G: Playlist Collaborator Discovery")
print("=" * 70)

known = load_known_ids()
seeds = pick_seeds("huge", n=5)
print(f"5 huge BR seeds: {seeds}\n")

results = {}
total_new_cids = set()

for seed in seeds:
    print(f"\n=== seed {seed} ===")
    ydl = make_ydl("tv")
    try:
        ie = ydl.get_info_extractor("YoutubeTab")
        # Step 1: home tab → find playlists
        t0 = time.time()
        resp = ie._call_api(ep="browse", video_id=seed, query={"browseId": seed})
        ms1 = int((time.time()-t0)*1000)

        playlist_renderers = find_all_renderers(resp, "playlistRenderer")
        grid_playlists = find_all_renderers(resp, "gridPlaylistRenderer")
        lockup_view = find_all_renderers(resp, "lockupViewModel")  # newer layout

        playlist_ids = []
        for pr in playlist_renderers + grid_playlists:
            pid = pr.get("playlistId")
            if pid: playlist_ids.append(pid)
        # lockup view model has different structure
        for lv in lockup_view:
            content_id = lv.get("contentId")
            if content_id and content_id.startswith("PL"):
                playlist_ids.append(content_id)

        print(f"  home tab browse: {ms1}ms")
        print(f"  playlistRenderer count: {len(playlist_renderers)}")
        print(f"  gridPlaylistRenderer count: {len(grid_playlists)}")
        print(f"  lockupViewModel count: {len(lockup_view)}")
        print(f"  total playlist IDs: {len(playlist_ids)}")

        # Step 2: for each playlist (cap at 3 per seed for cost), get its videos and owners
        new_cids_for_seed = set()
        n_video_calls = 0
        for pid in playlist_ids[:3]:
            ydl2 = make_ydl("tv")
            try:
                ie2 = ydl2.get_info_extractor("YoutubeTab")
                t1 = time.time()
                p_resp = ie2._call_api(ep="browse", video_id=pid, query={"browseId": "VL" + pid})
                ms2 = int((time.time()-t1)*1000)
                # Playlist videos: playlistVideoRenderer
                videos = find_all_renderers(p_resp, "playlistVideoRenderer")
                # Extract owner channel from each video
                video_owners = set()
                for v in videos:
                    runs = v.get("shortBylineText", {}).get("runs", [])
                    if runs and isinstance(runs[0], dict):
                        cid = runs[0].get("navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId")
                        if cid and cid.startswith("UC"):
                            video_owners.add(cid)
                video_owners.discard(seed)
                new_owners = video_owners - known
                new_cids_for_seed.update(new_owners)
                print(f"    playlist {pid[:20]}: {ms2}ms, {len(videos)} videos, "
                      f"{len(video_owners)} owners, {len(new_owners)} new")
                n_video_calls += 1
            except Exception as e:
                print(f"    playlist {pid[:20]}: ✗ {type(e).__name__}")
            finally:
                try: ydl2.close()
                except: pass

        new_cids_for_seed -= known
        total_new_cids |= new_cids_for_seed
        results[seed] = {
            "n_playlists": len(playlist_ids),
            "n_playlists_tested": min(3, len(playlist_ids)),
            "new_cids_found": len(new_cids_for_seed),
            "sample_new": list(new_cids_for_seed)[:10],
            "n_video_calls": n_video_calls,
        }
        print(f"  TOTAL new cids from {seed}: {len(new_cids_for_seed)}")
    except Exception as e:
        results[seed] = {"err": f"{type(e).__name__}: {str(e)[:50]}"}
        print(f"  ✗ {type(e).__name__}: {str(e)[:50]}")
    finally:
        try: ydl.close()
        except: pass

print(f"\n=== Aggregate ===")
print(f"  Total new cids across 5 seeds × ~3 playlists each: {len(total_new_cids)}")
print(f"  Avg new/seed: {len(total_new_cids)/5:.1f}")
print(f"  API cost: ~1 home browse + ~3 playlist browse per seed = ~20 calls/5seeds")

results["_aggregate"] = {
    "seeds_tested": 5,
    "playlists_tested_total": sum(s.get("n_playlists_tested", 0) for s in results.values() if isinstance(s, dict)),
    "total_new_cids": len(total_new_cids),
    "avg_new_per_seed": len(total_new_cids) / 5,
    "verdict": "WORTH adding" if len(total_new_cids) >= 25
               else "MARGINAL" if len(total_new_cids) >= 5
               else "NOT WORTH",
}
dump_json(os.path.join(os.path.dirname(__file__), "test_G_playlist_collab_results.json"), results)
print(f"\nresults dumped → test_G_playlist_collab_results.json")

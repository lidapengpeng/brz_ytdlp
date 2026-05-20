"""Test C v2: depth-2 BFS — FIXED to read v1 dump structure correctly."""
import time, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bfs_v2_helpers import make_ydl, load_known_ids, find_all_renderers, dump_json

print("=" * 70)
print("Test C v2: BFS depth-2 decay curve (FIXED)")
print("=" * 70)

known = load_known_ids()
print(f"loaded {len(known)} known_ids\n")

# Load v1 BFS-discovered cids
v1_dump_path = "/Users/dapeng/Desktop/word/brz_ytdlp/bfs_validate_new_results.json"
with open(v1_dump_path) as f:
    v1_data = json.load(f)

# Real structure: {"results": [{"cid": "...", "is_target": True, ...}, ...]}
v1_records = v1_data.get("results", [])
print(f"v1 dump has {len(v1_records)} validated records")

# Filter: keep only is_target=True ones (BR confirmed eligibles)
depth1_eligible = [
    r for r in v1_records
    if r.get("is_target") and not r.get("error") and (r.get("subs") or 0) >= 10000
]
print(f"v1 eligible BR cids (>= 10K subs, no errors): {len(depth1_eligible)}\n")

# Use these as depth-2 seeds
depth2_seeds = [r["cid"] for r in depth1_eligible]
print(f"Running BFS gridChannel on {len(depth2_seeds)} depth-2 seeds...")

per_seed = {}
total_d2_new = set()

for i, seed in enumerate(depth2_seeds, 1):
    ydl = make_ydl("tv")
    try:
        ie = ydl.get_info_extractor("YoutubeTab")
        t0 = time.time()
        resp = ie._call_api(ep="browse", video_id=seed, query={"browseId": seed})
        ms = int((time.time()-t0)*1000)
        cids = set()
        for r in find_all_renderers(resp, "gridChannelRenderer"):
            c = r.get("channelId")
            if c and c.startswith("UC"): cids.add(c)
        for r in find_all_renderers(resp, "channelRenderer"):
            c = r.get("channelId")
            if c and c.startswith("UC"): cids.add(c)
        cids.discard(seed)
        new_cids = cids - known
        total_d2_new |= new_cids
        per_seed[seed] = {
            "total_cids": len(cids), "new_cids": len(new_cids), "ms": ms,
            "sample_new": list(new_cids)[:5],
        }
        print(f"  [{i:>2d}/{len(depth2_seeds)}] {seed}: {ms}ms, {len(cids)} cids, {len(new_cids)} new")
    except Exception as e:
        per_seed[seed] = {"err": f"{type(e).__name__}: {str(e)[:50]}"}
        print(f"  [{i:>2d}/{len(depth2_seeds)}] {seed}: ✗ {type(e).__name__}")
    finally:
        try: ydl.close()
        except: pass

ok_seeds = [s for s in per_seed.values() if "err" not in s]
total_total = sum(s.get("total_cids", 0) for s in ok_seeds)
total_new = sum(s.get("new_cids", 0) for s in ok_seeds)
avg_new = total_new / max(1, len(ok_seeds))

print(f"\n=== Aggregate (depth-2 BFS) ===")
print(f"  Seeds OK: {len(ok_seeds)}/{len(depth2_seeds)}")
print(f"  Avg cids returned/seed: {total_total/max(1,len(ok_seeds)):.2f}")
print(f"  Avg new/seed:           {avg_new:.2f}")
print(f"  Total UNIQUE new cids:  {len(total_d2_new)}")
print(f"\n  v1 depth-1 baseline (huge seed): 3.25 new/seed")
print(f"  v1 depth-1 baseline (mid seed):  1.60 new/seed")
print(f"  depth-2 vs depth-1 (huge):       {avg_new/3.25*100:.1f}% retention")
print(f"  depth-2 vs depth-1 (mid):        {avg_new/1.60*100:.1f}% retention")

results = {
    "depth2_seeds_count": len(depth2_seeds),
    "ok_seeds": len(ok_seeds),
    "avg_total_cids_per_seed": total_total / max(1, len(ok_seeds)),
    "avg_new_per_seed": avg_new,
    "total_unique_new": len(total_d2_new),
    "decay_vs_depth1_huge": avg_new / 3.25,
    "decay_vs_depth1_mid": avg_new / 1.60,
    "per_seed": per_seed,
    "verdict": ("WORTH multi-depth" if avg_new >= 2.0
                else "MARGINAL" if avg_new >= 1.0
                else "DECAY too strong, stop at depth-1"),
    "sample_new_30": list(total_d2_new)[:30],
}
dump_json(os.path.join(os.path.dirname(__file__), "test_C_depth2_v2_results.json"), results)
print(f"\nresults → test_C_depth2_v2_results.json")

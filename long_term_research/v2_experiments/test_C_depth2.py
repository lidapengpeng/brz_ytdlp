"""Test C: BFS depth-2 — use v1 depth-1 discovered cids as new seeds.

Question: does running BFS on the NEW cids found by depth-1 still produce
worthwhile new yield? Hypothesis: 50% decay (since BR cluster is closed)."""
import time, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bfs_v2_helpers import make_ydl, load_known_ids, find_all_renderers, dump_json

print("=" * 70)
print("Test C: BFS depth-2 decay curve")
print("=" * 70)

known = load_known_ids()
print(f"loaded {len(known)} known_ids\n")

# Load v1 BFS-discovered cids from bfs_validate_new_results.json
v1_dump_path = "/Users/dapeng/Desktop/word/brz_ytdlp/bfs_validate_new_results.json"
try:
    with open(v1_dump_path) as f:
        v1_results = json.load(f)
    # v1_results structure: list of dicts with channel_id and validation outcome
    if isinstance(v1_results, list):
        depth1_cids = [r.get("channel_id") for r in v1_results if isinstance(r, dict) and r.get("channel_id")]
    elif isinstance(v1_results, dict):
        depth1_cids = list(v1_results.keys())
    else:
        depth1_cids = []
except Exception as e:
    print(f"could not load v1 dump: {type(e).__name__}: {e}")
    depth1_cids = []

print(f"v1 depth-1 cids available: {len(depth1_cids)}")
print(f"sample: {depth1_cids[:5]}")

if len(depth1_cids) == 0:
    print("\nFalling back to: pick a random sample of BR channels found in last 24h as depth-2 seeds")
    import sqlite3
    conn = sqlite3.connect("/Users/dapeng/Desktop/word/brz_ytdlp/results.db")
    rows = conn.execute("""
        SELECT channel_id FROM channels
        WHERE is_target=1 AND country IN ('Brazil','Brasil')
          AND subscribers >= 50000
          AND discovered_at > strftime('%s', 'now', '-24 hours')
        ORDER BY RANDOM() LIMIT 20
    """).fetchall()
    depth1_cids = [r[0] for r in rows]
    conn.close()
    print(f"using {len(depth1_cids)} recently-found BR cids as depth-2 seeds")

# Filter depth-1 cids to only valid UC* (some entries may be invalid)
depth1_cids = [c for c in depth1_cids if c and isinstance(c, str) and c.startswith("UC")]
# Limit to 20 for cost
depth2_seeds = depth1_cids[:20]
print(f"\nRunning BFS gridChannel on {len(depth2_seeds)} depth-2 seeds...")

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

# Aggregate
ok_seeds = [s for s in per_seed.values() if "err" not in s]
total_total = sum(s.get("total_cids", 0) for s in ok_seeds)
total_new = sum(s.get("new_cids", 0) for s in ok_seeds)
avg_new = total_new / max(1, len(ok_seeds))

print(f"\n=== Aggregate (depth-2 BFS) ===")
print(f"  Seeds OK: {len(ok_seeds)}/{len(depth2_seeds)}")
print(f"  Avg cids returned/seed: {total_total/max(1,len(ok_seeds)):.2f}")
print(f"  Avg new/seed:           {avg_new:.2f}")
print(f"  Total UNIQUE new cids:  {len(total_d2_new)}")

# Compare to v1 depth-1 baseline: 3.25 new/huge seed (or ~1.6 mid)
print(f"\n  vs v1 depth-1 huge seed: 3.25 new/seed")
print(f"  Decay ratio:             {avg_new/3.25*100:.1f}% of depth-1 yield")

results = {
    "depth2_seeds_count": len(depth2_seeds),
    "ok_seeds": len(ok_seeds),
    "avg_total_cids_per_seed": total_total / max(1, len(ok_seeds)),
    "avg_new_per_seed": avg_new,
    "total_unique_new": len(total_d2_new),
    "decay_vs_depth1": avg_new / 3.25,
    "per_seed": per_seed,
    "verdict": ("WORTH multi-depth" if avg_new >= 2.0
                else "MARGINAL" if avg_new >= 1.0
                else "DECAY too strong, stop at depth-1"),
    "sample_new_30": list(total_d2_new)[:30],
}
dump_json(os.path.join(os.path.dirname(__file__), "test_C_depth2_results.json"), results)
print(f"\nresults dumped → test_C_depth2_results.json")

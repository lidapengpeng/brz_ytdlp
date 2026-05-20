"""Test D: A/B test 3 clients × 3 locales on same seed, see if union > single."""
import time, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bfs_v2_helpers import make_ydl, pick_seeds, load_known_ids, find_all_renderers, dump_json

print("=" * 70)
print("Test D: Client/Locale A/B for BFS gridChannelRenderer yield")
print("=" * 70)

known = load_known_ids()
seeds = pick_seeds("huge", n=5)

CLIENTS = ["tv", "web_safari", "android_vr"]
LOCALES = [("pt-BR,pt;q=0.9", "BR"), ("en-US,en;q=0.9", "US"), ("es-419,es;q=0.9", "BR")]

per_seed = {}
for seed in seeds:
    print(f"\n=== seed {seed} ===")
    union_cids = set()
    per_combo = {}
    for client in CLIENTS:
        for locale, gl in LOCALES:
            t0 = time.time()
            ydl = make_ydl(client, locale, gl)
            try:
                ie = ydl.get_info_extractor("YoutubeTab")
                resp = ie._call_api(ep="browse", video_id=seed, query={"browseId": seed})
                cids = set()
                for r in find_all_renderers(resp, "gridChannelRenderer"):
                    cid = r.get("channelId")
                    if cid and cid.startswith("UC"): cids.add(cid)
                for r in find_all_renderers(resp, "channelRenderer"):
                    cid = r.get("channelId")
                    if cid and cid.startswith("UC"): cids.add(cid)
                cids.discard(seed)
                ms = int((time.time()-t0)*1000)
                combo = f"{client}+{locale.split(',')[0]}+gl={gl}"
                per_combo[combo] = {"n_cids": len(cids), "cids": list(cids), "ms": ms}
                union_cids |= cids
                print(f"  {combo:40s}: {len(cids)} cids, {ms}ms")
            except Exception as e:
                combo = f"{client}+{locale.split(',')[0]}+gl={gl}"
                per_combo[combo] = {"err": f"{type(e).__name__}: {str(e)[:50]}"}
                print(f"  {combo:40s}: ✗ {type(e).__name__}")
            finally:
                try: ydl.close()
                except: pass
    new_cids = union_cids - known
    per_seed[seed] = {
        "union_size": len(union_cids),
        "new_cids": len(new_cids),
        "per_combo": per_combo,
    }
    # baseline: tv + pt-BR
    base = per_combo.get("tv+pt-BR+gl=BR", {})
    base_size = base.get("n_cids", 0)
    print(f"  → union of 9 combos: {len(union_cids)} cids (vs tv+pt-BR alone: {base_size})")
    print(f"    boost ratio: {len(union_cids)/max(1,base_size):.2f}x")

# Aggregate
print(f"\n--- Aggregate ---")
total_union_new = sum(s["new_cids"] for s in per_seed.values())
print(f"  Total new cids across 5 seeds × 9 combos: {total_union_new}")
print(f"  Avg new per seed: {total_union_new/len(seeds):.2f}")

# Compare to v1 baseline (tv+pt-BR only)
total_baseline_new = sum(
    len(set(s["per_combo"].get("tv+pt-BR+gl=BR", {}).get("cids", [])) - known) for s in per_seed.values()
)
print(f"  Baseline (tv+pt-BR only) new cids: {total_baseline_new}")
print(f"  → boost vs baseline: {total_union_new/max(1,total_baseline_new):.2f}x")

results = {
    "seeds": seeds,
    "clients": CLIENTS, "locales": [l[0] for l in LOCALES],
    "per_seed": per_seed,
    "total_union_new": total_union_new,
    "total_baseline_new": total_baseline_new,
    "verdict": "marginal" if total_union_new / max(1, total_baseline_new) < 1.5
                  else "WORTH adopting locale/client rotation",
}
dump_json(os.path.join(os.path.dirname(__file__), "test_D_client_locale_ab_results.json"), results)
print("\nresults dumped → test_D_client_locale_ab_results.json")

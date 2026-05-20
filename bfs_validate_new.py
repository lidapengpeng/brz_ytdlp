"""Spot-validate new channel IDs discovered via BFS to measure BR conversion rate."""
import json
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from extract_v4 import extract as extract_v4

# Load BFS-discovered new ids from previous experiment
with open(ROOT / "bfs_experiment_v2_results.json") as f:
    data = json.load(f)

new_ids = set()
for r in data["results"]:
    for s in r["surfaces"].values():
        for cid in s.get("new_sample", []):
            new_ids.add(cid)

print(f"Validating {len(new_ids)} BFS-discovered new channel IDs...")

t0 = time.time()
results = []
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {pool.submit(extract_v4, None, cid): cid for cid in new_ids}
    for fut in futures:
        cid = futures[fut]
        try:
            info = fut.result(timeout=60)
        except Exception as e:
            results.append({"cid": cid, "error": str(e)})
            continue
        results.append({
            "cid": cid,
            "name": info.name,
            "subs": info.subscribers,
            "country": info.country,
            "short_circuited": info.short_circuited,
            "is_target": info.is_target,
            "target_reason": info.target_reason,
            "error": info.error,
        })

elapsed = time.time() - t0
print(f"Done in {elapsed:.1f}s\n")

# Categorize
ok = [r for r in results if not r.get("error")]
short = [r for r in ok if r.get("short_circuited")]
target = [r for r in ok if r.get("is_target")]
huge = [r for r in target if (r.get("subs") or 0) >= 100000]
errors = [r for r in results if r.get("error")]

print(f"Total validated: {len(results)}")
print(f"  errors: {len(errors)}")
print(f"  short_circuited (subs<1000): {len(short)}")
print(f"  is_target BR (subs>=1k): {len(target)}")
print(f"  large BR (subs>=100K):   {len(huge)}")
print(f"\nConversion rate (target/all): {len(target)/max(1,len(results))*100:.1f}%")
print(f"Conversion rate (target/non-error): {len(target)/max(1,len(ok))*100:.1f}%")

# Output sample
print("\nSample of new BR targets found:")
for t in sorted(target, key=lambda x: -(x.get("subs") or 0))[:15]:
    print(f"  {t['cid']}  {(t.get('name','?') or '?')[:30]:30s}  subs={t.get('subs','?'):>8}  country={t.get('country','?'):>10s}  reason={t.get('target_reason')}")

# Save
with open(ROOT / "bfs_validate_new_results.json","w") as f:
    json.dump({"timestamp": int(time.time()), "elapsed_s": elapsed,
               "total": len(results), "ok": len(ok), "target": len(target),
               "huge": len(huge), "results": results}, f, indent=2, ensure_ascii=False)

"""Test E: probe channel home browse response for hidden recommendation widgets."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bfs_v2_helpers import make_ydl, pick_seeds, load_known_ids, find_all, dump_json

print("=" * 70)
print("Test E: Subscribe Widget / Hidden Recommendation Probe")
print("=" * 70)

known = load_known_ids()
seeds = pick_seeds("huge", n=5)
print(f"5 huge BR seeds: {seeds}\n")

all_renderer_types = set()
all_subscribe_fields = set()
all_widget_keywords = set()
per_seed = {}

for seed in seeds:
    ydl = make_ydl("tv")
    try:
        ie = ydl.get_info_extractor("YoutubeTab")
        resp = ie._call_api(ep="browse", video_id=seed, query={"browseId": seed})
        # Collect all renderer types in this response
        renderer_types = set()
        subscribe_paths = set()
        widget_paths = set()
        cids_in_widgets = set()
        def walk(n, path=""):
            if isinstance(n, dict):
                for k, v in n.items():
                    if k.endswith("Renderer"):
                        renderer_types.add(k)
                    # Hunt for subscribe-related field names
                    lk = k.lower()
                    if "subscrib" in lk or "recommend" in lk or "widget" in lk:
                        subscribe_paths.add(k)
                        # Inside, look for channel ids
                        if isinstance(v, dict):
                            sub_cids = [c for c in find_all(v, "channelId") if isinstance(c, str) and c.startswith("UC")]
                            sub_cids += [c for c in find_all(v, "browseId") if isinstance(c, str) and c.startswith("UC")]
                            cids_in_widgets.update(sub_cids)
                    if "similar" in lk or "related" in lk or "suggest" in lk:
                        widget_paths.add(k)
                    walk(v, path + "." + k)
            elif isinstance(n, list):
                for x in n: walk(x, path)
        walk(resp)
        per_seed[seed] = {
            "renderer_types": sorted(renderer_types),
            "subscribe_keys": sorted(subscribe_paths),
            "widget_keys": sorted(widget_paths),
            "channel_ids_inside_widgets": list(cids_in_widgets),
            "channels_widgets_new": list(cids_in_widgets - known),
        }
        all_renderer_types.update(renderer_types)
        all_subscribe_fields.update(subscribe_paths)
        all_widget_keywords.update(widget_paths)
        print(f"  {seed}: {len(renderer_types)} renderer types, "
              f"{len(subscribe_paths)} subscribe-keys, {len(widget_paths)} widget-keys, "
              f"{len(cids_in_widgets - known)} new cids")
    except Exception as e:
        print(f"  {seed}: ✗ {type(e).__name__}: {str(e)[:50]}")
    finally:
        try: ydl.close()
        except: pass

print(f"\n--- Aggregate ---")
print(f"  Unique renderer types across 5 seeds: {len(all_renderer_types)}")
print(f"  Subscribe-related field names found:  {sorted(all_subscribe_fields)}")
print(f"  Recommendation/widget field names:    {sorted(all_widget_keywords)}")

all_new_from_widgets = set()
for s in per_seed.values():
    all_new_from_widgets.update(s.get("channels_widgets_new", []))
print(f"\n  TOTAL new cids extracted from widget paths: {len(all_new_from_widgets)}")
print(f"  → over 5 huge seeds = avg {len(all_new_from_widgets)/5:.1f} new/seed from widgets")

results = {
    "seeds": seeds,
    "n_seeds": len(seeds),
    "per_seed": per_seed,
    "all_subscribe_keys": sorted(all_subscribe_fields),
    "all_widget_keys": sorted(all_widget_keywords),
    "all_renderer_types": sorted(all_renderer_types),
    "total_new_cids_via_widgets": len(all_new_from_widgets),
    "verdict": "no hidden surface" if len(all_new_from_widgets) == 0 else "WORTH investigating",
}
dump_json(os.path.join(os.path.dirname(__file__), "test_E_widget_probe_results.json"), results)
print("\nresults dumped → test_E_widget_probe_results.json")

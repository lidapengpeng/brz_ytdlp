"""bfs_experiment_v2.py — Real BFS yield measurement, multi-surface.

For each seed:
  - surface A: /channels tab (params=EghjaGFubmVscw==)  -- often empty per probe
  - surface B: home tab default browse (no params) -- has gridChannelRenderer (featured/collabs)
  - surface C: home tab + "Featured" param (EghmZWF0dXJlZA==) -- same as B usually
  - surface D: about tab (params=EgVhYm91dPIGBAoCEgA=) -- description links

Output: per-seed counts + overlap with DB.
"""
import base64
import json
import random
import sqlite3
import sys
import time
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import yt_dlp

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
DB = ROOT / "results.db"

from extract_v3 import generate_visitor_data, random_brazil_ip


SAFE_CLIENTS = ("tv", "web_safari", "ios", "android_vr", "mweb")


def make_ydl():
    return yt_dlp.YoutubeDL({
        "quiet": True, "no_warnings": True, "skip_download": True,
        "socket_timeout": 30,
        "geo_bypass": True, "geo_bypass_country": "BR",
        "extractor_args": {
            "youtube": {
                "player_client": [random.choice(SAFE_CLIENTS)],
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


def _find_all(node, key, limit=None):
    out = []
    def walk(n):
        if limit is not None and len(out) >= limit: return True
        if isinstance(n, dict):
            if key in n:
                out.append(n[key])
                if limit is not None and len(out) >= limit: return True
            for v in n.values():
                if walk(v): return True
        elif isinstance(n, list):
            for x in n:
                if walk(x): return True
        return False
    walk(node)
    return out


def harvest_channel_ids(resp, seed_cid):
    """Find all channelRenderer / gridChannelRenderer / ownerText with channel ids."""
    ids = set()
    for r in _find_all(resp, "channelRenderer"):
        if isinstance(r, dict):
            cid = r.get("channelId")
            if cid and cid != seed_cid and cid.startswith("UC"):
                ids.add(cid)
    for r in _find_all(resp, "gridChannelRenderer"):
        if isinstance(r, dict):
            cid = r.get("channelId")
            if cid and cid != seed_cid and cid.startswith("UC"):
                ids.add(cid)
    # Also collect "browseEndpoint.browseId" pointing to UC channels
    # (these appear in shelfRenderer subtitle navigation, channel mentions, etc.)
    for be in _find_all(resp, "browseEndpoint"):
        if isinstance(be, dict):
            cid = be.get("browseId")
            if isinstance(cid, str) and cid.startswith("UC") and cid != seed_cid:
                ids.add(cid)
    return ids


# --- Discovery surfaces ----------------------------------------------------

def surface_channels_tab(ie, seed_cid):
    """Legacy /channels tab (mostly empty in 2025/2026)."""
    t0 = time.time()
    resp = ie._call_api(
        ep="browse", video_id=seed_cid,
        query={"browseId": seed_cid, "params": "EghjaGFubmVscw%3D%3D"},
    )
    return resp, time.time() - t0


def surface_home(ie, seed_cid):
    """Default channel home tab — contains gridChannelRenderer (Collabs, Outros Canais, Canal Principal, etc.)"""
    t0 = time.time()
    resp = ie._call_api(
        ep="browse", video_id=seed_cid,
        query={"browseId": seed_cid},
    )
    return resp, time.time() - t0


def surface_about(ie, seed_cid):
    """About panel — contains description with channel links."""
    # The about-panel token is usually in stage1 (need home first), but we can
    # try the static "about" tab params instead
    t0 = time.time()
    resp = ie._call_api(
        ep="browse", video_id=seed_cid,
        query={"browseId": seed_cid, "params": "EgVhYm91dPIGBAoCEgA%3D"},
    )
    return resp, time.time() - t0


def load_known(db_path):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    known = set()
    eligible = set()
    for (cid,) in conn.execute("SELECT channel_id FROM channels"):
        known.add(cid); eligible.add(cid)
    for (cid,) in conn.execute("SELECT channel_id FROM rejected_channel_ids"):
        known.add(cid)
    conn.close()
    return known, eligible


def pick_seeds(db_path, cohort, n):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    if cohort == "mid":
        q = ("""SELECT channel_id, name, subscribers, country FROM channels
                WHERE is_target=1 AND subscribers BETWEEN 10000 AND 1000000
                  AND country IN ('Brazil','Brasil')
                ORDER BY RANDOM() LIMIT ?""", (n,))
    elif cohort == "huge":
        q = ("""SELECT channel_id, name, subscribers, country FROM channels
                WHERE is_target=1 AND subscribers >= 1000000
                  AND country IN ('Brazil','Brasil')
                ORDER BY RANDOM() LIMIT ?""", (n,))
    elif cohort == "lang_rec":
        q = ("""SELECT channel_id, name, subscribers, country FROM channels
                WHERE target_reason='country=None,lang=pt' AND subscribers >= 5000
                ORDER BY RANDOM() LIMIT ?""", (n,))
    elif cohort == "small":
        q = ("""SELECT channel_id, name, subscribers, country FROM channels
                WHERE is_target=1 AND subscribers BETWEEN 1000 AND 10000
                  AND country IN ('Brazil','Brasil')
                ORDER BY RANDOM() LIMIT ?""", (n,))
    else:
        raise ValueError(cohort)
    cur = conn.execute(*q)
    rows = cur.fetchall()
    conn.close()
    return rows


def run_seed(seed_row, cohort, known, eligible):
    cid, name, subs, country = seed_row
    ydl = make_ydl()
    try:
        ie = ydl.get_info_extractor("YoutubeTab")

        results = {
            "cohort": cohort, "seed_cid": cid, "name": name, "subs": subs, "country": country,
            "surfaces": {},
        }

        for sname, fn in [("channels_tab", surface_channels_tab),
                          ("home", surface_home),
                          ("about", surface_about)]:
            try:
                resp, elapsed = fn(ie, cid)
            except Exception as e:
                results["surfaces"][sname] = {"error": f"{type(e).__name__}: {e}"}
                continue
            ids = harvest_channel_ids(resp, cid)
            new_ids = ids - known
            new_eligible_hits = ids & eligible
            results["surfaces"][sname] = {
                "n_total": len(ids),
                "n_new": len(new_ids),
                "n_eligible_hits": len(new_eligible_hits),
                "elapsed_s": round(elapsed, 2),
                "new_sample": list(new_ids)[:5],
            }
        return results
    finally:
        try: ydl.close()
        except: pass


def main():
    known, eligible = load_known(DB)
    print(f"[setup] {len(eligible)} eligible + {len(known)-len(eligible)} rejected = {len(known)} known IDs", flush=True)

    seeds = []
    for cohort, n in [("mid", 15), ("huge", 8), ("lang_rec", 8), ("small", 10)]:
        rows = pick_seeds(DB, cohort, n)
        for r in rows:
            seeds.append((r, cohort))
        print(f"[seeds] {cohort}: {len(rows)}", flush=True)

    all_results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(run_seed, row, cohort, known, eligible): (row, cohort)
                   for row, cohort in seeds}
        for fut in futures:
            row, cohort = futures[fut]
            try:
                r = fut.result(timeout=120)
            except Exception as e:
                print(f"  EXC {row[0]}: {e}", flush=True)
                continue
            all_results.append(r)
            home = r["surfaces"].get("home", {})
            ch_tab = r["surfaces"].get("channels_tab", {})
            about = r["surfaces"].get("about", {})
            print(f"  [{cohort:8s}] {r['seed_cid']}  {(r['name'] or '?')[:25]:25s}  subs={r['subs']:>8}  "
                  f"home(tot/new/hit)={home.get('n_total',0):>2}/{home.get('n_new',0):>2}/{home.get('n_eligible_hits',0):>2}  "
                  f"chTab={ch_tab.get('n_total','-'):>2}/{ch_tab.get('n_new','-'):>2}  "
                  f"about={about.get('n_total','-'):>2}/{about.get('n_new','-'):>2}",
                  flush=True)

    # Aggregate
    print("\n" + "="*100)
    print("AGGREGATE BY COHORT × SURFACE")
    print("="*100)
    cohorts = ["mid", "huge", "lang_rec", "small"]
    surfaces = ["channels_tab", "home", "about"]
    print(f"{'cohort':10s} {'surface':14s} {'n_seeds':>7s} {'avg_total':>10s} {'avg_new':>8s} {'avg_hits':>9s} {'avg_dup%':>9s} {'avg_time':>8s}")
    aggregate = []
    for c in cohorts:
        for s in surfaces:
            rs = [r["surfaces"][s] for r in all_results if r["cohort"]==c and "n_total" in r["surfaces"].get(s,{})]
            if not rs: continue
            n = len(rs)
            avg_t = sum(x["n_total"] for x in rs)/n
            avg_n = sum(x["n_new"] for x in rs)/n
            avg_h = sum(x["n_eligible_hits"] for x in rs)/n
            avg_e = sum(x["elapsed_s"] for x in rs)/n
            dup = round(100*(1-avg_n/max(0.001,avg_t)), 1) if avg_t else 0.0
            print(f"{c:10s} {s:14s} {n:>7d} {avg_t:>10.2f} {avg_n:>8.2f} {avg_h:>9.2f} {dup:>8.1f}% {avg_e:>7.2f}s")
            aggregate.append({"cohort":c, "surface":s, "n_seeds":n,
                              "avg_total":round(avg_t,2), "avg_new":round(avg_n,2),
                              "avg_hits":round(avg_h,2), "dup_pct":dup,
                              "avg_elapsed_s":round(avg_e,2)})

    # Save
    out = ROOT / "bfs_experiment_v2_results.json"
    with open(out, "w") as f:
        json.dump({"timestamp": int(time.time()),
                   "known_ids": len(known),
                   "eligible_ids": len(eligible),
                   "seeds_tested": len(all_results),
                   "results": all_results,
                   "aggregate": aggregate}, f, indent=2, ensure_ascii=False)
    print(f"\n[saved] {out}")

    # New IDs to spot-check
    new_set = set()
    for r in all_results:
        for s in r["surfaces"].values():
            for cid in s.get("new_sample", []):
                new_set.add(cid)
    print(f"[new IDs to spot-check] {len(new_set)}")
    return all_results, new_set


if __name__ == "__main__":
    main()

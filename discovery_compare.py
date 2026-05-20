"""Discovery-strategy comparison — measure conversion rate per strategy.

For each strategy:
  1. Surface ~30 candidate channel_ids
  2. Validate them via extract_v3 (definitive subs + country)
  3. Report conversion rate (eligible / discovered)

Strategies tested:
  A. kw="<query>" + channel filter (current baseline)
  B. kw="<query>" + video filter, extract video.owner.channelId (PDF §4)
  C. BFS from a confirmed-BR seed channel
  D. Handle-pattern: channels whose handle contains 'brasil' / 'br'

The goal: identify which strategy gives the highest %(BR + subs>=1000)/discovered ratio.
"""
from __future__ import annotations

import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Iterable, List, Optional, Set, Tuple

import yt_dlp

# Import our v3 extractor (and its monkey patch on _extract_context)
from extract_v3 import (
    ChannelInfo, ExtractorConfigV3, extract, is_brazil,
    generate_visitor_data, random_brazil_ip,
)

# Same client rotation as extract_v4 — diversify fingerprint across all callers.
# Without this, 5 discovery workers + 40 validators ALL look like mweb iPads.
SAFE_CLIENTS = (
    "tv",          # Cobalt SmartTV — uncommon, low throttle
    "web_safari",  # Mac Safari
    "ios",         # iPhone YouTube app
    "android_vr",  # Oculus VR
    "mweb",        # iPad mobile-web (kept for diversity)
)


# ----- discovery primitives -----------------------------------------------

def _find_all(node: Any, key: str, limit: Optional[int] = None) -> List[Any]:
    out: List[Any] = []
    def walk(n: Any) -> bool:
        if limit is not None and len(out) >= limit:
            return True
        if isinstance(n, dict):
            if key in n:
                out.append(n[key])
                if limit is not None and len(out) >= limit:
                    return True
            for v in n.values():
                if walk(v): return True
        elif isinstance(n, list):
            for x in n:
                if walk(x): return True
        return False
    walk(node)
    return out


def _make_ydl_for_search() -> yt_dlp.YoutubeDL:
    """Fresh yt-dlp with random visitor_data, random Brazil XFF, and a randomly
    chosen player_client. Rotating client per call spreads the fingerprint across
    Cobalt TV / Safari / iPhone / Oculus VR / iPad — matches extract_v4 behavior."""
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


def discover_via_channel_filter(query: str, limit: int = 30, min_subs: int = 1000) -> Tuple[List[str], dict]:
    """Strategy A: InnerTube /search with channel filter (params=EgIQAg%3D%3D).

    KEY OPTIMIZATION (2026-05-19): the search response's channelRenderer carries
    the subscriber count in `videoCountText` (yes — field name is misleading,
    YouTube's data model is weird). e.g. "43,5 mil inscritos" or "16 inscritos".
    We parse this and skip channels below `min_subs` BEFORE returning — this
    eliminates ~50-60% of downstream validator work (those subs<1000 would have
    been short-circuited anyway after a Stage-1 InnerTube call).
    Pre-filter at discovery saves an API call PER skipped channel.
    """
    from extract_v3 import parse_count
    ydl = _make_ydl_for_search()
    ie = ydl.get_info_extractor("YoutubeTab")
    t0 = time.time()
    resp = ie._call_api(
        ep="search", video_id="seed",
        query={"query": query, "params": "EgIQAg%3D%3D"},
    )
    elapsed = time.time() - t0
    # Channel results live in channelRenderer.channelId.
    # Sub count is in `videoCountText` (counter-intuitively) — parse with PDF plan C.
    ids: List[str] = []
    seen: Set[str] = set()
    filtered_small = 0
    for r in _find_all(resp, "channelRenderer"):
        cid = r.get("channelId") if isinstance(r, dict) else None
        # Pre-filter: parse sub count from videoCountText, skip subs<min_subs
        sub_text_field = r.get("videoCountText", {}) if isinstance(r, dict) else {}
        if isinstance(sub_text_field, dict):
            sub_text = sub_text_field.get("simpleText", "") or "".join(
                run.get("text", "") for run in sub_text_field.get("runs", []) if isinstance(run, dict)
            )
            sub_count = parse_count(sub_text)
            if sub_count is not None and sub_count < min_subs:
                filtered_small += 1
                continue   # skip — subs<1000, would be short-circuited anyway
        if cid and cid not in seen:
            seen.add(cid)
            ids.append(cid)
            if len(ids) >= limit: break
    return ids, {"elapsed_s": elapsed, "response_bytes": len(json.dumps(resp))}


def discover_via_video_owners(query: str, limit: int = 30) -> Tuple[List[str], dict]:
    """Strategy B (PDF §4): InnerTube /search WITHOUT filter (videos),
    extract owner channelId from each videoRenderer."""
    ydl = _make_ydl_for_search()
    ie = ydl.get_info_extractor("YoutubeTab")
    t0 = time.time()
    resp = ie._call_api(ep="search", video_id="seed", query={"query": query})
    elapsed = time.time() - t0
    ids: List[str] = []
    seen: Set[str] = set()
    for vr in _find_all(resp, "videoRenderer"):
        if not isinstance(vr, dict): continue
        owner = vr.get("ownerText", {})
        runs = owner.get("runs", []) if isinstance(owner, dict) else []
        if runs and isinstance(runs[0], dict):
            nav = runs[0].get("navigationEndpoint", {})
            be = nav.get("browseEndpoint", {}) if isinstance(nav, dict) else {}
            cid = be.get("browseId") if isinstance(be, dict) else None
            if cid and cid.startswith("UC") and cid not in seen:
                seen.add(cid)
                ids.append(cid)
                if len(ids) >= limit: break
    return ids, {"elapsed_s": elapsed, "response_bytes": len(json.dumps(resp))}


def discover_via_watchnext(seed_channel_id: str, limit: int = 50, n_videos: int = 3) -> Tuple[List[str], dict]:
    """Strategy D: BFS via watchEndpoint /next "Up Next" sidebar.

    Algorithm:
      1. Fetch seed's videos tab (params=EgZ2aWRlb3M%3D)
      2. Take top N video IDs (default 3)
      3. For each video, call /next endpoint with web_safari client
      4. Walk secondaryResults.secondaryResults.results[*].lockupViewModel
         and extract owner channel IDs from the decoratedAvatarViewModel path.

    Implemented after the 2024 YouTube layout change (replaced compactVideoRenderer
    with lockupViewModel). Verified yield 2026-05-19: 9.6-10.8 new cid/huge BR seed,
    2.95-3.32x vs gridChannel BFS. Surfaces algorithm-curated cousins, not just
    owner-curated. See long_term_research/06_bfs_discovery.md §12.1.
    """
    import random as _random
    ydl = _make_ydl_for_search()
    ie = ydl.get_info_extractor("YoutubeTab")
    t0 = time.time()
    # Step 1: get top N video ids from videos tab
    try:
        resp = ie._call_api(
            ep="browse", video_id=seed_channel_id,
            query={"browseId": seed_channel_id, "params": "EgZ2aWRlb3M%3D"},
            default_client="web_safari",
        )
    except Exception as e:
        try: ydl.close()
        except: pass
        return [], {"elapsed_s": time.time() - t0, "error": f"videos tab: {type(e).__name__}"}
    video_ids: List[str] = []
    # Modern (richItemRenderer.content.videoRenderer)
    for rir in _find_all(resp, "richItemRenderer"):
        if isinstance(rir, dict):
            inner = rir.get("content", {}).get("videoRenderer", {})
            if isinstance(inner, dict):
                vid = inner.get("videoId")
                if vid and vid not in video_ids:
                    video_ids.append(vid)
                    if len(video_ids) >= n_videos: break
    # Fallback: gridVideoRenderer / videoRenderer top-level
    if len(video_ids) < n_videos:
        for key in ("videoRenderer", "gridVideoRenderer"):
            for r in _find_all(resp, key):
                if isinstance(r, dict):
                    vid = r.get("videoId")
                    if vid and vid not in video_ids:
                        video_ids.append(vid)
                        if len(video_ids) >= n_videos: break
            if len(video_ids) >= n_videos: break
    # Fallback 2: lockupViewModel with valid 11-char contentId
    if len(video_ids) < n_videos:
        for lvm in _find_all(resp, "lockupViewModel"):
            if isinstance(lvm, dict):
                content_id = lvm.get("contentId")
                if content_id and len(content_id) == 11 and content_id not in video_ids:
                    video_ids.append(content_id)
                    if len(video_ids) >= n_videos: break
    try: ydl.close()
    except: pass

    # Step 2: call /next on each video, harvest owner cids
    all_owners: Set[str] = set([seed_channel_id])
    n_next_ok = 0
    for vid in video_ids:
        ydl2 = _make_ydl_for_search()
        try:
            ie2 = ydl2.get_info_extractor("YoutubeTab")
            n_resp = ie2._call_api(
                ep="next", video_id=vid, query={"videoId": vid},
                default_client="web_safari",
            )
            try:
                sec = (n_resp["contents"]["twoColumnWatchNextResults"]
                            ["secondaryResults"]["secondaryResults"]["results"])
            except (KeyError, TypeError):
                sec = []
            for entry in sec:
                lvm = entry.get("lockupViewModel") if isinstance(entry, dict) else None
                if not isinstance(lvm, dict): continue
                # Primary path: owner avatar's onTap browseEndpoint
                try:
                    cid = (lvm["metadata"]["lockupMetadataViewModel"]["image"]
                              ["decoratedAvatarViewModel"]["rendererContext"]
                              ["commandContext"]["onTap"]["innertubeCommand"]
                              ["browseEndpoint"]["browseId"])
                    if cid and cid.startswith("UC"):
                        all_owners.add(cid)
                except (KeyError, TypeError):
                    pass
            n_next_ok += 1
        except Exception:
            continue
        finally:
            try: ydl2.close()
            except: pass

    all_owners.discard(seed_channel_id)
    ids = list(all_owners)[:limit]
    return ids, {
        "elapsed_s": time.time() - t0,
        "n_videos_used": len(video_ids),
        "n_next_calls_ok": n_next_ok,
    }


def discover_via_bfs(seed_channel_id: str, limit: int = 30) -> Tuple[List[str], dict]:
    """Strategy C: visit seed's home tab and harvest collab/featured channels.

    NOTE: /channels tab was removed by YouTube in 2023-11 (verified by yt-dlp
    source _tab.py:1944, 1978 — "channels tab removed"). The home tab response
    (no params) contains gridChannelRenderer in shelfRenderer items — these are
    the "Outros Canais" / "Collabs" / "Canal Principal" shelves.

    Average yield: 0.6 (small) / 1.6 (mid) / 3.25 (huge BR) new cids per seed.
    BR conversion rate ~63%, vs ~12% for query-based. See §06_bfs_discovery.md.
    """
    ydl = _make_ydl_for_search()
    ie = ydl.get_info_extractor("YoutubeTab")
    t0 = time.time()
    # NO params — pre-2024 EghjaGFubmVscw== returns same as home now
    resp = ie._call_api(
        ep="browse", video_id=seed_channel_id,
        query={"browseId": seed_channel_id},
    )
    elapsed = time.time() - t0
    ids: List[str] = []
    seen: Set[str] = set([seed_channel_id])
    # gridChannelRenderer is the modern layout (collab shelves)
    for r in _find_all(resp, "gridChannelRenderer"):
        if isinstance(r, dict):
            cid = r.get("channelId")
            if cid and cid not in seen and cid.startswith("UC"):
                seen.add(cid); ids.append(cid)
                if len(ids) >= limit: break
    # channelRenderer is older layout (still appears in some channels)
    for r in _find_all(resp, "channelRenderer"):
        if isinstance(r, dict):
            cid = r.get("channelId")
            if cid and cid not in seen and cid.startswith("UC"):
                seen.add(cid); ids.append(cid)
                if len(ids) >= limit: break
    return ids, {"elapsed_s": elapsed, "response_bytes": len(json.dumps(resp))}


# ----- validation & metrics -----------------------------------------------

def validate_batch(channel_ids: List[str], concurrency: int = 10) -> List[ChannelInfo]:
    """Run extract_v3 on each channel ID via thread pool."""
    cfg = ExtractorConfigV3()
    results: List[Optional[ChannelInfo]] = [None] * len(channel_ids)
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(extract, None, cid): i for i, cid in enumerate(channel_ids)}
        for fut in futures:
            i = futures[fut]
            try:
                results[i] = fut.result(timeout=60)
            except Exception as e:
                results[i] = ChannelInfo(channel_id=channel_ids[i], error=f"timeout/{type(e).__name__}")
    return [r for r in results if r is not None]


def summarize(label: str, results: List[ChannelInfo], discovery_meta: dict) -> dict:
    n = len(results)
    ok = [r for r in results if not r.error]
    brazil = [r for r in ok if is_brazil(r.country)]
    eligible = [r for r in brazil if (r.subscribers or 0) >= 1000]
    big = [r for r in brazil if (r.subscribers or 0) >= 10_000]
    huge = [r for r in brazil if (r.subscribers or 0) >= 1_000_000]
    return {
        "label": label,
        "discovered": n,
        "validated_ok": len(ok),
        "brazil": len(brazil),
        "eligible_BR_ge1000": len(eligible),
        "eligible_BR_ge10000": len(big),
        "eligible_BR_ge1M": len(huge),
        "conv_rate_BR": round(len(brazil) / max(1, n), 3),
        "conv_rate_eligible": round(len(eligible) / max(1, n), 3),
        "discovery_elapsed_s": round(discovery_meta.get("elapsed_s", 0), 2),
        "discovery_bytes": discovery_meta.get("response_bytes", 0),
    }


# ----- main test ----------------------------------------------------------

def main():
    # 4 query themes × 3 discovery strategies (channel-filter, video-owners, BFS)
    queries = [
        "futebol brasil",         # broad sports
        "vlog brasileiro",        # personal content
        "receitas brasileiras",   # cooking / Brazil-specific noun
        "sertanejo música",       # genuinely BR genre
    ]
    bfs_seeds = [
        ("UCr4ARxgElIO21GWfIraZezg", "Garena Free Fire Brasil (BR, 10M)"),
        ("UCBR8-60-B28hp2BmDPdntcQ", "YouTube (just a control)"),
    ]

    all_stats = []

    print(f"yt-dlp {yt_dlp.version.__version__} — discovery-strategy comparison\n")

    for q in queries:
        print(f"=== query: {q!r} ===")
        # Strategy A
        ids_a, meta_a = discover_via_channel_filter(q, limit=30)
        print(f"  [A channel-filter]  discovered {len(ids_a)} ids in {meta_a['elapsed_s']:.1f}s")
        # Strategy B
        ids_b, meta_b = discover_via_video_owners(q, limit=30)
        print(f"  [B video-owners ]  discovered {len(ids_b)} ids in {meta_b['elapsed_s']:.1f}s")
        # Validate both
        res_a = validate_batch(ids_a)
        res_b = validate_batch(ids_b)
        all_stats.append(summarize(f"A | kw={q!r} | channel-filter", res_a, meta_a))
        all_stats.append(summarize(f"B | kw={q!r} | video-owners ", res_b, meta_b))

    for seed_id, seed_label in bfs_seeds:
        print(f"\n=== BFS seed: {seed_label} ===")
        ids_c, meta_c = discover_via_bfs(seed_id, limit=30)
        print(f"  [C bfs]  discovered {len(ids_c)} ids in {meta_c['elapsed_s']:.1f}s")
        res_c = validate_batch(ids_c)
        all_stats.append(summarize(f"C | bfs={seed_label}", res_c, meta_c))

    # Print final comparison
    print("\n" + "=" * 110)
    print(f"{'strategy':70s}  {'disc':>4s}  {'OK':>3s}  {'BR':>3s}  {'≥1K':>4s}  {'≥10K':>4s}  {'≥1M':>3s}  {'conv':>6s}")
    print("=" * 110)
    for s in all_stats:
        print(f"{s['label'][:70]:70s}  "
              f"{s['discovered']:>4d}  {s['validated_ok']:>3d}  {s['brazil']:>3d}  "
              f"{s['eligible_BR_ge1000']:>4d}  {s['eligible_BR_ge10000']:>4d}  "
              f"{s['eligible_BR_ge1M']:>3d}  {s['conv_rate_eligible']*100:>5.1f}%")


if __name__ == "__main__":
    main()

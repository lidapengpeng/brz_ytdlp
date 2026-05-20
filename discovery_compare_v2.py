"""Expanded conversion-rate test — 10 queries × 2 strategies, deduped channel
set, to get a more statistically sound estimate of the gap."""
from __future__ import annotations

import time
from typing import List, Set

from discovery_compare import (
    discover_via_channel_filter,
    discover_via_video_owners,
    validate_batch,
)
from extract_v3 import is_brazil


QUERIES = [
    # mix of: broad, niche, BR-genres, intent-words, ambiguous
    "futebol brasil",
    "vlog brasileiro",
    "receitas brasileiras",
    "sertanejo música",
    "humor brasileiro",
    "tutorial maquiagem",
    "review celular",
    "minecraft survival",     # potentially ambiguous (lots of non-BR)
    "notícias hoje",          # very broad
    "canal oficial brasil",   # high-intent BR
]


def run_one_strategy(name: str, discover_fn, queries: List[str]) -> dict:
    all_ids: List[str] = []
    seen: Set[str] = set()
    discovery_time = 0.0
    for q in queries:
        ids, meta = discover_fn(q, limit=25)
        discovery_time += meta.get("elapsed_s", 0)
        for cid in ids:
            if cid not in seen:
                seen.add(cid)
                all_ids.append(cid)
    print(f"[{name}] discovered {len(all_ids)} unique channels across {len(queries)} queries "
          f"in {discovery_time:.1f}s discovery time")
    # Validate
    val_t0 = time.time()
    results = validate_batch(all_ids, concurrency=15)
    val_elapsed = time.time() - val_t0

    ok = [r for r in results if not r.error]
    brazil = [r for r in ok if is_brazil(r.country)]
    eligible_1k  = [r for r in brazil if (r.subscribers or 0) >= 1000]
    eligible_10k = [r for r in brazil if (r.subscribers or 0) >= 10_000]
    eligible_1m  = [r for r in brazil if (r.subscribers or 0) >= 1_000_000]
    return {
        "strategy": name,
        "queries": len(queries),
        "unique_discovered": len(all_ids),
        "validated_ok": len(ok),
        "brazil": len(brazil),
        "eligible_1k": len(eligible_1k),
        "eligible_10k": len(eligible_10k),
        "eligible_1m": len(eligible_1m),
        "discovery_s": round(discovery_time, 1),
        "validation_s": round(val_elapsed, 1),
        "channels_per_query": round(len(all_ids) / len(queries), 1),
        "conv_rate_brazil": round(len(brazil) / max(1, len(all_ids)) * 100, 1),
        "conv_rate_eligible_1k": round(len(eligible_1k) / max(1, len(all_ids)) * 100, 1),
    }


def main():
    print(f"running {len(QUERIES)} queries × 2 strategies")
    print(f"  queries: {QUERIES}\n")

    A = run_one_strategy("A: channel-filter", discover_via_channel_filter, QUERIES)
    print()
    B = run_one_strategy("B: video-owners ", discover_via_video_owners, QUERIES)

    print("\n" + "=" * 86)
    print(f"{'metric':30s}  {'A (channel-filter)':>22s}  {'B (video-owners)':>22s}")
    print("=" * 86)
    for k in ["unique_discovered", "validated_ok", "brazil",
              "eligible_1k", "eligible_10k", "eligible_1m",
              "channels_per_query",
              "conv_rate_brazil", "conv_rate_eligible_1k",
              "discovery_s", "validation_s"]:
        suffix = "%" if "conv_rate" in k else ""
        print(f"{k:30s}  {A[k]!s:>22s}{suffix}  {B[k]!s:>22s}{suffix}")
    print()
    delta = B["conv_rate_eligible_1k"] - A["conv_rate_eligible_1k"]
    factor = B["conv_rate_eligible_1k"] / max(0.01, A["conv_rate_eligible_1k"])
    print(f"B vs A: +{delta:.1f} percentage points eligible-rate ({factor:.2f}x relative)")
    # ETA recalculation
    target = 700_000
    rate_per_sec = 15  # v3 sustained
    if A["conv_rate_eligible_1k"] > 0:
        eta_A = target / (A["conv_rate_eligible_1k"]/100) / rate_per_sec / 3600
        print(f"ETA for 700K at A's conv rate: {eta_A:.1f} hours")
    if B["conv_rate_eligible_1k"] > 0:
        eta_B = target / (B["conv_rate_eligible_1k"]/100) / rate_per_sec / 3600
        print(f"ETA for 700K at B's conv rate: {eta_B:.1f} hours")


if __name__ == "__main__":
    main()

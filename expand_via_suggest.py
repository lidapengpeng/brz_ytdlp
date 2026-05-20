"""Expand query bank via YouTube Suggest API BFS.

Algorithm:
  1. Start from ~100 BR cultural taxonomy seeds (states, cities, music genres,
     sports teams, food, festivals, etc.)
  2. Layer 1: call YouTube Suggest API for each seed → ~14 suggestions each
  3. Layer 2: call Suggest for each Layer 1 NEW suggestion (not in seeds/bank)
  4. Layer 3 (optional): call Suggest for each Layer 2 NEW suggestion
  5. Output combined unique queries + comparison vs current query_bank.txt

Reference: long_term_research/05_query_bank_diversity.md §3.1
Expected yield: 100 seeds → 1500-3000 unique queries (97% novel vs current 36K bank).
"""
from __future__ import annotations

import json, time, urllib.parse, urllib.request, sys, os
from pathlib import Path
from typing import List, Set, Tuple

SUGGEST_URL = "https://suggestqueries-clients6.youtube.com/complete/search"
QUERY_BANK_CURRENT = Path(__file__).resolve().parent / "query_bank.txt"
QUERY_BANK_EXTENDED = Path(__file__).resolve().parent / "query_bank_extended.txt"
DUMP_PATH = Path(__file__).resolve().parent / "expand_via_suggest_results.json"

# ==== BR cultural taxonomy seeds (~100) ====
# Designed to maximize diversity — pick queries that surface different channel clusters.
SEEDS_BR_CULTURAL = [
    # === 27 capitals (state-level diversity) ===
    "são paulo", "rio de janeiro", "belo horizonte", "salvador", "fortaleza",
    "brasília", "curitiba", "porto alegre", "recife", "manaus",
    "belém", "goiânia", "vitória", "natal", "florianópolis",
    "cuiabá", "joão pessoa", "maceió", "campo grande", "teresina",
    "aracaju", "são luís", "porto velho", "palmas", "rio branco",
    "macapá", "boa vista",
    # === Music genres (regional diversity) ===
    "forró", "sertanejo", "funk carioca", "samba", "pagode",
    "axé", "piseiro", "pisadinha", "mpb", "bossa nova",
    "brega funk", "trap br", "rap nacional", "gospel brasileiro",
    "arrocha", "tecnobrega", "carimbó", "frevo", "maracatu",
    "vaneira", "modão",
    # === Sports (Série A clubs + categories) ===
    "flamengo", "palmeiras", "corinthians", "santos", "vasco",
    "fluminense", "botafogo", "atlético mineiro", "cruzeiro", "grêmio",
    "internacional", "bahia", "sport recife", "fortaleza ec",
    "ufc brasileiro", "vôlei brasil", "surf brasileiro", "skate brasil",
    # === Food (regional cuisine) ===
    "feijoada", "pão de queijo", "acarajé", "moqueca", "tapioca",
    "tacacá", "churrasco gaúcho", "feijão tropeiro", "baião de dois",
    "carne de sol", "vatapá", "pirarucu", "açaí",
    # === Festivals / cultural events ===
    "carnaval do rio", "carnaval salvador", "festa junina",
    "rock in rio", "lollapalooza brasil", "réveillon copacabana",
    # === Niche communities ===
    "religiosos brasil", "evangélico oração", "umbanda candomblé",
    "youtuber brasileiro", "podcast brasileiro", "tiktok brasil",
    # === Tech / business / education ===
    "empreendedorismo brasil", "educação financeira brasil",
    "tecnologia br", "concurso público brasil", "enem 2025",
    # === Mainstream content ===
    "novela brasileira", "stand up brasil", "humor brasileiro",
    "infantil brasileiro", "vlog familia brasileira",
    "receita brasileira", "viagem brasil", "moda brasileira",
]


def suggest(prefix: str, timeout: float = 8.0) -> List[str]:
    """Hit Suggest API, return up to ~14 query suggestions for the prefix.

    Returns [] on any error. JSONP unwrap is robust to slight format variations.
    """
    q = urllib.parse.urlencode({
        "client": "youtube", "ds": "yt", "q": prefix,
        "hl": "pt-BR", "gl": "BR",
    })
    req = urllib.request.Request(f"{SUGGEST_URL}?{q}", headers={
        "User-Agent": "Mozilla/5.0 (compatible; SuggestExpander/1.0)",
        "Accept-Language": "pt-BR,pt;q=0.9",
    })
    try:
        raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
        s = raw.find("(")
        e = raw.rfind(")")
        if s < 0 or e < 0 or e <= s:
            return []
        arr = json.loads(raw[s+1:e])
        # arr structure: ["prefix", [[suggestion, 0], [suggestion, 0], ...]]
        if not isinstance(arr, list) or len(arr) < 2:
            return []
        out = []
        for x in arr[1]:
            if isinstance(x, list) and x and isinstance(x[0], str):
                s = x[0].strip().lower()
                if s and s != prefix.strip().lower():
                    out.append(s)
        return out
    except Exception:
        return []


def bfs_expand(seeds: List[str], depth: int = 2, sleep: float = 0.12) -> dict:
    """BFS through suggest API up to given depth.

    Returns dict with per-layer stats + final unique queries.
    """
    visited: Set[str] = set()        # what we've called suggest() on
    all_queries: Set[str] = set()    # all unique queries seen (seeds + outputs)

    layers = []
    current_layer = [s.strip().lower() for s in seeds if s and s.strip()]
    all_queries.update(current_layer)
    visited.update(current_layer)

    for layer_idx in range(depth):
        t_start = time.time()
        next_layer_set: Set[str] = set()
        n_calls = 0
        n_errors = 0
        for prefix in current_layer:
            n_calls += 1
            sugs = suggest(prefix)
            if not sugs:
                n_errors += 1
            # only add suggestions we haven't visited (avoid cycles)
            for s in sugs:
                if s not in visited and len(s) >= 2 and len(s) < 100:
                    next_layer_set.add(s)
            time.sleep(sleep)
            if n_calls % 50 == 0:
                print(f"  layer {layer_idx+1}: {n_calls}/{len(current_layer)} calls "
                      f"({n_errors} err) so far, found {len(next_layer_set)} new",
                      flush=True)

        elapsed = time.time() - t_start
        # next layer becomes inputs for next iteration
        new_uniques = list(next_layer_set - visited)
        visited.update(next_layer_set)
        all_queries.update(next_layer_set)

        layers.append({
            "layer": layer_idx + 1,
            "input_count": len(current_layer),
            "suggest_calls": n_calls,
            "errors": n_errors,
            "raw_new_yield": len(next_layer_set),
            "unique_yield": len(new_uniques),
            "elapsed_s": elapsed,
            "rate_q_per_s": n_calls / max(0.001, elapsed),
        })
        print(f"\nLayer {layer_idx+1} done: {n_calls} calls, {elapsed:.1f}s, "
              f"+{len(new_uniques)} unique new queries", flush=True)

        if not new_uniques:
            print(f"  → layer {layer_idx+1} produced nothing new, stopping early.")
            break

        # Prepare next layer (cap to prevent explosion)
        if len(new_uniques) > 3000:
            print(f"  → capping next layer to 3000 (was {len(new_uniques)})")
            new_uniques = new_uniques[:3000]
        current_layer = new_uniques

    return {
        "seeds_count": len(seeds),
        "depth_executed": len(layers),
        "total_unique_queries": len(all_queries),
        "all_queries": sorted(all_queries),
        "layers": layers,
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=int, default=2, help="BFS depth (1-3)")
    ap.add_argument("--sleep", type=float, default=0.12,
                    help="seconds between suggest API calls (rate limit safety)")
    ap.add_argument("--seeds-only", action="store_true",
                    help="just print seeds and exit (no API calls)")
    args = ap.parse_args()

    if args.seeds_only:
        for s in SEEDS_BR_CULTURAL: print(s)
        return

    print(f"=== expand_via_suggest depth={args.depth} ===")
    print(f"seeds: {len(SEEDS_BR_CULTURAL)} BR cultural taxonomy entries\n")

    result = bfs_expand(SEEDS_BR_CULTURAL, depth=args.depth, sleep=args.sleep)

    # Compare against current bank
    if QUERY_BANK_CURRENT.exists():
        current_bank = set(
            l.strip().lower()
            for l in QUERY_BANK_CURRENT.read_text(encoding="utf-8").splitlines()
            if l.strip()
        )
    else:
        current_bank = set()
    new_set = set(result["all_queries"])
    overlap = new_set & current_bank
    novel = new_set - current_bank
    print(f"\n=== Bank comparison ===")
    print(f"  current bank size: {len(current_bank)}")
    print(f"  new suggest queries: {len(new_set)}")
    print(f"  overlap with current bank: {len(overlap)} ({len(overlap)/max(1,len(new_set))*100:.1f}%)")
    print(f"  pure NEW queries: {len(novel)} ({len(novel)/max(1,len(new_set))*100:.1f}%)")

    # Save dump
    result["bank_comparison"] = {
        "current_bank_size": len(current_bank),
        "new_size": len(new_set),
        "overlap": len(overlap),
        "novel": len(novel),
        "overlap_pct": len(overlap) / max(1, len(new_set)) * 100,
    }
    with open(DUMP_PATH, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nfull dump → {DUMP_PATH}")

    # Write extended bank: current ∪ novel (deduped, shuffled within file later by production_v2)
    extended = sorted(current_bank | novel)
    with open(QUERY_BANK_EXTENDED, "w") as f:
        for q in extended:
            f.write(q + "\n")
    print(f"extended bank ({len(extended)} queries) → {QUERY_BANK_EXTENDED}")
    print(f"  net growth: +{len(extended) - len(current_bank)} queries ({(len(extended) - len(current_bank))/max(1,len(current_bank))*100:.1f}%)")


if __name__ == "__main__":
    main()

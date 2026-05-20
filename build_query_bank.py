"""Build a high-quality, easy-to-read pt-BR query bank from all 5 lexicons.

Sources:
  - claude.txt, chatgpt.txt, deepseek.txt, gemini.txt, grok.txt  (all JSON)

Outputs:
  - queries.json          — structured by industry, with provenance & scores
  - queries.txt           — flat list, one query per line, ranked by BR-confidence
  - queries_report.md     — human-readable summary

Each niche is scored by pt-BR confidence:
  +3  contains 'brasil' / 'brasileiro' / 'br' / 'brasileira'
  +2  has Portuguese diacritics (ç, ã, õ, á, é, í, ó, ú, etc.)
  +2  contains BR-specific cultural words (sertanejo, pagode, feijoada, ...)
  -2  appears purely English with no pt signal (e.g. 'review', 'unboxing')

Queries with score >= 1 go in the 'high-confidence' bucket.
The rest get a 'brasil'/'brasileiro' suffix added to lift them.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

LEXICON_FILES = ["claude.txt", "chatgpt.txt", "deepseek.txt", "gemini.txt", "grok.txt"]

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = Path(__file__).resolve().parent

# Heuristic vocabularies
PT_DIACRITICS = set("çãõáéíóúâêôàèò")
BR_TOKENS = {"brasil", "brasileiro", "brasileira", "brasileiros", "brasileiras", "br"}
BR_CULTURAL = {
    # Music
    "sertanejo", "sertaneja", "pagode", "samba", "funk", "forró", "axé", "axe",
    "modão", "piseiro", "frevo", "maracatu", "ijexá", "carimbó", "lambada",
    "vaneirão", "vanerão", "chamamé", "guarânia", "tecnobrega", "brega",
    # Food
    "feijoada", "brigadeiro", "churrasco", "acarajé", "moqueca", "tapioca",
    "cuscuz", "vatapá", "pamonha", "canjica", "coxinha", "empada", "farofa",
    "pastel", "tutu", "baião", "rapadura", "paçoca", "guaraná", "caipirinha",
    "cachaça",
    # Places / states
    "paulista", "carioca", "mineira", "mineiro", "baiana", "baiano",
    "gaúcho", "gaucho", "gaúcha", "nordestino", "nordestina",
    "fluminense", "paranaense", "amazonense", "cearense", "pernambucano",
    "bahia", "pernambuco", "ceará", "amazonas", "pará", "maranhão",
    "favela", "periferia", "quebrada", "comunidade",
    # Soccer clubs
    "flamengo", "corinthians", "palmeiras", "santos", "vasco", "fluminense",
    "botafogo", "grêmio", "internacional", "cruzeiro", "atlético",
    "brasileirão", "libertadores", "paulistão", "cariocão", "neymar",
    # Religion (BR-dominant)
    "evangélico", "evangélica", "evangelica", "umbanda", "candomblé",
    # Misc
    "youtuber", "criadora", "criador", "canal", "inscritos",
    "vlogueira", "vlogueiro",
}
ENGLISH_GENERIC = {
    "review", "unboxing", "tutorial", "gameplay", "shorts", "live",
    "streamer", "react", "reaction", "challenge", "tag", "haul",
    "vlog", "daily", "morning", "night", "weekly", "monthly",
    "freelancer", "homeschooling", "fitness", "workout",
    "highlights", "edit", "skin", "mod", "rom", "console",
    # most "tech" English terms — they hurt BR signal
    "react", "node", "python", "java", "javascript", "html", "css",
    "csharp", "sql", "linux", "windows", "mac",
    # platform names that match worldwide
    "tiktok", "twitter", "reddit", "instagram", "facebook", "x",
}

# Add the pt-BR intent suffixes that lift weak niches into clear BR signal
LIFT_SUFFIXES = ["brasil", "brasileiro", "canal", "oficial"]


def _strip_fence(text: str) -> str:
    m = re.match(r"^\s*```(?:json)?\s*\n(.*?)\n```\s*$", text, re.DOTALL)
    return m.group(1) if m else text


def load_lexicon(path: Path) -> Any:
    try:
        text = _strip_fence(path.read_text(encoding="utf-8"))
        return json.loads(text)
    except Exception as e:
        print(f"  [warn] {path.name} parse failed: {e}")
        return None


def collect_industry_niches(data: Any) -> dict[str, list[str]]:
    """Walk for industry_name_pt + their level_2_niches arrays."""
    out: dict[str, list[str]] = defaultdict(list)

    def walk(node: Any, current_industry: str | None = None):
        if isinstance(node, dict):
            iname = node.get("industry_name_pt") or current_industry
            niches = node.get("level_2_niches")
            if isinstance(niches, list):
                for n in niches:
                    if isinstance(n, str):
                        out[iname or "Sem categoria"].append(n)
            for k, v in node.items():
                if k != "level_2_niches":
                    walk(v, iname)
        elif isinstance(node, list):
            for x in node:
                walk(x, current_industry)

    walk(data)
    return dict(out)


def normalize(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def diacritic_count(s: str) -> int:
    return sum(1 for c in s.lower() if c in PT_DIACRITICS)


def score_niche(s: str) -> tuple[int, list[str]]:
    """Return (score, reasons)."""
    s_norm = normalize(s)
    tokens = set(s_norm.split())
    reasons = []
    score = 0
    if tokens & BR_TOKENS:
        score += 3; reasons.append("BR-token")
    if diacritic_count(s_norm) > 0:
        score += 2; reasons.append("pt-diacritic")
    if tokens & BR_CULTURAL:
        score += 2; reasons.append("BR-cultural")
    if tokens & ENGLISH_GENERIC and not (tokens & (BR_TOKENS | BR_CULTURAL)):
        # all-english-generic words drop score
        if all(t in ENGLISH_GENERIC for t in tokens):
            score -= 2; reasons.append("eng-generic")
    return score, reasons


def main():
    print("loading lexicons...")
    all_industry_niches: dict[str, dict[str, list[str]]] = {}  # source -> industry -> niches
    for fname in LEXICON_FILES:
        path = ROOT / fname
        if not path.exists():
            print(f"  [skip] {fname} not found"); continue
        data = load_lexicon(path)
        if data is None:
            print(f"  [skip] {fname} unparseable"); continue
        industry_niches = collect_industry_niches(data)
        all_industry_niches[fname] = industry_niches
        total = sum(len(ns) for ns in industry_niches.values())
        print(f"  {fname}: {len(industry_niches)} industries, {total} niche entries")

    # Merge all sources: industry -> set of unique niches + provenance
    merged: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    # merged[industry][niche] = set of source filenames
    industry_titles: set[str] = set()
    for source, industry_niches in all_industry_niches.items():
        for industry, niches in industry_niches.items():
            industry_titles.add(industry)
            for n in niches:
                n_norm = normalize(n)
                if 2 <= len(n_norm) <= 60 and 1 <= len(n_norm.split()) <= 6:
                    merged[industry][n_norm].add(source)

    # Now score every unique niche and bucket by confidence
    structured: dict[str, list[dict]] = {}  # industry -> list of niche records
    seen_global: set[str] = set()
    high_confidence_count = 0
    total_unique = 0
    for industry in sorted(merged.keys()):
        recs = []
        for niche, sources in sorted(merged[industry].items()):
            if niche in seen_global:
                continue
            seen_global.add(niche)
            total_unique += 1
            sc, reasons = score_niche(niche)
            if sc >= 1:
                high_confidence_count += 1
            recs.append({
                "niche": niche,
                "score": sc,
                "reasons": reasons,
                "sources": sorted(sources),
                "queries": []  # to fill below
            })
        # Sort per industry by score desc
        recs.sort(key=lambda r: (-r["score"], r["niche"]))
        structured[industry] = recs

    # Now generate query variants. For each niche:
    #   - if score >= 1: include the niche as-is (already pt-BR signal)
    #   - if score < 1: lift it with a BR/intent suffix (or skip if score deeply negative)
    flat_queries: list[tuple[int, str, str]] = []  # (score, query, industry)
    for industry, recs in structured.items():
        for r in recs:
            niche = r["niche"]
            queries: list[str] = []
            if r["score"] >= 1:
                queries.append(niche)
                # Plus 1-2 strong intent variants
                for sx in ("brasil", "canal"):
                    if sx not in niche:
                        queries.append(f"{niche} {sx}")
            else:
                # Need to lift — add ALL lift suffixes to give it BR signal
                for sx in LIFT_SUFFIXES:
                    if sx not in niche:
                        queries.append(f"{niche} {sx}")
            # Dedupe within record
            seen = set()
            r["queries"] = [q for q in queries if not (q in seen or seen.add(q))]
            for q in r["queries"]:
                flat_queries.append((r["score"], q, industry))

    # ---- Write outputs ----
    # 1. structured queries.json
    out_json_path = OUT_DIR / "query_bank.json"
    with out_json_path.open("w", encoding="utf-8") as f:
        json.dump({
            "meta": {
                "generated_from": LEXICON_FILES,
                "industries": len(structured),
                "unique_niches": total_unique,
                "high_confidence_niches": high_confidence_count,
                "total_queries": len(flat_queries),
                "scoring": {
                    "+3": "niche contains 'brasil'/'brasileiro'/'br'",
                    "+2": "pt diacritic (ç ã õ á é etc.)",
                    "+2": "BR-cultural term (sertanejo, feijoada, flamengo, ...)",
                    "-2": "all-English generic (review, unboxing, vlog, ...)",
                },
                "lift_suffixes_for_low_score": LIFT_SUFFIXES,
            },
            "by_industry": structured,
        }, f, ensure_ascii=False, indent=2)
    print(f"\nwrote {out_json_path}")

    # 2. flat queries.txt — ranked by score desc, deduped
    flat_queries.sort(key=lambda x: (-x[0], x[1]))
    seen_q = set()
    out_txt_path = OUT_DIR / "query_bank.txt"
    with out_txt_path.open("w", encoding="utf-8") as f:
        for sc, q, industry in flat_queries:
            if q in seen_q: continue
            seen_q.add(q)
            f.write(f"{q}\n")
    print(f"wrote {out_txt_path} ({len(seen_q)} unique queries)")

    # 3. report.md — human-readable
    out_md_path = OUT_DIR / "query_bank_report.md"
    with out_md_path.open("w", encoding="utf-8") as f:
        f.write("# pt-BR Query Bank\n\n")
        f.write(f"Generated from: {', '.join(LEXICON_FILES)}\n\n")
        f.write(f"- **{len(structured)}** industries\n")
        f.write(f"- **{total_unique}** unique niches\n")
        f.write(f"- **{high_confidence_count}** high-confidence niches (score ≥ 1)\n")
        f.write(f"- **{len(seen_q)}** total unique queries\n\n")
        f.write("## Scoring rules\n\n")
        f.write("| Score | Reason |\n|---|---|\n")
        f.write("| +3 | contains 'brasil'/'brasileiro'/'br' token |\n")
        f.write("| +2 | Portuguese diacritic (ç, ã, õ, á, é, …) |\n")
        f.write("| +2 | BR-cultural term (sertanejo, feijoada, flamengo, etc.) |\n")
        f.write("| -2 | all-English generic (review, unboxing, vlog, …) |\n\n")
        f.write("## Industry breakdown\n\n")
        f.write("| Industry | Niches | Queries | Top sample |\n|---|---|---|---|\n")
        for industry, recs in structured.items():
            top_sample = "; ".join(r["niche"] for r in recs[:3])
            n_queries = sum(len(r["queries"]) for r in recs)
            f.write(f"| {industry} | {len(recs)} | {n_queries} | {top_sample} |\n")
        f.write("\n## Top 30 highest-confidence queries (score)\n\n")
        for sc, q, industry in flat_queries[:30]:
            f.write(f"- `{q}` (score={sc}, industry={industry})\n")
    print(f"wrote {out_md_path}")

    # 4. console summary
    print("\n=== summary ===")
    print(f"  industries          : {len(structured)}")
    print(f"  unique niches       : {total_unique}")
    print(f"  high-confidence     : {high_confidence_count} ({high_confidence_count/max(1,total_unique)*100:.1f}%)")
    print(f"  total unique queries: {len(seen_q)}")
    print(f"\nTop 10 highest-scored queries:")
    for sc, q, industry in flat_queries[:10]:
        print(f"  [{sc:>2d}]  {q:<45s}  ({industry})")


if __name__ == "__main__":
    main()

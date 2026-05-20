from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import time
from collections import Counter, defaultdict
from datetime import datetime


ROOT = pathlib.Path(__file__).resolve().parent
PWCLI = pathlib.Path("/Users/dapeng/.codex/skills/playwright/scripts/playwright_cli.sh")


BR_TERMS = [
    "brasil", "brazil", "brasileiro", "brasileira", "brasileiros", "brasileiras",
    "brasilia", "brasília", "com.br", "gov.br", ".br", "pix", "cnpj", "cpf", "cep", "r$",
    "sao paulo", "são paulo", "paulista", "rio de janeiro", "carioca",
    "belo horizonte", "minas gerais", "mineiro", "mineira",
    "porto alegre", "rio grande do sul", "gaucho", "gaúcho",
    "curitiba", "parana", "paraná", "florianopolis", "florianópolis", "santa catarina",
    "sorocaba", "campinas", "santos", "ribeirão preto", "ribeirao preto",
    "salvador", "bahia", "baiano", "baiana", "recife", "pernambuco",
    "fortaleza", "ceara", "ceará", "goiania", "goiânia", "goias", "goiás",
    "belem", "belém", "manaus", "amazonas", "vitoria", "vitória", "espirito santo", "espírito santo",
    "maceio", "maceió", "aracaju", "natal", "joao pessoa", "joão pessoa",
    "teresina", "sao luis", "são luís", "campo grande", "cuiaba", "cuiabá",
    "nordeste", "nordestino", "sertanejo", "forró", "forro", "pagode", "samba",
    "funk carioca", "brega", "pisadinha", "piseiro", "arrocha", "axé", "axe",
    "flamengo", "corinthians", "palmeiras", "vasco", "botafogo", "fluminense",
    "gremio", "grêmio", "internacional", "cruzeiro", "atlético mineiro", "atletico mineiro",
    "bahia", "sport recife", "santa cruz", "náutico", "nautico", "fortaleza ec",
    "sus", "enem", "oab", "fgts", "inss", "senai", "senac", "sebrae", "sesc",
    "prefeitura", "câmara municipal", "camara municipal", "diário oficial", "diario oficial",
    "clt", "mei", "ibge", "petrobras", "embrapa", "caixa econômica", "caixa economica",
    "banco do brasil", "b3", "mini dólar", "mini dolar", "mini-índice", "mini-indice",
    "pataxó", "pataxo", "yanomami", "guarani", "tupiniquim", "kamayura", "xingu",
]

PT_TERMS = [
    "você", "voce", "vocês", "voces", "seja", "sejam", "bem-vindo", "bem vindo",
    "canal", "inscreva", "inscreva-se", "vídeo", "video", "vídeos", "videos",
    "aqui", "conteúdo", "conteudo", "oficial", "todos", "dias", "muito", "muita",
    "olá", "ola", "obrigado", "aprenda", "educação", "física", "dança", "vendas",
    "música", "musica", "engenharia", "receitas", "comédia", "comedia", "humor",
    "família", "familia", "notícias", "noticias", "futebol", "aula", "aulas",
    "dicas", "história", "historia", "brinquedos", "crianças", "criancas",
]


def build_chunk_code(rows: list[dict]) -> str:
    rows_js = json.dumps(rows, ensure_ascii=False)
    br_terms_js = json.dumps(BR_TERMS, ensure_ascii=False)
    pt_terms_js = json.dumps(PT_TERMS, ensure_ascii=False)
    return f"""
(async page => {{
  const rows = {rows_js};
  const BR_TERMS = {br_terms_js};
  const PT_TERMS = {pt_terms_js};
  const norm = s => String(s || '').toLowerCase()
    .normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
  const subRe = /((?:\\d+[\\.,]?\\d*|\\d+)\\s*(?:万|亿)?\\s*位订阅者|(?:\\d+[\\.,]?\\d*)\\s*(?:K|M|mi|mil)?\\s*(?:subscribers|inscritos))/i;
  const chineseRe = /[\\u4e00-\\u9fff]/;
  const dddRe = /\\(?\\b(?:11|12|13|14|15|16|17|18|19|21|22|24|27|28|31|32|33|34|35|37|38|41|42|43|44|45|46|47|48|49|51|53|54|55|61|62|63|64|65|66|67|68|69|71|73|74|75|77|79|81|82|83|84|85|86|87|88|89|91|92|93|94|95|96|97|98|99)\\)?\\s?9?\\d{{4}}[-\\s]?\\d{{4}}\\b/;

  if (!globalThis.__brzRouteSet) {{
    await page.route('**/*', route => {{
      const type = route.request().resourceType();
      if (['image', 'media', 'font'].includes(type)) return route.abort();
      return route.continue();
    }});
    globalThis.__brzRouteSet = true;
  }}

  function analyze(row, text, finalUrl, title) {{
    const lines = String(text || '').split(/\\r?\\n/).map(s => s.trim()).filter(Boolean);
    const nt = norm(text);
    const brHits = BR_TERMS.filter(t => nt.includes(norm(t))).slice(0, 16);
    const ptHits = PT_TERMS.filter(t => nt.includes(norm(t))).slice(0, 16);
    const visibleCountryBrazil = lines.some(l => l === '巴西' || /^brasil$/i.test(l) || /^brazil$/i.test(l));
    const visibleSubscribers = (String(text || '').match(subRe) || [''])[0];
    const hasBrazilPhone = dddRe.test(String(text || ''));
    const hasDiacritics = /[ãõçáéíóúâêôàÃÕÇÁÉÍÓÚÂÊÔÀ]/.test(String(text || ''));
    const brOk = visibleCountryBrazil || brHits.length > 0 || hasBrazilPhone;
    const ptOk = ptHits.length > 0 || hasDiacritics;
    const subsOk = Boolean(visibleSubscribers) || Number(row.subscribers || 0) >= 1000;
    let verdict = 'NEEDS_REVIEW';
    if (subsOk && brOk && ptOk) verdict = 'PASS_BROWSER_EVIDENCE';
    else if (subsOk && ptOk && !brOk) verdict = 'NEEDS_COUNTRY_EVIDENCE';
    else if (subsOk && brOk && !ptOk) verdict = 'NEEDS_PORTUGUESE_EVIDENCE';

    const evidence = [];
    for (const raw of lines) {{
      const line = raw.length > 220 ? raw.slice(0, 220) : raw;
      const low = norm(line);
      const latin = /[A-Za-zÀ-ÿ]/.test(line);
      const brLine = BR_TERMS.some(t => low.includes(norm(t))) || dddRe.test(line) || line === '巴西';
      const ptLine = PT_TERMS.some(t => low.includes(norm(t))) || /[ãõçáéíóúâêôàÃÕÇÁÉÍÓÚÂÊÔÀ]/.test(line);
      if ((latin || line === '巴西') && (brLine || ptLine) && !evidence.includes(line)) evidence.push(line);
      if (evidence.length >= 8) break;
    }}
    return {{
      sample_index: row.sample_index,
      channel_id: row.channel_id,
      name: row.name,
      handle: row.handle,
      db_subscribers: row.subscribers,
      db_country: row.country,
      db_target_reason: row.target_reason,
      requested_url: row.url,
      final_url: finalUrl,
      title,
      visible_subscribers: visibleSubscribers,
      visible_country_brazil: visibleCountryBrazil,
      browser_br_hits: brHits,
      browser_pt_hits: ptHits,
      has_brazil_phone: hasBrazilPhone,
      evidence_lines: evidence,
      verdict,
      text_len: String(text || '').length,
      text_preview: String(text || '').slice(0, 900),
    }};
  }}

  const out = [];
  for (const row of rows) {{
    try {{
      await page.goto(row.url, {{ waitUntil: 'domcontentloaded', timeout: 25000 }});
      await page.waitForTimeout(1200);
      let text = await page.evaluate(() => document.body ? document.body.innerText : '');
      if (!text || text.length < 500) {{
        await page.waitForTimeout(1600);
        text = await page.evaluate(() => document.body ? document.body.innerText : '');
      }}
      out.push(analyze(row, text, page.url(), await page.title()));
    }} catch (e) {{
      out.push({{
        sample_index: row.sample_index,
        channel_id: row.channel_id,
        name: row.name,
        handle: row.handle,
        db_subscribers: row.subscribers,
        db_country: row.country,
        db_target_reason: row.target_reason,
        requested_url: row.url,
        verdict: 'FETCH_ERROR',
        error: String(e && e.message || e).slice(0, 500),
      }});
    }}
  }}
  return out;
}})
"""


def run_chunk(chunk_rows: list[dict], chunk_index: int) -> list[dict]:
    code_path = ROOT / f".browser_random1000_chunk_{chunk_index:03d}.js"
    code_path.write_text(build_chunk_code(chunk_rows), encoding="utf-8")
    cmd = [str(PWCLI), "--raw", "run-code", "--filename", str(code_path)]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=240)
    if proc.returncode != 0:
        raise RuntimeError(f"chunk {chunk_index} failed: {proc.stderr[:800]} {proc.stdout[:800]}")
    try:
        return sanitize(json.loads(proc.stdout))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"chunk {chunk_index} returned non-json: {proc.stdout[:1000]}") from exc


def sanitize(value):
    if isinstance(value, str):
        return value.encode("utf-8", "replace").decode("utf-8")
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, dict):
        return {sanitize(k): sanitize(v) for k, v in value.items()}
    return value


def write_report(results: list[dict], out_md: pathlib.Path) -> None:
    verdict_counts = Counter(r.get("verdict") for r in results)
    by_db_country = defaultdict(Counter)
    for r in results:
        key = "country_BR" if r.get("db_country") in ("Brasil", "Brazil") else "country_NULL"
        by_db_country[key][r.get("verdict")] += 1

    lines = [
        "# Browser random-1000 validation report",
        "",
        f"Validation time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Asia/Shanghai",
        "",
        "Method: 1000 rows were randomly sampled from the SQLite snapshot, then each public YouTube `/about` page was opened in a Playwright browser session. The verdict uses browser-rendered text, not only DB fields.",
        "",
        "## Summary",
        "",
        f"- Sample size: {len(results)}",
    ]
    for verdict, count in verdict_counts.most_common():
        lines.append(f"- {verdict}: {count}")
    lines += ["", "## By DB Country", ""]
    for key, counts in by_db_country.items():
        lines.append(f"- {key}: " + ", ".join(f"{v}={n}" for v, n in counts.most_common()))

    weak = [r for r in results if r.get("verdict") != "PASS_BROWSER_EVIDENCE"]
    lines += ["", "## Non-Pass Samples", ""]
    for r in weak[:120]:
        lines += [
            f"### {r.get('sample_index')}. {r.get('name')} ({r.get('channel_id')})",
            "",
            f"- DB: subscribers={r.get('db_subscribers')}, country={r.get('db_country')}, target_reason={r.get('db_target_reason')}",
            f"- Browser verdict: `{r.get('verdict')}`",
            f"- Visible subscribers: {r.get('visible_subscribers') or 'not parsed'}",
            f"- Visible country row Brazil: {r.get('visible_country_brazil')}",
            f"- BR hits: {', '.join(r.get('browser_br_hits') or []) or 'none'}",
            f"- PT hits: {', '.join(r.get('browser_pt_hits') or []) or 'none'}",
            "- Evidence lines:",
        ]
        for ev in r.get("evidence_lines") or []:
            lines.append(f"  - {ev}")
        if r.get("error"):
            lines.append(f"- Error: {r.get('error')}")
        lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", default="browser_random1000_sample_20260517_141811.json")
    ap.add_argument("--chunk-size", type=int, default=20)
    ap.add_argument("--out-prefix", default="browser_random1000_20260517_141811")
    args = ap.parse_args()

    rows = json.loads((ROOT / args.sample).read_text(encoding="utf-8"))
    out_jsonl = ROOT / f"{args.out_prefix}.jsonl"
    out_json = ROOT / f"{args.out_prefix}.json"
    out_md = ROOT / f"{args.out_prefix}.md"
    out_jsonl.write_text("", encoding="utf-8")

    all_results: list[dict] = []
    chunks = [rows[i:i + args.chunk_size] for i in range(0, len(rows), args.chunk_size)]
    start = time.time()
    for idx, chunk in enumerate(chunks, 1):
        chunk_start = time.time()
        results = run_chunk(chunk, idx)
        all_results.extend(results)
        with out_jsonl.open("a", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        counts = Counter(r.get("verdict") for r in all_results)
        elapsed = time.time() - start
        print(
            f"[{idx:03d}/{len(chunks):03d}] rows={len(all_results):4d}/{len(rows)} "
            f"chunk_s={time.time()-chunk_start:5.1f} elapsed_m={elapsed/60:5.1f} "
            + " ".join(f"{k}={v}" for k, v in counts.most_common()),
            flush=True,
        )

    out_json.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(all_results, out_md)
    print(f"DONE jsonl={out_jsonl}")
    print(f"DONE json={out_json}")
    print(f"DONE md={out_md}")


if __name__ == "__main__":
    main()

# Browser sample review

Time: 2026-05-17 12:18 Asia/Shanghai

Input DB: `/Users/dapeng/Desktop/word/brz_ytdlp/results.db`

Browser evidence files:

- `/Users/dapeng/Desktop/word/brz_ytdlp/browser_sample_report_20260517_1200.md`
- `/Users/dapeng/Desktop/word/brz_ytdlp/browser_second_pass_weak_samples_20260517_1200.jsonl`

## Result

I sampled 24 channels across four buckets and opened public YouTube channel pages in a real browser:

- 4 explicit `country=Brasil` + strict local Portuguese pass
- 4 explicit `country=Brasil` but weak stored-description language signal
- 6 `country IS NULL` with local Brazil signal
- 10 `country IS NULL` with Portuguese-only local evidence

Reviewed result:

- Strong browser pass: 19 / 24
- Likely Brazil but not strict country proof from page text: 1 / 24
- Still missing direct browser-visible country/Brazil evidence: 4 / 24

## Strong Pass Examples

- `Cortes-style explicit country sample`: YouTube about dialog shows country row `巴西`, visible subscribers, and Portuguese video/about text.
- `Marcos Orlandini`: browser-visible video titles include `Santa Catarina`, `Águas Mornas - SC`, and `Rancho Queimado - SC`; this is strong Brazil locality evidence even though the YouTube country row is absent.
- `WM Vintage Club`: about text says `Sorocaba`, a Brazil city, and Portuguese channel description.
- `Gaby Azevedo- Trader`: about text references `mini-indice` / `mini-dolar`, Brazilian B3 futures-market terminology, plus Portuguese content.
- `Banda Diesel`: explicit browser-visible `Belo Horizonte - Brasil`; video title `Show completo em Belo Horizonte` gives enough Portuguese/Brazil context for the sampled check.

## Still Weak After Browser Check

These sampled channels had subscribers and Portuguese text, but I did not find strict browser-visible Brazil-country evidence on the channel/about/videos text:

- `UCNalsCNNx84Q6j_mutQ_8AQ` — Léo Medeiros
- `UCJmh73kPiGhN2xzvUsbNCBg` — Joyce Lopes
- `UCoNE6jXS4DZS060WJY9s96w` — Victor Hugo | Vendas
- `UCONubdfhAL1WPL-7dE4-_Cw` — canal falido

One sampled channel is Brazil-likely but still not strict proof:

- `UCS9a_eBLqdYiA_3mJWXc6dw` — REGINALDO PORTILHO: browser-visible content is Portuguese and heavily centered on Brazil-specific Volkswagen culture (`Gol GTI`, `Saveiro`, `Gol quadrado`), but the page did not show a country row or explicit Brazil location.

## Interpretation

The sample supports that explicit `country=Brasil` rows are solid.

The `country IS NULL AND target_reason=country=None,lang=pt` fallback is useful, but it is not equivalent to strict country proof. In this 16-row missing-country sample, 11 had strong browser-visible Brazil evidence, 1 was Brazil-likely, and 4 still lacked direct country evidence from the pages checked.

Recommendation: keep the fallback rows as candidates, but do not label them as fully country-proven unless a second evidence field is recorded, such as visible country row, Brazil city/state, `.br` link, Brazil institution, B3/PIX/CNPJ/CPF, or repeated Brazil-local video/title evidence.

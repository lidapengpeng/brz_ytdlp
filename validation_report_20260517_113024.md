# results.db channel validation report

Validation time: 2026-05-17 11:30:24 Asia/Shanghai

Database checked: `/Users/dapeng/Desktop/word/brz_ytdlp/results.db`

Stable snapshot: `/Users/dapeng/Desktop/word/brz_ytdlp/results_validation_snapshot_20260517_113024.db`

## Conclusion

The current `channels` table passes the hard import gate:

- Total rows: 58,290
- Rows with `subscribers >= 1000`: 58,290
- Rows with `is_target = 1`: 58,290
- SQL hard-rule violations: 0
- Duplicate `channel_id`: 0; no duplicate risk because `channel_id` is the primary key

Country split:

- `country = Brasil`: 50,009
- `country IS NULL` with `target_reason = country=None,lang=pt`: 8,281

## Portuguese Evidence

Language check used local `langdetect` plus `langid`, with strict pass only when both detectors returned `pt`.

All rows:

- Strict Portuguese pass: 50,590
- One detector says Portuguese: 1,359
- Description too short or empty: 5,151
- Neither detector says Portuguese: 1,190

Rows with missing country:

- Total: 8,281
- Strict Portuguese pass: 8,272
- One detector says Portuguese: 9
- Neither detector says Portuguese: 0
- Description too short or empty: 0

## Brazil Evidence For Missing Country Rows

For the 8,281 rows where YouTube did not expose a country field, I checked fast local Brazil signals in channel name and description, including `Brasil/brasileiro`, `.br`, `gov.br`, PIX, CNPJ/CPF, R$, Brazilian cities/states/demonyms, cultural terms, football clubs, public institutions, and Brazilian phone-area patterns.

- Missing-country rows with strong local Brazil signal: 6,014
- Missing-country rows with Portuguese evidence but no strong local Brazil text signal: 2,267

This means the missing-country cohort is very likely useful, but not all of it is independently country-proven from the fields currently stored in `results.db`.

## Risk Interpretation

If the acceptance rule is the current pipeline rule, `country=Brasil OR country missing + Portuguese description`, the database is clean.

If the acceptance rule is a strict factual rule that every row must have independently proven Brazil country plus Portuguese language, the database still has a residual risk set:

- 2,267 missing-country rows need additional Brazil evidence.
- 5,151 explicit-Brazil rows have descriptions too short or empty, so Portuguese cannot be proven from the stored description alone.
- 1,190 explicit-Brazil rows have descriptions where neither language detector returned Portuguese; some may be music/contact/link descriptions rather than real non-Portuguese channels.

Recommended next verification pass: enrich only the residual risk set using recent video titles/descriptions or live channel re-extraction, instead of rescanning all 58,290 rows.

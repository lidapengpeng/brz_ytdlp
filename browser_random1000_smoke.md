# Browser random-1000 validation report

Validation time: 2026-05-17 14:23:50 Asia/Shanghai

Method: 1000 rows were randomly sampled from the SQLite snapshot, then each public YouTube `/about` page was opened in a Playwright browser session. The verdict uses browser-rendered text, not only DB fields.

## Summary

- Sample size: 2
- FETCH_ERROR: 2

## By DB Country

- country_BR: FETCH_ERROR=2

## Non-Pass Samples

### 1. Cezar Augusto Fotografia (UCnevSGxAIzNkjll397ftPDg)

- DB: subscribers=307000, country=Brasil, target_reason=country=Brazil
- Browser verdict: `FETCH_ERROR`
- Visible subscribers: not parsed
- Visible country row Brazil: None
- BR hits: none
- PT hits: none
- Evidence lines:
- Error: setTimeout is not defined

### 2. Dr. João Dias - Reprodução Humana (UCstKns5Is1NOhzVFpaCE-iQ)

- DB: subscribers=5130, country=Brasil, target_reason=country=Brazil
- Browser verdict: `FETCH_ERROR`
- Visible subscribers: not parsed
- Visible country row Brazil: None
- BR hits: none
- PT hits: none
- Evidence lines:
- Error: setTimeout is not defined

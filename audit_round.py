"""Audit one round: re-extract a list of channels live and compare with DB values."""
import sys
import json
import time
import random
from extract_v4 import extract, detect_pt


def extract_with_retry(cid, max_attempts=5):
    """Retry on SSL/network errors with exponential backoff."""
    last_err = None
    for attempt in range(max_attempts):
        try:
            info = extract(None, cid)
            if info.error and ("SSL" in info.error or "timeout" in info.error.lower() or "EOF" in info.error or "Connection" in info.error or "HTTPError" in info.error):
                last_err = info.error
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"  attempt {attempt+1} failed: {info.error[:80]}; sleeping {wait:.1f}s", flush=True)
                time.sleep(wait)
                continue
            return info
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            wait = (2 ** attempt) + random.uniform(0, 1)
            print(f"  attempt {attempt+1} raised: {last_err[:80]}; sleeping {wait:.1f}s", flush=True)
            time.sleep(wait)
    # final attempt outside try
    return extract(None, cid)

# Read samples from stdin as TSV: channel_id\tname\thandle\tdb_subs\tdb_country\ttarget_reason
samples = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    parts = line.split("|")
    if len(parts) < 6:
        continue
    # Last 4 fields are well-defined; first field is channel_id; middle joined back is name
    channel_id = parts[0]
    target_reason = parts[-1]
    db_country = parts[-2]
    db_subs = parts[-3]
    handle = parts[-4]
    name = "|".join(parts[1:-4])
    db_subs = int(db_subs) if db_subs else None
    db_country = db_country if db_country else None
    samples.append({
        "channel_id": channel_id,
        "name": name,
        "handle": handle,
        "db_subs": db_subs,
        "db_country": db_country,
        "target_reason": target_reason,
    })

results = []
for i, s in enumerate(samples, 1):
    if i > 1:
        time.sleep(random.uniform(1.0, 2.5))  # space out requests
    cid = s["channel_id"]
    print(f"[{i}/{len(samples)}] {cid} ({s['name']!r}) extracting...", flush=True)
    try:
        info = extract_with_retry(cid)
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}", flush=True)
        s["live_subs"] = None
        s["live_country"] = None
        s["live_description"] = None
        s["verdict"] = f"ERROR: {type(e).__name__}"
        results.append(s)
        continue

    live_subs = info.subscribers
    live_country = info.country
    live_desc = info.description
    s["live_subs"] = live_subs
    s["live_country"] = live_country
    s["live_description"] = (live_desc or "")[:200]

    # Compare subs within 5%
    subs_ok = False
    if s["db_subs"] is not None and live_subs is not None:
        diff_pct = abs(live_subs - s["db_subs"]) / max(1, s["db_subs"]) * 100
        subs_ok = diff_pct <= 5.0
        s["subs_diff_pct"] = diff_pct
    else:
        subs_ok = (s["db_subs"] is None and live_subs is None)
        s["subs_diff_pct"] = None

    # Country match
    country_ok = False
    extra_note = ""
    if s["db_country"] == "Brasil":
        country_ok = (live_country == "Brasil")
    elif s["db_country"] is None and "lang=pt" in (s.get("target_reason") or ""):
        # confirm langdetect=pt on (live description or name)
        text_for_lang = (live_desc or s["name"] or "").strip()
        is_pt = detect_pt(text_for_lang)
        country_ok = (live_country is None and is_pt) or (live_country == "Brasil")
        extra_note = " (langdetect=pt)" if is_pt else " (langdetect FAILED)"
    else:
        country_ok = (s["db_country"] == live_country)

    if subs_ok and country_ok:
        s["verdict"] = "PASS" + extra_note
    else:
        reasons = []
        if not subs_ok:
            sdp = s.get('subs_diff_pct')
            if sdp is None:
                reasons.append(f"subs_db={s['db_subs']} live={live_subs}")
            else:
                reasons.append(f"subs_diff={sdp:.1f}%")
        if not country_ok:
            reasons.append(f"country_db={s['db_country']} live={live_country}{extra_note}")
        s["verdict"] = "FAIL: " + ", ".join(reasons)
    print(f"  -> live_subs={live_subs} live_country={live_country} {s['verdict']}", flush=True)
    results.append(s)

# Print JSON to stdout (markers help parse)
print("---RESULTS-JSON---")
print(json.dumps(results, ensure_ascii=False))

"""Test: is the about-panel UUID session-bound or channel-bound?

If session-bound, we can fetch stage 1 once and reuse the panel UUID across many
stage 2 calls for different channel IDs — that'd reduce per-channel cost from
~1MB to ~10KB (a ~100x improvement on bandwidth).

If channel-bound, we have to do stage 1 + stage 2 per channel as designed.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import base64
import yt_dlp

from extract_v2 import _get_about_panel_token, _find_first, make_ydl, ExtractorConfig

# Three known-good real channels
CHANNELS = [
    "UCr4ARxgElIO21GWfIraZezg",  # Garena Free Fire Brasil (BR)
    "UCJ0-OtVpF0wOKEqT2Z1HEtA",  # ElectroBOOM (CA)
    "UC295-Dw_tDNtZXFeAPAW6Aw",  # 5-Minute Crafts (US)
]


def decode_token(token: str) -> bytes:
    """URL-decode then base64-decode the panel continuation token."""
    s = urllib.parse.unquote(token)
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def extract_uuid_from_token(token: str) -> str:
    """Get the UUID-looking string that's wrapped inside the token."""
    raw = decode_token(token)
    # Find a UUID pattern (8-4-4-4-12 hex)
    m = re.search(rb"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", raw)
    return m.group(1).decode() if m else "<no UUID found>"


def main():
    ydl = make_ydl(ExtractorConfig(skip_webpage=True))
    ie = ydl.get_info_extractor("YoutubeTab")

    print(f"yt-dlp {yt_dlp.version.__version__}")
    print()

    # ----- Test 1: collect tokens + UUIDs for 3 different channels -----
    print("=" * 80)
    print("TEST 1: collect about-panel tokens from 3 different channels")
    print("=" * 80)
    tokens = {}
    for cid in CHANNELS:
        t0 = time.time()
        resp1 = ie._call_api(ep="browse", video_id=cid, query={"browseId": cid})
        elapsed = time.time() - t0
        tk = _get_about_panel_token(resp1)
        if not tk:
            print(f"  {cid}  FAIL — no token  ({elapsed:.2f}s)")
            continue
        uuid = extract_uuid_from_token(tk)
        tokens[cid] = tk
        print(f"  {cid}  token_uuid={uuid}  ({elapsed:.2f}s, {len(json.dumps(resp1)):,} bytes)")

    # ----- Test 2: cross-channel token portability -----
    print()
    print("=" * 80)
    print("TEST 2: can channel A's token return channel B's about data?")
    print("=" * 80)
    if len(tokens) >= 2:
        cid_a = CHANNELS[0]
        cid_b = CHANNELS[1]
        cid_c = CHANNELS[2]
        # Try B's token with C's video_id (just for tracking)
        for src_cid, tgt_cid in [(cid_a, cid_b), (cid_b, cid_a), (cid_a, cid_c)]:
            print(f"\n  --- using {src_cid}'s token to call /browse for channel {tgt_cid} ---")
            try:
                resp2 = ie._call_api(ep="browse", video_id=tgt_cid,
                                     query={"continuation": tokens[src_cid]})
                avm = _find_first(resp2, "aboutChannelViewModel")
                if isinstance(avm, dict):
                    returned_cid = avm.get("channelId")
                    country = avm.get("country")
                    subs = avm.get("subscriberCountText")
                    print(f"  returned channel_id={returned_cid!r}  country={country!r}  subs={subs!r}")
                    if returned_cid == src_cid:
                        print(f"  ↳ token is BOUND to source channel ({src_cid}) — non-portable")
                    elif returned_cid == tgt_cid:
                        print(f"  ↳ token is PORTABLE — returned target's data!")
                    else:
                        print(f"  ↳ token returned UNEXPECTED channel data")
                else:
                    # Might be onResponseReceivedEndpoints w/ different content
                    print(f"  no aboutChannelViewModel in response. Top keys: {list(resp2.keys())}")
                    print(f"  response (first 500 chars): {json.dumps(resp2)[:500]}")
            except Exception as e:
                print(f"  EXCEPTION: {type(e).__name__}: {e}")

    # ----- Test 3: same channel, two stage1 calls — UUID stable? -----
    print()
    print("=" * 80)
    print("TEST 3: same channel, second stage1 call — is the panel UUID the same?")
    print("=" * 80)
    cid = CHANNELS[0]
    resp1b = ie._call_api(ep="browse", video_id=cid, query={"browseId": cid})
    tk2 = _get_about_panel_token(resp1b)
    if tk2:
        uuid2 = extract_uuid_from_token(tk2)
        uuid1 = extract_uuid_from_token(tokens[cid])
        print(f"  first call uuid:  {uuid1}")
        print(f"  second call uuid: {uuid2}")
        if uuid1 == uuid2:
            print("  ↳ UUID is STABLE across stage1 calls for the same channel.")
        else:
            print("  ↳ UUID CHANGES between calls — it's probably session-tied.")
            # If both belong to "same session" because YDL reuses connection,
            # but UUID differs, then it's panel-instance-specific.


if __name__ == "__main__":
    main()

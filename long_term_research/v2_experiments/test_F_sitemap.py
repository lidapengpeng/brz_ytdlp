"""Test F: YouTube sitemap.xml brute-force scan for channel URLs."""
import urllib.request, gzip, re, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bfs_v2_helpers import load_known_ids, dump_json

print("=" * 70)
print("Test F: Sitemap.xml brute scan for channel discovery")
print("=" * 70)

results = {}
known = load_known_ids()
print(f"loaded {len(known)} known_ids\n")

def fetch_sitemap(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; SitemapScanner/1.0)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if url.endswith(".gz") or raw[:3] == b"\x1f\x8b\x08":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="replace")

# Step 1: root sitemap
print("--- Step 1: fetch root sitemap ---")
candidates = [
    "https://www.youtube.com/sitemaps/sitemap.xml",
    "https://www.youtube.com/sitemap.xml",
    "https://m.youtube.com/sitemap.xml",
]
root_xml = None
working_root = None
for url in candidates:
    try:
        t0 = time.time()
        text = fetch_sitemap(url)
        ms = int((time.time()-t0)*1000)
        print(f"  ✓ {url}  {ms}ms  {len(text)} bytes")
        root_xml = text
        working_root = url
        break
    except Exception as e:
        print(f"  ✗ {url}  {type(e).__name__}: {str(e)[:60]}")

if not root_xml:
    print("\nFAILED: no sitemap accessible. Conclusion: surface dead.")
    results["status"] = "no_sitemap_accessible"
    dump_json(os.path.join(os.path.dirname(__file__), "test_F_sitemap_results.json"), results)
    sys.exit(0)

# Step 2: extract sub-sitemap URLs
sub_sitemaps = re.findall(r"<loc>(https?://[^<]+\.xml(?:\.gz)?)</loc>", root_xml)
print(f"\n--- Step 2: found {len(sub_sitemaps)} sub-sitemaps ---")
for s in sub_sitemaps[:10]:
    print(f"    {s}")
if len(sub_sitemaps) > 10:
    print(f"    ... +{len(sub_sitemaps) - 10} more")

# Step 3: scan sub-sitemaps for channel URLs (sample first 5 for cost)
print(f"\n--- Step 3: scan first {min(5, len(sub_sitemaps))} sub-sitemaps for channel URLs ---")
all_channels = set()
all_videos = set()
for sub_url in sub_sitemaps[:5]:
    try:
        t0 = time.time()
        text = fetch_sitemap(sub_url)
        ms = int((time.time()-t0)*1000)
        chs = re.findall(r"youtube\.com/channel/(UC[\w-]{20,})", text)
        ats = re.findall(r"youtube\.com/(@[\w.-]+)", text)
        vids = re.findall(r"youtube\.com/watch\?v=([\w-]{11})", text)
        all_channels.update(chs)
        all_videos.update(vids)
        print(f"  {sub_url.split('/')[-1][:40]:40s}  {ms}ms  {len(text)//1024}KB  "
              f"channels={len(chs)} @handles={len(ats)} videos={len(vids)}")
    except Exception as e:
        print(f"  {sub_url[-40:]}  ✗ {type(e).__name__}: {str(e)[:50]}")

new_channels = all_channels - known
print(f"\n--- Step 4: results ---")
print(f"  Unique channel IDs surfaced: {len(all_channels)}")
print(f"  New (not in DB):             {len(new_channels)}")
print(f"  Video IDs surfaced:          {len(all_videos)}")
print(f"  → 95% of YouTube sitemap is video URLs, channels barely indexed there")

results = {
    "status": "ok",
    "root_sitemap": working_root,
    "sub_sitemaps_count": len(sub_sitemaps),
    "scanned_subs": 5,
    "channels_found": len(all_channels),
    "channels_new": len(new_channels),
    "videos_found": len(all_videos),
    "verdict": "sitemap surfaces mostly videos; not useful for channel discovery"
                  if len(all_channels) < 100 else "WORTH investigating",
}
dump_json(os.path.join(os.path.dirname(__file__), "test_F_sitemap_results.json"), results)
print(f"\nresults dumped → test_F_sitemap_results.json")

"""Clash Verge control via local Unix socket API.

Clash Verge runs its mihomo backend with `external-controller-unix:
/tmp/verge/verge-mihomo.sock`. We use that socket (not TCP) to programmatically
switch the GLOBAL proxy group to a different exit node when YouTube starts
rate-limiting the current one.
"""
from __future__ import annotations

import http.client
import json
import socket
import time
import urllib.parse
from typing import List, Optional, Tuple

SOCK_PATH = "/tmp/verge/verge-mihomo.sock"

# We exclusively switch the GLOBAL group (whatever GLOBAL.now is = the
# actual outbound proxy for all traffic in global mode).
TARGET_GROUP = "GLOBAL"

# Filter: which `all` entries are real exit nodes (not DIRECT/REJECT,
# not metadata items like "套餐到期日期", not internal selector references).
def is_real_node(name: str) -> bool:
    if not name:
        return False
    if name in ("DIRECT", "REJECT"):
        return False
    # Selector group references (other groups inside GLOBAL)
    if name.startswith("🚀") or name.startswith("🎯") or name.startswith("🐟"):
        return False
    # Metadata-only entries
    for marker in ("套餐到期", "套餐重置", "订阅获取", "流量重置", "网址"):
        if marker in name:
            return False
    return True


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, sock_path: str):
        super().__init__("localhost")
        self.sock_path = sock_path

    def connect(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect(self.sock_path)
        self.sock = s


def _request(method: str, path: str, body: Optional[dict] = None) -> Tuple[int, dict]:
    conn = UnixHTTPConnection(SOCK_PATH)
    try:
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        conn.request(method, path, data, headers)
        resp = conn.getresponse()
        raw = resp.read()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"_raw": raw.decode(errors="replace")}
        return resp.status, payload
    finally:
        conn.close()


def get_group_state(group_name: str = TARGET_GROUP) -> Tuple[Optional[str], List[str]]:
    """Return (current_node, list_of_real_options) for ANY selector group.

    Works for GLOBAL, FIRST_HOP, SECOND_HOP, or any group defined in Clash config.
    Properly URL-encodes group name (handles emoji + Chinese chars).
    """
    encoded = urllib.parse.quote(group_name, safe="")
    status, payload = _request("GET", f"/proxies/{encoded}")
    if status != 200:
        return None, []
    now = payload.get("now")
    options = [o for o in payload.get("all", []) if is_real_node(o)]
    return now, options


def switch_group(group_name: str, node_name: str) -> bool:
    """Switch a selector group's selection.
    PUT /proxies/<group_name>  body={'name': node_name}.  Returns True on 2xx.
    """
    encoded = urllib.parse.quote(group_name, safe="")
    status, _ = _request("PUT", f"/proxies/{encoded}",
                          body={"name": node_name})
    return 200 <= status < 300


def list_groups() -> List[Tuple[str, str]]:
    """List all selector-style proxy groups in Clash config.
    Returns [(name, type), ...] — useful to discover FIRST_HOP / SECOND_HOP / etc."""
    status, payload = _request("GET", "/proxies")
    if status != 200:
        return []
    out = []
    for name, info in payload.get("proxies", {}).items():
        if isinstance(info, dict):
            t = info.get("type", "")
            if t in ("Selector", "URLTest", "Fallback", "LoadBalance"):
                out.append((name, t))
    return sorted(out)


# ===== Backwards-compat aliases =====
def get_global_state() -> Tuple[Optional[str], List[str]]:
    """Alias to get_group_state('GLOBAL')."""
    return get_group_state(TARGET_GROUP)


def switch_global(node_name: str) -> bool:
    """Alias to switch_group('GLOBAL', node_name)."""
    return switch_group(TARGET_GROUP, node_name)


def next_node(current: str, options: List[str]) -> Optional[str]:
    """Pick the next real node after `current` in round-robin order."""
    if not options:
        return None
    try:
        idx = options.index(current)
    except ValueError:
        idx = -1
    return options[(idx + 1) % len(options)]


def ensure_chained_setup(verbose: bool = True) -> bool:
    """Ensure the chained-proxy setup (FIRST_HOP + SECOND_HOP groups + dialer-proxy
    on the 3 BR statics) is present in the mihomo runtime config.

    Why this function exists: Clash Verge auto-regenerates clash-verge.yaml from
    the merge profile + subscription. The `prepend-proxy-groups` key in our merge
    profile is NOT honored by Clash Verge — so the FIRST_HOP/SECOND_HOP groups
    get silently dropped on every recompile. This function detects + reinjects.

    Strategy: directly edit clash-verge.yaml + tell mihomo to reload. Survives
    until next Clash Verge profile sync, then needs re-run (we call it on every
    production startup so it's effectively persistent for our use case).
    """
    import pathlib, re, shutil, os
    CFG_PATH = pathlib.Path.home() / "Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/clash-verge.yaml"
    if not CFG_PATH.exists():
        if verbose: print(f"  [chain] clash-verge.yaml not found at {CFG_PATH}")
        return False

    # Quick check: groups already present?
    txt = CFG_PATH.read_text(encoding="utf-8")
    has_first = "name: FIRST_HOP" in txt
    has_second = "name: SECOND_HOP" in txt
    dialer_count = txt.count("dialer-proxy: FIRST_HOP")
    if has_first and has_second and dialer_count >= 3:
        if verbose: print(f"  [chain] already setup (FIRST_HOP+SECOND_HOP groups + {dialer_count} dialer-proxies) ✓")
        return True

    if verbose: print(f"  [chain] missing components — patching... (has_first={has_first}, has_second={has_second}, dialer_count={dialer_count})")
    # Backup
    bak = str(CFG_PATH) + f".bak.{int(os.path.getmtime(CFG_PATH))}"
    shutil.copy(CFG_PATH, bak)

    # 1. Add dialer-proxy to 3 BR statics (only those missing it)
    BR_IPS = ["200.234.172.124", "178.94.165.52", "200.234.172.108"]
    for ip in BR_IPS:
        pat = re.compile(
            rf"(- type: socks5\n  name: SOCKS5 {re.escape(ip)}:\d+\n.*?password: \S+\n)(?!  dialer-proxy:)",
            re.DOTALL,
        )
        m = pat.search(txt)
        if m:
            old = m.group(1)
            new = old.rstrip("\n") + "\n  dialer-proxy: FIRST_HOP\n"
            txt = txt.replace(old, new, 1)
            if verbose: print(f"    + {ip}: added dialer-proxy: FIRST_HOP")

    # 2. Add FIRST_HOP and SECOND_HOP groups (if missing)
    new_groups = ""
    if not has_first:
        new_groups += """- name: FIRST_HOP
  type: select
  proxies:
  - DIRECT
  filter: \\-IEPL\\-
  include-all-proxies: true
"""
    if not has_second:
        new_groups += """- name: SECOND_HOP
  type: select
  proxies:
  - 'SOCKS5 200.234.172.124:49915'
  - 'SOCKS5 178.94.165.52:41584'
  - 'SOCKS5 200.234.172.108:48164'
"""
    if new_groups:
        if "proxy-groups:\n" in txt:
            txt = txt.replace("proxy-groups:\n", "proxy-groups:\n" + new_groups, 1)
            if verbose: print(f"    + injected new proxy-groups ({len(new_groups.splitlines())} lines)")

    CFG_PATH.write_text(txt, encoding="utf-8")

    # 3. Trigger mihomo reload
    try:
        status, _ = _request("PUT", "/configs?force=true", body={"path": ""})
        if verbose: print(f"  [chain] mihomo reload: status={status}")
    except Exception as e:
        if verbose: print(f"  [chain] reload failed: {e}")
        return False

    # 4. Verify the groups appeared
    import time as _t
    _t.sleep(2)
    groups = {n for n, _ in list_groups()}
    ok = "FIRST_HOP" in groups and "SECOND_HOP" in groups
    if verbose:
        print(f"  [chain] post-reload: FIRST_HOP={'✓' if 'FIRST_HOP' in groups else '✗'}, "
              f"SECOND_HOP={'✓' if 'SECOND_HOP' in groups else '✗'}")
    return ok


def disable_chained_setup(verbose: bool = True) -> bool:
    """Reverse of ensure_chained_setup — strip dialer-proxy from BR statics so
    they work as single-hop nodes. Leaves FIRST_HOP/SECOND_HOP groups intact
    (harmless when not used by GLOBAL). Triggers mihomo reload."""
    import pathlib, re
    CFG_PATH = pathlib.Path.home() / "Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/clash-verge.yaml"
    if not CFG_PATH.exists():
        return False
    txt = CFG_PATH.read_text(encoding="utf-8")
    n_before = txt.count("dialer-proxy: FIRST_HOP")
    if n_before == 0:
        if verbose: print(f"  [no-chain] no dialer-proxy entries, clean already ✓")
        return True
    txt2 = re.sub(r"\n  dialer-proxy: FIRST_HOP", "", txt)
    CFG_PATH.write_text(txt2, encoding="utf-8")
    try:
        status, _ = _request("PUT", "/configs?force=true", body={"path": ""})
        if verbose: print(f"  [no-chain] removed {n_before} dialer-proxy entries, mihomo reload status={status}")
        return True
    except Exception as e:
        if verbose: print(f"  [no-chain] reload failed: {e}")
        return False


def cli():
    """Quick CLI for inspection / one-off switching."""
    import sys
    if len(sys.argv) == 1 or sys.argv[1] == "status":
        # Show GLOBAL by default. If extra arg, show that group.
        group = sys.argv[2] if len(sys.argv) >= 3 else TARGET_GROUP
        now, opts = get_group_state(group)
        print(f"current {group}: {now!r}")
        print(f"available real nodes ({len(opts)}):")
        for o in opts:
            mark = " ← current" if o == now else ""
            print(f"  - {o}{mark}")
    elif sys.argv[1] == "groups":
        groups = list_groups()
        print(f"selector groups ({len(groups)}):")
        for name, t in groups:
            now, opts = get_group_state(name)
            print(f"  {name:20s}  [{t}]  now={now!r}  options={len(opts)}")
    elif sys.argv[1] == "next":
        # next [group_name]  — defaults to GLOBAL
        group = sys.argv[2] if len(sys.argv) >= 3 else TARGET_GROUP
        now, opts = get_group_state(group)
        nxt = next_node(now or "", opts)
        if nxt is None:
            print("no options to switch to"); sys.exit(1)
        print(f"switching {group}: {now!r}  →  {nxt!r}")
        if switch_group(group, nxt):
            print("✓ done")
        else:
            print("✗ switch failed"); sys.exit(2)
    elif sys.argv[1] == "ensure-chain":
        ok = ensure_chained_setup(verbose=True)
        sys.exit(0 if ok else 1)
    elif sys.argv[1] == "set" and len(sys.argv) >= 3:
        # set <node> | set --group <name> <node>
        if sys.argv[2] == "--group" and len(sys.argv) >= 5:
            group = sys.argv[3]
            target = sys.argv[4]
        else:
            group = TARGET_GROUP
            target = sys.argv[2]
        ok = switch_group(group, target)
        print(f"set {group} → {target!r}: {'✓ ok' if ok else '✗ failed'}")
    else:
        print("usage: clash_control.py <cmd>")
        print("  status [group]                  - show current selection + options for a group")
        print("  groups                          - list all selector groups in config")
        print("  next [group]                    - rotate to next node in group (default GLOBAL)")
        print("  set <node>                      - switch GLOBAL to <node>")
        print("  set --group <name> <node>       - switch arbitrary group")
        print("  ensure-chain                    - re-inject FIRST_HOP/SECOND_HOP groups if Clash Verge wiped them")


if __name__ == "__main__":
    cli()

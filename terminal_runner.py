"""Terminal-friendly wrapper around production_v2.py.

What it does:
  1. Runs production_v2 as subprocess, reads stdout line-by-line.
  2. Reformats every status line with color + larger metrics block.
  3. Detects rate drop (eligible rate < threshold for 2+ windows) and
     prints LOUD '🚨 SWITCH IP NOW' alert with terminal bell (\a).
  4. After the user switches the Clash node, throughput recovers
     automatically in the next status window (no further action needed).
  5. Ctrl-C sends SIGINT to production (graceful drain + DB flush).
"""
from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

try:
    import clash_control
    CLASH_OK = True
except ImportError:
    CLASH_OK = False

# ----- visuals ------------------------------------------------------------

C = {
    "green":  "\033[92m",
    "yellow": "\033[93m",
    "red":    "\033[91m",
    "cyan":   "\033[96m",
    "bold":   "\033[1m",
    "dim":    "\033[2m",
    "reset":  "\033[0m",
}

# ----- parse production_v2 status line ------------------------------------

# Example:
# [  127s]  disc=  1374  val=  1272  eligible= 1005 (+325)  target= 1005  lang_rec=  95  short=   53  err=   11  q=   2  vr=13.54/s  er=10.81/s
STATUS_RE = re.compile(
    r"\[\s*(\d+)s\]\s+disc=\s*(\d+)\s+val=\s*(\d+)\s+"
    r"eligible=\s*(\d+)\s+\(\+(\d+)\).*?"
    r"lang_rec=\s*(\d+)\s+short=\s*(\d+)\s+err=\s*(\d+)\s+"
    r"q=\s*(\d+)\s+vr=\s*([\d.]+)/s\s+er=\s*([\d.]+)/s"
)

# ----- thresholds for alerts ----------------------------------------------

ELIGIBLE_RATE_WARN = 3.0      # below this = yellow "slowing"
ELIGIBLE_RATE_ALERT = 1.5     # below this for ALERT_STREAK windows = red ALERT
ALERT_STREAK = 2              # consecutive low-rate windows before alerting
ALERT_REMIND_INTERVAL = 60    # seconds between re-alerts if still slow
AUTO_SWITCH_STREAK = 4        # 4 × 30s = 2 min sustained red → auto-switch (was 10)
AUTO_SWITCH_COOLDOWN = 90     # seconds before next auto-switch attempt
WARMUP_SECONDS = 120          # ignore low rates during worker pool / queue warm-up
PROACTIVE_CHANNELS_PER_NODE = 300  # switch SECOND_HOP/GLOBAL after N validations regardless of streak.
                                   # YouTube's official guest quota is ~1000 req/hr per IP.
                                   # 300 channels × 2 stages = 600 req per IP — well under 1000,
                                   # leaving headroom for next visit. With 30 nodes rotating
                                   # round-robin, each IP gets ~30 min rest = quota refills.

# === Chained-proxy rotation (added 2026-05-20) ===
# When SECOND_HOP group exists in Clash config, we treat it as the "exit IP rotator"
# (3 BR static residentials). FIRST_HOP rotates more frequently to diversify the
# TCP source (origin of the chain) — this doesn't affect YouTube's view but
# reduces per-(IP×fingerprint) correlation.
FIRST_HOP_ROTATE_EVERY = 100  # rotate FIRST_HOP every N validations (cheap — no proc restart)
SECOND_HOP_GROUP = "SECOND_HOP"  # group containing 3 BR statics
FIRST_HOP_GROUP = "FIRST_HOP"   # group containing subscription nodes (91 options)


def banner_start(auto_rotate: bool = True, chained: bool = False):
    if auto_rotate and chained:
        mode_line1 = f"║   • CHAINED MODE: SECOND_HOP every {PROACTIVE_CHANNELS_PER_NODE} ch, FIRST_HOP every {FIRST_HOP_ROTATE_EVERY}.  ║"
        mode_line2 = "║     3 BR exit IPs × 91 source nodes — full chain auto-cycle. ║"
    elif auto_rotate:
        mode_line1 = f"║   • Auto-rotate Clash GLOBAL every {PROACTIVE_CHANNELS_PER_NODE} channels (proactive),  ║"
        mode_line2 = "║     or after 2 min sustained red (reactive). Hands-off.       ║"
    else:
        mode_line1 = "║   • Auto-rotate DISABLED — stays on current Clash node.       ║"
        mode_line2 = "║     ⚠ When eligible rate drops, switch Clash node manually.   ║"
    return f"""
{C['cyan']}{C['bold']}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🇧🇷  brz_ytdlp Production — Brazilian Channel Scraper       ║
║                                                               ║
║   • Press Ctrl-C to stop gracefully (saves all progress).     ║
{mode_line1}
{mode_line2}
║                                                               ║
║   Results auto-persist to brz_ytdlp/results.db                ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝{C['reset']}
"""


def banner_switch_ip(elapsed_str: str, er: float, err_delta: int, auto_rotate: bool = True):
    if auto_rotate:
        action_line = f"║   Auto-switch in {AUTO_SWITCH_STREAK*30}s ({AUTO_SWITCH_STREAK*30//60}min) if not recovered.{' '*(33-len(str(AUTO_SWITCH_STREAK*30//60)))}║"
    else:
        action_line = "║   ⚠ Auto-switch DISABLED — open Clash Verge to swap node.    ║"
    return f"""
{C['red']}{C['bold']}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🚨  SWITCH IP NOW  ({elapsed_str})
║                                                               ║
║   Eligible rate dropped to {er:.2f}/s (need ≥{ELIGIBLE_RATE_ALERT}/s)
║   Recent errors: +{err_delta}
║                                                               ║
{action_line}
║   Or manually switch in Clash Verge GUI right now.            ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝{C['reset']}
\a"""


def banner_auto_switched(old_node: str, new_node: str, elapsed_str: str):
    return f"""
{C['cyan']}{C['bold']}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🔄  AUTO-SWITCHED GLOBAL PROXY  ({elapsed_str})              ║
║                                                               ║
║   {old_node[:55]:55s}
║       ↓                                                       ║
║   {new_node[:55]:55s}
║                                                               ║
║   Throughput should recover within ~30s.                      ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝{C['reset']}
\a"""


def status_block(elapsed_s: int, val: int, eligible: int, eligible_new: int,
                 lang_rec: int, errors: int, vr: float, er: float, q: int,
                 color: str, health: str):
    mm, ss = divmod(elapsed_s, 60)
    hh, mm = divmod(mm, 60)
    elapsed_str = f"t+{hh:02d}h{mm:02d}m{ss:02d}s"
    conv = eligible / max(1, val) * 100
    err_pct = errors / max(1, val) * 100
    return (
        f"\n{color}┌─ {C['bold']}{elapsed_str}{C['reset']}{color}  "
        f"─ {C['bold']}{health}{C['reset']}{color}  "
        f"─ +{eligible_new} new eligible "
        f"───────────────────────┐{C['reset']}\n"
        f"  Validated  : {C['bold']}{val:>9,d}{C['reset']}\n"
        f"  Eligible   : {C['green']}{C['bold']}{eligible:>9,d}{C['reset']}  ({conv:5.1f}%)\n"
        f"  Lang-recov : {lang_rec:>9,d}\n"
        f"  Errors     : {errors:>9,d}  ({err_pct:5.1f}%)\n"
        f"  Queue      : {q:>9,d}\n"
        f"  Rate (30s) : {vr:>5.2f} val/s  │  {color}{er:>5.2f} eligible/s{C['reset']}\n"
    )


# ----- main loop ----------------------------------------------------------

def prompt_auto_rotate() -> bool:
    """Ask user at startup whether to enable auto IP rotation.
    Default = YES on Enter or 'y'. 'n' disables both proactive + reactive switching.
    Honors --no-rotate / --rotate CLI flags as override (non-interactive)."""
    # Non-interactive override
    if "--no-rotate" in sys.argv:
        return False
    if "--rotate" in sys.argv:
        return True
    print(f"\n{C['bold']}🔄 启动选项{C['reset']}", flush=True)
    print(f"{C['dim']}  是否启用 Clash 节点自动轮换？{C['reset']}", flush=True)
    print(f"{C['dim']}  - 是 (Y, 默认): 每 300 channel 主动切节点 + 2 min 红色自动救场{C['reset']}", flush=True)
    print(f"{C['dim']}  - 否 (n)     : 全程用当前 Clash GLOBAL 节点，不切换{C['reset']}", flush=True)
    try:
        ans = input(f"{C['cyan']}启用自动轮换? [Y/n]: {C['reset']}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(f"{C['yellow']}(no input — defaulting to ROTATE){C['reset']}", flush=True)
        return True
    if ans in ("n", "no", "nao", "não"):
        return False
    return True


def prompt_chained_proxy() -> bool:
    """Ask whether to use chained proxy (FIRST_HOP + SECOND_HOP).

    DEFAULT = NO — chained proxy adds 5-8s latency per InnerTube call
    (measured 2026-05-20: single hop 0.98s vs chained 10.8s = 11x slower).
    Only useful if your 3 BR static IPs have meaningfully more quota than
    using 91 subscription nodes round-robin. Empirically the latency tax
    eats all the IP-diversity gains.

    Override flags: --chained / --no-chained.
    """
    if "--chained" in sys.argv: return True
    if "--no-chained" in sys.argv: return False
    print(f"\n{C['bold']}🔗 链式代理 (高级){C['reset']}", flush=True)
    print(f"{C['dim']}  是否启用链式代理（first hop → second hop → YouTube）？{C['reset']}", flush=True)
    print(f"{C['dim']}  - 否 (N, 默认): 单跳轮换 91+ 订阅节点。延迟 ~1s/call。{C['reset']}", flush=True)
    print(f"{C['dim']}  - 是 (y)     : 双层链 (3 BR 住宅 IP × 91 source)。延迟 ~10s/call，慢 10x。{C['reset']}", flush=True)
    print(f"{C['dim']}  实测：单跳显著优于链式（除非住宅 IP 有特殊价值）{C['reset']}", flush=True)
    try:
        ans = input(f"{C['cyan']}启用链式代理? [y/N]: {C['reset']}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans in ("y", "yes", "sim")

def main():
    here = Path(__file__).resolve().parent
    os.chdir(here)

    # ----- Startup option: auto-rotate or pin to current node -----
    auto_rotate = prompt_auto_rotate()
    if auto_rotate:
        print(f"{C['green']}{C['bold']}→ 自动轮换：开启{C['reset']}", flush=True)
    else:
        print(f"{C['yellow']}{C['bold']}→ 自动轮换：关闭 — 全程沿用当前 Clash 节点{C['reset']}", flush=True)

    # ----- Optional: chained-proxy setup -----
    # Only ask if user already wants auto-rotation. Default is NO (single hop)
    # because chained mode measured ~11x slower per call (1s → 10s).
    chained_mode = False
    if CLASH_OK and auto_rotate:
        use_chain = prompt_chained_proxy()
        if use_chain:
            try:
                ok = clash_control.ensure_chained_setup(verbose=True)
                if ok:
                    chained_mode = True
                    cur_global, _ = clash_control.get_global_state()
                    if cur_global != "SECOND_HOP":
                        clash_control.switch_global("SECOND_HOP")
                        print(f"{C['cyan']}  [chain] set GLOBAL → SECOND_HOP{C['reset']}", flush=True)
                    cur_fh, opts_fh = clash_control.get_group_state(FIRST_HOP_GROUP)
                    if cur_fh in ("DIRECT", None) and opts_fh:
                        real_fh = next((o for o in opts_fh if o != "DIRECT"), None)
                        if real_fh:
                            clash_control.switch_group(FIRST_HOP_GROUP, real_fh)
                            print(f"{C['cyan']}  [chain] set FIRST_HOP → {real_fh}{C['reset']}", flush=True)
                else:
                    print(f"{C['yellow']}  [chain] setup failed — falling back to single-hop{C['reset']}", flush=True)
            except Exception as e:
                print(f"{C['yellow']}  [chain] ensure failed ({type(e).__name__}: {e}){C['reset']}", flush=True)
        else:
            # Single-hop mode — clean any leftover dialer-proxy from a previous
            # chained-mode session (otherwise BR statics in node pool are slow).
            try:
                clash_control.disable_chained_setup(verbose=True)
                cur_global, opts = clash_control.get_global_state()
                if cur_global == "SECOND_HOP":
                    # Pick a fresh subscription node (W-IEPL or E-IEPL etc.)
                    sub_node = next((o for o in opts if "-IEPL-" in o), None)
                    if sub_node:
                        clash_control.switch_global(sub_node)
                        print(f"{C['dim']}  ↻ GLOBAL was on SECOND_HOP (chained), reset to {sub_node}{C['reset']}", flush=True)
            except Exception:
                pass

    # Build the production_v2 command.
    # NOTE: Worker counts deliberately reduced from 40/5 → 15/3.
    # Empirically YouTube per-IP throttle triggers MUCH harder at >20 concurrent
    # connections to youtube.com from one IP. Lower concurrency yields BETTER
    # sustained throughput (~1.5-2.5 val/s sustained) than higher (~0.3 val/s
    # after throttle kicks in). See diagnostic 2026-05-17.
    cmd = [
        "./.venv/bin/python", "-u", "production_v2.py",
        "--val-workers", "15",
        "--disc-workers", "3",
        "--bfs-workers", "2",   # BFS gridChannel + watchnext over BR seeds
        "--status-every", "30",
        "--queries-file", "query_bank_extended.txt",   # 46K (36K + 10K YouTube Suggest BFS, dedup overlap 84.5%→78.8%)
        "--minutes", "10000",   # ~1 week budget; Ctrl-C stops it
    ]

    print(banner_start(auto_rotate, chained_mode), flush=True)
    print(f"{C['dim']}starting: {' '.join(cmd)}{C['reset']}", flush=True)

    # Show current Clash GLOBAL node + auto-switch readiness
    if CLASH_OK:
        try:
            cur, opts = clash_control.get_global_state()
            if cur:
                print(f"{C['cyan']}Clash GLOBAL = {cur!r}  ({len(opts)} rotate options available){C['reset']}", flush=True)
                if auto_rotate:
                    print(f"{C['dim']}Auto-switch armed: will rotate GLOBAL after {AUTO_SWITCH_STREAK*30}s of sustained red.{C['reset']}\n", flush=True)
                else:
                    print(f"{C['dim']}Auto-switch DISABLED — staying on this node for the full run.{C['reset']}\n", flush=True)
            else:
                print(f"{C['yellow']}Clash API responded but GLOBAL has no current node?{C['reset']}\n", flush=True)
        except Exception as e:
            print(f"{C['yellow']}Clash control unavailable ({type(e).__name__}); auto-switch disabled.{C['reset']}\n", flush=True)
            auto_rotate = False   # force disabled if Clash unreachable
    else:
        print(f"{C['yellow']}clash_control module not importable; auto-switch disabled.{C['reset']}\n", flush=True)
        auto_rotate = False   # force disabled if module missing

    # ----- spawn / respawn helper -----
    def spawn_production():
        return subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1, text=True, errors="replace",
        )

    proc_box = [spawn_production()]
    shutting_down = [False]

    streak = 0
    last_alert_t = 0.0
    last_auto_switch_t = 0.0
    prev_errors = 0
    # Proactive rotation state — tracks validations on current node
    val_since_switch = 0          # cumulative validations since last SECOND_HOP/GLOBAL switch
    val_since_first_hop_switch = 0  # cumulative validations since last FIRST_HOP switch
    prev_val_in_proc = 0          # previous val_i seen within current proc (reset on respawn)

    # Set rotation target group based on chained_mode (detected earlier)
    rotation_group = SECOND_HOP_GROUP if chained_mode else "GLOBAL"
    if chained_mode:
        print(f"{C['cyan']}↻ chained mode: rotating {SECOND_HOP_GROUP} every "
              f"{PROACTIVE_CHANNELS_PER_NODE} ch (exit IP) + {FIRST_HOP_GROUP} every "
              f"{FIRST_HOP_ROTATE_EVERY} ch (source diversity){C['reset']}", flush=True)

    def graceful_stop(*_a):
        shutting_down[0] = True
        print(f"\n{C['yellow']}{C['bold']}↓ Ctrl-C received — telling production to drain and exit...{C['reset']}", flush=True)
        try:
            proc_box[0].send_signal(signal.SIGINT)
        except Exception:
            pass

    signal.signal(signal.SIGINT, graceful_stop)
    signal.signal(signal.SIGTERM, graceful_stop)

    try:
        while not shutting_down[0]:
            proc = proc_box[0]
            restart_after_switch = False

            for line in proc.stdout:
                line = line.rstrip("\n")
                if not line:
                    continue
                if "Deprecated Feature" in line or "zoxide" in line.lower():
                    continue   # silence noise

                m = STATUS_RE.search(line)
                if m:
                    (elapsed, _disc, val, eligible, eligible_new,
                     lang_rec, _short, errors, q, vr, er) = m.groups()
                    elapsed_s = int(elapsed)
                    val_i = int(val); eligible_i = int(eligible)
                    eligible_new_i = int(eligible_new)
                    lang_rec_i = int(lang_rec); errors_i = int(errors)
                    q_i = int(q); vr_f = float(vr); er_f = float(er)
                    err_delta = max(0, errors_i - prev_errors)
                    prev_errors = errors_i
                    # Track validations on current node for proactive rotation
                    val_delta = max(0, val_i - prev_val_in_proc)
                    prev_val_in_proc = val_i
                    val_since_switch += val_delta
                    val_since_first_hop_switch += val_delta

                    # decide health color
                    if elapsed_s < WARMUP_SECONDS:
                        # workers spinning up, queues filling — low rate is expected
                        color = C['cyan']
                        health = f"WARMING UP  ({elapsed_s}s/{WARMUP_SECONDS}s)"
                        streak = 0   # do not accumulate streak during warm-up
                    elif er_f < ELIGIBLE_RATE_ALERT:
                        streak += 1
                        color = C['red']
                        health = f"⚠️ BLOCKED  (streak={streak})"
                    elif er_f < ELIGIBLE_RATE_WARN:
                        streak = max(0, streak - 1)
                        color = C['yellow']
                        health = "SLOWING"
                    else:
                        streak = 0
                        color = C['green']
                        health = "HEALTHY"

                    # print status block
                    hh, mm = divmod(elapsed_s // 60, 60)
                    ss = elapsed_s % 60
                    elapsed_str = f"t+{hh:02d}h{mm:02d}m{ss:02d}s"
                    print(status_block(elapsed_s, val_i, eligible_i, eligible_new_i,
                                       lang_rec_i, errors_i, vr_f, er_f, q_i,
                                       color, health), flush=True)

                    # fire alert?  (suppressed during warm-up)
                    if (elapsed_s >= WARMUP_SECONDS
                            and streak >= ALERT_STREAK
                            and (time.time() - last_alert_t) >= ALERT_REMIND_INTERVAL):
                        print(banner_switch_ip(elapsed_str, er_f, err_delta, auto_rotate), flush=True)
                        last_alert_t = time.time()

                    # ----- FIRST_HOP cheap rotation (chained mode only) -----
                    # Rotates the subscription node providing the chain entry.
                    # Doesn't affect YouTube's view (it sees SECOND_HOP IP), so
                    # NO proc restart needed — TCP keep-alive connections to
                    # SECOND_HOP remain valid even though new connections are
                    # tunneled through a different first hop.
                    if (auto_rotate and chained_mode
                            and val_since_first_hop_switch >= FIRST_HOP_ROTATE_EVERY):
                        try:
                            cur_fh, opts_fh = clash_control.get_group_state(FIRST_HOP_GROUP)
                            if cur_fh and opts_fh:
                                nxt_fh = clash_control.next_node(cur_fh, opts_fh)
                                if nxt_fh and nxt_fh != cur_fh and clash_control.switch_group(FIRST_HOP_GROUP, nxt_fh):
                                    print(f"{C['dim']}↻ FIRST_HOP rotated: {cur_fh} → {nxt_fh}  "
                                          f"({val_since_first_hop_switch} validations on prev){C['reset']}", flush=True)
                                    val_since_first_hop_switch = 0
                        except Exception as e:
                            print(f"{C['yellow']}FIRST_HOP rotate failed: {type(e).__name__}: {e}{C['reset']}", flush=True)

                    # ----- SECOND_HOP / GLOBAL expensive rotation -----
                    # Decide whether to switch the exit-IP node (proc restart required):
                    #   1) REACTIVE: streak >= 4 (2 min sustained red) — node degraded
                    #   2) PROACTIVE: val_since_switch >= 300 — preventive rotation
                    #      to keep each IP under YouTube's ~1000 req/hr guest quota.
                    # Gated by `auto_rotate` (set at startup via prompt).
                    switch_reason = None
                    if auto_rotate and CLASH_OK and (time.time() - last_auto_switch_t) >= AUTO_SWITCH_COOLDOWN:
                        if streak >= AUTO_SWITCH_STREAK:
                            switch_reason = f"reactive: sustained red (streak={streak})"
                        elif val_since_switch >= PROACTIVE_CHANNELS_PER_NODE:
                            switch_reason = f"proactive: {val_since_switch} channels on this node — rotating before quota exhausted"

                    if switch_reason:
                        try:
                            cur, opts = clash_control.get_group_state(rotation_group)
                            if cur and opts:
                                nxt = clash_control.next_node(cur, opts)
                                if nxt and nxt != cur and clash_control.switch_group(rotation_group, nxt):
                                    print(f"{C['cyan']}↻ switching {rotation_group}: {switch_reason}{C['reset']}", flush=True)
                                    print(banner_auto_switched(cur, nxt, elapsed_str), flush=True)
                                    last_auto_switch_t = time.time()
                                    streak = 0
                                    val_since_switch = 0   # reset counter for new node
                                    # New node won't help while old TCP keep-alive
                                    # connections survive in the worker pool.
                                    # Kill production and respawn → fresh sockets.
                                    restart_after_switch = True
                                    break   # exit inner for; outer while will respawn
                                else:
                                    print(f"{C['yellow']}auto-switch: could not pick next node (cur={cur!r}, opts={len(opts)}){C['reset']}", flush=True)
                            else:
                                print(f"{C['yellow']}auto-switch: clash returned no options for {rotation_group}{C['reset']}", flush=True)
                        except Exception as e:
                            print(f"{C['yellow']}auto-switch failed: {type(e).__name__}: {e}{C['reset']}", flush=True)
                else:
                    # pass through other lines dimmed (init messages, etc.)
                    if line.strip():
                        print(f"{C['dim']}{line}{C['reset']}", flush=True)

            # ----- inner for loop ended -----
            if shutting_down[0]:
                break
            if not restart_after_switch:
                # production exited on its own (normal completion or crash)
                break

            # Restart production to drop stale TCP / keep-alive connections.
            print(f"\n{C['yellow']}{C['bold']}↻ restarting production_v2 to drop stale TCP connections "
                  f"(new proxy node can't take effect until old keep-alives die){C['reset']}", flush=True)
            try:
                proc.terminate()
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                print(f"{C['yellow']}  production did not exit in 20s, sending SIGKILL...{C['reset']}", flush=True)
                proc.kill()
                proc.wait()
            proc_box[0] = spawn_production()
            prev_errors = 0          # new process resets its error counter
            prev_val_in_proc = 0     # new process starts val_i from 0
            # NOTE: val_since_first_hop_switch NOT reset — FIRST_HOP rotation
            # cadence is independent of proc lifecycle (cheap, doesn't restart).

    finally:
        try:
            proc_box[0].wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc_box[0].kill()
            proc_box[0].wait()
        print(f"\n{C['cyan']}{C['bold']}─ done. Final DB stats:{C['reset']}", flush=True)
        os.system("sqlite3 results.db \""
                  "SELECT 'total='||COUNT(*) FROM channels "
                  "UNION ALL SELECT 'eligible='||COUNT(*) FROM channels "
                  "WHERE is_target=1 AND subscribers>=1000 "
                  "UNION ALL SELECT 'huge_1M='||COUNT(*) FROM channels "
                  "WHERE is_target=1 AND subscribers>=1000000\"")


if __name__ == "__main__":
    main()

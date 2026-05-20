#!/bin/bash
# run.sh — one-command launcher for brz_ytdlp production scrape.
#
# Usage (from anywhere in terminal):
#   bash /Users/dapeng/Desktop/word/brz_ytdlp/run.sh
#
# What it does:
#   1. Gracefully kills any previous production_v2.py (if frozen / running).
#   2. Starts a fresh production scrape with terminal-friendly formatting.
#   3. Watches the rate — when eligible/s drops, fires 🚨 SWITCH IP alert.
#   4. Persists results to brz_ytdlp/results.db (eligible & rejected & errors).
#   5. Ctrl-C anytime → graceful drain + final stats.

set -e
cd "$(dirname "$0")"   # chdir into brz_ytdlp/

# ----- bump file descriptor limit (macOS default 256 → 65536) -------------
# Each YoutubeDL instance opens many sockets / temp files.
# Without this we hit OSError: [Errno 24] Too many open files almost immediately.
ulimit -n 65536 2>/dev/null || ulimit -n 4096   # fall back to 4096 if 65536 denied
echo "→ ulimit -n now: $(ulimit -n)"

# ----- clean up any stale process -----------------------------------------
OLD_PID=$(pgrep -f "production_v2.py" 2>/dev/null | head -1)
if [ -n "$OLD_PID" ]; then
    echo "→ found stale production_v2.py PID=$OLD_PID, sending SIGINT..."
    kill -CONT $OLD_PID 2>/dev/null || true   # un-freeze if SIGSTOP'd
    kill -INT  $OLD_PID 2>/dev/null || true
    # wait up to 15s for graceful exit
    for i in $(seq 1 15); do
        kill -0 $OLD_PID 2>/dev/null || break
        sleep 1
    done
    # force kill if still alive
    if kill -0 $OLD_PID 2>/dev/null; then
        echo "→ still alive, force killing..."
        kill -9 $OLD_PID 2>/dev/null || true
        sleep 1
    fi
    echo "→ previous run stopped."
fi

# ----- run --------------------------------------------------------------
exec ./.venv/bin/python -u terminal_runner.py

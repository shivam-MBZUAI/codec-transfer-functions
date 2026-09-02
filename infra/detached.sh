#!/bin/bash
# Run a command in a detached tmux session so it survives SSH disconnect.
#
#   ./infra/detached.sh <name> <command...>
#   ./infra/detached.sh status
#   ./infra/detached.sh log <name>
#
# Why this exists: a command launched over `ssh host "cmd"` is a child of that
# SSH session and dies with it, so closing a laptop kills a running experiment.
# `nohup ... &` and `setsid` both proved unreliable through a non-interactive
# ssh here. tmux is reliable: the session is owned by the tmux server, not by
# any connection.
set -u
ROOT="${CODECS_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT"
mkdir -p logs

case "${1:-}" in
  status)
    echo "sessions:"; tmux ls 2>/dev/null || echo "  (none)"
    echo "sweeps running: $(pgrep -fc run_sweep.py || echo 0)"
    echo "training running: $(pgrep -fc train_rvq.py || echo 0)"
    exit 0 ;;
  log)
    tr -d '\r' < "logs/${2}.log" | tail -30; exit 0 ;;
esac

name=$1; shift
# Wrap in an explicit bash -c: tmux runs the command through its default shell,
# and a bare pipeline there exited immediately and wrote no log.
tmux new-session -d -s "$name" bash -c \
  "cd '$ROOT' && export HF_HOME='${HF_HOME:-$ROOT/.hf}' && PYTHONUNBUFFERED=1 $* > logs/${name}.log 2>&1"
echo "launched '$name' detached; check with: ./infra/detached.sh status"

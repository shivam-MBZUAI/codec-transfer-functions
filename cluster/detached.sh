#!/bin/bash
# Run a command in a detached tmux session so it survives SSH disconnect.
#
#   ./cluster/detached.sh <name> <command...>
#   ./cluster/detached.sh status
#   ./cluster/detached.sh log <name>
#
# Why this exists: a command launched over `ssh host "cmd"` is a child of that
# SSH session and dies with it, so closing a laptop kills a running experiment.
# `nohup ... &` and `setsid` both proved unreliable through a non-interactive
# ssh here. tmux is reliable: the session is owned by the tmux server, not by
# any connection.
set -u
cd /workspace/codecs
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
tmux new-session -d -s "$name" \
  "cd /workspace/codecs && export HF_HOME=/workspace/.hf && { $*; } 2>&1 | tee logs/${name}.log"
echo "launched '$name' detached; check with: ./cluster/detached.sh status"

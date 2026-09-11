#!/bin/bash
# Full experimental programme. Sweeps are CPU-bound on F0 estimation, not
# GPU-bound, so they run concurrently: one process per configuration, each
# single-threaded, across a machine with 255 vCPUs.
set -u
ROOT="${CODECS_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
export HF_HOME="${HF_HOME:-$ROOT/.hf}"
cd "$ROOT/experiments"
mkdir -p ../results ../figures ../logs ../checkpoints

REPS=${REPS:-5}
run () {  # run <tag> <args...>
  tag=$1; shift
  python run_sweep.py "$@" --out "../results/${tag}.csv" > "../logs/${tag}.log" 2>&1 &
}

echo "=== A. detuning regression: 11 reference offsets, 0 to 100 cents ==="
# The decisive test. If the residual is locked to an absolute learned grid, its
# phase must track reference detuning with slope 1 across all eleven points. A
# two-point test can pass by chance; this cannot.
REFS=""
for c in 0 10 20 30 40 50 60 70 80 90 100; do
  f=$(python -c "print(440.0 * 2**($c/1200.0))")
  REFS="$REFS $f"
done
run detune_encodec3 --codec encodec:3 --reps $REPS --references $REFS

echo "=== B. rate sweep: EnCodec at every rate it exposes ==="
for kb in 1.5 3 6 12 24; do
  run "rate_encodec_${kb}" --codec "encodec:${kb}" --reps $REPS --references 440 452.8929
done

echo "=== C. mechanism controls ==="
run mech_bypass   --codec encodec_bypass   --reps $REPS --references 440 452.8929

echo "=== D. codec breadth: the registration sweep for every codec (Table 1) ==="
run detune_encodec24kbps --codec encodec:24     --reps 4 --references $REFS
run detune_encodec48     --codec encodec48:6    --reps 4 --references $REFS
run detune_mimi          --codec mimi:8         --reps 4 --references $REFS
run detune_dac16         --codec dac16:6        --reps 4 --references $REFS
run detune_dac24         --codec dac24:8        --reps 4 --references $REFS
run detune_dac44         --codec dac:4          --reps 4 --references $REFS
run detune_snac          --codec snac           --reps 4 --references $REFS
run detune_snac32        --codec snac32         --reps 4 --references $REFS
run detune_snac44        --codec snac44         --reps 4 --references $REFS

echo "=== E. controls ==="
run ctrl_identity  --codec identity:24000 --reps $REPS --references 440 452.8929
run ctrl_sinusoid  --codec encodec:3 --reps $REPS --references 440 452.8929 --sinusoid

echo
echo "launched $(jobs -r | wc -l) concurrent sweeps; waiting..."
wait
echo "=== all sweeps complete ==="
ls -la ../results/*.csv | tail -25

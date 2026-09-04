#!/bin/bash
# Runbook for the additional experiments on a single-GPU pod.
#
#   bash infra/pod_run.sh setup        # system deps, python deps, checkpoints, corpora
#   bash infra/pod_run.sh classical    # Opus and MP3 through the detuning sweep (CPU)
#   bash infra/pod_run.sh registers    # EnCodec registration at 220 and 880 Hz (CPU)
#   bash infra/pod_run.sh corpus       # transfer function on real polyphonic music
#   bash infra/pod_run.sh asr          # Whisper and MMS at 100 utterances per language (GPU)
#   bash infra/pod_run.sh causal5      # EnCodec decoder fine-tune, four arms x five seeds (GPU)
#   bash infra/pod_run.sh causal_dac   # the same on DAC 16 kHz Q6, arms grid and flat (GPU)
#   bash infra/pod_run.sh mgswap       # MusicGen tokens decoded by stock / grid / flat EnCodec 32k (GPU)
#
# Every step writes to results/ with a .meta.json sidecar and can be re-run.
set -euo pipefail
ROOT="${CODECS_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT"
export HF_HOME="${HF_HOME:-$ROOT/.hf}"
export PYTHONUNBUFFERED=1
mkdir -p results logs corpora

# Eleven reference pitches, 0 to 100 cents above the base in 10-cent steps.
refs () { python3 -c "print(' '.join(f'{$1*2**(d/1200):.4f}' for d in range(0,101,10)))"; }

case "${1:-}" in
setup)
  which ffmpeg > /dev/null || (apt-get update -qq && apt-get install -y -qq ffmpeg tmux > /dev/null)
  # The pod ships torch 2.8.0+cu128 already, the version every result was
  # produced under; reinstalling it from the pin is pointless and risky.
  export PIP_BREAK_SYSTEM_PACKAGES=1
  grep -v '^torch' requirements.txt | pip install -q -r /dev/stdin
  pip install -q jiwer accelerate
  python3 data/fetch_checkpoints.py
  python3 data/fetch_pod_corpora.py
  python3 experiments/make_detuned_corpus.py --src corpora/gtzan --dst corpora/gtzan_detuned --max-files 400
  python3 data/get_fleurs_pod.py
  echo "setup complete"
  ;;
classical)
  R=$(refs 440)
  for c in opus:6 opus:12 mp3:16 mp3:32; do
    tag="detune_${c/:/}"
    python3 experiments/run_sweep.py --codec "$c" --reps 5 --references $R \
        --out "results/${tag}.csv" > "logs/${tag}.log" 2>&1 &
  done
  wait
  for c in opus6 opus12 mp316 mp332; do
    echo "== $c"; python3 analysis/analyze_detuning.py "results/detune_${c}.csv" | tail -6
  done
  ;;
registers)
  for base in 220 880; do
    R=$(refs $base)
    python3 experiments/run_sweep.py --codec encodec:3 --reps 5 --references $R \
        --out "results/detune_encodec3_${base}.csv" > "logs/detune_encodec3_${base}.log" 2>&1 &
  done
  wait
  for base in 220 880; do
    echo "== $base Hz"; python3 analysis/analyze_detuning.py "results/detune_encodec3_${base}.csv" | tail -6
  done
  ;;
corpus)
  for c in encodec:3 dac16:6 opus:12; do
    tag="corpus_pull_${c/:/}"
    python3 experiments/corpus_pull.py --audio-root corpora/gtzan_detuned --codec "$c" \
        --max-files 200 --out "results/${tag}.csv" > "logs/${tag}.log" 2>&1
    echo "== $c"; python3 analysis/analyze_corpus_pull.py "results/${tag}.csv"
  done
  ;;
asr)
  python3 experiments/run_asr.py --codec encodec:3 --per-language 100 --out results/asr_encodec3_n100.csv
  python3 experiments/run_asr_mms.py --codec encodec:3 --per-language 100 --out results/asr_mms_encodec3_n100.csv
  python3 experiments/run_asr_mms.py --codec mimi:8 --per-language 100 --out results/asr_mms_mimi_n100.csv
  for f in asr_encodec3_n100 asr_mms_encodec3_n100 asr_mms_mimi_n100; do
    echo "== $f"; python3 analysis/analyze_asr.py "results/$f.csv" | tail -25
  done
  ;;
causal3)
  # Three arms, three seeds. grid: original clips. flat: every clip resampled by
  # a random offset within the semitone. gridres: every clip resampled by
  # exactly one semitone, the control for the resampling itself.
  R=$(refs 440)
  [ -d corpora/gtzan_gridres ] || python3 experiments/make_detuned_corpus.py --src corpora/gtzan \
      --dst corpora/gtzan_gridres --max-files 400 --whole-semitones
  for seed in 0 1 2; do
    for arm in grid:gtzan flat:gtzan_detuned gridres:gtzan_gridres; do
      name=${arm%%:*}; src=${arm#*:}; tag="ftm_${name}_s${seed}"
      if [ ! -f "checkpoints/encodec_${tag}/config.json" ]; then
        python3 experiments/finetune_encodec.py --audio-root "corpora/${src}" --steps 4000 \
            --seed $seed --out "checkpoints/encodec_${tag}" > "logs/${tag}_train.log" 2>&1
      fi
      python3 experiments/run_sweep.py --codec "encodec_ft:checkpoints/encodec_${tag}@3.0" \
          --reps 5 --references $R --out "results/${tag}.csv" > "logs/${tag}.log" 2>&1 &
    done
  done
  wait
  for f in results/ftm_*_s?.csv; do echo "== $f"; python3 analysis/analyze_detuning.py "$f" | tail -n 5; done
  ;;
causal5)
  # Four arms, five seeds: the three arms above plus gridmix, a control matched
  # to the flat arm in MEAN resampling magnitude (each clip shifted by 0 or
  # exactly 100 cents, mean 50 cents) that keeps the grid peaked. Two
  # fine-tunes run concurrently on an 80 GB GPU; sweeps follow each checkpoint.
  R=$(refs 440)
  [ -d corpora/gtzan_gridres ] || python3 experiments/make_detuned_corpus.py --src corpora/gtzan \
      --dst corpora/gtzan_gridres --max-files 400 --whole-semitones
  [ -d corpora/gtzan_gridmix ] || python3 experiments/make_detuned_corpus.py --src corpora/gtzan \
      --dst corpora/gtzan_gridmix --max-files 400 --mixed-semitones
  jobs_list=()
  for seed in 0 1 2 3 4; do
    for arm in grid:gtzan flat:gtzan_detuned gridres:gtzan_gridres gridmix:gtzan_gridmix; do
      jobs_list+=("${arm}:${seed}")
    done
  done
  run_one () {
    local arm=$1 src=$2 seed=$3 tag="ftm_${1}_s${3}"
    if [ ! -f "checkpoints/encodec_${tag}/config.json" ]; then
      python3 experiments/finetune_encodec.py --audio-root "corpora/${src}" --steps 4000 \
          --seed $seed --out "checkpoints/encodec_${tag}" > "logs/${tag}_train.log" 2>&1
    fi
    [ -f "results/${tag}.csv" ] || python3 experiments/run_sweep.py \
        --codec "encodec_ft:checkpoints/encodec_${tag}@3.0" \
        --reps 5 --references $R --out "results/${tag}.csv" > "logs/${tag}.log" 2>&1
  }
  i=0
  for job in "${jobs_list[@]}"; do
    arm=${job%%:*}; rest=${job#*:}; src=${rest%%:*}; seed=${rest#*:}
    run_one "$arm" "$src" "$seed" &
    i=$((i+1)); if [ $((i % 2)) -eq 0 ]; then wait; fi
  done
  wait
  python3 analysis/summary_causal.py results
  ;;
saraga)
  python3 - <<'PY'
import mirdata
d = mirdata.initialize("saraga_carnatic", data_home="corpora/saraga_carnatic")
d.download(partial_download=None, cleanup=True)
print(d.validate())
PY
  for c in encodec:3 dac16:6 opus:12; do
    tag="corpus_pull_saraga_${c/:/}"
    python3 experiments/corpus_pull.py --audio-root corpora/saraga_carnatic --codec "$c" \
        --max-files 200 --out "results/${tag}.csv" > "logs/${tag}.log" 2>&1
    echo "== $c"; python3 analysis/analyze_corpus_pull.py "results/${tag}.csv"
  done
  ;;
swap)
  R=$(refs 440)
  S="facebook/encodec_24khz"
  for arm in grid flat; do
    F="checkpoints/encodec_ftm_${arm}_s0"
    python3 experiments/run_sweep.py --codec "encodec_swap:${S}|${F}@3.0" --reps 5 --references $R \
        --out "results/swap_stockenc_${arm}dec.csv" > "logs/swap_stockenc_${arm}dec.log" 2>&1 &
    python3 experiments/run_sweep.py --codec "encodec_swap:${F}|${S}@3.0" --reps 5 --references $R \
        --out "results/swap_${arm}enc_stockdec.csv" > "logs/swap_${arm}enc_stockdec.log" 2>&1 &
  done
  wait
  for f in results/swap_*.csv; do echo "== $f"; python3 analysis/analyze_detuning.py "$f" | tail -n 5; done
  ;;
causal_dac)
  # Second codec family for the causal contrast: DAC 16 kHz at Q6, decoder-only
  # fine-tune (experiments/finetune_dac.py), arms grid and flat, five seeds, on
  # the same references and reps as causal5. Fine-tunes run two at a time,
  # then the sweeps four at a time. The stock model is swept on the same
  # references as well: results/detune_dac16.csv was run on a different
  # reference list (ten pitches to 90 cents, four reps), so it is not the
  # matched baseline and is left as it is.
  R=$(refs 440)
  ft_one () {
    local arm=$1 src=$2 seed=$3 tag="dac_ftm_${1}_s${3}"
    [ -f "checkpoints/${tag}/config.json" ] || python3 experiments/finetune_dac.py \
        --audio-root "corpora/${src}" --steps 4000 --seed $seed \
        --out "checkpoints/${tag}" > "logs/${tag}_train.log" 2>&1
  }
  sweep_one () {   # $1 codec spec, $2 result tag
    [ -f "results/${2}.csv" ] || python3 experiments/run_sweep.py --codec "$1" --reps 5 \
        --references $R --out "results/${2}.csv" > "logs/${2}.log" 2>&1
  }
  i=0
  for seed in 0 1 2 3 4; do
    for arm in grid:gtzan flat:gtzan_detuned; do
      ft_one "${arm%%:*}" "${arm#*:}" "$seed" &
      i=$((i+1)); if [ $((i % 2)) -eq 0 ]; then wait; fi
    done
  done
  wait
  sweep_one dac16:6 dacftm_stock &
  i=1
  for seed in 0 1 2 3 4; do
    for arm in grid flat; do
      sweep_one "dac_ft:checkpoints/dac_ftm_${arm}_s${seed}@6" "dacftm_${arm}_s${seed}" &
      i=$((i+1)); if [ $((i % 4)) -eq 0 ]; then wait; fi
    done
  done
  wait
  echo "== stock dac16:6"; python3 analysis/analyze_detuning.py results/dacftm_stock.csv | tail -n 5
  python3 analysis/summary_causal.py results --prefix dacftm
  ;;
mgswap)
  # Same MusicGen tokens through three EnCodec 32 kHz decoders. The decoder is
  # fine-tuned (decoder-only, as in causal5) on GTZAN (grid) and on tuning-
  # flattened GTZAN (flat); encodec_32khz supports only 2.2 kbps, which
  # finetune_encodec.py picks up from the config. The token ids are cached so
  # a re-run with another decoder decodes the very same generations.
  for arm in grid:gtzan flat:gtzan_detuned; do
    name=${arm%%:*}; src=${arm#*:}; tag="encodec32_ftm_${name}_s0"
    if [ ! -f "checkpoints/${tag}/config.json" ]; then
      python3 experiments/finetune_encodec.py --model-id facebook/encodec_32khz --audio-root "corpora/${src}" \
          --steps 4000 --seed 0 --out "checkpoints/${tag}" > "logs/${tag}_train.log" 2>&1 &
    fi
  done
  wait
  python3 experiments/musicgen_swap.py --n 40 --generate-seconds 10 --seed 0 \
      --decoders stock=stock grid=checkpoints/encodec32_ftm_grid_s0 flat=checkpoints/encodec32_ftm_flat_s0 \
      --tokens-cache /workspace/musicgen_tokens --save-audio /workspace/musicgen_swap_audio \
      --out results/musicgen_swap.csv > logs/musicgen_swap.log 2>&1
  tail -n 3 logs/musicgen_swap.log
  python3 analysis/analyze_musicgen_swap.py results/musicgen_swap.csv
  ;;
*)
  echo "usage: $0 {setup|classical|registers|corpus|asr|causal3|causal5|causal_dac|saraga|swap|mgswap}"; exit 1 ;;
esac

# Reproducing the paper

Every figure and table maps to a command. Results land in `results/` as raw
per-trial CSV with a `.meta.json` sidecar; every derived number comes from
`analysis/`.

## Setup

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python data/fetch_checkpoints.py        # ~2 GB, ten checkpoints
```

**Do not install `xcodec2` into this environment.** It downgrades torch to
2.5.0, and every result here was produced under 2.8.0. We found this only
because each result file carries a `.meta.json` recording the package versions
of the run that produced it; all 49 recorded runs agree on torch 2.8.0+cu128 and
transformers 5.16.1. If you extend this work, keep those sidecars.

A GPU helps but is not required for most of this. The pitch experiments are
**CPU-bound on F₀ estimation**, not GPU-bound: the codec forward pass is a small
fraction of the time. Only the ASR passes and the fine-tuning genuinely need a
GPU.

## The gate, first

Nothing below means anything until these pass.

```bash
make gate
```

| Check | Expected |
|---|---|
| `experiments/test_estimator.py` | `PASS`, floor below 10⁻⁴ cents |
| identity codec through the full pipeline | `NULL` |
| pilot sweep, EnCodec 3 kbps | grid bias ≈ 9 cents |

The identity run is the important one: it puts the same stimuli through the same
estimator and the same analysis with **no codec**, and must find nothing.

---

## Main text

**Exclusion scheme.** Every number in the paper uses the octave gate alone,
which excludes 0% of trials on every reported run. The estimator cross-check
(`--exclusion=full` on `analyze_sweep.py`, `analyze_detuning.py` and
`analyze_rate.py`) is a robustness variant and is reported as such in the
paper, because it fires preferentially 30 to 50 cents from a grid point.
`analysis/diagnose_exclusions.py` prints all three schemes side by side.

### Figure 1, the registration regression

Eleven reference pitches from 0 to 100 cents above A440 in 10-cent steps. The
100-cent point is one semitone up and folds onto the 0-cent condition, so ten
distinct conditions enter the regression.

```bash
REFS="440 442.5489 445.1126 447.6911 450.2845 452.8930 455.5166 458.1553 460.8094 463.4789 466.1638"
python experiments/run_sweep.py --codec encodec:3 --reps 5 --references $REFS \
    --out results/detune_encodec3.csv
python analysis/analyze_detuning.py results/detune_encodec3.csv \
    figures/detuning_regression.png
```
Expect slope 1.0010, CI [0.9935, 1.0085], *R²* 0.99988, amplitude 13.72 ± 0.16.

### The universality table, phase registration across codecs

```bash
for c in encodec:3 encodec:24 encodec48:6 mimi:8 dac16:6 dac24:8 dac:4 snac snac32 snac44; do
  python experiments/run_sweep.py --codec $c --reps 4 --references $REFS \
      --out results/detune_${c/:/}.csv
done
python analysis/summary_table.py
```
Two conditions are **refused** rather than reported: SNAC 24k and DAC 44k fail
the amplitude-stability guard. That is the intended behaviour, not a failure.

### The rate table and the rate-scaling figure, with the bypass floor

```bash
for kb in 1.5 3 6 12 24; do
  python experiments/run_sweep.py --codec encodec:$kb --reps 5 \
      --references 440 452.8929 --out results/rate_encodec_${kb}.csv
done
python experiments/run_sweep.py --codec encodec_bypass --reps 5 \
    --references 440 452.8929 --out results/mech_bypass.csv
python analysis/analyze_rate.py
```
Expect the sweep to plateau at the bypass value (5.66 cents), raw slope −0.324
and floor-subtracted slope −2.612.

### The codebook probe

```bash
python experiments/probe_codebook.py --codec encodec:3 --out results/probe_encodec3.csv
python analysis/analyze_probe.py results/probe_encodec3.csv
```
Expect uniform boundary positions, Rayleigh *p* = 0.86.

### The training-density premise (pitch histograms)

```bash
python data/fetch_corpora.py
python experiments/pitch_histogram.py --audio-root corpora/gtzan \
    --out results/hist_gtzan.csv
python experiments/pitch_histogram.py --audio-root corpora/librispeech \
    --out results/hist_librispeech.csv
python analysis/plot_histograms.py
```
Expect peak/mean 1.788 for music and 1.113 for speech.

### The causal experiment

```bash
python experiments/make_detuned_corpus.py --src corpora/gtzan --dst corpora/gtzan_detuned
python experiments/pitch_histogram.py --audio-root corpora/gtzan_detuned \
    --out results/hist_gtzan_detuned.csv          # verify: 1.073
for arm in grid:gtzan flat:gtzan_detuned; do
  python experiments/finetune_encodec.py --audio-root corpora/${arm#*:} --steps 4000 \
      --out checkpoints/encodec_ftm_${arm%%:*}
  python experiments/run_sweep.py --codec encodec_ft:checkpoints/encodec_ftm_${arm%%:*}@3.0 \
      --reps 5 --references $REFS --out results/ftm_${arm%%:*}.csv
done
```
Expect 4.44 cents on grid-peaked music against 3.76 on flattened, an 18%
reduction with both retaining unit slope.

---

## Experiments 2 and 3

```bash
python data/get_fleurs_pod.py                      # 21 languages, test splits
python experiments/run_phonology.py --codec encodec:3 --per-language 150 \
    --out results/phon_encodec3_big.csv
python analysis/analyze_phonology.py results/phon_encodec3_big.csv

python experiments/run_asr.py --codec encodec:3 --per-language 30 \
    --out results/asr_encodec3_v2.csv              # Whisper
python experiments/run_asr_mms.py --codec encodec:3 --per-language 30 \
    --out results/asr_mms_encodec3.csv             # MMS cross-check
python analysis/analyze_asr.py results/asr_mms_encodec3.csv
```

Both return nulls. Two caveats are built into the code rather than left to the
reader: utterances are **level-normalised** before coding, because FLEURS levels
span a factor of 100 and a codec cannot represent near-silent input (Whisper
then emits its silence hallucination, which reads as catastrophic codec damage);
and languages where the recogniser fails **before** any codec is applied are
flagged and excluded, since a baseline error near 1.0 leaves no headroom.

## The ecological test, and its control

```bash
python data/get_nsynth.py
python experiments/retune_real.py --audio-root corpora/nsynth --codec encodec:3 \
    --max-files 300 --out results/retune_encodec3_big.csv
# the control that validates the protocol: same protocol, synthetic stimuli
python experiments/retune_real.py --synthetic-control --codec encodec:3 \
    --max-files 200 --out results/retune_synthetic.csv
```
The control must find the effect (+6.6 cents) for the null on real recordings to
mean anything.

---

## Supporting runs

These produce results the paper discusses but that are not headline figures.

```bash
# Does vibrato destroy the effect? It amplifies it, refuting the
# out-of-distribution account. check_vibrato confirms the trend is the codec and
# not the estimator, by running the same statistic on the UNCODED signal.
for v in 0 5 10 20 40; do
  python experiments/run_sweep.py --codec encodec:3 --reps 4 --vibrato-cents $v \
      --references 440 452.8929 --out results/vib_${v}.csv
done
python analysis/check_vibrato.py

# The failed designs, retained because the paper discusses why they failed.
python experiments/train_rvq.py --distribution 12tet --steps 30000 \
    --out checkpoints/rvq_12tet.pt          # collapses or keeps only the fundamental
python experiments/tune_loss.py 6000        # the loss sweep that showed why

# Corpus and model acquisition beyond the core checkpoints.
python data/fetch_aux.py            # forced aligner and NSynth, via HF mirrors
python data/fetch_pod_corpora.py    # GTZAN and LibriSpeech samples
python data/extract_librispeech.py  # LibriSpeech ships as parquet; decode a sample
python data/fetch_makam.py          # open makam annotations from Zenodo (no audio)
```

**Makam audio is not obtainable through this repository.** A Dunya API token
gives metadata and SymbTr scores; the `/document/` audio endpoints use session
authentication and return 401 under token auth, including through the official
`pycompmusic` client. Audio requires a separate CompMusic agreement.

## Regenerating everything derived

```bash
make figures        # every paper figure from results/
make results        # RESULTS.md
```

Neither reads anything but `results/`. If a figure cannot be regenerated this
way it does not belong in the paper.

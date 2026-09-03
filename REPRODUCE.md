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
of the run that produced it; all 76 sidecars record torch 2.8.0+cu128 and
transformers 5.16.1 (the seven `corpus_pull_*` sidecars were annotated after
the fact from a sweep sidecar of the same pod session, and say so). If you extend this work, keep those sidecars.

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
which excludes 0% of trials on the headline run and up to 9% on most reported
runs; DAC 16k loses 65% (`analysis/guard_sensitivity.py` lists every run, and
`--exclusion=none` shows its registration slope survives without the gate). The estimator cross-check
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
Expect slope 1.0010, CI [0.9922, 1.0099] (t on 8 degrees of freedom), *R²* 0.99988,
amplitude 13.72 ± 0.16.

### The universality table, phase registration across codecs

```bash
for pair in encodec:24=encodec24kbps encodec48:6=encodec48 mimi:8=mimi dac16:6=dac16 dac24:8=dac24 dac:4=dac44 snac=snac snac32=snac32 snac44=snac44; do
  c=${pair%%=*}; stem=${pair##*=}
  python experiments/run_sweep.py --codec $c --reps 4 --references $REFS \
      --out results/detune_$stem.csv     # the checked-in file names; the headline encodec:3 run above uses --reps 5
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
That is the single-seed original. The replicated version, five seeds with a
whole-semitone resampling control and a magnitude-matched 0/100-cent control,
is `bash infra/pod_run.sh causal5` (about 2.5 hours on one A100): expect
4.51 +- 0.09 cents on the original clips, 4.62 +- 0.04 on the same clips
resampled by exactly one semitone, 4.69 +- 0.05 on the 0/100-cent mix, and
3.75 +- 0.11 on the flattened corpus (single seeds move by up to 0.2 cents
between GPU instances; `results/replication/` is a second instance's run) (`python analysis/summary_causal.py
results`). The three-seed, three-arm subset is `causal3`.
Note that this fine-tuning changes only the decoder (code assignment is an
argmin, so no gradient reaches the encoder or codebooks); `bash
infra/pod_run.sh swap` demonstrates it. The Carnatic measurement is
`bash infra/saraga_fetch.sh` (resumable 14 GB download from Zenodo, then
`corpus_pull.py` on the recordings); expect EnCodec +2.63 cents [2.27, 2.97]
and Opus nothing.

---

## Experiment 2: the two speech tests

```bash
python data/get_fleurs_pod.py                      # 21 languages, test splits
python experiments/run_phonology.py --codec encodec:3 --per-language 150 \
    --out results/phon_encodec3_big.csv
python analysis/analyze_phonology.py results/phon_encodec3_big.csv
# Table 2 also reports Mimi and DAC 16k: repeat with --codec mimi:8 --out results/phon_mimi.csv
# and --codec dac16:6 --out results/phon_dac16.csv (150 utterances per language each).

python experiments/run_asr.py --codec encodec:3 --per-language 100 \
    --out results/asr_encodec3_n100.csv            # Whisper
python experiments/run_asr_mms.py --codec encodec:3 --per-language 100 \
    --out results/asr_mms_encodec3_n100.csv        # MMS
python experiments/run_asr_mms.py --codec mimi:8 --per-language 100 \
    --out results/asr_mms_mimi_n100.csv
python analysis/analyze_asr.py results/asr_mms_encodec3_n100.csv   # prints bootstrap intervals
```

Both return nulls. Two caveats are built into the code rather than left to the
reader: utterances are **level-normalised** before coding, because FLEURS levels
span a factor of 100 and a codec cannot represent near-silent input (Whisper
then emits its silence hallucination, which reads as catastrophic codec damage);
and languages where the recogniser fails **before** any codec is applied are
flagged and excluded, since a baseline error near 1.0 leaves no headroom.

## The classical-codec control, the extra registers, and real music

`infra/pod_run.sh` runs all of these (`classical`, `registers`, `corpus`);
the commands behind it are:

```bash
REFS=$(python3 -c "print(' '.join(f'{440*2**(d/1200):.4f}' for d in range(0,101,10)))")
for c in opus:6 opus:12 mp3:16 mp3:32; do          # no learned component
  python experiments/run_sweep.py --codec $c --reps 5 --references $REFS --out results/detune_${c/:/}.csv
  python analysis/analyze_detuning.py results/detune_${c/:/}.csv
done
python experiments/run_sweep.py --codec opus:6 --reps 5 --references 110 220 440 880 --out results/octaves_opus6.csv
python experiments/make_detuned_corpus.py --src corpora/gtzan --dst corpora/gtzan_detuned
for c in encodec:3 dac16:6 opus:6 opus:12; do      # the transfer function on real music
  python experiments/corpus_pull.py --audio-root corpora/gtzan_detuned --codec $c --out results/corpus_pull_${c/:/}.csv
  python analysis/analyze_corpus_pull.py results/corpus_pull_${c/:/}.csv
done
```
Expect EnCodec 3 kbps to pull real music by +2.49 cents [2.21, 2.81] with a
3.05-cent sinusoid at phase +163°, and Opus to show nothing. Opus 12 kbps and
MP3 32 kbps are refused by the guard; MP3 16 kbps registers at 0.01 cents;
Opus 6 kbps shows a 1.6-cent residual with zero grid bias whose amplitude
tracks the octave-gate rate, not pitch.

## The ecological test on isolated notes, and its control

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

## Accumulation under repeated coding

Does the pull compound when audio is coded again and again? `encodec_iter:<kbps>@<n>`
applies EnCodec n times in succession (decode, then encode the decoded audio).
The headline sweep through 1, 2, 4 and 8 round trips runs on CPU in about
fifteen minutes each:

```bash
for k in 1 2 4 8; do
  python experiments/run_sweep.py --codec encodec_iter:3@$k --reps 5 --out results/iter_encodec3_k$k.csv
  python analysis/analyze_sweep.py results/iter_encodec3_k$k.csv
done
```
Expect all-trial grid biases of 8.88, 8.20, 7.39 and 7.26 cents at the on-grid
reference, with the fitted amplitude between 13.0 and 13.9 cents and the phase
within 3 degrees: the pull is applied once and then held, not accumulated.
These four runs were produced on CPU (torch 2.8.0, transformers 5.16.1 pinned
to the same checkpoint revision); the k = 1 run reproduces the GPU value 8.88
of `rate_encodec_3.csv` exactly.

## Downstream generation through MusicGen

Does a token language model built on EnCodec inherit the grid? `experiments/musicgen_pull.py`
generates with `facebook/musicgen-small` (EnCodec tokens, EnCodec decoder) and reads the
output with the paper's blind estimator. Needs a GPU and the flattened corpus.

```bash
python experiments/musicgen_pull.py --mode text --n 60 --out results/musicgen_text.csv
python experiments/musicgen_pull.py --mode continue --audio-root corpora/gtzan_detuned --n 80 \
    --out results/musicgen_continue.csv
python analysis/analyze_musicgen.py results/musicgen_text.csv       # peak/mean 4.28 at +3.6 cents
python analysis/analyze_musicgen.py results/musicgen_continue.csv   # grid-directed +7.5 [4.3, 11.4] cents, then the null models
```
Text-prompted output peaks at 4.28 times its mean within the semitone (GTZAN 1.79), 3.6 cents
sharp of A440. Continuations of tuning-flattened prompts move toward the grid by a median
7.5 cents for prompts at least 20 cents off-grid, but the same script's null block shows a
shuffle null (prompt-ignoring reversion to the model's grid-peaked output) of 13.3 [0.4, 23.5]
cents and a direction-free tracking null of 0 [-4.1, 4.1]: the continuations track the prompt
with a grid-directed residual, and the statistic does not separate a pull from reversion to the
marginal. Neither test was pre-specified.

## Which partials move (spectral check)

```bash
python experiments/spectral_check.py --kbps 3      # ~2 min on CPU; also --kbps 1.5 and 24
```
Prints, per partial, the location of the decoded line relative to the input partial at 440 and
220 Hz for δ = 0, ±20, ±30, ±40 cents, the estimator's reading on all eight partials and on the
first two, and writes `figures/spectral_check.pdf`. Expect the fundamental within 0.4 cents at
every bitrate, and the first displaced partial at about 0.9 / 1.3 / 2.2 kHz for 1.5 / 3 / 24 kbps
(Table A15 in the paper).

## The flat-sampling nulls, the YIN stage, and the isolated-notes recipe

```bash
python analysis/flat_sampling_null.py                 # 1.070 at 53,678 samples (speech), 1.037 at 180,859 (music)
python experiments/test_yin_bias.py                   # plain YIN vs the refined estimator on 721 synthetic fundamentals
python analysis/analyze_retune.py results/retune_encodec3.csv   # 884/3455 usable, +0.007 [-0.232, +0.260]
```
`test_yin_bias.py` shows the YIN stage used by the histograms, the MusicGen readings and the
phonology contours is about 0.2 to 0.3 cents sharp on clean tones and flat across the
within-semitone position; on MusicGen's polyphonic output it and the refined estimator agree on
the density's peak/mean (4.28 vs 4.27) but differ by about 2 cents on its absolute offset. Point it
at a directory of wavs with `--audio-dir` to repeat that comparison. `analyze_retune.py` is the
recipe behind the isolated-notes rows of the ecological table (usable: both coarse-seeded readings
agree within 50 cents and the shift is within the 60-cent window; statistic: median shift toward
the grid for notes 30 cents or more from a grid pitch minus that for notes within 10 cents;
bootstrap over readings); `--sensitivity` shows the null holds under every gate and split.

## Table 1's adjusted intervals, phase errors and the DAC 16k gate profile

```bash
python analysis/summary_table.py results            # adds 99.5% (Bonferroni) CI, phase SE, strict pass/fail
python analysis/analyze_detuning.py results/detune_dac16.csv --gate-profile
```
The strict rule passes exactly five conditions (four EnCodec, SNAC 32k). DAC 16k's gate rate is
flat over the whole sweep (64 to 66%) and rises from 48% to 63% with grid distance at the
on-grid reference; its off-grid bias with octave errors folded modulo 1200 cents is
-0.14 [-0.27, 0.01].

## Five seeds and a magnitude-matched control (causal experiment)

`bash infra/pod_run.sh causal5` fine-tunes four arms (original, +100 cents, mixed 0/100 cents,
flattened) for seeds 0 to 4 and sweeps each; `python analysis/summary_causal.py results` prints
the arm means, seed spreads and Welch tests. Expected output:

```
  arm      seeds   amplitude (c)     sd     slope range
    grid         5            4.51   0.09   [0.998, 0.999]
  gridres      5            4.62   0.04   [0.996, 0.997]
  gridmix      5            4.69   0.05   [0.995, 0.997]
  flat         5            3.75   0.11   [0.996, 0.998]
  flat vs grid     drop 17.0%   t = 12.40  df = 7.6
  flat vs gridres  drop 19.0%   t = 17.02  df = 5.1
  flat vs gridmix  drop 20.2%   t = 17.90  df = 5.5
```

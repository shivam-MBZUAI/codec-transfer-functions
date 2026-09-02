# Codec Transfer Functions

**Measuring *where* a neural audio codec loses information, rather than how much.**

Neural audio codecs supply the token vocabulary for modern audio language
models, and they are evaluated almost entirely by aggregate perceptual scores.
Those scores say how much a codec loses on average. They cannot say where it
goes.

This repository treats a codec as a measurement instrument: drive it with
stimuli in which exactly one property varies, recover that property from the
output, and report the **transfer function** and its residual.

The headline result is that the residual is periodic in log frequency with a
period of exactly one semitone, and registered to an **absolute** twelve-tone
grid rather than to the interval under test.

<p align="center">
  <img src="figures/detuning_regression.png" width="88%"><br>
  <em>Detuning the reference pitch advances the residual's phase with slope
  1.0010, 95% CI [0.9935, 1.0085], R² = 0.99988. A residual locked to the
  interval, or produced by the analysis, would sit on the dotted line at zero.</em>
</p>

---

## What was found

| | |
|---|---|
| **Registered to the grid** | slope 1.0010, *R²* = 0.99988, across 10 conditions and 4 codec families |
| **Aggregate metrics conceal it** | DAC 16k and SNAC 44k report a median grid bias of 0.000 and register cleanly |
| **Not architectural** | period constant in cents across four octaves; conv strides would give constant Hz |
| **Not in the codebook** | removing quantisation leaves 5.66 of 8.88 cents; code boundaries uniform (Rayleigh *p* = 0.86) |
| **Learned** | flattening the tuning grid of the training audio weakens it by 18% |
| **Bounded** | absent on real instrument recordings, in phonology across 20 languages, and in downstream WER |

Two of seven pre-registered predictions are falsified. **[FINDINGS.md](FINDINGS.md)
states every number, every null, and every design that failed.**

---

## Quickstart

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
make gate
```

`make gate` runs the three checks that must pass before any measurement means
anything, and takes a few minutes:

1. the estimator's noise floor on uncoded stimuli
2. the whole pipeline with **no codec in the loop**, which must report null
3. the pilot sweep on EnCodec

See **[REPRODUCE.md](REPRODUCE.md)** for the exact command behind every figure
and table in the paper.

---

## Repository map

```
experiments/     measurement entry points; each writes raw per-trial CSV
  stimuli.py         deterministic synthesis: tone pairs, vowels, vibrato, noise
  estimator.py       YIN + harmonic-sum coarse stages, harmonic least-squares refine
  codec_zoo.py       every codec behind one interface, plus identity and bypass controls
  run_sweep.py       the pitch sweep
  run_phonology.py   Experiment 2
  run_asr.py         Experiment 3, Whisper
  run_asr_mms.py     Experiment 3, MMS cross-check
  train_rvq.py       from-scratch codec (a failed design, retained)
  finetune_encodec.py  the causal experiment
  retune_real.py     ecological test on real recordings
  probe_codebook.py  reads code assignments across pitch

analysis/        every derived number and figure
  analyze_sweep.py       summary statistics for one sweep
  analyze_detuning.py    the registration regression
  make_results.py        regenerates RESULTS.md
  make_figures.py        regenerates every paper figure
  diagnose_exclusions.py checks the exclusion rule is not creating the effect

data/            corpus and checkpoint acquisition
infra/           Slurm and detached-session tooling
results/         raw per-trial CSVs, each with a .meta.json provenance
                 sidecar. See results/README.md for what each family is,
                 including the ones retained but deliberately not reported
figures/         generated; never hand-edited
docs/            DATA.md, EXPERIMENTS.md, CLUSTER.md, PIPELINE.md
```

`run_*.py` computes no statistics. It writes raw estimates and a sidecar
recording arguments and package versions. Every derived number comes from
`analysis/`, so the analysis can be rerun and audited without repeating the
codec passes.

---

## What is measured

For a stimulus `x(θ)` in which one property takes value `θ`, and an estimator
`E` recovering it:

```
T(θ) = E[ C(x(θ)) ]                    transfer function
r(θ) = T(θ) − θ                        residual
b(θ) = sign(g(θ) − θ) · r(θ)           grid bias
```

`g(θ)` is the nearest 12-tone equal-tempered interval. **The sign carries the
argument**: a residual of a given magnitude symmetric about the true value is
ordinary degradation; the same magnitude directed consistently toward `g(θ)` is
quantisation onto a learned grid.

---

## Controls

The pipeline is built around the ways this measurement can lie.

| Control | What it rules out |
|---|---|
| `identity` codec | any effect from the stimuli, estimator or analysis |
| Detuned reference | an effect locked to the interval rather than absolute pitch |
| Per-sample-rate noise floor | estimator error read as codec error |
| Blind estimation | ground truth leaking into the estimate and suppressing the effect |
| Octave gate at 200 cents | estimator failures, without suppressing a real effect (max measurable is 50 cents). **The only exclusion in the primary analysis**; it fires on 0% of trials in every reported run |
| Estimator cross-check (`--exclusion=full`) | reported as a robustness variant, never as the primary number: it fires preferentially 30 to 50 cents from a grid point |
| Exclusion-vs-grid-distance | an exclusion rule manufacturing the effect |
| Sawtooth vs sinusoid fit | confusing a density correction with coarse cell assignment |
| **Amplitude-stability guard** | **a confident slope fitted through noise phases** |

That last one is not decoration. Two codecs produced clean-looking slopes
(−0.92 at *R²* 0.61, and 1.017 at *R²* 0.994) from phases that were pure noise.
Both are now refused and reported as not measurable. Anyone repeating this on a
codec outside its operating domain will hit the same trap.

---

## A note on numbers

`RESULTS.md` is generated by `analysis/make_results.py` from files in
`results/`. There is no path by which a value that was not measured can appear
in it, and unrun experiments are listed as *not yet measured* rather than shown
with placeholders. The figures are generated the same way.

## Licence

MIT. See [LICENSE](LICENSE).

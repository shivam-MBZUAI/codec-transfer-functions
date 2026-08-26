# Codec transfer functions

Measuring **where** a neural audio codec loses information, rather than how much.

Aggregate codec benchmarks report a scalar summary of reconstruction error over
a corpus. That marginalises out the dependence on the property under test, and
so cannot distinguish a codec that loses a little of everything from one that
loses a single class of distinction entirely. This repository treats a codec as
a measurement instrument: drive it with stimuli in which exactly one property
varies, recover that property from the output, and report the *transfer
function* and its residual.

The pitch experiment needs no dataset. Stimuli are synthesised from a short
deterministic script, so the central result reproduces from this repository and
publicly released codec checkpoints alone.

## Quick start

```bash
uv venv --python 3.12 && uv pip install -r requirements.txt
cd experiments

python test_estimator.py                                    # must print PASS
python run_sweep.py --codec identity:24000 --reps 2 --theta-step 25 \
    --out ../results/selftest_identity.csv
python analyze_sweep.py ../results/selftest_identity.csv    # must report NULL
```

Those two must pass before any codec run means anything. The first measures the
estimator's noise floor; the second runs the same stimuli through the same
estimator and analysis with **no codec**, and must find nothing.

Then the real thing:

```bash
python run_sweep.py --codec encodec:3 --reps 3 --out ../results/pilot_encodec3.csv
python analyze_sweep.py ../results/pilot_encodec3.csv --fig ../figures/pilot.png
```

## What is measured

For a stimulus `x(theta)` in which one property takes value `theta`, and an
estimator `E` recovering it:

```
T(theta) = E[ C(x(theta)) ]        transfer function
r(theta) = T(theta) - theta        residual
b(theta) = sign(g(theta) - theta) * r(theta)     grid bias
```

where `g(theta)` is the nearest 12-tone equal-tempered interval. The sign is the
point: a residual of a given magnitude symmetric about the true value is
ordinary degradation, while the same magnitude directed consistently toward
`g(theta)` is quantisation onto a learned grid.

## Controls

The pipeline is built around the ways this measurement can lie to you.

| Control | What it rules out |
|---|---|
| `identity` codec | any effect produced by the stimuli, estimator or analysis |
| Detuned reference | an effect locked to the interval rather than to absolute pitch |
| Per-sample-rate noise floor | estimator error masquerading as codec error |
| Blind estimation | ground truth leaking into the estimate and suppressing the effect |
| Octave gate at 200 cents | estimator failures, without being able to suppress a real effect (the largest measurable effect is 50 cents) |
| Exclusion-vs-grid-distance correlation | an exclusion rule that manufactures the effect |
| Sawtooth vs sinusoid fit | confusing a density correction with coarse cell assignment |

## Layout

| file | role |
|---|---|
| `experiments/stimuli.py` | deterministic tone-pair synthesis, no dataset |
| `experiments/estimator.py` | YIN and harmonic-sum coarse stages, harmonic least-squares refinement |
| `experiments/codec_zoo.py` | codec round trips behind one interface, plus the identity control |
| `experiments/run_sweep.py` | runs a sweep, writes raw per-trial CSV, computes no statistics |
| `experiments/analyze_sweep.py` | every summary statistic and figure |
| `experiments/test_estimator.py` | noise floor and octave robustness |

`run_sweep.py` writes only raw estimates. Every derived number comes from
`analyze_sweep.py`, so the analysis can be rerun and audited without repeating
the codec passes. Each results CSV carries a `.meta.json` sidecar recording the
full argument set and package versions.

## Status

Experiment 1's pipeline is complete and tested against the identity control.
The EnCodec, DAC and Mimi wrappers have not yet been executed against real
checkpoints. See `EXPERIMENTS.md` for the full programme and what remains.

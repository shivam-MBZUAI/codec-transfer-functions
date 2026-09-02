# Codec transfer functions

Measuring **where** a neural audio codec loses information, rather than how much.

Aggregate codec benchmarks report a scalar summary of reconstruction error over
a corpus. That marginalises out the dependence on the property under test, so it
cannot distinguish a codec that loses a little of everything from one that loses
a single class of distinction entirely. This repository treats a codec as a
measurement instrument: drive it with stimuli in which exactly one property
varies, recover that property from the output, and report the **transfer
function** and its residual.

The pitch experiments need no dataset. Stimuli come from a short deterministic
script, so the central result reproduces from this repository and publicly
released checkpoints alone.

| | |
|---|---|
| **[DATA.md](DATA.md)** | every model and corpus, with links and download instructions |
| **[EXPERIMENTS.md](EXPERIMENTS.md)** | the programme, why each experiment is in it, and what is blocked |
| **[RESULTS.md](RESULTS.md)** | generated from `results/`; never hand-written |
| **[cluster/README.md](cluster/README.md)** | Slurm setup and the environment traps worth knowing |

---

## Quick start

```bash
uv venv --python 3.12 && uv pip install -r requirements.txt
python cluster/fetch_checkpoints.py
cd experiments
```

Two things must pass before any codec run means anything:

```bash
python test_estimator.py                                     # must print PASS
python run_sweep.py --codec identity:24000 --reps 2 --theta-step 25 \
    --out ../results/selftest_identity.csv
python analyze_sweep.py ../results/selftest_identity.csv      # must report NULL
```

The first measures the estimator's own noise floor. The second runs the same
stimuli through the same estimator and the same analysis with **no codec in the
loop**, and must find nothing. An analysis that reports an effect on that run is
measuring itself.

Then the real thing:

```bash
python run_sweep.py --codec encodec:3 --reps 3 --out ../results/pilot_encodec3.csv
python analyze_sweep.py ../results/pilot_encodec3.csv --fig ../figures/pilot.png
python ../scripts/make_results.py        # regenerate RESULTS.md
```

---

## What is measured

For a stimulus `x(theta)` in which one property takes value `theta`, and an
estimator `E` recovering it from a waveform:

```
T(theta) = E[ C(x(theta)) ]                      transfer function
r(theta) = T(theta) - theta                      residual
b(theta) = sign(g(theta) - theta) * r(theta)     grid bias
```

`g(theta)` is the nearest 12-tone equal-tempered interval. **The sign carries
the argument.** A residual of a given magnitude symmetric about the true value
is ordinary degradation. The same magnitude directed consistently toward
`g(theta)` is quantisation onto a learned grid. Those are different claims and
aggregate metrics cannot separate them.

---

## Controls

The pipeline is built around the ways this measurement can lie to you.

| Control | What it rules out |
|---|---|
| Amplitude-stability guard | a confident slope fitted through noise phases |
| `identity` codec | any effect produced by the stimuli, estimator or analysis |
| Detuned reference | an effect locked to the interval rather than to absolute pitch |
| Per-sample-rate noise floor | estimator error masquerading as codec error |
| Blind estimation | ground truth leaking into the estimate and suppressing the effect |
| Octave gate at 200 cents | estimator failures, without being able to suppress a real effect, since the largest measurable effect is 50 cents |
| Exclusion vs grid distance | an exclusion rule that manufactures the effect |
| Sawtooth vs sinusoid fit | confusing a density correction with coarse cell assignment |
| Below-floor guard in `make_results.py` | ratios computed from two numbers that are both noise |

---

## Layout

```
experiments/
  stimuli.py           deterministic tone-pair synthesis, no dataset
  estimator.py         YIN + harmonic-sum coarse stages, harmonic LS refinement
  codec_zoo.py         codec round trips behind one interface, plus identity
  run_sweep.py         runs a sweep, writes raw per-trial CSV, no statistics
  analyze_sweep.py     every summary statistic and figure
  test_estimator.py    noise floor and octave robustness
cluster/
  fetch_checkpoints.py core codec weights
  fetch_all.py         ASR models and additional codecs
  fetch_fleurs.py      FLEURS test splits
  sweep.sbatch         Slurm array over codec/rate configurations
scripts/
  make_results.py      regenerates RESULTS.md from results/
```

`run_sweep.py` computes no statistics; it writes raw estimates only. Every
derived number comes from `analyze_sweep.py` or `make_results.py`, so the
analysis can be rerun and audited without repeating the codec passes. Each
results CSV carries a `.meta.json` sidecar recording the full argument set and
package versions, because a results file that cannot say what produced it is not
reproducible evidence.

---

## A note on numbers

`RESULTS.md` is generated. There is no path by which a value that was not
measured can appear in it, and experiments that have not run are listed as *not
yet measured* rather than shown with placeholder values. A placeholder that
looks like a result is how a draft ends up asserting things nobody measured.

# Experiment 1: the pitch transfer function

Run order, cheapest first. Nothing here needs a dataset.

## 0. Environment

```
uv venv --python 3.12 && uv pip install -r ../requirements.txt
```

`numpy` and `matplotlib` alone are enough for steps 1 and 2.

## 1. Estimator noise floor

```
python test_estimator.py
```

Must print PASS. This measures the floor every later claim is judged against.
On uncoded stimuli the retained floor is far below a thousandth of a cent, so
the real floor in a codec run will be set by the codec, not the estimator.

Roughly 2 to 5 percent of uncoded trials are dropped by the octave gate and the
cross-check. That rate is higher than it should be for clean synthetic tones and
is worth reducing, but it does not bias anything as long as it stays
uncorrelated with distance from the grid, which `analyze_sweep.py` reports.

## 2. Null control

```
python run_sweep.py --codec identity:24000 --reps 2 --theta-step 25 \
  --out ../results/selftest_identity.csv
python analyze_sweep.py ../results/selftest_identity.csv
```

Must report NULL and an UNDEFINED phase test. Same stimuli, same estimator, same
analysis, no codec. If this ever reports an effect, the effect is in the
pipeline.

## 3. The go/no-go pilot

```
python run_sweep.py --codec encodec:3 --reps 3 \
  --out ../results/pilot_encodec3.csv
python analyze_sweep.py ../results/pilot_encodec3.csv --fig ../figures/pilot.png
```

About 13 minutes of audio. Two things decide whether the paper exists:

**Does the grid bias clear the noise floor?** If not, `PREDICTIONS.md` says do
not attempt to rescue the microtonal framing.

**Does the phase shift by 180 degrees between the two reference conditions?**
The default references are A440 and A440 detuned by 50 cents. If the residual is
locked to an absolute learned grid, its phase in interval space must shift by
half a period. If it does not move, the effect is an artefact of the analysis,
not a property of the codec.

The analysis also fits a **sawtooth** alongside the sinusoid. This is the
mechanism test. A Bennett-type density correction predicts a sinusoid; coarse
cell assignment, where the codebook simply has a reconstruction level near each
grid point, predicts a sawtooth. Both give "period 100 cents, zero at grid
points, negative just above", so periodicity alone cannot separate them. They
scale differently with rate (sawtooth ~ Delta, sinusoid ~ Delta squared), so
which one wins determines whether the predicted C3 slope is -1 or -2.

## 4. Full sweep

```
python run_sweep.py --codec encodec:3 --reps 20 --references 110 220 440 880 \
  --out ../results/encodec3.csv
```

19,280 trials, about 5.9 hours of audio per codec and rate.

## Files

| file | role |
|---|---|
| `stimuli.py` | deterministic tone-pair synthesis, no dataset |
| `estimator.py` | YIN + harmonic sum coarse, harmonic least-squares refinement |
| `codec_zoo.py` | codec round trips behind one interface, plus the identity control |
| `run_sweep.py` | runs a sweep, writes raw per-trial CSV, computes no statistics |
| `analyze_sweep.py` | every summary statistic and figure, rerunnable without the codec |
| `test_estimator.py` | noise floor and octave-robustness check |

`run_sweep.py` writes only raw estimates. Every number that could reach the
paper is derived in `analyze_sweep.py`, so the analysis can be rerun and audited
without repeating the codec passes.

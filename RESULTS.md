# Results

<!-- GENERATED FILE. Do not edit by hand.
     Regenerate with:  python scripts/make_results.py
     Every number below is computed from a CSV in results/. Nothing here is a
     prediction, a placeholder, or a value typed by a human. -->

Every figure and table here is derived from a file in `results/`. Experiments
that have not run are listed as not yet measured rather than shown with
placeholder values.

## Pitch transfer function
| run | codec | rate | reference | n | floor (c) | on-grid (c) | off-grid (c) | ratio | grid bias (c) | 95% CI | sine R2 | saw R2 | better |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `selftest_identity` | identity | uncoded | 440Hz_ongrid | 98 | 5.0e-06 | 2.9e-06 | 7.6e-06 | n/a, below floor | 0.000 | [0.00, 0.00] | 0.04 | 0.10 | n/a, below floor |
| `selftest_identity` | identity | uncoded | 452.9Hz_+50c | 98 | 4.3e-06 | 8.8e-07 | 5.2e-06 | n/a, below floor | 0.000 | [0.00, 0.00] | 0.02 | 0.03 | n/a, below floor |

**Reading this table.** `floor` is the estimator's own error on uncoded stimuli in the same run: no effect below it means anything. `grid bias` is positive when the codec moved an interval *toward* the Western semitone grid, which is the directional claim; a symmetric residual of the same magnitude is ordinary degradation. `sine R2` against `saw R2` discriminates the two candidate mechanisms: a density correction predicts a sinusoid, coarse cell assignment predicts a sawtooth, and they scale differently with rate.

## Figures

### `selftest.png`

![selftest](figures/selftest.png)

## Programme status

| id | experiment | status |
|---|---|---|
| E0.1 | Estimator noise floor | not yet measured |
| E0.2 | Identity control (no codec) | measured |
| E0.3 | Resample-only control | not yet measured |
| E0.4 | Pilot gate | not yet measured |
| E1.1 | Detuning sweep, phase vs reference offset | not yet measured |
| E1.2 | Quantiser bypass | not yet measured |
| E1.3 | Direct codebook probing | not yet measured |
| E1.4 | Per-RVQ-level decomposition | not yet measured |
| E1.5 | Random-codebook control | not yet measured |
| E1.6 | Causal: RVQ trained on controlled pitch distributions | not yet measured |
| E2.1 | Codec breadth | not yet measured |
| E2.2 | Training-distribution contrast | not yet measured |
| E2.3 | Rate sweep in bits per latent dimension | not yet measured |
| E2.4 | Stimulus ablations | not yet measured |
| E3.1 | Speech-shaped pitch stimuli | not yet measured |
| E3.2 | Retuned instrument samples | not yet measured |
| E3.3 | Makam validation | not yet measured |
| E3.4 | Token-level probe | not yet measured |
| E3.5 | Phonological survival (FLEURS) | not yet measured |
| E3.6 | Downstream ASR | not yet measured |

See [EXPERIMENTS.md](EXPERIMENTS.md) for what each of these tests and why it is in the programme.

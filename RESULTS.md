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
| `codec_dac16` | dac | Q6 | 440Hz_ongrid | 518 | 1.6e-05 | 0.916 | 0.813 | 0.89 | 0.000 | [-0.04, 0.00] | 0.12 | 0.08 | n/a, below floor |
| `codec_dac16` | dac | Q6 | 452.9Hz_+50c | 197 | 3.0e-05 | 0.908 | 1.356 | 1.49 | 0.000 | [-0.31, 0.12] | 0.11 | 0.13 | n/a, below floor |
| `codec_dac24` | dac | Q8 | 440Hz_ongrid | 1195 | 4.9e-06 | 0.425 | 0.857 | 2.02 | 0.029 | [0.00, 0.09] | 0.10 | 0.10 | sinusoid |
| `codec_dac24` | dac | Q8 | 452.9Hz_+50c | 1191 | 5.2e-06 | 1.079 | 1.598 | 1.48 | -0.124 | [-0.31, 0.00] | 0.10 | 0.10 | n/a, below floor |
| `codec_dac44` | dac | Q4 | 440Hz_ongrid | 1098 | 2.9e-06 | 0.224 | 0.383 | 1.71 | 0.000 | [0.00, 0.02] | 2.3e-03 | 0.01 | n/a, below floor |
| `codec_dac44` | dac | Q4 | 452.9Hz_+50c | 1108 | 5.0e-06 | 0.588 | 0.351 | 0.60 | 0.000 | [-0.03, 0.00] | 3.4e-03 | 0.01 | n/a, below floor |
| `codec_encodec48` | encodec | 6.0kbps | 440Hz_ongrid | 1070 | 4.9e-06 | 1.209 | 7.373 | 6.10 | 3.809 | [3.40, 4.18] | 0.55 | 0.60 | sawtooth |
| `codec_encodec48` | encodec | 6.0kbps | 452.9Hz_+50c | 195 | 5.2e-06 | 6.556 | 2.218 | 0.34 | -3.723 | [-4.63, -3.06] | 0.49 | 0.55 | n/a, below floor |
| `codec_mimi` | mimi | Q8 | 440Hz_ongrid | 695 | 4.9e-06 | 5.907 | 9.478 | 1.60 | 3.594 | [2.43, 4.56] | 0.20 | 0.11 | sinusoid |
| `codec_mimi` | mimi | Q8 | 452.9Hz_+50c | 561 | 5.2e-06 | 10.500 | 7.719 | 0.74 | -4.194 | [-5.12, -2.92] | 0.17 | 0.11 | n/a, below floor |
| `codec_speechtok` | speechtokenizer | Q8 | 440Hz_ongrid | 28 | 1.6e-05 | 19.634 | 59.166 | 3.01 | 6.516 | [-38.01, 26.17] | 0.29 | 0.36 | sawtooth |
| `codec_speechtok` | speechtokenizer | Q8 | 452.9Hz_+50c | 156 | 3.0e-05 | 23.174 | 42.240 | 1.82 | 9.900 | [2.25, 15.74] | 0.11 | 0.10 | sinusoid |
| `ctrl_identity` | identity | uncoded | 440Hz_ongrid | 1205 | 4.9e-06 | 6.5e-06 | 6.0e-06 | n/a, below floor | 7.5e-08 | [0.00, 4.9e-07] | 8.6e-03 | 0.02 | n/a, below floor |
| `ctrl_identity` | identity | uncoded | 452.9Hz_+50c | 1205 | 5.2e-06 | 5.1e-06 | 5.4e-06 | n/a, below floor | 0.000 | [-2.4e-07, 0.00] | 4.9e-03 | 0.02 | n/a, below floor |
| `ctrl_sinusoid` | encodec | 3.0kbps | 440Hz_ongrid | 1205 | 2.9e-05 | 0.094 | 0.105 | 1.11 | 2.6e-04 | [0.00, 0.01] | 4.6e-03 | 6.7e-03 | sawtooth |
| `ctrl_sinusoid` | encodec | 3.0kbps | 452.9Hz_+50c | 1205 | 4.9e-05 | 0.200 | 0.195 | 0.98 | 0.000 | [-0.02, 0.00] | 2.6e-03 | 5.3e-03 | n/a, below floor |
| `detune_encodec3` | encodec | 3.0kbps | 440Hz_ongrid | 1119 | 4.9e-06 | 4.199 | 14.626 | 3.48 | 9.257 | [8.40, 9.84] | 0.68 | 0.67 | sinusoid |
| `detune_encodec3` | encodec | 3.0kbps | 442.5Hz_+10c | 1110 | 8.2e-06 | 3.811 | 16.736 | 4.39 | 9.506 | [8.96, 10.28] | 0.67 | 0.67 | sinusoid |
| `detune_encodec3` | encodec | 3.0kbps | 445.1Hz_+20c | 1127 | 8.3e-06 | 3.899 | 19.724 | 5.06 | 7.462 | [6.83, 8.57] | 0.68 | 0.69 | sawtooth |
| `detune_encodec3` | encodec | 3.0kbps | 447.7Hz_+30c | 1121 | 4.5e-06 | 4.224 | 24.401 | 5.78 | 5.762 | [4.90, 6.74] | 0.68 | 0.69 | sawtooth |
| `detune_encodec3` | encodec | 3.0kbps | 450.3Hz_+40c | 1055 | 8.9e-06 | 5.440 | 23.945 | 4.40 | 0.181 | [0.00, 1.87] | 0.57 | 0.58 | sawtooth |
| `detune_encodec3` | encodec | 3.0kbps | 452.9Hz_+50c | 1117 | 5.1e-06 | 7.649 | 16.051 | 2.10 | -4.541 | [-6.50, -2.45] | 0.62 | 0.63 | n/a, below floor |
| `detune_encodec3` | encodec | 3.0kbps | 455.5Hz_+40c | 980 | 4.7e-06 | 14.614 | 6.759 | 0.46 | -8.819 | [-9.64, -8.20] | 0.58 | 0.58 | n/a, below floor |
| `detune_encodec3` | encodec | 3.0kbps | 458.2Hz_+30c | 1095 | 8.2e-06 | 3.592 | 19.583 | 5.45 | 0.000 | [0.00, 0.44] | 0.65 | 0.68 | n/a, below floor |
| `detune_encodec3` | encodec | 3.0kbps | 460.8Hz_+20c | 1118 | 4.5e-06 | 3.466 | 22.337 | 6.44 | 4.010 | [3.05, 4.88] | 0.67 | 0.70 | sawtooth |
| `detune_encodec3` | encodec | 3.0kbps | 463.5Hz_+10c | 1123 | 7.2e-06 | 3.862 | 21.669 | 5.61 | 6.941 | [5.89, 7.81] | 0.67 | 0.68 | sawtooth |
| `detune_encodec3` | encodec | 3.0kbps | 466.2Hz_ongrid | 1115 | 6.4e-06 | 4.607 | 17.593 | 3.82 | 8.992 | [8.31, 9.63] | 0.67 | 0.71 | sawtooth |
| `mech_bypass` | encodec_bypass | no-quantiser | 440Hz_ongrid | 1159 | 4.9e-06 | 2.574 | 8.723 | 3.39 | 5.744 | [5.38, 6.14] | 0.70 | 0.65 | sinusoid |
| `mech_bypass` | encodec_bypass | no-quantiser | 452.9Hz_+50c | 1151 | 5.2e-06 | 5.241 | 7.416 | 1.42 | -4.681 | [-5.87, -3.67] | 0.70 | 0.64 | n/a, below floor |
| `pilot_encodec3` | encodec | 3.0kbps | 440Hz_ongrid | 672 | 4.9e-06 | 4.196 | 14.649 | 3.49 | 9.433 | [8.61, 10.17] | 0.67 | 0.68 | sawtooth |
| `pilot_encodec3` | encodec | 3.0kbps | 452.9Hz_+50c | 664 | 5.2e-06 | 8.692 | 15.572 | 1.79 | -5.971 | [-8.50, -3.29] | 0.63 | 0.64 | n/a, below floor |
| `pod_identity` | identity | uncoded | 440Hz_ongrid | 50 | 6.2e-06 | 2.9e-06 | 7.5e-06 | n/a, below floor | 0.000 | [0.00, 0.00] | 0.05 | 0.06 | n/a, below floor |
| `pod_identity` | identity | uncoded | 452.9Hz_+50c | 50 | 2.0e-06 | 8.9e-07 | 5.2e-06 | n/a, below floor | 0.000 | [0.00, 0.00] | 0.02 | 0.04 | n/a, below floor |
| `rate_encodec_1.5` | encodec | 1.5kbps | 440Hz_ongrid | 1060 | 4.9e-06 | 4.051 | 18.227 | 4.50 | 10.591 | [9.94, 11.25] | 0.62 | 0.59 | sinusoid |
| `rate_encodec_1.5` | encodec | 1.5kbps | 452.9Hz_+50c | 752 | 5.2e-06 | 11.674 | 15.161 | 1.30 | -9.000 | [-12.02, -6.47] | 0.41 | 0.38 | n/a, below floor |
| `rate_encodec_12` | encodec | 12.0kbps | 440Hz_ongrid | 1159 | 4.9e-06 | 2.584 | 9.199 | 3.56 | 6.001 | [5.50, 6.40] | 0.70 | 0.67 | sinusoid |
| `rate_encodec_12` | encodec | 12.0kbps | 452.9Hz_+50c | 1148 | 5.2e-06 | 5.066 | 9.171 | 1.81 | -4.080 | [-5.31, -3.14] | 0.70 | 0.66 | n/a, below floor |
| `rate_encodec_24` | encodec | 24.0kbps | 440Hz_ongrid | 1158 | 4.9e-06 | 2.567 | 8.860 | 3.45 | 5.836 | [5.39, 6.24] | 0.71 | 0.65 | sinusoid |
| `rate_encodec_24` | encodec | 24.0kbps | 452.9Hz_+50c | 1150 | 5.2e-06 | 5.399 | 7.831 | 1.45 | -4.618 | [-5.69, -3.56] | 0.70 | 0.67 | n/a, below floor |
| `rate_encodec_3` | encodec | 3.0kbps | 440Hz_ongrid | 1119 | 4.9e-06 | 4.199 | 14.626 | 3.48 | 9.257 | [8.40, 9.84] | 0.68 | 0.67 | sinusoid |
| `rate_encodec_3` | encodec | 3.0kbps | 452.9Hz_+50c | 1106 | 5.2e-06 | 8.368 | 15.386 | 1.84 | -5.488 | [-7.76, -3.31] | 0.62 | 0.62 | n/a, below floor |
| `rate_encodec_6` | encodec | 6.0kbps | 440Hz_ongrid | 1149 | 4.9e-06 | 2.990 | 10.529 | 3.52 | 6.682 | [6.26, 7.30] | 0.70 | 0.68 | sinusoid |
| `rate_encodec_6` | encodec | 6.0kbps | 452.9Hz_+50c | 1135 | 5.2e-06 | 5.430 | 11.004 | 2.03 | -3.855 | [-5.81, -2.90] | 0.69 | 0.66 | n/a, below floor |
| `selftest_identity` | identity | uncoded | 440Hz_ongrid | 98 | 5.0e-06 | 2.9e-06 | 7.6e-06 | n/a, below floor | 0.000 | [0.00, 0.00] | 0.04 | 0.10 | n/a, below floor |
| `selftest_identity` | identity | uncoded | 452.9Hz_+50c | 98 | 4.3e-06 | 8.8e-07 | 5.2e-06 | n/a, below floor | 0.000 | [0.00, 0.00] | 0.02 | 0.03 | n/a, below floor |

**Skipped:** `causal_12tet` (no usable rows), `causal_53tet` (no usable rows), `causal_uniform` (no usable rows), `mech_shuffled` (no usable rows)

**Reading this table.** `floor` is the estimator's own error on uncoded stimuli in the same run: no effect below it means anything. `grid bias` is positive when the codec moved an interval *toward* the Western semitone grid, which is the directional claim; a symmetric residual of the same magnitude is ordinary degradation. `sine R2` against `saw R2` discriminates the two candidate mechanisms: a density correction predicts a sinusoid, coarse cell assignment predicts a sawtooth, and they scale differently with rate.

## Figures

### `detuning_regression.png`

![detuning_regression](figures/detuning_regression.png)

### `pilot_encodec3.png`

![pilot_encodec3](figures/pilot_encodec3.png)

### `selftest.png`

![selftest](figures/selftest.png)

## Programme status

| id | experiment | status |
|---|---|---|
| E0.1 | Estimator noise floor | not yet measured |
| E0.2 | Identity control (no codec) | measured |
| E0.3 | Resample-only control | not yet measured |
| E0.4 | Pilot gate | measured |
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

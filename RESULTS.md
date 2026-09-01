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
| `detune_dac16` | dac | Q6 | 440Hz_ongrid | 408 | 1.6e-05 | 0.927 | 0.855 | 0.92 | 0.000 | [-0.04, 0.00] | 0.11 | 0.09 | n/a, below floor |
| `detune_dac16` | dac | Q6 | 442.5Hz_+09.8c | 497 | 8.6e-06 | 1.165 | 1.659 | 1.42 | 0.099 | [0.00, 0.35] | 0.16 | 0.13 | sinusoid |
| `detune_dac16` | dac | Q6 | 445.1Hz_+20.0c | 195 | 2.1e-05 | 0.849 | 0.473 | 0.56 | 0.325 | [0.21, 0.44] | 0.17 | 0.17 | sinusoid |
| `detune_dac16` | dac | Q6 | 447.7Hz_+30.0c | 69 | 1.2e-05 | 0.551 | 1.136 | 2.06 | 0.471 | [0.10, 0.85] | 0.17 | 0.18 | sawtooth |
| `detune_dac16` | dac | Q6 | 450.3Hz_+40.1c | 75 | 1.2e-05 | 1.798 | 1.419 | 0.79 | 0.252 | [-0.24, 0.86] | 0.21 | 0.24 | sawtooth |
| `detune_dac16` | dac | Q6 | 452.9Hz_+50.0c | 138 | 2.7e-05 | 0.953 | 1.132 | 1.19 | -0.070 | [-0.35, 0.04] | 0.19 | 0.16 | n/a, below floor |
| `detune_dac16` | dac | Q6 | 455.5Hz_+59.9c | 445 | 9.2e-06 | 0.939 | 1.319 | 1.40 | -0.278 | [-0.51, -0.19] | 0.19 | 0.14 | n/a, below floor |
| `detune_dac16` | dac | Q6 | 458.2Hz_+70.2c | 463 | 1.6e-05 | 1.386 | 1.496 | 1.08 | -0.367 | [-0.68, -0.11] | 0.12 | 0.11 | n/a, below floor |
| `detune_dac16` | dac | Q6 | 460.8Hz_+80.0c | 385 | 1.1e-05 | 1.765 | 2.010 | 1.14 | -0.672 | [-1.14, -0.26] | 0.20 | 0.17 | n/a, below floor |
| `detune_dac16` | dac | Q6 | 463.5Hz_+90.1c | 542 | 9.1e-06 | 1.954 | 2.777 | 1.42 | -1.251 | [-1.78, -0.02] | 0.19 | 0.14 | n/a, below floor |
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
| `detune_mimi` | mimi | Q8 | 440Hz_ongrid | 556 | 4.9e-06 | 6.067 | 8.954 | 1.48 | 3.423 | [2.30, 4.42] | 0.20 | 0.14 | sinusoid |
| `detune_mimi` | mimi | Q8 | 442.5Hz_+09.8c | 567 | 4.5e-06 | 7.324 | 13.613 | 1.86 | 4.137 | [2.95, 5.35] | 0.17 | 0.12 | sinusoid |
| `detune_mimi` | mimi | Q8 | 445.1Hz_+20.0c | 563 | 7.0e-06 | 8.847 | 19.863 | 2.25 | 7.302 | [4.31, 8.76] | 0.13 | 0.09 | sinusoid |
| `detune_mimi` | mimi | Q8 | 447.7Hz_+30.0c | 548 | 1.2e-05 | 7.969 | 15.879 | 1.99 | 3.379 | [1.06, 4.60] | 0.10 | 0.07 | sinusoid |
| `detune_mimi` | mimi | Q8 | 450.3Hz_+40.1c | 563 | 5.4e-06 | 10.142 | 13.479 | 1.33 | 0.000 | [-1.78, 0.00] | 0.13 | 0.09 | n/a, below floor |
| `detune_mimi` | mimi | Q8 | 452.9Hz_+50.0c | 448 | 4.8e-06 | 11.426 | 7.221 | 0.63 | -3.666 | [-5.27, -2.80] | 0.21 | 0.13 | n/a, below floor |
| `detune_mimi` | mimi | Q8 | 455.5Hz_+59.9c | 177 | 4.5e-06 | 15.124 | 7.989 | 0.53 | -7.150 | [-8.19, -5.82] | 0.23 | 0.19 | n/a, below floor |
| `detune_mimi` | mimi | Q8 | 458.2Hz_+70.2c | 33 | 5.0e-06 | 26.834 | 15.466 | 0.58 | 0.518 | [-2.97, 11.04] | 0.17 | 0.33 | sawtooth |
| `detune_mimi` | mimi | Q8 | 460.8Hz_+80.0c | 200 | 4.5e-06 | 6.411 | 15.410 | 2.40 | 2.537 | [0.00, 4.88] | 0.23 | 0.23 | sinusoid |
| `detune_mimi` | mimi | Q8 | 463.5Hz_+90.1c | 548 | 4.7e-06 | 4.958 | 13.434 | 2.71 | 3.581 | [2.19, 4.95] | 0.21 | 0.17 | sinusoid |
| `detune_vowel_encodec` | encodec | 3.0kbps | 221.3Hz_+10.0c | 35 | 1.8e-05 | 0.364 | 3.647 | 10.01 | 0.295 | [0.01, 0.50] | 0.62 | 0.62 | sinusoid |
| `detune_vowel_encodec` | encodec | 3.0kbps | 222.6Hz_+20.0c | 26 | 1.8e-05 | 0.410 | -- | -- | 0.515 | [0.36, 0.68] | 0.57 | 0.60 | sawtooth |
| `detune_vowel_speechtok` | speechtokenizer | Q8 | 220Hz_ongrid | 643 | 3.6e-05 | 0.654 | 0.729 | 1.12 | 0.000 | [-0.04, 9.7e-04] | 0.02 | 0.01 | n/a, below floor |
| `detune_vowel_speechtok` | speechtokenizer | Q8 | 221.3Hz_+10.0c | 698 | 3.7e-05 | 0.822 | 0.866 | 1.05 | 0.000 | [-1.7e-04, 0.06] | 0.05 | 0.05 | n/a, below floor |
| `detune_vowel_speechtok` | speechtokenizer | Q8 | 222.6Hz_+20.0c | 673 | 4.5e-05 | 0.957 | 1.004 | 1.05 | 0.000 | [-0.02, 0.08] | 0.03 | 0.06 | n/a, below floor |
| `detune_vowel_speechtok` | speechtokenizer | Q8 | 223.8Hz_+29.9c | 672 | 3.6e-05 | 1.115 | 0.931 | 0.83 | 0.047 | [0.00, 0.20] | 0.05 | 0.04 | sinusoid |
| `detune_vowel_speechtok` | speechtokenizer | Q8 | 225.1Hz_+39.9c | 664 | 3.6e-05 | 0.929 | 0.865 | 0.93 | 0.047 | [0.00, 0.15] | 0.06 | 0.06 | sinusoid |
| `detune_vowel_speechtok` | speechtokenizer | Q8 | 226.4Hz_+49.9c | 652 | 6.0e-05 | 0.897 | 0.954 | 1.06 | 0.036 | [0.00, 0.14] | 0.04 | 0.03 | sinusoid |
| `detune_vowel_speechtok` | speechtokenizer | Q8 | 227.8Hz_+59.9c | 641 | 3.7e-05 | 0.640 | 0.584 | 0.91 | 0.000 | [0.00, 0.09] | 0.04 | 0.05 | n/a, below floor |
| `detune_vowel_speechtok` | speechtokenizer | Q8 | 229.1Hz_+69.9c | 634 | 3.9e-05 | 0.746 | 0.740 | 0.99 | 0.000 | [-6.0e-03, 0.07] | 0.06 | 0.05 | n/a, below floor |
| `detune_vowel_speechtok` | speechtokenizer | Q8 | 230.4Hz_+80.0c | 627 | 4.3e-05 | 0.737 | 0.883 | 1.20 | 0.000 | [-1.8e-03, 0.05] | 0.04 | 0.04 | n/a, below floor |
| `detune_vowel_speechtok` | speechtokenizer | Q8 | 231.7Hz_+90.0c | 610 | 5.8e-05 | 0.625 | 0.770 | 1.23 | 0.000 | [-0.06, 0.02] | 0.04 | 0.04 | n/a, below floor |
| `ft_12tet` | encodec_ft_encodec_ft_12tet | 3.0kbps | 440Hz_ongrid | 348 | 4.9e-06 | 0.244 | 0.904 | 3.71 | 0.267 | [0.20, 0.36] | 0.44 | 0.39 | sinusoid |
| `ft_53tet` | encodec_ft_encodec_ft_53tet | 3.0kbps | 440Hz_ongrid | 233 | 4.9e-06 | 0.245 | 0.821 | 3.35 | 0.310 | [0.23, 0.39] | 0.52 | 0.49 | sinusoid |
| `ft_uniform` | encodec_ft_encodec_ft_uniform | 3.0kbps | 440Hz_ongrid | 252 | 4.9e-06 | 0.269 | 0.908 | 3.38 | 0.299 | [0.22, 0.37] | 0.54 | 0.49 | sinusoid |
| `mech_bypass` | encodec_bypass | no-quantiser | 440Hz_ongrid | 1159 | 4.9e-06 | 2.574 | 8.723 | 3.39 | 5.744 | [5.38, 6.14] | 0.70 | 0.65 | sinusoid |
| `mech_bypass` | encodec_bypass | no-quantiser | 452.9Hz_+50c | 1151 | 5.2e-06 | 5.241 | 7.416 | 1.42 | -4.681 | [-5.87, -3.67] | 0.70 | 0.64 | n/a, below floor |
| `octaves_encodec3` | encodec | 3.0kbps | 110Hz_ongrid | 1436 | 2.6e-05 | 0.725 | 1.480 | 2.04 | 0.720 | [0.57, 0.84] | 0.33 | 0.24 | sinusoid |
| `octaves_encodec3` | encodec | 3.0kbps | 220Hz_ongrid | 1411 | 8.4e-06 | 2.281 | 10.653 | 4.67 | 6.010 | [5.52, 6.53] | 0.51 | 0.42 | sinusoid |
| `octaves_encodec3` | encodec | 3.0kbps | 440Hz_ongrid | 1331 | 4.9e-06 | 4.440 | 14.266 | 3.21 | 9.107 | [8.55, 9.80] | 0.68 | 0.65 | sinusoid |
| `octaves_encodec3` | encodec | 3.0kbps | 880Hz_ongrid | 936 | 3.4e-06 | 4.443 | 21.129 | 4.76 | 8.673 | [7.74, 9.48] | 0.27 | 0.25 | sinusoid |
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
| `vowel_mimi` | mimi | Q8 | 220Hz_ongrid | 480 | 1.6e-05 | 0.708 | 0.879 | 1.24 | 0.000 | [-0.07, 1.9e-04] | 1.5e-03 | 5.4e-03 | n/a, below floor |
| `vowel_mimi` | mimi | Q8 | 226.4Hz_+49.6c | 486 | 2.7e-05 | 0.515 | 0.604 | 1.17 | 0.000 | [-0.05, 9.9e-03] | 1.0e-03 | 3.9e-03 | n/a, below floor |
| `vowel_speechtok` | speechtokenizer | Q8 | 220Hz_ongrid | 643 | 3.6e-05 | 0.654 | 0.729 | 1.12 | 0.000 | [-0.04, 9.7e-04] | 0.02 | 0.01 | n/a, below floor |
| `vowel_speechtok` | speechtokenizer | Q8 | 226.4Hz_+49.6c | 661 | 3.4e-05 | 0.952 | 0.836 | 0.88 | 0.033 | [0.00, 0.15] | 0.06 | 0.07 | sawtooth |

**Skipped:** `causal_12tet` (no usable rows), `causal_53tet` (no usable rows), `causal_uniform` (no usable rows), `ftvowel_12tet` (no usable rows), `ftvowel_53tet` (no usable rows), `ftvowel_uniform` (no usable rows), `hist_gtzan` (no usable rows), `hist_librispeech` (no usable rows), `mech_shuffled` (no usable rows), `mech_untrained` (no usable rows), `probe_encodec3` (no usable rows), `vowel_encodec3` (no usable rows)

**Reading this table.** `floor` is the estimator's own error on uncoded stimuli in the same run: no effect below it means anything. `grid bias` is positive when the codec moved an interval *toward* the Western semitone grid, which is the directional claim; a symmetric residual of the same magnitude is ordinary degradation. `sine R2` against `saw R2` discriminates the two candidate mechanisms: a density correction predicts a sinusoid, coarse cell assignment predicts a sawtooth, and they scale differently with rate.

## Figures

### `detuning_regression.png`

![detuning_regression](figures/detuning_regression.png)

### `pilot_encodec3.png`

![pilot_encodec3](figures/pilot_encodec3.png)

### `pitch_histograms.png`

![pitch_histograms](figures/pitch_histograms.png)

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

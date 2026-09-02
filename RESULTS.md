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
| `detune_dac24` | dac | Q8 | 440Hz_ongrid | 956 | 4.9e-06 | 0.434 | 0.853 | 1.97 | 0.033 | [0.00, 0.11] | 0.09 | 0.09 | sinusoid |
| `detune_dac24` | dac | Q8 | 442.5Hz_+09.8c | 960 | 4.5e-06 | 0.439 | 0.902 | 2.06 | 0.131 | [0.05, 0.19] | 0.09 | 0.08 | sinusoid |
| `detune_dac24` | dac | Q8 | 445.1Hz_+20.0c | 959 | 7.0e-06 | 0.935 | 1.077 | 1.15 | 0.248 | [0.06, 0.37] | 0.10 | 0.10 | sawtooth |
| `detune_dac24` | dac | Q8 | 447.7Hz_+30.0c | 959 | 1.2e-05 | 1.126 | 0.871 | 0.77 | 0.165 | [0.03, 0.33] | 0.09 | 0.09 | sawtooth |
| `detune_dac24` | dac | Q8 | 450.3Hz_+40.1c | 949 | 5.4e-06 | 0.846 | 0.742 | 0.88 | 0.119 | [0.04, 0.20] | 0.09 | 0.08 | sinusoid |
| `detune_dac24` | dac | Q8 | 452.9Hz_+50.0c | 953 | 4.8e-06 | 1.015 | 1.601 | 1.58 | -0.057 | [-0.43, 0.00] | 0.10 | 0.10 | n/a, below floor |
| `detune_dac24` | dac | Q8 | 455.5Hz_+59.9c | 954 | 4.5e-06 | 1.344 | 1.558 | 1.16 | -0.652 | [-0.85, -0.46] | 0.09 | 0.11 | n/a, below floor |
| `detune_dac24` | dac | Q8 | 458.2Hz_+70.2c | 952 | 5.0e-06 | 0.890 | 0.611 | 0.69 | -0.241 | [-0.33, -0.17] | 0.10 | 0.10 | n/a, below floor |
| `detune_dac24` | dac | Q8 | 460.8Hz_+80.0c | 955 | 4.5e-06 | 0.881 | 0.864 | 0.98 | -0.204 | [-0.29, -0.09] | 0.09 | 0.11 | n/a, below floor |
| `detune_dac24` | dac | Q8 | 463.5Hz_+90.1c | 949 | 4.7e-06 | 0.617 | 1.014 | 1.64 | 0.000 | [-0.01, 0.01] | 0.10 | 0.11 | n/a, below floor |
| `detune_dac44` | dac | Q4 | 440Hz_ongrid | 879 | 2.9e-06 | 0.211 | 0.378 | 1.79 | 0.000 | [0.00, 0.02] | 3.6e-03 | 0.02 | n/a, below floor |
| `detune_dac44` | dac | Q4 | 442.5Hz_+09.8c | 883 | 3.6e-06 | 0.281 | 0.341 | 1.21 | 0.000 | [-3.8e-04, 9.0e-03] | 4.6e-03 | 0.02 | n/a, below floor |
| `detune_dac44` | dac | Q4 | 445.1Hz_+20.0c | 883 | 6.9e-06 | 0.361 | 0.376 | 1.04 | 0.000 | [0.00, 0.02] | 6.5e-03 | 0.02 | n/a, below floor |
| `detune_dac44` | dac | Q4 | 447.7Hz_+30.0c | 888 | 4.0e-06 | 0.508 | 0.364 | 0.72 | 0.004 | [0.00, 0.05] | 3.3e-04 | 7.5e-03 | sawtooth |
| `detune_dac44` | dac | Q4 | 450.3Hz_+40.1c | 888 | 4.7e-06 | 0.534 | 0.320 | 0.60 | 0.000 | [0.00, 0.01] | 1.3e-03 | 8.5e-03 | n/a, below floor |
| `detune_dac44` | dac | Q4 | 452.9Hz_+50.0c | 886 | 6.3e-06 | 0.511 | 0.358 | 0.70 | -0.005 | [-0.05, 0.00] | 1.1e-03 | 7.6e-03 | n/a, below floor |
| `detune_dac44` | dac | Q4 | 455.5Hz_+59.9c | 888 | 4.2e-06 | 0.562 | 0.422 | 0.75 | 0.000 | [-0.03, 0.00] | 5.4e-03 | 0.01 | n/a, below floor |
| `detune_dac44` | dac | Q4 | 458.2Hz_+70.2c | 877 | 3.9e-06 | 0.447 | 0.431 | 0.96 | 0.000 | [-0.01, 0.02] | 6.6e-03 | 9.1e-03 | n/a, below floor |
| `detune_dac44` | dac | Q4 | 460.8Hz_+80.0c | 888 | 5.0e-06 | 0.442 | 0.536 | 1.21 | -0.034 | [-0.07, 0.00] | 0.01 | 0.01 | n/a, below floor |
| `detune_dac44` | dac | Q4 | 463.5Hz_+90.1c | 881 | 5.1e-06 | 0.316 | 0.596 | 1.89 | 0.011 | [0.00, 0.05] | 0.01 | 0.02 | sawtooth |
| `detune_encodec24kbps` | encodec | 24.0kbps | 440Hz_ongrid | 927 | 4.9e-06 | 2.607 | 8.860 | 3.40 | 5.796 | [5.30, 6.30] | 0.71 | 0.65 | sinusoid |
| `detune_encodec24kbps` | encodec | 24.0kbps | 442.5Hz_+09.8c | 928 | 4.5e-06 | 2.208 | 9.986 | 4.52 | 6.142 | [5.71, 6.64] | 0.70 | 0.66 | sinusoid |
| `detune_encodec24kbps` | encodec | 24.0kbps | 445.1Hz_+20.0c | 927 | 7.0e-06 | 2.457 | 11.558 | 4.70 | 4.813 | [4.29, 5.37] | 0.70 | 0.61 | sinusoid |
| `detune_encodec24kbps` | encodec | 24.0kbps | 447.7Hz_+30.0c | 924 | 1.2e-05 | 2.761 | 13.940 | 5.05 | 2.924 | [2.22, 3.61] | 0.70 | 0.65 | sinusoid |
| `detune_encodec24kbps` | encodec | 24.0kbps | 450.3Hz_+40.1c | 936 | 5.4e-06 | 4.509 | 11.678 | 2.59 | 0.000 | [-0.55, 0.00] | 0.64 | 0.60 | n/a, below floor |
| `detune_encodec24kbps` | encodec | 24.0kbps | 452.9Hz_+50.0c | 929 | 4.8e-06 | 5.021 | 7.943 | 1.58 | -4.238 | [-5.63, -3.17] | 0.68 | 0.61 | n/a, below floor |
| `detune_encodec24kbps` | encodec | 24.0kbps | 455.5Hz_+59.9c | 929 | 4.5e-06 | 8.369 | 4.555 | 0.54 | -5.901 | [-6.48, -5.45] | 0.69 | 0.62 | n/a, below floor |
| `detune_encodec24kbps` | encodec | 24.0kbps | 458.2Hz_+70.2c | 928 | 5.0e-06 | 6.516 | 7.754 | 1.19 | -3.709 | [-4.65, -2.96] | 0.68 | 0.63 | n/a, below floor |
| `detune_encodec24kbps` | encodec | 24.0kbps | 460.8Hz_+80.0c | 920 | 4.5e-06 | 2.631 | 13.102 | 4.98 | 1.506 | [0.37, 2.47] | 0.68 | 0.64 | sinusoid |
| `detune_encodec24kbps` | encodec | 24.0kbps | 463.5Hz_+90.1c | 926 | 4.7e-06 | 2.571 | 13.241 | 5.15 | 4.727 | [4.14, 5.18] | 0.71 | 0.67 | sinusoid |
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
| `detune_encodec48` | encodec | 6.0kbps | 440Hz_ongrid | 853 | 4.9e-06 | 1.221 | 7.168 | 5.87 | 3.841 | [3.38, 4.21] | 0.55 | 0.59 | sawtooth |
| `detune_encodec48` | encodec | 6.0kbps | 442.5Hz_+09.8c | 854 | 4.5e-06 | 1.085 | 7.203 | 6.64 | 3.482 | [3.11, 3.89] | 0.54 | 0.60 | sawtooth |
| `detune_encodec48` | encodec | 6.0kbps | 445.1Hz_+20.0c | 849 | 7.0e-06 | 1.630 | 6.918 | 4.24 | 2.299 | [1.99, 2.62] | 0.54 | 0.60 | sawtooth |
| `detune_encodec48` | encodec | 6.0kbps | 447.7Hz_+30.0c | 856 | 1.2e-05 | 2.531 | 9.084 | 3.59 | 2.157 | [1.50, 2.76] | 0.54 | 0.59 | sawtooth |
| `detune_encodec48` | encodec | 6.0kbps | 450.3Hz_+40.1c | 593 | 5.4e-06 | 4.042 | 7.370 | 1.82 | -1.230 | [-2.80, -0.23] | 0.46 | 0.51 | n/a, below floor |
| `detune_encodec48` | encodec | 6.0kbps | 452.9Hz_+50.0c | 148 | 4.8e-06 | 7.344 | 3.080 | 0.42 | -4.334 | [-5.45, -2.77] | 0.47 | 0.50 | n/a, below floor |
| `detune_encodec48` | encodec | 6.0kbps | 455.5Hz_+59.9c | 170 | 4.5e-06 | 8.104 | 17.667 | 2.18 | -0.542 | [-12.20, 1.97] | 0.51 | 0.46 | n/a, below floor |
| `detune_encodec48` | encodec | 6.0kbps | 458.2Hz_+70.2c | 859 | 5.0e-06 | 6.452 | 17.466 | 2.71 | 4.981 | [1.32, 6.88] | 0.44 | 0.50 | sawtooth |
| `detune_encodec48` | encodec | 6.0kbps | 460.8Hz_+80.0c | 854 | 4.5e-06 | 4.496 | 13.529 | 3.01 | 5.169 | [4.12, 5.96] | 0.46 | 0.47 | sawtooth |
| `detune_encodec48` | encodec | 6.0kbps | 463.5Hz_+90.1c | 845 | 4.7e-06 | 3.429 | 11.181 | 3.26 | 5.215 | [4.75, 5.69] | 0.49 | 0.58 | sawtooth |
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
| `detune_snac32` | snac | 32khz | 440Hz_ongrid | 961 | 1.6e-05 | 0.536 | 1.516 | 2.83 | 0.441 | [0.35, 0.60] | 0.21 | 0.18 | sinusoid |
| `detune_snac32` | snac | 32khz | 442.5Hz_+09.8c | 962 | 8.6e-06 | 0.460 | 1.421 | 3.09 | 0.454 | [0.34, 0.57] | 0.20 | 0.16 | sinusoid |
| `detune_snac32` | snac | 32khz | 445.1Hz_+20.0c | 963 | 2.1e-05 | 1.188 | 1.641 | 1.38 | 0.669 | [0.54, 0.83] | 0.18 | 0.13 | sinusoid |
| `detune_snac32` | snac | 32khz | 447.7Hz_+30.0c | 963 | 1.2e-05 | 1.453 | 1.229 | 0.85 | 0.087 | [0.00, 0.22] | 0.17 | 0.14 | sinusoid |
| `detune_snac32` | snac | 32khz | 450.3Hz_+40.1c | 963 | 1.2e-05 | 2.412 | 0.987 | 0.41 | -0.314 | [-0.44, -0.15] | 0.23 | 0.18 | n/a, below floor |
| `detune_snac32` | snac | 32khz | 452.9Hz_+50.0c | 961 | 2.7e-05 | 1.689 | 0.819 | 0.49 | -0.541 | [-0.72, -0.42] | 0.22 | 0.17 | n/a, below floor |
| `detune_snac32` | snac | 32khz | 455.5Hz_+59.9c | 961 | 9.2e-06 | 1.036 | 0.874 | 0.84 | -0.525 | [-0.64, -0.37] | 0.25 | 0.22 | n/a, below floor |
| `detune_snac32` | snac | 32khz | 458.2Hz_+70.2c | 960 | 1.6e-05 | 1.774 | 2.099 | 1.18 | -0.423 | [-0.69, -0.22] | 0.10 | 0.09 | n/a, below floor |
| `detune_snac32` | snac | 32khz | 460.8Hz_+80.0c | 963 | 1.1e-05 | 0.972 | 1.398 | 1.44 | -0.023 | [-0.13, 0.00] | 0.17 | 0.14 | n/a, below floor |
| `detune_snac32` | snac | 32khz | 463.5Hz_+90.1c | 962 | 9.1e-06 | 0.624 | 1.630 | 2.61 | 0.334 | [0.21, 0.42] | 0.20 | 0.16 | sinusoid |
| `detune_snac44` | snac | 44khz | 440Hz_ongrid | 960 | 2.9e-06 | 0.430 | 0.787 | 1.83 | 0.037 | [0.00, 0.10] | 0.03 | 0.04 | sawtooth |
| `detune_snac44` | snac | 44khz | 442.5Hz_+09.8c | 959 | 3.6e-06 | 0.345 | 0.880 | 2.55 | 0.000 | [0.00, 0.04] | 0.03 | 0.04 | n/a, below floor |
| `detune_snac44` | snac | 44khz | 445.1Hz_+20.0c | 959 | 6.9e-06 | 0.658 | 0.908 | 1.38 | 0.000 | [-0.07, 0.00] | 0.03 | 0.04 | n/a, below floor |
| `detune_snac44` | snac | 44khz | 447.7Hz_+30.0c | 960 | 4.0e-06 | 0.603 | 0.827 | 1.37 | -0.118 | [-0.17, -0.03] | 0.05 | 0.06 | n/a, below floor |
| `detune_snac44` | snac | 44khz | 450.3Hz_+40.1c | 953 | 4.7e-06 | 0.816 | 0.788 | 0.97 | -0.163 | [-0.26, -0.07] | 0.04 | 0.05 | n/a, below floor |
| `detune_snac44` | snac | 44khz | 452.9Hz_+50.0c | 957 | 6.3e-06 | 1.015 | 0.662 | 0.65 | -0.157 | [-0.25, -0.09] | 0.04 | 0.05 | n/a, below floor |
| `detune_snac44` | snac | 44khz | 455.5Hz_+59.9c | 957 | 4.2e-06 | 1.401 | 1.266 | 0.90 | 0.000 | [-0.06, 0.00] | 0.03 | 0.04 | n/a, below floor |
| `detune_snac44` | snac | 44khz | 458.2Hz_+70.2c | 783 | 3.9e-06 | 2.051 | 2.134 | 1.04 | 0.223 | [0.00, 0.59] | 0.06 | 0.05 | sinusoid |
| `detune_snac44` | snac | 44khz | 460.8Hz_+80.0c | 832 | 5.0e-06 | 1.849 | 1.566 | 0.85 | 0.000 | [0.00, 0.13] | 0.04 | 0.05 | n/a, below floor |
| `detune_snac44` | snac | 44khz | 463.5Hz_+90.1c | 963 | 5.1e-06 | 0.773 | 0.916 | 1.19 | 0.086 | [0.00, 0.16] | 0.06 | 0.05 | sinusoid |
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
| `ftm_flat` | encodec_ft_encodec_ftm_flat | 3.0kbps | 440Hz_ongrid | 1116 | 4.9e-06 | 1.297 | 2.833 | 2.18 | 2.014 | [1.83, 2.21] | 0.59 | 0.49 | sinusoid |
| `ftm_flat` | encodec_ft_encodec_ftm_flat | 3.0kbps | 442.5Hz_+09.8c | 1091 | 4.5e-06 | 1.067 | 3.100 | 2.91 | 2.186 | [1.99, 2.36] | 0.62 | 0.50 | sinusoid |
| `ftm_flat` | encodec_ft_encodec_ftm_flat | 3.0kbps | 445.1Hz_+20.0c | 1123 | 7.0e-06 | 1.248 | 4.301 | 3.45 | 1.845 | [1.58, 2.02] | 0.60 | 0.49 | sinusoid |
| `ftm_flat` | encodec_ft_encodec_ftm_flat | 3.0kbps | 447.7Hz_+30.0c | 976 | 1.2e-05 | 1.542 | 5.901 | 3.83 | 0.994 | [0.66, 1.60] | 0.58 | 0.47 | sinusoid |
| `ftm_flat` | encodec_ft_encodec_ftm_flat | 3.0kbps | 450.3Hz_+40.1c | 910 | 5.4e-06 | 1.993 | 5.534 | 2.78 | -0.009 | [-0.50, 0.00] | 0.44 | 0.37 | n/a, below floor |
| `ftm_flat` | encodec_ft_encodec_ftm_flat | 3.0kbps | 452.9Hz_+50.0c | 1020 | 4.8e-06 | 1.837 | 3.164 | 1.72 | -1.725 | [-1.99, -1.28] | 0.56 | 0.46 | n/a, below floor |
| `ftm_flat` | encodec_ft_encodec_ftm_flat | 3.0kbps | 455.5Hz_+59.9c | 1084 | 4.5e-06 | 2.108 | 1.608 | 0.76 | -2.146 | [-2.28, -1.98] | 0.59 | 0.46 | n/a, below floor |
| `ftm_flat` | encodec_ft_encodec_ftm_flat | 3.0kbps | 458.2Hz_+70.2c | 1100 | 5.0e-06 | 2.339 | 3.013 | 1.29 | -1.523 | [-1.75, -1.19] | 0.55 | 0.45 | n/a, below floor |
| `ftm_flat` | encodec_ft_encodec_ftm_flat | 3.0kbps | 460.8Hz_+80.0c | 1089 | 4.5e-06 | 1.327 | 5.026 | 3.79 | 0.236 | [0.00, 0.80] | 0.57 | 0.47 | sinusoid |
| `ftm_flat` | encodec_ft_encodec_ftm_flat | 3.0kbps | 463.5Hz_+90.1c | 1093 | 4.7e-06 | 1.096 | 4.706 | 4.29 | 1.500 | [1.28, 1.74] | 0.58 | 0.48 | sinusoid |
| `ftm_grid` | encodec_ft_encodec_ftm_grid | 3.0kbps | 440Hz_ongrid | 1108 | 4.9e-06 | 1.355 | 3.488 | 2.57 | 2.348 | [2.12, 2.60] | 0.61 | 0.52 | sinusoid |
| `ftm_grid` | encodec_ft_encodec_ftm_grid | 3.0kbps | 442.5Hz_+09.8c | 1103 | 4.5e-06 | 1.138 | 4.010 | 3.52 | 2.560 | [2.37, 2.80] | 0.62 | 0.52 | sinusoid |
| `ftm_grid` | encodec_ft_encodec_ftm_grid | 3.0kbps | 445.1Hz_+20.0c | 1113 | 7.0e-06 | 1.405 | 5.230 | 3.72 | 2.202 | [1.86, 2.52] | 0.62 | 0.52 | sinusoid |
| `ftm_grid` | encodec_ft_encodec_ftm_grid | 3.0kbps | 447.7Hz_+30.0c | 1010 | 1.2e-05 | 1.765 | 7.267 | 4.12 | 1.554 | [1.14, 2.04] | 0.60 | 0.53 | sinusoid |
| `ftm_grid` | encodec_ft_encodec_ftm_grid | 3.0kbps | 450.3Hz_+40.1c | 779 | 5.4e-06 | 2.583 | 7.386 | 2.86 | 0.000 | [-0.32, 0.10] | 0.43 | 0.37 | n/a, below floor |
| `ftm_grid` | encodec_ft_encodec_ftm_grid | 3.0kbps | 452.9Hz_+50.0c | 997 | 4.8e-06 | 2.638 | 4.492 | 1.70 | -1.865 | [-2.64, -1.15] | 0.57 | 0.48 | n/a, below floor |
| `ftm_grid` | encodec_ft_encodec_ftm_grid | 3.0kbps | 455.5Hz_+59.9c | 1077 | 4.5e-06 | 3.016 | 1.766 | 0.59 | -2.508 | [-2.70, -2.30] | 0.60 | 0.52 | n/a, below floor |
| `ftm_grid` | encodec_ft_encodec_ftm_grid | 3.0kbps | 458.2Hz_+70.2c | 1100 | 5.0e-06 | 2.941 | 3.729 | 1.27 | -1.562 | [-1.87, -1.19] | 0.56 | 0.49 | n/a, below floor |
| `ftm_grid` | encodec_ft_encodec_ftm_grid | 3.0kbps | 460.8Hz_+80.0c | 1087 | 4.5e-06 | 1.504 | 6.006 | 3.99 | 0.859 | [0.30, 1.29] | 0.59 | 0.52 | sinusoid |
| `ftm_grid` | encodec_ft_encodec_ftm_grid | 3.0kbps | 463.5Hz_+90.1c | 1076 | 4.7e-06 | 1.294 | 5.624 | 4.35 | 1.980 | [1.70, 2.31] | 0.61 | 0.53 | sinusoid |
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
| `vib_0` | encodec | 3.0kbps | 440Hz_ongrid | 896 | 4.9e-06 | 4.179 | 14.671 | 3.51 | 9.316 | [8.51, 9.96] | 0.67 | 0.67 | sawtooth |
| `vib_0` | encodec | 3.0kbps | 452.9Hz_+50.0c | 881 | 5.2e-06 | 8.848 | 15.472 | 1.75 | -5.776 | [-8.25, -3.31] | 0.63 | 0.63 | n/a, below floor |
| `vib_10` | encodec | 3.0kbps | 440Hz_ongrid | 889 | 1.036 | 4.767 | 15.936 | 3.34 | 10.228 | [9.56, 10.98] | 0.72 | 0.74 | sawtooth |
| `vib_10` | encodec | 3.0kbps | 452.9Hz_+50.0c | 879 | 0.314 | 9.882 | 16.972 | 1.72 | -6.539 | [-8.98, -3.92] | 0.59 | 0.62 | n/a, below floor |
| `vib_20` | encodec | 3.0kbps | 440Hz_ongrid | 855 | 2.420 | 5.316 | 20.825 | 3.92 | 13.018 | [12.38, 14.04] | 0.73 | 0.75 | sawtooth |
| `vib_20` | encodec | 3.0kbps | 452.9Hz_+50.0c | 715 | 2.258 | 9.624 | 22.873 | 2.38 | -7.860 | [-12.29, -4.25] | 0.66 | 0.75 | n/a, below floor |
| `vib_40` | encodec | 3.0kbps | 440Hz_ongrid | 725 | 3.308 | 7.618 | 29.079 | 3.82 | 17.204 | [16.43, 18.25] | 0.78 | 0.85 | sawtooth |
| `vib_40` | encodec | 3.0kbps | 452.9Hz_+50.0c | 331 | 2.208 | 5.908 | 36.946 | 6.25 | 2.767 | [-24.69, 8.13] | 0.78 | 0.88 | n/a, below floor |
| `vib_5` | encodec | 3.0kbps | 440Hz_ongrid | 900 | 0.422 | 4.715 | 15.030 | 3.19 | 9.641 | [8.78, 10.25] | 0.70 | 0.71 | sawtooth |
| `vib_5` | encodec | 3.0kbps | 452.9Hz_+50.0c | 890 | 0.206 | 7.523 | 15.929 | 2.12 | -4.991 | [-7.25, -2.75] | 0.60 | 0.62 | n/a, below floor |
| `vowel_mimi` | mimi | Q8 | 220Hz_ongrid | 480 | 1.6e-05 | 0.708 | 0.879 | 1.24 | 0.000 | [-0.07, 1.9e-04] | 1.5e-03 | 5.4e-03 | n/a, below floor |
| `vowel_mimi` | mimi | Q8 | 226.4Hz_+49.6c | 486 | 2.7e-05 | 0.515 | 0.604 | 1.17 | 0.000 | [-0.05, 9.9e-03] | 1.0e-03 | 3.9e-03 | n/a, below floor |
| `vowel_speechtok` | speechtokenizer | Q8 | 220Hz_ongrid | 643 | 3.6e-05 | 0.654 | 0.729 | 1.12 | 0.000 | [-0.04, 9.7e-04] | 0.02 | 0.01 | n/a, below floor |
| `vowel_speechtok` | speechtokenizer | Q8 | 226.4Hz_+49.6c | 661 | 3.4e-05 | 0.952 | 0.836 | 0.88 | 0.033 | [0.00, 0.15] | 0.06 | 0.07 | sawtooth |

**Skipped:** `asr_encodec3` (no usable rows), `asr_encodec3_v2` (no usable rows), `asr_mms_encodec3` (no usable rows), `asr_mms_mimi` (no usable rows), `causal_12tet` (no usable rows), `causal_53tet` (no usable rows), `causal_uniform` (no usable rows), `detune_snac` (no usable rows), `ftvowel_12tet` (no usable rows), `ftvowel_53tet` (no usable rows), `ftvowel_uniform` (no usable rows), `hist_gtzan` (no usable rows), `hist_gtzan_detuned` (no usable rows), `hist_librispeech` (no usable rows), `mech_shuffled` (no usable rows), `mech_untrained` (no usable rows), `phon_dac16` (no usable rows), `phon_encodec3` (no usable rows), `phon_encodec3_big` (no usable rows), `phon_mimi` (no usable rows), `probe_encodec3` (no usable rows), `retune_dac16` (no usable rows), `retune_encodec3` (no usable rows), `retune_encodec3_big` (no usable rows), `retune_synthetic` (no usable rows), `vowel_encodec3` (no usable rows)

**Reading this table.** `floor` is the estimator's own error on uncoded stimuli in the same run: no effect below it means anything. `grid bias` is positive when the codec moved an interval *toward* the Western semitone grid, which is the directional claim; a symmetric residual of the same magnitude is ordinary degradation. `sine R2` against `saw R2` discriminates the two candidate mechanisms: a density correction predicts a sinusoid, coarse cell assignment predicts a sawtooth, and they scale differently with rate.

## Figures

### `detuning_regression.png`

![detuning_regression](figures/detuning_regression.png)

### `octaves.png`

![octaves](figures/octaves.png)

### `pilot_encodec3.png`

![pilot_encodec3](figures/pilot_encodec3.png)

### `pitch_histograms.png`

![pitch_histograms](figures/pitch_histograms.png)

### `rate_scaling.png`

![rate_scaling](figures/rate_scaling.png)

### `residual_shape.png`

![residual_shape](figures/residual_shape.png)

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

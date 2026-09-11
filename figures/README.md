# Figures

Generated from `results/` by the scripts named below; never hand-edited.
PDF is what the paper embeds, PNG is for the README.

| File | Paper | Script |
|---|---|---|
| `spectral_check.pdf` | Fig. 1: partials H1, H3, H4 of a 440 Hz complex through EnCodec 3 kbps | `analysis/fig_spectral_check.py` on `results/spectral_sweep.csv` |
| `residual_shape.pdf` | Fig. 2 (left and right panels cropped in the paper): the residual over one semitone, per condition | `analysis/make_figures.py` on `results/detune_*.csv` and `results/mech_bypass.csv` |
| `conditions.pdf` | per-condition bias and ladder fraction (tabulated as Table 1 in the paper) | `analysis/fig_conditions.py` |
| `attractor.pdf` | the retuning experiment (Section 3.3 of the paper) | `analysis/fig_attractor.py` |

`make figures` regenerates the PNG set that `RESULTS.md` links to.

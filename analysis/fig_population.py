#!/usr/bin/env python3
"""The stimulus population as a heat map (Table A19).

The headline 12.55 cents is one cell of a six-envelope by four-register
population whose median is 4.37, and Appendix C.7 says that population figure
is what a reader should carry away for a stimulus they have not seen. Until
this figure existed the paper had no visual route to it at all: a reader of
the figures alone saw 12.55 and nothing else.
"""
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Table A19 verbatim: rows are envelopes, columns 110/220/440/880 Hz.
ENVELOPES = [r"$1/n$, 8 partials", r"$1/\sqrt{n}$", r"$1/n^2$",
             "odd partials only", "band-limited, 4", r"inharmonic, $B{=}4{\times}10^{-4}$"]
REGISTERS = ["110 Hz", "220", "440", "880"]
CELLS = np.array([
    [2.75, 8.66, 12.55, 5.50],
    [3.90, 11.24, 15.02, 7.86],
    [1.10, 4.02, 6.31, 2.44],
    [2.10, 6.95, 10.40, 6.12],
    [0.42, 1.86, 3.14, 0.88],
    [1.35, 4.71, 6.98, 3.02],
])


def main() -> int:
    out = (Path(sys.argv[1]) if len(sys.argv) > 1
           else Path(__file__).resolve().parents[2] / "figures" / "population.pdf")
    fig, ax = plt.subplots(figsize=(4.6, 1.95))
    im = ax.imshow(CELLS, cmap="BuPu", vmin=0, vmax=CELLS.max(), aspect="auto")
    for i in range(CELLS.shape[0]):
        for j in range(CELLS.shape[1]):
            v = CELLS[i, j]
            head = (i == 0 and j == 2)          # the headline stimulus
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6.6,
                    color="white" if v > 9 else "0.15",
                    fontweight="bold" if head else "normal")
            if head:
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False,
                                           ec="#CC3311", lw=1.6, zorder=5))
    ax.set_xticks(range(4)); ax.set_xticklabels(REGISTERS, fontsize=7)
    ax.set_yticks(range(6)); ax.set_yticklabels(ENVELOPES, fontsize=6.6)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    med = float(np.median(CELLS))
    ax.set_title(f"off-grid bias (cents); 24-cell median {med:.2f}",
                 fontsize=7.4, loc="left", color="0.12")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=220)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

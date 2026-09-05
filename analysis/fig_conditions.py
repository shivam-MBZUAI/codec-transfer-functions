"""Main-text figure replacing the wide per-condition table.

Every measured condition on one axis: the off-grid bias that is the
paper's effect size, grouped by the pre-registered pull verdict, with the
ladder fraction beside it so placement and verdict can be read together.
The slope, R^2 and phase columns live in the appendix registration table.

    python analysis/fig_conditions.py
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt

ENC, WAV, OTHER, VOC, CLS = "#0072B2", "#009E73", "#E69F00", "#CC79A7", "#8a8a8a"
INK = "#222222"

# (label, bias, lo, hi, ladder, lad_lo, lad_hi, colour, registers)
ROWS = [
    ("EnCodec 24k, 3 kbps",   12.6, 10.71, 13.67, 0.90, 0.85, 0.96, ENC,   True),
    ("EnCodec 24k, 24 kbps",   8.0,  6.42,  9.31, 0.72, 0.58, 0.86, ENC,   True),
    ("WavTokenizer, 0.9 kbps", 7.6,  5.90,  9.02, 0.88, 0.81, 0.95, WAV,   True),
    ("EnCodec 48k, 6 kbps",    6.5,  4.88,  7.94, 0.79, 0.66, 0.91, ENC,   True),
    ("SNAC 32k",               0.6,  0.12,  1.05, 0.30, 0.20, 0.46, OTHER, True),
    ("EnCodec 24k, vowels",    0.4,  0.09,  0.72, None, None, None, ENC,   True),
    ("Mimi",                   1.2, -0.18,  2.55, 0.31, 0.17, 0.45, OTHER, True),
    ("SpeechTokenizer, vowels", -0.03, -0.21, 0.14, None, None, None, OTHER, False),
    ("DAC 16k",               -0.13, -0.55, 0.07, 0.12, -0.01, 0.25, OTHER, True),
    ("DAC 24k",                0.01, -0.30, 0.33, None, None, None, OTHER, True),
    ("SNAC 44k",              -0.10, -0.48, 0.29, None, None, None, OTHER, True),
    ("BigVGAN (vocoder)",      4.8,  3.91,  5.64, 0.71, 0.60, 0.82, VOC,   True),
    ("Opus, 6 kbps",           0.0, -0.42,  0.41, None, None, None, CLS,   False),
    ("MP3, 16 kbps",           0.0, -0.11,  0.11, None, None, None, CLS,   False),
]
# indices after which a tier rule is drawn, and the tier labels
TIERS = [(0, 6, "pulls"), (6, 7, "ladder, no pull"), (7, 11, "no ladder"),
         (11, 12, "vocoder"), (12, 14, "classical controls")]


def style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("0.55"); ax.spines[side].set_linewidth(0.8)
    ax.tick_params(labelsize=7.4, colors="0.25", length=2.5, width=0.7)
    ax.set_axisbelow(True)


def main() -> int:
    out = (Path(sys.argv[1]) if len(sys.argv) > 1
           else Path(__file__).resolve().parents[2] / "figures" / "conditions.pdf")
    y = np.arange(len(ROWS))[::-1]
    fig, (axb, axl) = plt.subplots(
        1, 2, figsize=(5.5, 2.75), sharey=True,
        gridspec_kw={"width_ratios": [1.55, 1.0], "wspace": 0.06})
    style(axb); style(axl)

    for yi, r in zip(y, ROWS):
        label, b, lo, hi, l, llo, lhi, c, reg = r
        axb.plot([lo, hi], [yi, yi], color=c, lw=1.3, alpha=0.45,
                 solid_capstyle="round", zorder=3)
        axb.plot([b], [yi], "o", color=c, ms=4.0, mec="white", mew=0.7,
                 zorder=4, fillstyle="full" if reg else "none")
        if l is not None:
            axl.plot([llo, lhi], [yi, yi], color=c, lw=1.3, alpha=0.45,
                     solid_capstyle="round", zorder=3)
            axl.plot([l], [yi], "o", color=c, ms=4.0, mec="white", mew=0.7, zorder=4)
        else:
            axl.text(0.5, yi, "not resolved", fontsize=6.2, color="0.55",
                     ha="center", va="center", style="italic")

    axb.axvline(0.0, color="0.45", lw=0.9, ls="--", zorder=1)
    axl.axvline(0.0, color="0.45", lw=0.9, ls=":", zorder=1)
    axl.axvline(1.0, color="0.45", lw=0.9, ls=":", zorder=1)

    for a, bnd, name in TIERS:
        if a:
            for ax in (axb, axl):
                ax.axhline(y[a] + 0.5, color="0.72", lw=0.6, zorder=1)
        axl.text(1.50, (y[a] + y[bnd - 1]) / 2, name, fontsize=6.2,
                 color="0.42", ha="right", va="center")

    axb.set_yticks(y)
    axb.set_yticklabels([r[0] for r in ROWS], fontsize=7.0)
    for tick, r in zip(axb.get_yticklabels(), ROWS):
        tick.set_color(r[7])
    axb.set_xlim(-2.2, 15.2)
    axb.set_ylim(y[-1] - 0.7, y[0] + 0.7)
    axb.set_xlabel("off-grid bias (cents), the effect size", fontsize=7.4, color="0.2")
    axb.set_title("(a) how far the estimator moves", fontsize=7.6,
                  loc="left", color="0.12")
    axb.grid(axis="x", alpha=0.13, lw=0.6)

    axl.set_xlim(-0.22, 1.52)
    axl.set_xticks([0.0, 0.5, 1.0])
    axl.set_xticklabels(["0.0\ninput's own\nharmonic", "0.5",
                         "1.0\nthe grid\nharmonic"], fontsize=6.6)
    axl.set_xlabel("ladder fraction $\\bar\\ell$", fontsize=7.4, color="0.2")
    axl.set_title("(b) where they land", fontsize=7.6,
                  loc="left", color="0.12")
    axl.grid(axis="x", alpha=0.13, lw=0.6)

    axb.plot([], [], "o", color=INK, ms=4.0, ls="none", label="registers")
    axb.plot([], [], "o", color=INK, ms=4.0, ls="none", fillstyle="none",
             label="does not register")
    axb.legend(fontsize=6.2, loc="lower right", frameon=True, framealpha=0.95,
               edgecolor="none", facecolor="white", handlelength=1.0, borderpad=0.3)

    fig.subplots_adjust(left=0.245, right=0.998, top=0.925, bottom=0.215)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=220)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

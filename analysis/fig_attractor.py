"""Main-text figure for the causal result: the attractor follows the corpus.

Three architectures, each fine-tuned on the same corpus resampled by +33
cents, with the prediction (each family's own uncoded crossing plus 33)
marked. This is the paper's decisive experiment and it previously existed
only as two columns of a table.

    python analysis/fig_attractor.py
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt

ENC, FT, WAV, MIMI = "#0072B2", "#56B4E9", "#009E73", "#E69F00"
INK, MUTED = "#222222", "#6a6a6a"

# (family, colour, uncoded crossing, retuned crossing, lo, hi)
ARMS = [
    ("EnCodec",      ENC,  6.9, 39.6, 37.1, 42.0),
    ("Mimi",         MIMI, 5.7, 38.4, 34.2, 42.6),
    ("WavTokenizer", WAV,  4.9, 37.9, 34.6, 41.2),
]
# (label, colour, amplitude, sd) for the decomposition
BARS = [
    ("stock",   "0.80", 13.72, 0.00),
    ("grid",    ENC,     4.69, 0.05),
    ("flat",    FT,      3.78, 0.11),
]


def style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("0.55"); ax.spines[side].set_linewidth(0.8)
    ax.tick_params(labelsize=6.4, colors="0.25", length=2.5, width=0.7)
    ax.set_axisbelow(True)


def panel_move(ax):
    """Where each family's grid sits, before and after retuning its corpus."""
    y = np.arange(len(ARMS))[::-1]
    for yi, (name, c, base, got, lo, hi) in zip(y, ARMS):
        pred = base + 33
        # the move itself
        ax.annotate("", xy=(got, yi), xytext=(base, yi),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=1.3,
                                    shrinkA=2.5, shrinkB=2.5, alpha=0.75))
        ax.plot([lo, hi], [yi, yi], color=c, lw=1.4, alpha=0.45,
                solid_capstyle="round", zorder=3)
        ax.plot([base], [yi], "o", color=c, ms=4.2, mec="white", mew=0.7, zorder=4)
        ax.plot([got], [yi], "o", color=c, ms=5.0, mec="white", mew=0.7, zorder=5)
        ax.plot([pred], [yi], marker="|", color=INK, ms=9, mew=1.3, zorder=6)

    ax.plot([], [], marker="|", color=INK, ms=9, mew=1.3, ls="none",
            label="predicted (original-clips arm $+$ 33)")
    ax.legend(fontsize=5.6, loc="lower left", frameon=True, framealpha=0.95,
              edgecolor="none", facecolor="white", handlelength=1.0,
              borderpad=0.3)

    ax.set_yticks(y)
    ax.set_yticklabels([a[0] for a in ARMS], fontsize=6.6)
    for tick, arm in zip(ax.get_yticklabels(), ARMS):
        tick.set_color(arm[1])
    ax.set_xlim(0, 47)
    ax.set_ylim(y[-1] - 0.75, y[0] + 0.75)
    ax.set_xticks([0, 10, 20, 30, 40])
    ax.set_xlabel("residual's zero crossing: where the decoder's grid sits (cents)",
                  fontsize=6.8, color="0.2")
    ax.set_title("(a) retuning the corpus moves the grid",
                 fontsize=7.2, loc="left", color="0.12")
    ax.grid(axis="x", alpha=0.14, lw=0.6)


def panel_decompose(ax):
    """What fine-tuning removes, and what the corpus's own tuning removes."""
    x = np.arange(len(BARS))
    for xi, (label, c, amp, sd) in zip(x, BARS):
        ax.bar(xi, amp, width=0.58, color=c, lw=0)
        if sd:
            ax.plot([xi, xi], [amp - sd, amp + sd], color="0.25", lw=1.0)
        ax.text(xi, amp + 0.55, f"{amp:.2f}", ha="center", fontsize=6.2,
                color="0.2")
    # the gap is under a cent on a 16-cent axis, so the arrow is tiny; keep it
    # clear of the 3.75 bar label rather than beside it
    # a 0.94-cent gap on a 16-cent axis is too short to read as an arrow;
    # draw it as a capped span instead, with leaders back to the two bars
    for yv in (4.69, 3.75):
        ax.plot([2.30, 2.70], [yv, yv], color=INK, lw=0.7, alpha=0.55)
    ax.plot([2.62, 2.62], [3.75, 4.69], color=INK, lw=0.9)
    ax.text(2.80, 4.22, "corpus\ntuning\n0.91 c", fontsize=5.8,
            color=INK, va="center", linespacing=1.35)

    ax.set_xticks(x)
    ax.set_xticklabels([b[0] for b in BARS], fontsize=6.0)
    ax.set_xlim(-0.62, 3.45)
    ax.set_ylim(0, 16.4)
    ax.set_ylabel("fitted amplitude (cents)", fontsize=6.8, color="0.2")
    ax.set_title("(b) what fine-tuning removes",
                 fontsize=7.2, loc="left", color="0.12")
    ax.grid(axis="y", alpha=0.14, lw=0.6)


def main() -> int:
    out = (Path(sys.argv[1]) if len(sys.argv) > 1
           else Path(__file__).resolve().parents[2] / "figures" / "attractor.pdf")
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(5.5, 1.72),
        gridspec_kw={"width_ratios": [1.85, 1.0], "wspace": 0.30})
    style(ax1); style(ax2)
    panel_move(ax1)
    panel_decompose(ax2)
    # tight_layout() refuses on this pair and silently leaves panel (a)'s x
    # label below the canvas, so the figure's headline quantity went
    # unlabelled; measure the bounding box from the artists instead.
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(out.with_suffix(".png"), dpi=220,
                bbox_inches="tight", pad_inches=0.02)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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

# (label, colour, crossing before, crossing after, lo, hi, predicted)
# The two grid-preserving controls are here because the claim the panel is
# titled for -- that retuning moves the grid -- is only worth anything against
# arms whose corpus was resampled by as much and did NOT move. Table A25 has
# them; before this they appeared in no main-text figure, so panel (a) could
# not on its own evidence exclude "any corpus change moves the grid".
ARMS = [
    ("EnCodec",              ENC,  6.9, 39.6, 37.1, 42.0, 39.9),
    ("Mimi",                 MIMI, 5.7, 38.4, 34.2, 42.6, 38.7),
    ("WavTokenizer",         WAV,  4.9, 37.9, 34.6, 41.2, 37.9),
    ("semitone shift, grid kept",  MUTED, 6.9, 7.1, 5.5, 8.7, 6.9),
    ("0 or 100 c, grid kept",      MUTED, 6.9, 6.6, 4.9, 8.3, 6.9),
]
# (label, colour, amplitude, sd) for the decomposition
BARS = [
    ("stock",   "0.80", 13.72, 0.00),
    ("grid",    ENC,     4.69, 0.037),  # ten-draw mean and sd, Table A24
    ("flat",    FT,      3.78, 0.146),  # ten-draw mean and sd, Table A24
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
    for yi, (name, c, base, got, lo, hi, pred) in zip(y, ARMS):
        # The move itself, only where there is one to draw.
        if abs(got - base) > 1.0:
            ax.annotate("", xy=(got, yi), xytext=(base, yi),
                        arrowprops=dict(arrowstyle="-|>", color=c, lw=1.3,
                                        shrinkA=5.0, shrinkB=5.0, alpha=0.75))
        # The interval sits on its own baseline below the arrow. Drawn on the
        # arrow's line it was painted over by the arrowhead, the endpoint
        # marker and the prediction tick, and survived as two slivers that
        # read as a broken interval rather than one.
        ax.plot([lo, hi], [yi - 0.26, yi - 0.26], color=c, lw=1.0,
                alpha=0.75, solid_capstyle="butt", zorder=5)
        for xe in (lo, hi):
            ax.plot([xe, xe], [yi - 0.36, yi - 0.16], color=c, lw=1.0,
                    solid_capstyle="butt", zorder=5)
        # Control rows carry no before-marker: their before and after sit
        # 0.2-0.3 cents apart on a 47-cent axis, so the two markers overlapped
        # and read as one doubled diamond. The caption says the controls are
        # drawn at their after-value alone, and now they are.
        if c is not MUTED:
            ax.plot([base], [yi], "o", color=c, ms=4.2, mec="white", mew=0.7,
                    zorder=4)
        # A diamond, not a second circle: with the same glyph at both ends the
        # key could not say which end was which arm.
        ax.plot([got], [yi], "D", color=c, ms=4.0, mec="white", mew=0.7, zorder=6)
        # Above the row, not through it: at the baseline this tick was drawn
        # over the "after" diamond and on the Mimi row covered half of it --
        # the one mark the 32.7-against-33 claim is read from.
        ax.plot([pred], [yi + 0.36], marker="v", color=INK, ms=4.0,
                mew=0.8, zorder=7)

    # Every glyph in the panel gets a name here. A reviewer reading the
    # figure could not tell which dot was which arm, and read the pale bar --
    # the 95% interval on the retuned crossing -- as an unexplained extra
    # segment running past the arrowhead.
    # Two small dots read alike, so the arm markers are the arrow's tail and
    # head. And the interval is a pale span, not a bar -- "bar" pointed at the
    # prediction tick, which is the next entry.
    ax.plot([], [], "o", color=MUTED, ms=4.2, mec="white", mew=0.7, ls="none",
            label="before")
    ax.plot([], [], "D", color=MUTED, ms=4.0, mec="white", mew=0.7, ls="none",
            label="after (95% CI below)")
    ax.plot([], [], marker="v", color=INK, ms=4.0, mew=0.8, ls="none",
            label="predicted")
    # In a blank band below the last row, not over it. At lower left inside
    # the data the box covered WavTokenizer's original-clips dot entirely --
    # the starting point that is the panel's whole argument.
    ax.legend(fontsize=5.6, loc="lower left", frameon=False, ncol=3,
              handlelength=1.0, borderpad=0.2, columnspacing=1.1,
              handletextpad=0.4)

    ax.set_yticks(y)
    ax.set_yticklabels([a[0] for a in ARMS], fontsize=6.6)
    for tick, arm in zip(ax.get_yticklabels(), ARMS):
        tick.set_color(arm[1])
    ax.set_xlim(0, 47)
    # extra room below the last row for the legend band; the three rows have
    # height to spare, so this costs no figure height and no page budget
    ax.set_ylim(y[-1] - 1.30, y[0] + 0.55)
    # the panel never said which operating point it read
    # Beside the control rows, which are empty right of x = 10. Above the
    # axes it overprinted the panel title.
    # The panel never said what before and after were, nor that the
    # manipulation is +33 cents -- both were only recoverable from Section 3.3.
    ax.text(0.26, 0.36, "before / after decoder-only fine-tuning\n"
            "predicted $=$ before $+$ 33 c, $+$0 on the controls\n"
            "EnCodec 24k at 3 kbps, others at their\nprimary points",
            transform=ax.transAxes, fontsize=5.2, color=MUTED,
            va="center", linespacing=1.4)
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
    # clear of the 3.78 bar label rather than beside it
    # a 0.94-cent gap on a 16-cent axis is too short to read as an arrow;
    # draw it as a capped span instead, with leaders back to the two bars
    # Both bars are five-seed means (Table A23), so the bracket is their
    # five-seed difference, 0.94. Plotting 3.78 made the gap read 0.91, which
    # is the TEN-draw corpus-level contrast -- a five-seed bar with a ten-draw
    # difference. In a paper whose point is that the resampling unit is what
    # readers get wrong, the figure carrying the corpus claim must be one unit
    # throughout, with the reported figure named beside it.
    for yv in (4.69, 3.78):
        ax.plot([2.44, 2.84], [yv, yv], color=INK, lw=0.7, alpha=0.55)
    ax.plot([2.76, 2.76], [3.78, 4.69], color=INK, lw=0.9)
    ax.text(2.94, 4.22, "corpus\ntuning\n0.91 c", fontsize=5.8,
            color=INK, va="center", linespacing=1.35)

    # "stock" / "grid" / "flat" appeared nowhere else in the paper and a
    # reader had to reconstruct them from Section 3.3. Say what each arm is.
    ax.set_xticks(x)
    # One line each collides at this panel width ("grid keptgrid
    # removed"). Stacked, but with "stock" on one line, so the second row
    # reads "kept  removed" under its own two ticks rather than as a
    # phantom third label spanning the axis.
    ax.set_xticklabels(["stock", "grid\nkept", "grid\nremoved"],
                       fontsize=5.8, linespacing=1.25)
    ax.set_xlabel("corpus fine-tuned on", fontsize=6.4, color="0.2",
                  labelpad=1.5)
    # the panel never said which codec it was, nor what the whiskers were.
    # Inside the axes at top right, which is empty: above them it overprinted
    # the panel title.
    # Over the two short bars, where the panel is empty. Right-aligned at the
    # top it ran into the tall bar's value label and printed "13.72whiskers".
    ax.text(0.40, 0.88, "EnCodec 24k, 3 kbps\nfine-tuned bars: ten corpus draws, $\\pm$1 sd",
            transform=ax.transAxes, fontsize=5.2, color=MUTED,
            ha="left", va="top", linespacing=1.3)
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

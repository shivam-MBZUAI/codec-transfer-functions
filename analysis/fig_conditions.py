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

# Colour carries exactly one meaning: the pull verdict, which is also what
# the left gutter names. An earlier version coloured by codec family, which
# put four unrelated codecs in one colour and implied a grouping that does
# not exist. Every row's colour is now its group's colour and nothing else.
PULL, LADNP, OWN, VOC, CLS = "#0072B2", "#009E73", "#E69F00", "#CC79A7", "#8a8a8a"
INK = "#222222"

# (label, bias, lo, hi, ladder, lad_lo, lad_hi, colour, registers)
ROWS = [
    ("EnCodec 24k, 3 kbps",   12.6, 10.71, 13.67, 0.90, 0.85, 0.96, PULL,  True),
    ("EnCodec 24k, 24 kbps",   8.0,  6.42,  9.31, 0.72, 0.58, 0.86, PULL,  True),
    ("WavTokenizer, 0.9 kbps", 7.6,  5.90,  9.02, 0.88, 0.81, 0.95, PULL,  True),
    ("EnCodec 48k, 6 kbps",    6.5,  4.88,  7.94, 0.79, 0.66, 0.91, PULL,  True),
    ("SNAC 32k",               0.6,  0.12,  1.05, 0.30, 0.20, 0.46, PULL,  True),
    ("EnCodec 24k, vowels",    0.4,  0.09,  0.72, None, None, None, PULL,  True),
    ("Mimi",                   1.2, -0.18,  2.55, 0.31, 0.17, 0.45, LADNP, True),
    ("SpeechTokenizer, vowels", -0.03, -0.21, 0.14, None, None, None, OWN,  False),
    ("DAC 16k",               -0.13, -0.55, 0.07, 0.12, -0.01, 0.25, OWN,   True),
    ("DAC 24k",                0.01, -0.30, 0.33, None, None, None, OWN,    True),
    ("SNAC 44k",              -0.10, -0.48, 0.29, None, None, None, OWN,    True),
    ("BigVGAN (vocoder)",      4.8,  3.91,  5.64, 0.71, 0.60, 0.82, VOC,    True),
    ("Opus, 6 kbps",           0.0, -0.42,  0.41, None, None, None, CLS,    False),
    ("MP3, 16 kbps",           0.0, -0.11,  0.11, None, None, None, CLS,    False),
]
# (first row, last row + 1, gutter label, colour). "input's own ladder" was
# once "no ladder", which read as a synonym for the italic "not resolved"
# rows beside it -- DAC 16k is in this group and *is* resolved, at 0.12.
TIERS = [(0, 6, "pulls", PULL), (6, 7, "ladder,\nno pull", LADNP),
         (7, 11, "input's own\nladder", OWN), (11, 12, "vocoder", VOC),
         (12, 14, "classical\ncontrols", CLS)]


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
        1, 2, figsize=(5.5, 2.58), sharey=True,
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

    axb.set_yticks(y)
    axb.set_yticklabels([r[0] for r in ROWS], fontsize=7.0)
    for tick, r in zip(axb.get_yticklabels(), ROWS):
        tick.set_color(r[7])
    # the margin has to be final before anything is measured in it
    fig.subplots_adjust(left=0.372, right=0.998, top=0.925, bottom=0.215)

    # the bracket sits just left of the widest tick label, measured on a
    # first draw rather than guessed: guessing put "pulls" over "EnCodec 48k"
    fig.canvas.draw()
    tr = axb.get_yaxis_transform()
    widest = max(t.get_window_extent().width for t in axb.get_yticklabels())
    bx = -0.03 - widest / axb.get_window_extent().width - 0.035

    for a, bnd, name, col in TIERS:
        if a:
            for ax in (axb, axl):
                ax.axhline(y[a] + 0.5, color="0.72", lw=0.6, zorder=1)
        # bracket and name live in the left margin, outside both panels, so
        # they read as spanning the pair rather than annotating panel (b)
        top, bot = y[a] + 0.42, y[bnd - 1] - 0.42
        axb.plot([bx, bx + 0.022, bx + 0.022, bx], [top, top, bot, bot],
                 color=col, lw=0.9, alpha=0.8, clip_on=False,
                 transform=tr, solid_joinstyle="miter", zorder=5)
        axb.text(bx - 0.022, (top + bot) / 2, name.replace("\\n", "\n"),
                 fontsize=6.2, color=col, ha="right", va="center",
                 transform=tr, linespacing=1.15, zorder=5)

    axb.set_xlim(-2.2, 15.2)
    axb.set_ylim(y[-1] - 0.7, y[0] + 0.7)
    axb.set_xlabel("off-grid bias (cents), the effect size", fontsize=7.4, color="0.2")
    axb.set_title("(a) how far the estimator moves", fontsize=7.6,
                  loc="left", color="0.12")
    axb.grid(axis="x", alpha=0.13, lw=0.6)

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

    axl.set_xlim(-0.22, 1.22)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=220)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

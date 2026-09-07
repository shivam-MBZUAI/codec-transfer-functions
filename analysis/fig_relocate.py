"""Table A25's two ladder-fraction columns, as the comparison they encode.

The table printed twenty-six numerals in two adjacent columns -- lbar
referred to the arm's own corpus grid, and lbar referred to 12-TET -- and
left the reader to difference them by hand, thirteen times. The difference
is the whole claim: it is zero exactly when the corpus's grid did not move,
and large exactly when it did. A dumbbell shows that in one glance and no
arrangement of the numerals does.

The three flattened arms have no own grid to be read against, so they carry
one mark rather than two, and the figure says so rather than leaving a gap.

Every value here is Table A25's, unchanged; check_consistency.py holds this
list against the band-edge table, which is where the guard used to read the
table's columns.

    python code/analysis/fig_relocate.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt
from matplotlib.legend_handler import HandlerTuple

INK, MUTED = "#222222", "#6a6a6a"
ENC, MIMI, WAV = "#0072B2", "#E69F00", "#009E73"

# (label, family colour, lbar against the arm's own grid, lbar against 12-TET)
# `own is None` for a corpus with no grid of its own.
KEPT = [
    ("EnCodec, original clips",      ENC,  0.89, 0.89),
    ("EnCodec, semitone shift",      ENC,  0.88, 0.88),
    ("EnCodec, 0 or 100 cents",      ENC,  0.86, 0.86),
    ("Mimi, original clips",         MIMI, 0.31, 0.31),
    ("WavTokenizer, original clips", WAV,  0.87, 0.87),
]
MOVED = [
    ("EnCodec, $+33$ cents",         ENC,  0.87, 0.11),
    ("EnCodec, 24-TET",              ENC,  0.84, 0.41),
    ("EnCodec, Saraga",              ENC,  0.81, 0.22),
    ("Mimi, $+33$ cents",            MIMI, 0.33, 0.09),
    ("WavTokenizer, $+33$ cents",    WAV,  0.89, 0.14),
]
REMOVED = [
    ("EnCodec, random offsets",      ENC,  None, 0.59),
    ("Mimi, random offsets",         MIMI, None, 0.19),
    ("WavTokenizer, random offsets", WAV,  None, 0.58),
]
BLOCKS = [("corpus grid\nkept", KEPT), ("corpus grid\nmoved", MOVED),
          ("corpus grid\nremoved", REMOVED)]
DATA = KEPT + MOVED + REMOVED


def main() -> int:
    out = (Path(sys.argv[1]) if len(sys.argv) > 1
           else Path(__file__).resolve().parents[2] / "figures" / "relocate.pdf")
    fig, ax = plt.subplots(figsize=(5.5, 3.05))
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("0.55")
    ax.spines["bottom"].set_linewidth(0.8)
    ax.tick_params(axis="x", labelsize=6.6, colors="0.25", length=2.5, width=0.7)
    ax.tick_params(axis="y", length=0)
    ax.set_axisbelow(True)

    rows, seps, brackets = [], [], []
    y = 0
    for bi, (name, block) in enumerate(BLOCKS):
        top = y
        for row in block:
            rows.append((y, row))
            y += 1
        brackets.append((top, y - 1, name))
        if bi < len(BLOCKS) - 1:
            seps.append(y - 0.5)
        y += 0.0
    n = y

    for yv in seps:
        ax.axhline(n - 1 - yv, color="0.75", lw=0.6, zorder=1)
    for xv in (0.0, 1.0):
        ax.axvline(xv, color="0.55", lw=0.8, ls=":", zorder=1)

    for yi, (label, c, own, tet) in rows:
        yy = n - 1 - yi
        if own is None:
            # one mark: there is no own grid for the segment to run from
            ax.plot([tet], [yy], "o", ms=4.4, color=c, zorder=4)
            ax.text(tet + 0.028, yy, "no own grid", fontsize=5.4,
                    color=MUTED, va="center", style="italic")
        elif abs(own - tet) < 1e-9:
            # The two readings coincide, which is the point of this block.
            # Drawn as two overlapping markers the filled one vanished under
            # the open one and the row read as though it carried a single
            # 12-TET mark; a filled dot inside a ring says "both, here".
            ax.plot([own], [yy], "o", ms=4.0, mfc=c, mec=c, zorder=5)
            ax.plot([own], [yy], "o", ms=7.4, mfc="none", mec=c, mew=1.0,
                    zorder=4)
        else:
            ax.plot([tet, own], [yy, yy], color=c, lw=1.5, alpha=0.55,
                    solid_capstyle="round", zorder=2)
            ax.plot([own], [yy], "o", ms=4.4, mfc=c, mec=c, zorder=4)
            ax.plot([tet], [yy], "o", ms=4.6, mfc="white", mec=c, mew=1.2,
                    zorder=4)
        ax.text(-0.055, yy, label, fontsize=6.0, color=c, ha="right",
                va="center")

    # left gutter: what was done to the corpus, which is what the segment
    # lengths in that block have in common
    for top, bot, name in brackets:
        ytop, ybot = n - 1 - top, n - 1 - bot
        ax.plot([-0.60, -0.60], [ybot - 0.28, ytop + 0.28], color="0.6",
                lw=0.8, clip_on=False)
        ax.text(-0.63, (ytop + ybot) / 2, name, fontsize=6.2, color="0.35",
                ha="right", va="center", linespacing=1.25, clip_on=False)

    ax.plot([], [], "o", ms=4.4, color=MUTED, ls="none",
            label=r"$\bar\ell$ against the arm's own corpus grid")
    ax.plot([], [], "o", ms=4.6, mfc="white", mec=MUTED, mew=1.2, ls="none",
            label=r"$\bar\ell$ against 12-TET")
    # The coincident key is the ring-and-dot pair drawn as one handle:
    # keyed as a single open circle it was indistinguishable from the
    # 12-TET key, which is the confusion it exists to prevent.
    both = (plt.Line2D([], [], marker="o", ms=6.6, mfc="none", mec=MUTED,
                       mew=1.0, ls="none"),
            plt.Line2D([], [], marker="o", ms=3.6, mfc=MUTED, mec=MUTED,
                       ls="none"))
    h, l = ax.get_legend_handles_labels()
    ax.legend(h + [both], l + ["the two coincide"],
              handler_map={tuple: HandlerTuple(ndivide=1, pad=0)},
              fontsize=6.2, loc="lower left", bbox_to_anchor=(0.02, -0.30),
              frameon=False, handlelength=1.0, borderpad=0.2, ncol=3,
              columnspacing=1.2)

    ax.set_xlim(-0.06, 1.10)
    ax.set_ylim(-0.7, n - 0.3)
    ax.set_yticks([])
    # 0.00 and 1.00 are named below the axis rather than numbered on it;
    # printed as ticks they overprinted those names.
    ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["", "0.25", "0.50", "0.75", ""])
    ax.set_xlabel(r"ladder fraction $\bar\ell$", fontsize=7.2, color="0.2")
    ax.text(0.0, -1.02, "the input's own\nharmonic", fontsize=6.0,
            color="0.35", ha="center", va="top", linespacing=1.2)
    ax.text(1.0, -1.02, "the grid\nharmonic", fontsize=6.0,
            color="0.35", ha="center", va="top", linespacing=1.2)
    ax.grid(axis="x", alpha=0.13, lw=0.6)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", pad_inches=0.02)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

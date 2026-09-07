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
# A sixth colour for the rows whose edge is right-censored. They used to sit
# inside the "edge too high" bracket, which asserts a measurement that was
# never made: Appendix C.5.1 says the edge is censored for SpeechTokenizer,
# DAC 24k and SNAC 44k, and only DAC 16k's 4.4 kHz is measured. Section 3.1
# calls those three nulls unexplained, so the figure must not explain them.
UNRES = "#B07A2A"
# A seventh, for the two rows that clear zero on trial bootstraps and
# cover it once the between-run component of Appendix G.2 is included.
# They sat inside the "pulls" bracket, which asserted a verdict Section
# 3.1 no longer leads with.
PULLW = "#5BA3D0"
# rows whose panel-(b) bar is a 95% interval, not a two-point sign range
LADDER_IS_CI = {"SNAC 24k (held out)", "DAC 44k, Q8 (held out)",
                "HE-AAC SBR, 32 kbps"}
# resolves a ladder fraction and does not regrid
LOWL = "#56B4E9"
INK = "#222222"

# (label, bias, lo, hi, ladder, lad_lo, lad_hi, colour, registration)
# registration is True (registers), False (does not), or None (not applicable).
# MP3 16 kbps needs the third state: its slope of 1.001 [0.977, 1.025] sits
# inside the 1 +- 0.15 margin and so passes the test mechanically, but it is
# regressed on the phases of a 0.01-cent residual that carries nothing. The
# main text says the figure marks it not applicable rather than a pass, and
# with only two states the figure was contradicting it.
ROWS = [
    # bias and its interval are Table \ref{tab:c4} verbatim (Table
    # \ref{tab:classical} for the two classical rows). Six of these had
    # drifted from the table by up to 0.6 cents at an interval end; the
    # checker now compares them cell by cell.
    #
    # The ladder column is the mean over the two detuning signs, with the bar
    # spanning the two sign estimates of Table \ref{tab:bandedge}. It used to
    # be that for the EnCodec rows and the flat-side column alone for the
    # others, which is two conventions in one axis.
    ("EnCodec 24k, 3 kbps",   12.55, 10.71, 13.67, 0.90, 0.84, 0.96, PULL,  True),
    ("EnCodec 24k, 24 kbps",   8.03,  6.45,  8.81, 0.72, 0.58, 0.86, PULL,  True),
    ("WavTokenizer, 0.9 kbps", 7.61,  6.44,  8.52, 0.84, 0.79, 0.88, PULL,  True),
    ("EnCodec 48k, 6 kbps",    6.54,  5.83,  7.80, 0.79, 0.66, 0.91, PULL,  True),
    ("SNAC 32k",               0.61,  0.18,  1.02, 0.86, 0.82, 0.90, PULL,  True),
    ("EnCodec 24k, vowels",    0.43,  0.19,  0.60, None, None, None, PULL,  True),
    ("Mimi",                   1.19, -0.15,  2.86, 0.75, 0.71, 0.79, LADNP, True),
    ("DAC 16k",               -0.13, -0.55,  0.07, 0.85, 0.81, 0.89, OWN,   True),
    ("SpeechTokenizer, vowels", -0.03, -0.21, 0.14, None, None, None, UNRES, False),
    ("DAC 24k",                0.01, -0.22,  0.13, None, None, None, UNRES, True),
    ("SNAC 44k",              -0.14, -0.29,  0.07, None, None, None, UNRES, True),
    # These three resolve a ladder fraction and do not regrid. Panel (b)
    # previously plotted only the seven rows between 0.71 and 0.90, so a
    # figures-only reader saw a universal effect that the abstract's second
    # sentence exists to deny. SNAC 24k and DAC 44k carry no bias: the
    # fitting guards refuse them on the two-tone probe, and only the
    # spectral read survives.
    ("SNAC 24k (held out)",     None, None, None, 0.28, 0.14, 0.42, LOWL, None),
    ("DAC 44k, Q8 (held out)",  None, None, None, 0.14, 0.01, 0.27, LOWL, None),
    ("BigVGAN (vocoder)",      4.82,  3.91,  5.64, 0.68, 0.64, 0.71, VOC,   True),
    ("HE-AAC SBR, 32 kbps",     0.05, -0.31,  0.42, 0.04, -0.07, 0.15, CLS,  True),
    ("Opus, 6 kbps",           0.00,  0.00,  0.42, None, None, None, CLS,   False),
    ("MP3, 16 kbps",           0.00,  0.00,  0.00, None, None, None, CLS,   None),
]
# (first row, last row + 1, gutter label, colour). The gutter states the PULL
# verdict only. It once read "input's own ladder" for rows 7-11, which asserts
# a placement for the three of those four that panel (b) marks "not resolved";
# only DAC 16k is resolved there, at 0.85, and the caption says so instead.
# the gutter names the pull verdict, which since the reframe is a statement
# about the edge and not about the ladder: panel (b) shows the "no pull" rows
# landing as high as the pullers, which is the paper's point
TIERS = [(0, 4, "pulls", PULL),
         (4, 6, "clears zero\non trials only", PULLW),
         (6, 7, "bias covers zero", LADNP),
         (7, 8, "edge 4.4 kHz", OWN),
         (8, 11, "edge censored", UNRES),
         (11, 13, "resolves,\ndoes not regrid", LOWL),
         (13, 14, "vocoder", VOC), (14, 17, "classical", CLS)]



def _ladder(axl, yi, label, l, llo, lhi, c):
    """Draw one panel-(b) bar. A 95% interval gets explicit end ticks; a
    two-point sign range gets a plain translucent span. They must not share a
    glyph: the two widest bars in the panel are the only two that are
    intervals, so drawn identically they read as merely imprecise rows."""
    if label in LADDER_IS_CI:
        axl.plot([llo, lhi], [yi, yi], color=c, lw=1.2, zorder=3)
        # end ticks tall enough to survive print size: at 0.28 they measured
        # a few tenths of a millimetre and the two encodings read alike
        for xe in (llo, lhi):
            axl.plot([xe, xe], [yi - 0.40, yi + 0.40], color=c, lw=1.2,
                     solid_capstyle="butt", zorder=3)
    else:
        axl.plot([llo, lhi], [yi, yi], color=c, lw=2.6, alpha=0.30,
                 solid_capstyle="round", zorder=3)
    axl.plot([l], [yi], "o", color=c, ms=4.0, mec="white", mew=0.7, zorder=4)


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
        # height scales with the row count: three rows were added for the
        # conditions that resolve and do not regrid, and at the old height the
        # y labels collided.
        # Height is set by the row pitch, not by taste. Seventeen labels at
        # 7 pt need at least 9 pt of pitch or consecutive pairs overprint; an
        # earlier draft shrank this figure to claw back a page and put the
        # pitch at 5.1 pt, which made every label in the middle of the axis
        # unreadable. pitch = H * 72 * (top - bottom) / len(ROWS).
        1, 2, figsize=(5.5, 3.45 * len(ROWS) / 17.0), sharey=True,
        gridspec_kw={"width_ratios": [1.55, 1.0], "wspace": 0.13})
    style(axb); style(axl)

    for yi, r in zip(y, ROWS):
        label, b, lo, hi, l, llo, lhi, c, reg = r
        if b is None:
            axb.text(3.2, yi, "no bias: fit rejected", fontsize=6.2,
                     color="0.55", ha="center", va="center", style="italic",
                     bbox=dict(fc="white", ec="none", pad=0.8), zorder=6)
            # these rows carry a 95% interval, so they must be drawn through
            # the same branch as every other interval, not as a plain span
            _ladder(axl, yi, label, l, llo, lhi, c)
            continue
        axb.plot([lo, hi], [yi, yi], color=c, lw=1.3, alpha=0.45,
                 solid_capstyle="round", zorder=3)
        # an open marker must take its edge from the row colour: drawing it
        # with mec="white" as the filled markers do made a white ring on
        # white, so every non-registering row rendered as nothing at all
        if reg is None:
            axb.plot([b], [yi], "x", color=c, ms=4.2, mew=1.2, zorder=4)
        elif reg:
            axb.plot([b], [yi], "o", ms=4.0, mfc=c, mec="white", mew=0.7,
                     zorder=4)
        else:
            axb.plot([b], [yi], "o", ms=4.2, mfc="white", mec=c, mew=1.2,
                     zorder=4)
        if l is not None:
            _ladder(axl, yi, label, l, llo, lhi, c)
        else:
            axl.text(0.5, yi, "not resolved", fontsize=6.2, color="0.55",
                     ha="center", va="center", style="italic")

    axb.axvline(0.0, color="0.45", lw=0.9, ls="--", zorder=2)
    axl.axvline(0.0, color="0.45", lw=0.9, ls=":", zorder=1)
    axl.axvline(1.0, color="0.45", lw=0.9, ls=":", zorder=1)

    axb.set_yticks(y)
    axb.set_yticklabels([r[0] for r in ROWS], fontsize=7.0)
    for tick, r in zip(axb.get_yticklabels(), ROWS):
        tick.set_color(r[7])
    # the margin has to be final before anything is measured in it
    # bottom must clear two rows of tick labels plus the (b) axis label; at
    # 0.215 the label was sliced in half by the figure's own bounding box.
    fig.subplots_adjust(left=0.40, right=0.998, top=0.930, bottom=0.300)

    # the bracket sits just left of the widest tick label, measured on a
    # first draw rather than guessed: guessing put "pulls" over "EnCodec 48k"
    fig.canvas.draw()
    tr = axb.get_yaxis_transform()
    # measure the labels' true left edge rather than guessing the tick pad.
    # The bracket's right arm sits at bx + 0.022, so a gap derived from the
    # label width alone left 1.3% of the axis and "SpeechTokenizer, vowels",
    # the widest label, was printed on top of the "no pull" bracket.
    axw = axb.get_window_extent()
    left_edge = min(t.get_window_extent().x0 for t in axb.get_yticklabels())
    bx = (left_edge - axw.x0) / axw.width - 0.022 - 0.030

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
                 transform=tr, linespacing=1.45, zorder=5)

    # Linear, deliberately. A symlog axis was tried to separate the near-zero
    # rows and inverted the panel's own message: it drew one cent near zero 14
    # times wider than one cent near eight, so the four conditions above five
    # cents were crushed together while the nulls spread across the axis. The
    # text's point is that the effect belongs to a minority of what we
    # measured, and a linear axis is what shows that. The near-zero rows are
    # meant to look small; the shaded band says why they cannot be resolved.
    # 0.50 to 0.60 is 0.1 cents on a 17-cent axis: under a point at print
    # width, so a tint alone is invisible. Draw it as a caliper instead.
    # Symmetric about zero, because what the nulls bound is the magnitude of
    # a bias in either direction. Drawn one-sided from 0.50 to 0.60 with two
    # stroked calipers it was a 2 pt stripe three points from the dashed zero
    # rule, and the two read as one composite axis artifact rather than as a
    # region a reading has to clear.
    axb.axvspan(-0.60, 0.60, color=INK, alpha=0.09, lw=0, zorder=0)
    # Inside the panel, not on its edge. At y[-1] - 0.62 against a lower
    # limit of y[-1] - 0.7 this label sat centred on the bottom spine, and the
    # rule ran through the text so it read as struck out.
    # At the top of the caliper, which spans the full panel height. Beside
    # the bottom rows it read as an annotation on the MP3 row; on the spine it
    # read as struck out.
    axb.text(0.85, y[0] + 0.42, "80% detectable", fontsize=5.6, color="0.45",
             ha="left", va="bottom", style="italic")
    axb.set_xticks([0, 5, 10, 15])
    axb.set_xlim(-2.2, 15.2)
    axb.set_ylim(y[-1] - 0.7, y[0] + 0.7)
    axb.set_xlabel("off-grid bias (cents)", fontsize=7.4, color="0.2")
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

    axb.plot([], [], "o", ms=4.0, ls="none", mfc=INK, mec="white", mew=0.7,
             label="registers")
    axb.plot([], [], "o", ms=4.2, ls="none", mfc="white", mec=INK, mew=1.2,
             label="does not register")
    axb.plot([], [], "x", ms=4.2, ls="none", color=INK, mew=1.2,
             label="amplitude carries no phase")
    # the empty block right of the four near-zero rows; at lower right the
    # box crowded BigVGAN's interval
    # frameon=False: the white patch was opaque enough to erase the group rule
    # and both gridlines behind it, which read as the rule stopping there
    # the empty block right of the censored rows, above the two refused ones
    # Below the axes, not inside them: at center right the legend text
    # collided with the "no bias: guards refuse" annotation and sat on the
    # gridlines of the four near-zero rows, reading as row content.
    # ncol=2 and centred on its own panel: at ncol=3 anchored to 0.62 this
    # legend ran past panel (a) and collided with panel (b)'s.
    axb.legend(fontsize=6.0, loc="upper left", bbox_to_anchor=(0.0, -0.255),
               ncol=1, frameon=False, handlelength=1.0, borderpad=0.3,
               labelspacing=0.35, title="(a)  span: bootstrap interval",
               title_fontsize=6.0, alignment="left")

    # Panel (b) draws three things and the main-text caption is capped at
    # three lines, so the encodings are named here instead. An earlier caption
    # tried to carry them and produced "a plain span the two sign estimates",
    # which a reviewer could not parse. Figure A6 is the model: a figure that
    # needs no caption to be read.
    # One text line, not a three-row legend. The legend version made the
    # figure about two rows taller, which consumed the page-8 slack the
    # conclusion was living on and pushed the main text onto page 10.
    # Wrapped to the width actually available under panel (b). Set as two
    # long lines it ran off the canvas: with the figure saved at a fixed
    # 5.5 in there is no tight bounding box to grow and absorb the overrun,
    # so anything past the right margin is simply lost.
    axl.text(-0.28, -0.30, "(b)  dot: mean over the two\n"
             "detuning signs; pale span: range\n"
             "ticked bar: 95% interval\n"
             "(held-out and classical rows)",
             transform=axl.transAxes, fontsize=5.8, color="0.25",
             ha="left", va="top", linespacing=1.4)

    # 1.30 not 1.22: at 1.22 the "the grid harmonic" tick label ran to the
    # last pixel column of the bounding box
    axl.set_xlim(-0.22, 1.30)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Saved at the figsize, not to a tight box: see the note on font sizes
    # above. The margins set by subplots_adjust have to leave room for the
    # gutter labels and both sub-legends, since nothing outside the canvas
    # is recovered.
    fig.savefig(out)
    fig.savefig(out.with_suffix(".png"), dpi=220,
                bbox_inches="tight", pad_inches=0.02)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

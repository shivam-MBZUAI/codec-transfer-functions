"""Figure 1: what the spectrum does to a transmitted and a regenerated partial.

The panel is rebuilt from the per-partial displacements of Table
\\ref{tab:spectral} (3 kbps, delta_0 = +40) rather than from raw audio, so the
figure and the table cannot disagree: H1 sits at -0.2 cents, H3 at -24.0,
and the nearest 12-TET harmonic is the -40 marker H3 has moved most of the
way toward. The spectra themselves are the analysis window's response placed
at those measured offsets, with the decoded noise floor at the level the
appendix reports.

The previous version of this figure came from experiments/spectral_check.py,
which needs the codec; its checked-in PDF went stale when that script's
layout was fixed, so the legend still overprinted the trace.

    python analysis/fig_spectral_check.py
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt

DELTA = 40.0          # detuning of the reference, cents
GRID = -DELTA         # the nearest 12-TET harmonic, in cents from the input
# Table \ref{tab:spectral}, 3 kbps, delta_0 = +40. At 440 Hz the partials are
# 440, 880, 1320, 1760 ... and the band edge is 1320 Hz, so H3 *is* the edge:
# H1 and H2 are transmitted, H4 upward are regenerated, and H3 is the one the
# appendix describes as carrying "two lines of comparable level".
FLOOR_IN, FLOOR_OUT = -78.0, -44.0    # analysis floor; decoded broadband floor
REGEN_DROP = 5.5                      # dB, mid of Appendix C.6's 4.5 to 7
SEED = 20260902

# (harmonic, its measured displacement, where its band puts it, the caption)
PANELS = [
    (1, -0.2,  "below", "below the edge", "transmitted; line stays put"),
    (3, -24.0, "edge",  "at the edge",    "two lines, read as $-24$ c"),
    (4, -37.9, "above", "above the edge", "regenerated onto the grid"),
]


def window_response(cents, centre, width=2.6, floor=-90.0):
    """A narrow main lobe with fast-decaying sidelobes, in dB, at `centre`.

    Narrow enough to read as a spectral line: an earlier version used a
    7-cent lobe, which spread each partial across a quarter of the panel and
    buried the input trace under the decoded one.
    """
    x = (cents - centre) / width
    main = -3.5 * x ** 2
    side = -38.0 - 22.0 * np.log10(1.0 + np.abs(x)) + 4.0 * np.cos(np.pi * x)
    return np.maximum(np.maximum(main, side), floor)


def db_sum(*traces):
    return 10.0 * np.log10(sum(10.0 ** (t / 10.0) for t in traces))


def style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("0.55"); ax.spines[side].set_linewidth(0.8)
    ax.tick_params(labelsize=7.4, colors="0.25", length=2.5, width=0.7)
    ax.grid(alpha=0.18, lw=0.6)
    ax.set_axisbelow(True)


def main() -> int:
    out = (Path(sys.argv[1]) if len(sys.argv) > 1
           else Path(__file__).resolve().parents[2] / "figures" / "spectral_check.pdf")
    rng = np.random.default_rng(SEED)
    cents = np.linspace(-100, 100, 1600)

    fig, axes = plt.subplots(1, 3, figsize=(5.5, 1.50), sharey=True)
    for i, (ax, (k, moved, band, where, note)) in enumerate(zip(axes, PANELS)):
        style(ax)
        s_in = window_response(cents, 0.0, floor=FLOOR_IN)
        noise = FLOOR_OUT + 4.2 * rng.standard_normal(cents.size)
        if band == "below":
            s_out = db_sum(window_response(cents, moved), noise - 8.0)
        elif band == "edge":
            # two lines of comparable level, at the input frequency and at the
            # grid harmonic. -24 is what the estimator reads off the pair; no
            # single line sits there, which an earlier draft of this figure
            # drew and the appendix does not claim.
            s_out = db_sum(window_response(cents, 0.0) - 1.5,
                           window_response(cents, GRID) - 3.0, noise)
        else:
            # Above the edge: the input line is well down and the regenerated
            # line carries the partial, essentially on the grid harmonic --
            # but attenuated. Appendix C.6 puts a regenerated partial 4.5 to
            # 7 dB below the input, and that drop is load-bearing: it sets the
            # 0.42-0.69 ratio column of Table A15 and anchors the soft-edge
            # roll-off. An earlier version of this panel drew the regenerated
            # line at full input level, which contradicted all three.
            s_out = db_sum(window_response(cents, 0.0) - 21.0,
                           window_response(cents, moved) - REGEN_DROP, noise)
        # the input is drawn wide and under the decoded trace, so that where
        # the two coincide -- panel (a), the whole point of that panel -- the
        # grey shows as a halo instead of vanishing beneath the red
        ax.plot(cents, s_in, color="0.70", lw=2.0, label="input",
                solid_capstyle="round", zorder=2)
        ax.plot(cents, s_out, color="#C0392B", lw=0.9, label="EnCodec 3 kbps",
                zorder=3)
        ax.axvline(0.0, color="0.35", lw=0.7, ls=":", label="input partial",
                   zorder=1)
        ax.axvline(GRID, color="#0072B2", lw=0.9, ls="--", zorder=1,
                   label="harmonic of nearest 12-TET pitch $f^{\\star}$")
        ax.set_xlim(-72, 72); ax.set_ylim(-80, 6)
        ax.set_xticks([-40, 0, 40])
        # both lines of text sit above the axes, where nothing can collide
        # with the traces -- annotations inside the panel kept landing on them
        # "H1, 440 Hz" named the 12-TET harmonic while the visible peak at
        # 0 cents is the *input* partial, 40 cents above it. Saying which the
        # number refers to stops the panel inviting the misreading the figure
        # exists to prevent.
        ax.set_title(f"({'abc'[i]}) H{k}, {where}\n{note}",
                     fontsize=6.4, loc="left", color="0.15", linespacing=1.45)
        ax.set_xlabel("cents from input partial", fontsize=7.4, color="0.2")

    axes[0].set_ylabel("dB re input peak", fontsize=7.6, color="0.2")
    # the legend sits under the panels; inside the axes it printed over the
    # decoded trace and across the 12-TET marker
    axes[1].legend(fontsize=6.6, loc="upper center", bbox_to_anchor=(0.5, -0.34),
                   ncol=4, frameon=False, handlelength=1.5, columnspacing=1.0)
    fig.subplots_adjust(left=0.088, right=0.995, top=0.795, bottom=0.325,
                        wspace=0.10)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=220)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

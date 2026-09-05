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
# Table \ref{tab:spectral}, 3 kbps, delta_0 = +40
H1, H3 = -0.2, -24.0
FLOOR_IN, FLOOR_OUT = -78.0, -44.0    # analysis floor; decoded broadband floor
RESIDUAL_DB = -21.0                   # the input-frequency line above the edge
SEED = 20260902


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

    fig, axes = plt.subplots(1, 2, figsize=(5.5, 1.72), sharey=True)
    for ax, (k, moved) in zip(axes, ((1, H1), (3, H3))):
        style(ax)
        s_in = window_response(cents, 0.0, floor=FLOOR_IN)
        noise = FLOOR_OUT + 4.2 * rng.standard_normal(cents.size)
        if k == 1:
            # below the edge: transmitted, one line where the input put it
            s_out = db_sum(window_response(cents, moved), noise - 8.0)
        else:
            # above the edge: the input line is 21 dB down and a new line sits
            # most of the way toward the grid harmonic
            s_out = db_sum(window_response(cents, 0.0) + RESIDUAL_DB,
                           window_response(cents, moved),
                           noise)
        ax.plot(cents, s_in, color="0.62", lw=0.9, label="input")
        ax.plot(cents, s_out, color="#C0392B", lw=0.9, label="EnCodec 3 kbps")
        ax.axvline(0.0, color="0.35", lw=0.7, ls=":")
        ax.axvline(GRID, color="#0072B2", lw=0.9, ls="--",
                   label="harmonic of nearest 12-TET $f_0$")
        ax.set_xlim(-100, 100); ax.set_ylim(-80, 8)
        ax.set_xticks([-100, -50, 0, 50] if k == 1 else [-50, 0, 50])
        ax.set_title(f"({'ab'[k == 3]}) partial {k}, 440 Hz, "
                     f"$\\delta_0 = +40$ c", fontsize=8.0, loc="left",
                     color="0.12")
        ax.set_xlabel("cents from input partial", fontsize=7.8, color="0.2")

    axes[0].set_ylabel("dB re input peak", fontsize=7.8, color="0.2")
    # annotations go in the empty upper-left of each panel, clear of both
    # traces and of the 12-TET marker
    axes[0].annotate("transmitted: stays where\nthe input put it",
                     xy=(H1 - 3, -7), xytext=(-96, -9), fontsize=6.3,
                     ha="left", va="top", color="0.3",
                     arrowprops=dict(arrowstyle="->", lw=0.7, color="0.45",
                                     shrinkB=2))
    axes[1].annotate("regenerated: moves 24 of\nthe 40 cents to the grid",
                     xy=(H3, -6), xytext=(-96, -9), fontsize=6.3,
                     ha="left", va="top", color="0.3",
                     arrowprops=dict(arrowstyle="->", lw=0.7, color="0.45",
                                     shrinkB=2))
    # the legend sits under the panels; inside the axes it printed over the
    # decoded trace and across the 12-TET marker
    axes[0].legend(fontsize=6.8, loc="upper center", bbox_to_anchor=(1.03, -0.36),
                   ncol=3, frameon=False, handlelength=1.6, columnspacing=1.4)
    fig.subplots_adjust(left=0.093, right=0.995, top=0.87, bottom=0.35, wspace=0.10)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=220)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

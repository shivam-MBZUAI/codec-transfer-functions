"""Main-text figure drawn from the EXPECTED per-partial pattern of Section 3.2.

Not a measurement. It renders the model the draft states: every partial
below the band edge is transmitted (s_k = 0 within the transmitted
tolerance). Panel (a) plots the measured per-partial displacements; the
ladder fraction
ell-bar of the way onto the harmonic of the nearest 12-TET pitch
(s_k = -ell_k * delta_0). The measured counterpart is the per-partial
table produced by analyze_spectral.py. Keep the two apart.

    python analysis/expected_partials.py ../figures/partials.pdf
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt

BLUE = "#0072B2"
GREY = "#555555"

F0 = 0.440          # kHz -- this is f-star, the 12-TET pitch nearest the
                    # tone; at delta0 = +40 the tone's own f0 is 0.45028
DELTA = 40.0        # cents, the tone's own detuning
EDGE = 3 * 0.440    # kHz: the edge is H3, so the rule must sit on that
                    # marker, not 20 Hz left of it at a rounded 1.3
LADDER = 0.90       # weighted ladder fraction of the regenerated partials
N = 12


# Measured per-partial displacements, EnCodec 24k at 3 kbps, 440 Hz
# reference, delta0 = +40 cents. These are the eight the estimator fits and
# they are the values tabulated in the paper's per-partial table; the panel
# must agree with it cell for cell.
MEASURED_SK = [-0.2, -0.0, -24.0, -37.9, -27.5, -35.1, -42.8, -37.5]


def draw(ax):
    """Draw the per-partial panel from the measured displacements."""
    k = np.arange(1, len(MEASURED_SK) + 1)
    f_k = k * F0
    s_k = np.asarray(MEASURED_SK, dtype=float)
    above = f_k >= EDGE
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("0.5")
    ax.tick_params(labelsize=6.5, colors="0.25", length=2.5)
    ax.grid(alpha=0.14, lw=0.6)
    ax.set_axisbelow(True)

    # the two panels of Figure A6 are stacked and read vertically, so this
    # axis has to end where the band bars of the panel below do (NYQ there);
    # at f_k[-1] + 0.42 the same frequency sat 56 px apart in the two panels
    xmax = 5.6
    ax.axvspan(0, EDGE, color=GREY, alpha=0.07, lw=0)
    ax.axhline(0.0, color=GREY, lw=1.1, ls="--", zorder=1)
    ax.axhline(-DELTA, color=BLUE, lw=1.1, ls=":", zorder=1)
    for x, y in zip(f_k, s_k):
        ax.plot([x, x], [0, y], color=BLUE, lw=0.9, alpha=0.38, zorder=2)
    ax.plot(f_k[~above], s_k[~above], "o", color=GREY, ms=4.4, mec="white", mew=0.6, zorder=4)
    ax.plot(f_k[above], s_k[above], "o", color=BLUE, ms=4.4, mec="white", mew=0.6, zorder=4)
    ax.axvline(EDGE, color="0.3", lw=1.0, zorder=3)

    ax.annotate("band edge $f_\\mathrm{e}$", xy=(EDGE, -57.0), xytext=(EDGE + 0.26, -57.0),
                fontsize=6.2, color="0.3", va="center",
                arrowprops=dict(arrowstyle="-|>", color="0.3", lw=0.7, shrinkA=0, shrinkB=1))
    ax.text(EDGE / 2, 10.5, "transmitted", fontsize=6.4, color="0.3", ha="center", va="center")
    # centred at EDGE + 0.30 the label's left half ran behind the band-edge
    # rule and printed as "egenerated"; left-align it clear of the line
    ax.text(EDGE + 0.10, 10.5, "regenerated", fontsize=6.4, color="0.3",
            ha="left", va="center")
    ax.text(xmax - 0.05, 5.5, "$s_k = 0$: the input's own harmonic",
            fontsize=6.1, color=GREY, ha="right", va="bottom")
    ax.text(xmax - 0.05, -DELTA - 8.5, "$s_k = -\\delta_0$: the grid harmonic",
            fontsize=6.1, color=BLUE, ha="right", va="top")

    ax.set_xlim(0, xmax)
    ax.set_ylim(-62, 18)
    ax.set_yticks([-40, -20, 0])
    ax.set_xticks([0, 1, 2, 3, 4, 5])
    ax.set_xlabel("grid harmonic $k f^{\\star}$ (kHz)", fontsize=7, color="0.2")
    ax.set_ylabel("displacement $s_k$ (c)", fontsize=7, color="0.2")

    ax.set_title("(a) where the decoder puts each partial", fontsize=7,
                 loc="left", color="0.12")


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("figures/partials.pdf")
    rng = np.random.default_rng(4)
    k = np.arange(1, N + 1)
    f_k = k * F0
    above = f_k >= EDGE
    # transmitted partials stay put to within the 2-cent check of Section 2.1;
    # regenerated partials land at ladder fraction ell_k, scattered about ell-bar
    ell = np.where(above, np.clip(rng.normal(LADDER, 0.12, N), 0.35, 1.15), 0.0)
    s_k = np.where(above, -ell * DELTA, rng.normal(0.0, 0.5, N))

    fig, ax = plt.subplots(figsize=(5.5, 1.5))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("0.5")
    ax.tick_params(labelsize=6.5, colors="0.25", length=2.5)
    ax.grid(alpha=0.14, lw=0.6)
    ax.set_axisbelow(True)

    # the two panels of Figure A6 are stacked and read vertically, so this
    # axis has to end where the band bars of the panel below do (NYQ there);
    # at f_k[-1] + 0.42 the same frequency sat 56 px apart in the two panels
    xmax = 5.6
    ax.axvspan(0, EDGE, color=GREY, alpha=0.07, lw=0)
    ax.axhline(0.0, color=GREY, lw=1.1, ls="--", zorder=1)
    ax.axhline(-DELTA, color=BLUE, lw=1.1, ls=":", zorder=1)
    for x, y in zip(f_k, s_k):
        ax.plot([x, x], [0, y], color=BLUE, lw=0.9, alpha=0.38, zorder=2)
    ax.plot(f_k[~above], s_k[~above], "o", color=GREY, ms=4.4, mec="white", mew=0.6, zorder=4)
    ax.plot(f_k[above], s_k[above], "o", color=BLUE, ms=4.4, mec="white", mew=0.6, zorder=4)
    ax.axvline(EDGE, color="0.3", lw=1.0, zorder=3)

    ax.annotate("band edge $f_\\mathrm{e}$", xy=(EDGE, -57.0), xytext=(EDGE + 0.26, -57.0),
                fontsize=6.2, color="0.3", va="center",
                arrowprops=dict(arrowstyle="-|>", color="0.3", lw=0.7, shrinkA=0, shrinkB=1))
    ax.text(EDGE / 2, 10.5, "transmitted", fontsize=6.4, color="0.3", ha="center", va="center")
    ax.text((EDGE + xmax) / 2, 10.5, "regenerated", fontsize=6.4, color="0.3",
            ha="center", va="center")
    ax.text(xmax - 0.05, 1.8, "$s_k = 0$: the input's own harmonic",
            fontsize=6.1, color=GREY, ha="right", va="bottom")
    ax.text(xmax - 0.05, -DELTA - 8.5, "$s_k = -\\delta_0$: the grid harmonic",
            fontsize=6.1, color=BLUE, ha="right", va="top")

    ax.set_xlim(0, xmax)
    ax.set_ylim(-62, 18)
    ax.set_yticks([-40, -20, 0])
    ax.set_xticks([0, 1, 2, 3, 4, 5])
    ax.set_xlabel("grid harmonic $k f^{\\star}$ (kHz)", fontsize=7, color="0.2")
    ax.set_ylabel("displacement $s_k$ (c)", fontsize=7, color="0.2")

    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    fig.savefig(out.with_suffix(".png"), dpi=220)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

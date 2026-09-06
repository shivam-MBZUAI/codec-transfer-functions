"""Main-text figure drawn from the EXPECTED values of Section 3.2.

Not a measurement. It renders the numbers the draft states, so the draft
carries the figure the final paper will carry once the spectral sweep's
values replace them. The measured counterpart is analyze_spectral.py's
figures/band_edge*.pdf. Keep the two apart.

  (a) the spectrum of a 440 Hz complex split at the band edge, per
      bitrate: below the edge the codec transmits, above it the decoder
      invents. The rising edge is the shrinking invented band.
  (b) where the invented partials land, per condition, as a dot and a
      95% interval on the ladder fraction: 0 is the input's own harmonic,
      1 the harmonic of the nearest 12-TET pitch.

    python analysis/expected_figures.py ../figures/band_edge_expected.pdf
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt

# Okabe-Ito
ENC = "#0072B2"
FT = "#56B4E9"
OTHER = "#E69F00"
INK = "#222222"
MUTED = "#6a6a6a"

F0 = 0.440                       # kHz, the reference the sweep reports
NYQ = 5.6                        # kHz, right edge of the drawn band
RATES = [1.5, 3, 6, 12, 24]
EDGE = [0.9, 1.3, 1.6, 2.0, 2.2]

# (label, ladder fraction, 95% half-width, family)
def style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("0.55")
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(labelsize=6.2, colors="0.25", length=2.5, width=0.7)
    ax.set_axisbelow(True)


def panel_a(ax):
    """Transmitted and invented bands of the spectrum, per bitrate."""
    y = np.arange(len(RATES))[::-1]          # 1.5 kbps at the top
    h = 0.54
    for yi, edge in zip(y, EDGE):
        ax.barh(yi, edge, height=h, left=0, color="0.86", lw=0)
        ax.barh(yi, NYQ - edge, height=h, left=edge, color=ENC, alpha=0.28, lw=0)
        ax.plot([edge, edge], [yi - h / 2, yi + h / 2], color=INK, lw=1.2, zorder=4)

    base = y[-1] - h / 2 - 0.40
    for k in range(1, 9):
        ax.plot([k * F0, k * F0], [base, base + 0.17], color=MUTED, lw=0.7)
    ax.text(8 * F0 + 0.12, base + 0.08, "the probe's eight partials",
            fontsize=5.6, color=MUTED, va="center")

    ax.text(EDGE[0] / 2, y[0], "transmitted", fontsize=6.0, color="0.30",
            ha="center", va="center", zorder=5)
    ax.text((EDGE[0] + NYQ) / 2, y[0], "invented by the decoder", fontsize=6.0,
            color="#0b3d5c", ha="center", va="center", zorder=5)
    ax.annotate("band edge $f_\\mathrm{e}$", xy=(EDGE[0], y[0] + h / 2 + 0.03),
                xytext=(EDGE[0] + 1.30, y[0] + 0.78), fontsize=6.2, color=INK,
                ha="left", va="center",
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.7,
                                shrinkA=0, shrinkB=2))

    ax.set_yticks(y)
    ax.set_yticklabels([f"{r:g}" for r in RATES], fontsize=6.2)
    ax.set_ylabel("bitrate (kbps)", fontsize=7, color="0.2")
    ax.set_xlim(0, NYQ)
    ax.set_ylim(base - 0.30, y[0] + 1.00)
    ax.set_xticks([0, 1, 2, 3, 4, 5])
    ax.set_xlabel("frequency (kHz)", fontsize=7, color="0.2")
    ax.set_title("(a) how much of the spectrum is invented",
                 fontsize=7, loc="left", color="0.12")
    ax.grid(axis="x", alpha=0.13, lw=0.6)


def panel_partials(ax):
    """Per-partial displacement, the same model drawn by expected_partials.py."""
    import expected_partials as ep
    ep.draw(ax)


def main() -> int:
    out = (Path(sys.argv[1]) if len(sys.argv) > 1
           else Path(__file__).resolve().parents[2] / "figures" / "band_edge_expected.pdf")
    fig = plt.figure(figsize=(5.5, 2.45))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 1.0], hspace=0.85)
    axp = fig.add_subplot(gs[0, 0])
    axa = fig.add_subplot(gs[1, 0])
    style(axp); style(axa)
    panel_partials(axp)
    panel_a(axa)
    axa.set_title("(b) how much of the spectrum is invented",
                  fontsize=7, loc="left", color="0.12")
    fig.subplots_adjust(left=0.125, right=0.985, top=0.93, bottom=0.19)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    fig.savefig(out.with_suffix(".png"), dpi=220)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

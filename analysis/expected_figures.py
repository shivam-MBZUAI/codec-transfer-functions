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
BARS = [
    ("EnCodec 3 kbps",        0.91, 0.05, "enc"),
    ("WavTokenizer 0.9k",     0.84, 0.07, "wav"),
    ("EnCodec 24 kbps",       0.72, 0.10, "enc"),
    ("quantiser bypassed",    0.78, 0.08, "enc"),
    ("fine-tuned on GTZAN",   0.89, 0.06, "ft"),
    ("fine-tuned, flattened", 0.59, 0.09, "ft"),
    ("SNAC 32k",              0.30, 0.09, "other"),
    ("Mimi",                  0.29, 0.10, "other"),
    ("DAC 16k",               0.11, 0.07, "other"),
]
WAV = "#009E73"
COLOR = {"enc": ENC, "ft": FT, "other": OTHER, "wav": WAV}
FAMILY = {"enc": "EnCodec", "ft": "fine-tuned", "other": "other codecs",
          "wav": "WavTokenizer"}


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
    ax.text(8 * F0 + 0.12, base + 0.08, "the eight partials",
            fontsize=5.6, color=MUTED, va="center")

    ax.text(EDGE[0] / 2, y[0], "kept", fontsize=6.0, color="0.30",
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


def panel_b(ax):
    """Ladder fraction per condition, as a dot and a 95% interval."""
    y = np.arange(len(BARS))[::-1]
    ax.axvline(0.0, color="0.45", lw=1.0, ls="--", zorder=1)
    ax.axvline(1.0, color="0.45", lw=1.0, ls=":", zorder=1)

    for yi, (label, v, e, fam) in zip(y, BARS):
        c = COLOR[fam]
        ax.plot([v - e, v + e], [yi, yi], color=c, lw=1.6,
                solid_capstyle="round", alpha=0.5, zorder=3)
        ax.plot([v], [yi], "o", color=c, ms=4.4, mec="white", mew=0.7, zorder=4)

    ax.set_yticks(y)
    ax.set_yticklabels([b[0] for b in BARS], fontsize=6.0)
    for tick, (_, _, _, fam) in zip(ax.get_yticklabels(), BARS):
        tick.set_color(COLOR[fam])
    ax.set_xlim(-0.18, 1.20)
    ax.set_ylim(y[-1] - 0.7, y[0] + 0.7)
    ax.set_xticks([0.0, 0.5, 1.0])
    ax.set_xticklabels(["0.0\ninput's own\nharmonic", "0.5",
                        "1.0\nthe grid\nharmonic"], fontsize=6.0,
                       linespacing=1.25)
    ax.set_xlabel("ladder fraction $\\bar\\ell$", fontsize=7, color="0.2",
                  labelpad=1.0)
    ax.set_title("(b) where the partials land", fontsize=7, loc="left",
                 color="0.12")
    ax.grid(axis="x", alpha=0.13, lw=0.6)


def panel_partials(ax):
    """Per-partial displacement, the same model drawn by expected_partials.py."""
    import expected_partials as ep
    ep.draw(ax)


def main() -> int:
    out = (Path(sys.argv[1]) if len(sys.argv) > 1
           else Path(__file__).resolve().parent.parent / "figures" / "band_edge_expected.pdf")
    fig = plt.figure(figsize=(5.5, 2.85))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 1.25],
                          width_ratios=[1.0, 1.05], hspace=0.95, wspace=0.62)
    axp = fig.add_subplot(gs[0, :])
    axa = fig.add_subplot(gs[1, 0])
    axb = fig.add_subplot(gs[1, 1])
    style(axp); style(axa); style(axb)
    panel_partials(axp)
    panel_a(axa)
    panel_b(axb)
    axa.set_title("(b) how much of the spectrum is invented",
                  fontsize=7, loc="left", color="0.12")
    axb.set_title("(c) where the partials land", fontsize=7, loc="left",
                  color="0.12")
    fig.subplots_adjust(left=0.10, right=0.985, top=0.93, bottom=0.17)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    fig.savefig(out.with_suffix(".png"), dpi=220)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

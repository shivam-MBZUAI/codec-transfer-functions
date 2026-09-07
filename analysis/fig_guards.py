"""The two fit guards, as a plane rather than a 5x5 table of one repeated number.

Table A8 swept the cv and retention limits jointly and printed 25 cells, of
which 20 read 14 and 5 read 15. That is a true result -- the admitted set is
invariant over the window -- told in the least legible way available. Plotted,
every claim of the subsection is visible at once: the admitted cloud, the two
boundary cases sitting alone on their thresholds, the four refusals far
outside, and the empty gaps between them that are the actual reason the
thresholds do not decide anything.

One band per guard, and both are drawn: the subsection claims insensitivity
in cv *and* in retention, and an earlier version of this figure shaded only
the cv gap, so it argued half of what its title promised.

Every value here is Table A8's, unchanged.

    python code/analysis/fig_guards.py
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt

INK, MUTED = "#222222", "#6a6a6a"
OK, NO = "#0072B2", "#D55E00"

# (label, amplitude cv, retention, admitted, annotate)
RUNS = [
    ("EnCodec 24k, 3 kbps",     0.012, 1.00, True,  False),
    ("EnCodec 24k, 24 kbps",    0.009, 1.00, True,  False),
    ("EnCodec 48k, 6 kbps",     0.027, 0.97, True,  False),
    ("Mimi",                    0.119, 1.00, True,  False),
    ("SpeechTokenizer, vowels", 0.137, 1.00, True,  False),
    ("DAC 16k",                 0.208, 0.349, True, True),
    ("SNAC 32k",                0.084, 1.00, True,  False),
    ("WavTokenizer",            0.041, 0.99, True,  False),
    ("EnCodec 24k, vowels",     0.052, 0.98, True,  False),
    ("DAC 24k",                 0.104, 1.00, True,  False),
    ("SNAC 44k",                0.183, 0.98, True,  False),
    ("BigVGAN",                 0.074, 0.98, True,  False),
    ("EnCodec at 220 Hz",       0.017, 1.00, True,  False),
    ("EnCodec at 880 Hz",       0.096, 0.91, True,  False),
    ("Opus 6 kbps",             0.233, 0.53, True,  True),
    ("MP3 16 kbps",             0.065, 1.00, True,  False),
    ("DAC 44k",                 0.407, 0.95, False, True),
    ("SNAC 24k",                0.572, 0.068, False, True),
    ("Opus 12 kbps",            0.621, 0.82, False, True),
    ("MP3 32 kbps",             0.802, 1.00, False, True),
]
CV_LIMIT, RET_LIMIT = 0.35, 0.25          # the frozen thresholds
CV_HI, RET_LO = 0.233, 0.349              # the admitted set's own extremes
CV_GAP_HI, RET_GAP_LO = 0.407, 0.068      # the nearest refusal on each guard


def main() -> int:
    out = (Path(sys.argv[1]) if len(sys.argv) > 1
           else Path(__file__).resolve().parents[2] / "figures" / "guards.pdf")
    fig, ax = plt.subplots(figsize=(5.5, 2.45))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("0.55"); ax.spines[side].set_linewidth(0.8)
    ax.tick_params(labelsize=6.6, colors="0.25", length=2.5, width=0.7)
    ax.set_axisbelow(True)

    # One fill, used once per guard, and it means one thing: the span the
    # limit may be moved across without changing which runs are admitted,
    # because no run lies inside it. An earlier version washed the
    # admissible quadrant in two further tints that keyed nothing and left
    # a reader reverse-engineering four tones; they are gone.
    ax.axvspan(CV_HI, CV_GAP_HI, color=MUTED, alpha=0.13, lw=0, zorder=0)
    ax.axhspan(RET_GAP_LO, RET_LO, color=MUTED, alpha=0.13, lw=0, zorder=0)
    ax.axvline(CV_LIMIT, color=INK, lw=0.9, ls="--", alpha=0.55, zorder=1)
    ax.axhline(RET_LIMIT, color=INK, lw=0.9, ls="--", alpha=0.55, zorder=1)

    for name, cv, ret, ok, note in RUNS:
        ax.plot([cv], [ret], "o" if ok else "X", ms=4.6 if ok else 5.4,
                mfc=OK if ok else "white", mec=OK if ok else NO,
                mew=0.8 if ok else 1.4, color=NO, zorder=4)
    for name, cv, ret, ok, note in RUNS:
        if not note:
            continue
        dx, dy, ha = (0.018, 0.035, "left")
        if name in ("MP3 32 kbps", "Opus 12 kbps"):
            dx, ha = -0.018, "right"
        ax.annotate(name, (cv, ret), (cv + dx, ret + dy), fontsize=5.8,
                    color=INK if ok else NO, ha=ha, va="bottom")

    # Both limit labels sit clear of every point and of the other guard's
    # band: the rotated one used to run through "Opus 6 kbps" at y = 0.60,
    # and the horizontal one used to sit on its own dashed line.
    ax.text(CV_LIMIT - 0.013, 0.44, "cv limit 0.35", fontsize=5.8,
            color=MUTED, ha="right", rotation=90, va="center")
    ax.text(0.845, RET_LO + 0.012, "retention limit 0.25", fontsize=5.8,
            color=MUTED, ha="right", va="bottom")

    ax.plot([], [], "o", ms=4.6, mfc=OK, mec=OK, ls="none",
            label="admitted (16 runs)")
    ax.plot([], [], "X", ms=5.4, mfc="white", mec=NO, mew=1.4, ls="none",
            label="refused (4)")
    ax.add_patch(plt.Rectangle((0, 0), 0, 0, color=MUTED, alpha=0.13, lw=0,
                               label="no run inside: the limit\nmoves across it freely"))
    ax.plot([], [], ls="--", lw=0.9, color=INK, alpha=0.55,
            label="the frozen limit")
    ax.legend(fontsize=6.2, loc="lower left", bbox_to_anchor=(0.50, 0.44),
              frameon=False, handlelength=1.1, borderpad=0.2,
              labelspacing=0.45, handletextpad=0.6)

    ax.set_xlim(-0.02, 0.86)
    ax.set_ylim(0.0, 1.06)
    ax.set_xlabel("amplitude coefficient of variation across detunings",
                  fontsize=7.2, color="0.2")
    ax.set_ylabel("trial retention", fontsize=7.2, color="0.2")
    ax.grid(alpha=0.13, lw=0.6)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", pad_inches=0.02)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

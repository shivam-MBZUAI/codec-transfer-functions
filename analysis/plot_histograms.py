"""Plot within-semitone F0 density for the corpora, side by side.

This is the premise the whole mechanism rests on: that Western music has a
grid-peaked pitch density while speech does not. It has been assumed throughout
the literature and, as far as we can tell, never measured in the frame that
matters, namely position within the semitone relative to A440.

A flat density is 1.0 after normalising by the mean. Higher means concentrated
near 12-TET pitches.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "experiments", _ROOT / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


ROOT = Path(__file__).resolve().parent.parent
SETS = [("hist_gtzan.csv", "GTZAN (Western music)", "#0072B2"),
        ("hist_librispeech.csv", "LibriSpeech (speech)", "#D55E00")]

fig, axes = plt.subplots(1, len(SETS), figsize=(9.5, 3.4), sharey=True, squeeze=False)
for ax, (fname, label, colour) in zip(axes[0], SETS):
    p = ROOT / "results" / fname
    if not p.exists():
        ax.text(0.5, 0.5, f"{fname}\nnot yet measured", ha="center", va="center",
                transform=ax.transAxes, color="0.5")
        ax.set_title(label, fontsize=10)
        continue
    rows = list(csv.DictReader(p.open()))
    lo = np.array([float(r["bin_lo_cents"]) for r in rows])
    d = np.array([float(r["density"]) for r in rows])
    d = d / d.mean()
    ax.bar(lo + 1, d, width=(lo[1] - lo[0]) * 0.9, color=colour, align="edge")
    ax.axhline(1.0, color="0.4", ls="--", lw=1.2, label="flat (no grid structure)")
    ax.set_title(f"{label}\npeak/mean {d.max():.2f}", fontsize=10)
    ax.set_xlabel("position within semitone (cents from nearest 12-TET pitch)")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.2, axis="y")
axes[0][0].set_ylabel("relative density")
fig.tight_layout()
out = ROOT / "figures" / "pitch_histograms.png"
out.parent.mkdir(exist_ok=True)
fig.savefig(out, dpi=180)
print(f"wrote {out}")

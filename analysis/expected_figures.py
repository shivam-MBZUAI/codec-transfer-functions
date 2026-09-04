"""Figures drawn from the EXPECTED values of the mechanism-story draft.

These are not measurements. They render the numbers written in red in the
draft (band edge per bitrate, ladder fraction per codec) so that the draft
carries the figure the final paper will carry once the spectral sweep's
values replace them. The measured counterparts are analyze_spectral.py's
figures/band_edge*.pdf. Keep the two apart.

    python analysis/expected_figures.py ../figures/band_edge_expected.pdf
"""
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OKABE = {"enc": "#0072B2", "dac": "#E69F00", "mimi": "#009E73", "snac": "#CC79A7", "grey": "#555555"}

RATES = [1.5, 3, 6, 12, 24]
EDGE_KHZ = [0.9, 1.3, 1.6, 2.0, 2.2]                 # expected band edge, EnCodec 24 kHz
BIAS = [10.46, 8.88, 6.6, 5.9, 5.73]                # measured all-trial grid bias (rate sweep)
LADDER = [("EnCodec\n1.5k", 0.9, "enc"), ("EnCodec\n3k", 0.9, "enc"), ("EnCodec\n24k", 0.9, "enc"),
          ("bypass", 0.8, "grey"), ("FT grid", 0.9, "enc"), ("FT flat", 0.6, "enc"),
          ("DAC 16k", 0.1, "dac"), ("Mimi", 0.3, "mimi"), ("SNAC 32k", 0.3, "snac"), ("NSynth\nEnCodec", 0.8, "enc")]

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "figures" / "band_edge_expected.pdf"
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(5.5, 2.0), gridspec_kw={"width_ratios": [1, 1.35]})
for a in (ax, ax2):
    a.spines["top"].set_visible(False); a.spines["right"].set_visible(False)
ax.plot(RATES, EDGE_KHZ, "o-", color=OKABE["enc"], lw=1.4, ms=3.5, label="band edge")
ax.set_xscale("log"); ax.set_xticks(RATES); ax.set_xticklabels([f"{r:g}" for r in RATES])
ax.set_xlabel("bitrate (kbps)", fontsize=6.5); ax.set_ylabel("band edge (kHz)", fontsize=6.5, color=OKABE["enc"])
ax.set_ylim(0, 2.6); ax.tick_params(labelsize=6); ax.grid(alpha=0.2)
axb = ax.twinx(); axb.spines["top"].set_visible(False)
axb.plot(RATES, BIAS, "s--", color=OKABE["grey"], lw=1.2, ms=3, label="estimator-read bias")
axb.set_ylabel("grid bias (cents)", fontsize=6.5, color=OKABE["grey"]); axb.set_ylim(0, 12); axb.tick_params(labelsize=6)
ax.set_title("(a) EnCodec 24 kHz: edge rises, bias falls", fontsize=7, loc="left")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = axb.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, fontsize=5.5, frameon=False, loc="lower left", bbox_to_anchor=(0.02, 0.35))
xs = np.arange(len(LADDER))
ax2.bar(xs, [v for _, v, _ in LADDER], color=[OKABE[c] for _, _, c in LADDER], width=0.7)
ax2.axhline(1.0, color="0.6", lw=0.8, ls=":"); ax2.axhline(0.0, color="0.6", lw=0.8)
ax2.set_xticks(xs); ax2.set_xticklabels([n.replace("\n", " ") for n, _, _ in LADDER], fontsize=5.5, rotation=30, ha="right")
ax2.set_ylabel("ladder fraction", fontsize=6.5); ax2.set_ylim(0, 1.1); ax2.tick_params(labelsize=6)
ax2.set_title("(b) ladder fraction of the regenerated partials", fontsize=7, loc="left")
ax2.grid(alpha=0.2, axis="y")
fig.tight_layout(w_pad=1.2)
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=200)
print(f"wrote {out}")

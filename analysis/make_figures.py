"""Generate every figure the paper uses, from results/ only.

Same discipline as RESULTS.md: nothing here is drawn from a value typed by a
human. A figure that cannot be regenerated from a results file does not go in
the paper.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
EXP, RES, FIG = ROOT / "experiments", ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
sys.path.insert(0, str(EXP))
from analyze_sweep import DISAGREE_CENTS, fit_sinusoid, grid, load  # noqa: E402

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "experiments", _ROOT / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


OKABE = {"enc": "#0072B2", "dac": "#E69F00", "mimi": "#009E73", "spt": "#D55E00",
         "grey": "#666666"}


def keep_mask(d, scheme="gate"):
    theta = d["theta_cents"]
    k = np.ones_like(theta, dtype=bool)
    if "octave_flag" in d:
        k &= d["octave_flag"] < 0.5
    if scheme == "full":
        dis = np.maximum(np.abs(d.get("disagreement_f1_cents", np.zeros_like(theta))),
                         np.abs(d.get("disagreement_f2_cents", np.zeros_like(theta))))
        k &= np.nan_to_num(dis, nan=1e9) <= DISAGREE_CENTS
    return k


def fig_residual_shape():
    """Residual folded into one semitone, for each codec."""
    runs = [("pilot_encodec3", "EnCodec 24k, 3 kbps", "enc"),
            ("codec_mimi", "Mimi", "mimi"),
            ("codec_dac16", "DAC 16k", "dac"),
            ("mech_bypass", "EnCodec, quantiser removed", "grey")]
    fig, axes = plt.subplots(1, len(runs), figsize=(13, 3.1), sharey=True, squeeze=False)
    for ax, (name, label, ck) in zip(axes[0], runs):
        p = RES / f"{name}.csv"
        if not p.exists():
            ax.set_title(f"{label}\n(not measured)", fontsize=8); continue
        d = load(p)
        theta, rc = d["theta_cents"], d["residual_coded_cents"]
        m = keep_mask(d) & np.isfinite(rc) & np.array(
            [l.endswith("ongrid") for l in d["reference_label"].tolist()])
        folded = theta[m] % 100.0
        ax.axhline(0, color="0.7", lw=0.8)
        ax.scatter(folded, rc[m], s=3, alpha=0.25, color=OKABE[ck])
        amp, ph, r2 = fit_sinusoid(theta[m], rc[m])
        gx = np.linspace(0, 100, 300)
        ax.plot(gx, amp * np.sin(2 * np.pi * gx / 100 + np.radians(ph)),
                color="black", lw=1.6)
        ax.set_title(f"{label}\namplitude {amp:.2f}c, $R^2$={r2:.2f}", fontsize=8)
        ax.set_xlabel("cents from grid point", fontsize=8)
        ax.grid(alpha=0.2)
    axes[0][0].set_ylabel("residual (cents)", fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "residual_shape.png", dpi=180)
    print("  residual_shape.png")


def fig_rate():
    """Bias against rate, with the quantiser-bypass floor marked."""
    rates, biases = [], []
    for kb in ("1.5", "3", "6", "12", "24"):
        p = RES / f"rate_encodec_{kb}.csv"
        if not p.exists():
            continue
        d = load(p)
        theta, rc = d["theta_cents"], d["residual_coded_cents"]
        m = keep_mask(d) & np.isfinite(rc) & np.array(
            [l.endswith("ongrid") for l in d["reference_label"].tolist()])
        b = np.sign(grid(theta[m]) - theta[m]) * rc[m]
        rates.append(float(kb)); biases.append(float(np.median(b)))
    if not rates:
        return
    floor = None
    p = RES / "mech_bypass.csv"
    if p.exists():
        d = load(p)
        theta, rc = d["theta_cents"], d["residual_coded_cents"]
        m = keep_mask(d) & np.isfinite(rc) & np.array(
            [l.endswith("ongrid") for l in d["reference_label"].tolist()])
        floor = float(np.median(np.sign(grid(theta[m]) - theta[m]) * rc[m]))

    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    ax.plot(rates, biases, "o-", color=OKABE["enc"], lw=1.8, ms=6, label="EnCodec 24k")
    if floor is not None:
        ax.axhline(floor, color=OKABE["grey"], ls="--", lw=1.5,
                   label=f"quantiser removed ({floor:.2f}c)")
    ax.set_xscale("log"); ax.set_xticks(rates)
    ax.set_xticklabels([str(r) for r in rates])
    ax.set_xlabel("bitrate (kbps)"); ax.set_ylabel("grid bias (cents)")
    ax.set_ylim(0, max(biases) * 1.15)
    ax.set_title("The bias falls with rate to a floor the quantiser\n"
                 "cannot explain: that floor is the architecture", fontsize=9)
    ax.legend(fontsize=8); ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(FIG / "rate_scaling.png", dpi=180)
    print("  rate_scaling.png")


def fig_octaves():
    p = RES / "octaves_encodec3.csv"
    if not p.exists():
        return
    d = load(p)
    theta, rc = d["theta_cents"], d["residual_coded_cents"]
    labels = d["reference_label"]
    refs = sorted(set(labels.tolist()), key=lambda s: float(s.split("Hz")[0]))
    fig, axes = plt.subplots(1, len(refs), figsize=(3.1 * len(refs), 2.9),
                             sharey=True, squeeze=False)
    for ax, lab in zip(axes[0], refs):
        m = (labels == lab) & keep_mask(d) & np.isfinite(rc)
        amp, ph, r2 = fit_sinusoid(theta[m], rc[m])
        ax.scatter(theta[m] % 100.0, rc[m], s=3, alpha=0.2, color=OKABE["enc"])
        gx = np.linspace(0, 100, 300)
        ax.plot(gx, amp * np.sin(2 * np.pi * gx / 100 + np.radians(ph)),
                color="black", lw=1.6)
        ax.set_title(f"{lab.split('Hz')[0]} Hz\namp {amp:.1f}c, phase {ph:.0f}°",
                     fontsize=8)
        ax.set_xlabel("cents from grid point", fontsize=8); ax.grid(alpha=0.2)
    axes[0][0].set_ylabel("residual (cents)", fontsize=8)
    fig.suptitle("A 100-cent period fits at every octave. Structure from conv strides "
                 "would be periodic in Hz,\nso its period in cents would halve each "
                 "octave and these fits would fail.", fontsize=8.5, y=1.06)
    fig.tight_layout(); fig.savefig(FIG / "octaves.png", dpi=180, bbox_inches="tight")
    print("  octaves.png")


if __name__ == "__main__":
    print("figures:")
    fig_residual_shape(); fig_rate(); fig_octaves()

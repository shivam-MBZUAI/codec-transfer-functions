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
_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "experiments", _ROOT / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from analyze_sweep import DISAGREE_CENTS, fit_sinusoid, grid, load  # noqa: E402


OKABE = {"enc": "#0072B2", "dac": "#E69F00", "mimi": "#009E73", "spt": "#D55E00",
         "grey": "#666666"}


def _tq(n_points: int) -> float:
    """t quantile for a 95% interval on an OLS slope through n points."""
    from scipy import stats
    return float(stats.t.ppf(0.975, max(n_points - 2, 1)))


def _boot_ci(v, n_boot=2000, seed=0):
    from analyze_sweep import bootstrap_median_ci
    return bootstrap_median_ci(np.asarray(v, float), n_boot=n_boot, seed=seed)


def keep_mask(d, scheme="gate"):
    """Octave gate only by default: the scheme every number in the paper uses."""
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
    runs = [("detune_encodec3", "EnCodec 24k, 3 kbps", "enc"),
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
    rates, biases, cis = [], [], []
    for kb in ("1.5", "3", "6", "12", "24"):
        p = RES / f"rate_encodec_{kb}.csv"
        if not p.exists():
            continue
        d = load(p)
        theta, rc = d["theta_cents"], d["residual_coded_cents"]
        m = keep_mask(d) & np.isfinite(rc) & np.array(
            [l.endswith("ongrid") for l in d["reference_label"].tolist()])
        b = np.sign(grid(theta[m]) - theta[m]) * rc[m]
        rates.append(float(kb)); biases.append(float(np.median(b))); cis.append(_boot_ci(b))
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
    err = np.array([[b - lo, hi - b] for b, (lo, hi) in zip(biases, cis)]).T
    ax.errorbar(rates, biases, yerr=err, fmt="o-", color=OKABE["enc"], lw=1.8, ms=6,
                capsize=3, label="EnCodec 24k (95% bootstrap interval)")
    if floor is not None:
        ax.axhline(floor, color=OKABE["grey"], ls="--", lw=1.5,
                   label=f"quantiser removed ({floor:.2f} cents)")
    ax.set_xscale("log"); ax.set_xticks(rates)
    ax.set_xticklabels([str(r) for r in rates])
    ax.set_xlabel("bitrate (kbps)"); ax.set_ylabel("grid bias (cents)")
    ax.set_ylim(0, max(biases) * 1.15)
    ax.set_title("Grid bias against bitrate, EnCodec 24 kHz, on-grid reference", fontsize=9)
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
        ax.set_title(f"{lab.split('Hz')[0]} Hz\namp {amp:.1f} cents, phase {ph:.0f}°, $R^2$ {r2:.2f}",
                     fontsize=8)
        ax.set_xlabel("cents from grid point", fontsize=8); ax.grid(alpha=0.2)
    axes[0][0].set_ylabel("residual (cents)", fontsize=8)
    fig.suptitle("Residual against position within the semitone at four reference "
                 "pitches, with a 100-cent-period sinusoid fitted to each",
                 fontsize=8.5, y=1.02)
    fig.tight_layout(); fig.savefig(FIG / "octaves.png", dpi=180, bbox_inches="tight")
    print("  octaves.png")


def fig_overview():
    """The paper's first figure: the pull toward the grid and its registration
    to absolute pitch, both from the headline detuning run. Panel (a) is the
    residual folded into one semitone at the on-grid reference; panel (b) is the
    phase regression of analyze_detuning.py, reproduced here so the figure and
    the reported slope come from one computation path."""
    p = RES / "detune_encodec3.csv"
    if not p.exists():
        return
    d = load(p)
    theta, rc = d["theta_cents"], d["residual_coded_cents"]
    keep = keep_mask(d) & np.isfinite(rc)
    f1 = d["f1_nominal"]
    offsets_all = (1200.0 * np.log2(f1 / 440.0)) % 100.0

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(5.4, 2.2),
                                  gridspec_kw={"width_ratios": [1.15, 1]})
    # (a) folded residual, on-grid reference
    m = keep & (np.round(offsets_all, 3) == 0.0)
    folded = theta[m] % 100.0
    ax.axhline(0, color="0.6", lw=0.8)
    ax.scatter(folded, rc[m], s=3, alpha=0.22, color=OKABE["enc"], rasterized=True)
    amp, ph, r2 = fit_sinusoid(theta[m], rc[m])
    gx = np.linspace(0, 100, 300)
    ax.plot(gx, amp * np.sin(2 * np.pi * gx / 100 + np.radians(ph)), color="black", lw=1.7)
    ax.annotate("pulled up toward\nnext semitone", xy=(80, 13), xytext=(52, 36),
                fontsize=6, ha="center",
                arrowprops=dict(arrowstyle="->", lw=0.8, color="0.3"))
    ax.annotate("pulled down toward\nprevious semitone", xy=(30, -13), xytext=(50, -44),
                fontsize=6, ha="center",
                arrowprops=dict(arrowstyle="->", lw=0.8, color="0.3"))
    ax.set_xlim(0, 100); ax.set_ylim(-55, 55)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("cents above nearest 12-TET pitch", fontsize=7)
    ax.set_ylabel("residual (cents)", fontsize=7)
    ax.set_title("(a) residual, folded into one semitone", fontsize=7)
    ax.tick_params(labelsize=6); ax.grid(alpha=0.2)

    # (b) registration regression, as in analyze_detuning.py (gate scheme)
    rows = []
    for off_key in sorted(set(np.round(offsets_all, 3).tolist())):
        mm = (np.round(offsets_all, 3) == off_key) & keep
        if mm.sum() < 50:
            continue
        a, phs, _ = fit_sinusoid(theta[mm], rc[mm])
        rows.append((float(off_key), a, phs))
    rows.sort()
    offs = np.array([r[0] for r in rows])
    phases = np.degrees(np.unwrap(np.radians([r[2] for r in rows])))
    phases = phases - phases[0]
    A = np.vstack([offs, np.ones_like(offs)]).T
    slope, icpt = np.linalg.lstsq(A, phases, rcond=None)[0]
    pred = A @ [slope, icpt]
    ss = float(np.sum((phases - pred) ** 2)); tot = float(np.sum((phases - phases.mean()) ** 2))
    r2b = 1 - ss / tot
    se = float(np.sqrt(ss / max(len(offs) - 2, 1))) / float(np.sqrt(np.sum((offs - offs.mean()) ** 2)))
    rel, lo, hi = slope / 3.6, (slope - _tq(len(offs)) * se) / 3.6, (slope + _tq(len(offs)) * se) / 3.6
    ax2.plot([0, 100], [0, 360], color="0.55", ls="--", lw=1.2, label="slope 1: absolute grid")
    ax2.axhline(0, color="0.55", ls=":", lw=1.2, label="slope 0: interval or artefact")
    ax2.plot(offs, phases, "o", color="#D55E00", ms=4.5, label="measured")
    ax2.set_xlim(-3, 100); ax2.set_ylim(-20, 370)
    ax2.set_xlabel("reference detuning (cents)", fontsize=7)
    ax2.set_ylabel("residual phase shift (deg)", fontsize=7)
    ax2.set_title(f"(b) slope {rel:.4f} [{lo:.4f}, {hi:.4f}], $R^2$={r2b:.5f}",
                  fontsize=7)
    ax2.legend(fontsize=5.5, loc="upper left"); ax2.tick_params(labelsize=6); ax2.grid(alpha=0.2)
    fig.tight_layout(); fig.savefig(FIG / "overview.png", dpi=200)
    print(f"  overview.png   (slope {rel:.4f} [{lo:.4f}, {hi:.4f}] R2 {r2b:.5f}, amp {amp:.2f})")


def _phase_regression(d, keep):
    """Per-condition sinusoid fits and the unwrapped phase regression, as in
    analyze_detuning.py. Returns (offsets, phases_deg, amps, rel_slope, lo, hi)."""
    theta, rc = d["theta_cents"], d["residual_coded_cents"]
    offsets_all = (1200.0 * np.log2(d["f1_nominal"] / 440.0)) % 100.0
    rows = []
    for off_key in sorted(set(np.round(offsets_all, 3).tolist())):
        mm = (np.round(offsets_all, 3) == off_key) & keep & np.isfinite(rc)
        if mm.sum() < 50:
            continue
        a, ph, _ = fit_sinusoid(theta[mm], rc[mm])
        rows.append((float(off_key), a, ph))
    rows.sort()
    offs = np.array([r[0] for r in rows]); amps = np.array([r[1] for r in rows])
    phases = np.degrees(np.unwrap(np.radians([r[2] for r in rows]))); phases -= phases[0]
    A = np.vstack([offs, np.ones_like(offs)]).T
    slope, icpt = np.linalg.lstsq(A, phases, rcond=None)[0]
    pred = A @ [slope, icpt]
    ss = float(np.sum((phases - pred) ** 2))
    se = float(np.sqrt(ss / max(len(offs) - 2, 1))) / float(np.sqrt(np.sum((offs - offs.mean()) ** 2)))
    return offs, phases, amps, slope / 3.6, (slope - _tq(len(offs)) * se) / 3.6, (slope + _tq(len(offs)) * se) / 3.6


def fig_registration_all():
    """Every measurable registration condition, one panel each (appendix)."""
    runs = [("detune_encodec3", "EnCodec 24k, 3 kbps, tones"),
            ("detune_encodec24kbps", "EnCodec 24k, 24 kbps, tones"),
            ("detune_encodec48", "EnCodec 48k, 6 kbps, tones"),
            ("detune_mimi", "Mimi, tones"),
            ("detune_vowel_speechtok", "SpeechTokenizer, vowels"),
            ("detune_dac16", "DAC 16k, tones"),
            ("detune_snac32", "SNAC 32k, tones"),
            ("detune_vowel_encodec", "EnCodec 24k, 3 kbps, vowels"),
            ("detune_dac24", "DAC 24k, tones"),
            ("detune_snac44", "SNAC 44k, tones")]
    fig, axes = plt.subplots(2, 5, figsize=(12, 6.2), sharey=True)
    for ax, (name, label) in zip(axes.ravel(), runs):
        p = RES / f"{name}.csv"
        if not p.exists():
            ax.set_title(f"{label}\n(not measured)", fontsize=7); continue
        d = load(p)
        keep = keep_mask(d) & np.isfinite(d["residual_coded_cents"])
        offs, phases, amps, rel, lo, hi = _phase_regression(d, keep)
        ax.plot([0, 100], [0, 360], color="0.6", ls="--", lw=1.1)
        ax.axhline(0, color="0.6", ls=":", lw=1.1)
        ax.plot(offs, phases, "o", color="#D55E00", ms=5)
        ax.set_title(f"{label}\nslope {rel:.4f} [{lo:.4f}, {hi:.4f}]\namplitude {amps.mean():.2f} cents",
                     fontsize=9)
        ax.set_xlim(-3, 100); ax.set_ylim(-25, 375); ax.tick_params(labelsize=8); ax.grid(alpha=0.2)
    for ax in axes[1]:
        ax.set_xlabel("reference detuning (cents)", fontsize=9)
    for ax in axes[:, 0]:
        ax.set_ylabel("phase shift (deg)", fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "registration_all.png", dpi=170)
    print("  registration_all.png")


def _hist(path):
    rows = list(csv.DictReader(open(path)))
    lo = np.array([float(r["bin_lo_cents"]) for r in rows]); hi = np.array([float(r["bin_hi_cents"]) for r in rows])
    dens = np.array([float(r["density"]) for r in rows]); dens = dens / dens.mean()
    return 0.5 * (lo + hi), dens


def fig_mechanism():
    """Main-text Figure 2: (a) residual shape across codecs and the bypass,
    (b) bias against rate with the bypass floor and bootstrap intervals,
    (c) the per-frame residual on real music with per-bin intervals,
    (d) the causal experiment: fitted amplitude per seed for the three arms."""
    fig, axes = plt.subplots(1, 4, figsize=(7.6, 2.05),
                             gridspec_kw={"width_ratios": [1.25, 1, 1, 1.05]})
    ax = axes[0]
    runs = [("detune_encodec3", "EnCodec 3 kbps", "enc"), ("codec_mimi", "Mimi", "mimi"),
            ("codec_dac16", "DAC 16k", "dac"), ("mech_bypass", "EnCodec, no quantiser", "grey")]
    gx = np.linspace(0, 100, 300)
    for name, label, ck in runs:
        p = RES / f"{name}.csv"
        if not p.exists():
            continue
        d = load(p)
        theta, rc = d["theta_cents"], d["residual_coded_cents"]
        m = keep_mask(d) & np.isfinite(rc) & np.array(
            [l.endswith("ongrid") for l in d["reference_label"].tolist()])
        amp, ph, _ = fit_sinusoid(theta[m], rc[m])
        ax.plot(gx, amp * np.sin(2 * np.pi * gx / 100 + np.radians(ph)), color=OKABE[ck],
                lw=1.8 if ck != "grey" else 1.8, ls="-" if ck != "grey" else "--",
                label=f"{label} ({amp:.1f}c)")
    ax.axhline(0, color="0.7", lw=0.8)
    ax.set_xlim(0, 100); ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("cents above nearest 12-TET pitch", fontsize=6.4)
    ax.set_ylabel("fitted residual (cents)", fontsize=6.4)
    ax.set_title("(a) residual: same phase, four codecs", fontsize=6.6)
    ax.legend(fontsize=5.2, loc="upper left", frameon=False); ax.tick_params(labelsize=5.6); ax.grid(alpha=0.2)

    ax = axes[1]
    rates, biases, cis = [], [], []
    for kb in ("1.5", "3", "6", "12", "24"):
        p = RES / f"rate_encodec_{kb}.csv"
        if not p.exists():
            continue
        d = load(p); theta, rc = d["theta_cents"], d["residual_coded_cents"]
        m = keep_mask(d) & np.isfinite(rc) & np.array([l.endswith("ongrid") for l in d["reference_label"].tolist()])
        bb = np.sign(grid(theta[m]) - theta[m]) * rc[m]
        rates.append(float(kb)); biases.append(float(np.median(bb))); cis.append(_boot_ci(bb))
    d = load(RES / "mech_bypass.csv"); theta, rc = d["theta_cents"], d["residual_coded_cents"]
    m = keep_mask(d) & np.isfinite(rc) & np.array([l.endswith("ongrid") for l in d["reference_label"].tolist()])
    floor = float(np.median(np.sign(grid(theta[m]) - theta[m]) * rc[m]))
    err = np.array([[b - lo, hi - b] for b, (lo, hi) in zip(biases, cis)]).T
    ax.errorbar(rates, biases, yerr=err, fmt="o-", color=OKABE["enc"], lw=1.6, ms=4.5,
                capsize=2.5, elinewidth=0.9, label="EnCodec 24k, 95% CI")
    ax.axhline(floor, color=OKABE["grey"], ls="--", lw=1.3, label=f"no quantiser ({floor:.2f} c)")
    ax.set_xscale("log"); ax.set_xticks(rates); ax.set_xticklabels([str(r) for r in rates])
    ax.set_ylim(0, 12); ax.set_xlabel("bitrate (kbps)", fontsize=6.4); ax.set_ylabel("grid bias (cents)", fontsize=6.4)
    ax.set_title("(b) bias vs rate, bypass floor", fontsize=6.6)
    ax.legend(fontsize=5.2, frameon=False, loc="upper right"); ax.tick_params(labelsize=5.6); ax.grid(alpha=0.2)

    ax = axes[2]
    # (c) the transfer function on real polyphonic music: binned median residual
    # against input position within the semitone, from corpus_pull.py.
    for name, label, ck, ls in [("corpus_pull_encodec3", "EnCodec 3 kbps, GTZAN", "enc", "-"),
                                ("corpus_pull_saraga_encodec3", "EnCodec 3 kbps, Carnatic", "enc", ":"),
                                ("corpus_pull_dac166", "DAC 16k, GTZAN", "dac", "-"),
                                ("corpus_pull_opus12", "Opus 12 kbps, GTZAN", "grey", "--")]:
        p = RES / f"{name}.csv"
        if not p.exists():
            continue
        rows = list(csv.DictReader(open(p)))
        pos = np.array([float(r["position_cents"]) for r in rows])
        res = np.array([float(r["residual_cents"]) for r in rows])
        din = np.array([float(r["disagreement_in"]) for r in rows])
        dout = np.array([float(r["disagreement_out"]) for r in rows])
        k = (np.nan_to_num(din, nan=1e9) <= 20) & (np.nan_to_num(dout, nan=1e9) <= 20) & (np.abs(res) <= 200)
        pos, res = pos[k], res[k]
        edges = np.arange(0, 101, 10); xs, ys, los, his = [], [], [], []
        for a, b in zip(edges[:-1], edges[1:]):
            m = (pos >= a) & (pos < b)
            if m.sum() > 50:
                lo, hi = _boot_ci(res[m], n_boot=500)
                xs.append(0.5 * (a + b)); ys.append(float(np.median(res[m]))); los.append(lo); his.append(hi)
        ax.fill_between(xs, los, his, color=OKABE[ck], alpha=0.12, lw=0)
        ax.plot(xs, ys, "o-", color=OKABE[ck], ls=ls, lw=1.5, ms=3.2, label=label)
    ax.axhline(0, color="0.7", lw=0.8)
    ax.set_xlim(0, 100); ax.set_xticks([0, 25, 50, 75, 100]); ax.set_ylim(-6, 6)
    ax.set_xlabel("cents above nearest 12-TET pitch", fontsize=6.4)
    ax.set_ylabel("median residual (cents)", fontsize=6.4)
    ax.set_title("(c) real music, per-bin median, 95% CI", fontsize=6.6)
    ax.legend(fontsize=4.6, frameon=False, loc="upper left", handlelength=1.8); ax.tick_params(labelsize=5.6); ax.grid(alpha=0.2)

    ax = axes[3]
    # (d) the causal experiment: fitted amplitude per seed for the three arms.
    arms = [("grid", "original", OKABE["enc"]), ("gridres", "+100 c", OKABE["dac"]),
            ("flat", "flattened", OKABE["spt"])]
    for i, (arm, label, colour) in enumerate(arms):
        amps = []
        for seed in range(3):
            p = RES / f"ftm_{arm}_s{seed}.csv"
            if not p.exists():
                continue
            d = load(p)
            keep = keep_mask(d) & np.isfinite(d["residual_coded_cents"])
            amps.append(float(_phase_regression(d, keep)[2].mean()))
        if not amps:
            continue
        ax.scatter([i] * len(amps), amps, s=14, color=colour, zorder=3)
        ax.errorbar([i], [np.mean(amps)], yerr=[np.std(amps, ddof=1)] if len(amps) > 1 else None,
                    fmt="_", color="black", ms=14, capsize=4, elinewidth=0.9, zorder=4)
        ax.text(i, np.mean(amps) + 0.22, f"{np.mean(amps):.2f}", ha="center", fontsize=5.4)
    ax.set_xticks(range(3)); ax.set_xticklabels([a[1] for a in arms], fontsize=5.6)
    ax.set_xlabel("fine-tuning corpus", fontsize=6.4)
    ax.set_xlim(-0.6, 2.6); ax.set_ylim(3.2, 5.1)
    ax.set_ylabel("residual amplitude (cents)", fontsize=6.4)
    ax.set_title("(d) decoder fine-tuning, 3 seeds", fontsize=6.6)
    ax.tick_params(labelsize=5.6); ax.grid(alpha=0.2, axis="y")
    fig.tight_layout(w_pad=0.6); fig.savefig(FIG / "mechanism.png", dpi=200)
    print("  mechanism.png")


if __name__ == "__main__":
    print("figures:")
    fig_overview(); fig_mechanism(); fig_registration_all(); fig_residual_shape(); fig_rate(); fig_octaves()

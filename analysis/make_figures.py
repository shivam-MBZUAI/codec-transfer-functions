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
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
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


OKABE = {"enc": "#0072B2", "dac": "#E69F00", "mimi": "#009E73", "spt": "#D55E00", "opus": "#CC79A7", "snac": "#CC79A7",
         "grey": "#666666"}


def _save(fig, stem: str, dpi: int = 300) -> None:
    """Vector PDF for the paper plus a PNG preview. Every figure is generated
    at the physical width it occupies on the page, so the font sizes set here
    are the printed font sizes."""
    fig.savefig(FIG / f"{stem}.pdf")
    fig.savefig(FIG / f"{stem}.png", dpi=dpi)
    print(f"  {stem}.pdf")


def _tq(n_points: int) -> float:
    """t quantile for a 95% interval on an OLS slope through n points."""
    from scipy import stats
    return float(stats.t.ppf(0.975, max(n_points - 2, 1)))


def _clip_ci(v, cluster, n_boot=300, seed=0):
    units = np.unique(cluster)
    idx = {u: np.where(cluster == u)[0] for u in units}
    rng = np.random.default_rng(seed)
    meds = []
    for _ in range(n_boot):
        pick = rng.choice(units, units.size, replace=True)
        meds.append(np.median(np.concatenate([v[idx[u]] for u in pick])))
    return float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def _boot_ci(v, n_boot=2000, seed=0):
    from analyze_sweep import bootstrap_median_ci
    return bootstrap_median_ci(np.asarray(v, float), n_boot=n_boot, seed=seed)


def base_reference_mask(d):
    """Trials of the run's base on-grid reference only (440 Hz for the tone
    sweeps), excluding the folded 100-cent reference, so fitted amplitudes
    and R^2 match the on-grid numbers quoted in the text."""
    f1 = d["f1_nominal"]
    offs = (1200.0 * np.log2(f1 / 440.0)) % 100.0
    base = np.round(offs, 3) == 0
    return base & (f1 < f1[base].min() + 0.01)


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
            ("detune_mimi", "Mimi", "mimi"),
            ("detune_dac16", "DAC 16k", "dac"),
            ("mech_bypass", "EnCodec, quantiser removed", "grey")]
    fig, axes = plt.subplots(1, len(runs), figsize=(5.5, 2.1), sharey=True, squeeze=False)
    for ax, (name, label, ck) in zip(axes[0], runs):
        p = RES / f"{name}.csv"
        if not p.exists():
            ax.set_title(f"{label}\n(not measured)", fontsize=6.5); continue
        d = load(p)
        theta, rc = d["theta_cents"], d["residual_coded_cents"]
        m = keep_mask(d) & np.isfinite(rc) & base_reference_mask(d)
        folded = theta[m] % 100.0
        ax.axhline(0, color="0.7", lw=0.8, zorder=1)
        # the cloud is 1,205 trials deep, so keep the marks small and faint
        # and let the binned medians carry the shape
        ax.scatter(folded, rc[m], s=1.6, alpha=0.12, color=OKABE[ck],
                   lw=0, zorder=2)
        edges = np.arange(0, 101, 5)
        bx = [0.5 * (a + b) for a, b in zip(edges[:-1], edges[1:])]
        by = [float(np.median(rc[m][(folded >= a) & (folded < b)]))
              if ((folded >= a) & (folded < b)).sum() > 5 else np.nan
              for a, b in zip(edges[:-1], edges[1:])]
        ax.plot(bx, by, "o", color=OKABE[ck], ms=2.2, mec="white", mew=0.4, zorder=4)
        amp, ph, r2 = fit_sinusoid(theta[m], rc[m])
        gx = np.linspace(0, 100, 300)
        ax.plot(gx, amp * np.sin(2 * np.pi * gx / 100 + np.radians(ph)),
                color="0.15", lw=1.4, zorder=5)
        ax.set_title(f"{label}\namp {amp:.2f} c, $R^2$ {r2:.2f}", fontsize=6.2,
                     color="0.15", linespacing=1.25)
        ax.tick_params(labelsize=6, colors="0.25", length=2.4, width=0.7)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("0.55"); ax.spines[side].set_linewidth(0.8)
        ax.set_xticks([0, 50, 100])
        ax.grid(alpha=0.14, lw=0.6); ax.set_axisbelow(True)
    axes[0][0].set_ylabel("residual (cents)", fontsize=6.5, color="0.2")
    fig.supxlabel("cents above the 12-TET pitch", fontsize=6.8, color="0.2", y=0.03)
    fig.tight_layout(rect=[0, 0.04, 1, 1]); _save(fig, "residual_shape")


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

    fig, ax = plt.subplots(figsize=(3.4, 2.4))
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
    ax.set_title("Grid bias against bitrate, EnCodec 24 kHz", fontsize=7.5)
    ax.tick_params(labelsize=7); ax.xaxis.label.set_size(7.5); ax.yaxis.label.set_size(7.5)
    ax.legend(fontsize=6.5); ax.grid(alpha=0.25)
    fig.tight_layout(); _save(fig, "rate_scaling")


def fig_octaves():
    p = RES / "octaves_encodec3.csv"
    if not p.exists():
        return
    d = load(p)
    theta, rc = d["theta_cents"], d["residual_coded_cents"]
    labels = d["reference_label"]
    refs = sorted(set(labels.tolist()), key=lambda s: float(s.split("Hz")[0]))
    fig, axes = plt.subplots(1, len(refs), figsize=(5.5, 2.1),
                             sharey=True, squeeze=False)
    for ax, lab in zip(axes[0], refs):
        m = (labels == lab) & keep_mask(d) & np.isfinite(rc)
        amp, ph, r2 = fit_sinusoid(theta[m], rc[m])
        folded = theta[m] % 100.0
        ax.axhline(0, color="0.7", lw=0.8, zorder=1)
        ax.scatter(folded, rc[m], s=1.6, alpha=0.10, color=OKABE["enc"],
                   lw=0, zorder=2)
        edges = np.arange(0, 101, 5)
        bx = [0.5 * (a + b) for a, b in zip(edges[:-1], edges[1:])]
        by = [float(np.median(rc[m][(folded >= a) & (folded < b)]))
              if ((folded >= a) & (folded < b)).sum() > 5 else np.nan
              for a, b in zip(edges[:-1], edges[1:])]
        ax.plot(bx, by, "o", color=OKABE["enc"], ms=2.2, mec="white", mew=0.4, zorder=4)
        gx = np.linspace(0, 100, 300)
        ax.plot(gx, amp * np.sin(2 * np.pi * gx / 100 + np.radians(ph)),
                color="0.15", lw=1.4, zorder=5)
        weak = " (weak fit)" if r2 < 0.1 else ""
        ax.set_title(f"{lab.split('Hz')[0]} Hz\n$A$ = {amp:.1f} c, $\\varphi$ = {ph:.0f}°"
                     f"\n$R^2$ = {r2:.2f}{weak}", fontsize=6.0, color="0.15",
                     linespacing=1.25)
        ax.tick_params(labelsize=6, colors="0.25", length=2.4, width=0.7)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("0.55"); ax.spines[side].set_linewidth(0.8)
        ax.set_xticks([0, 50, 100])
        ax.grid(alpha=0.14, lw=0.6); ax.set_axisbelow(True)
    axes[0][0].set_ylabel("residual (cents)", fontsize=6.5, color="0.2")
    fig.supxlabel("cents above the 12-TET pitch", fontsize=6.8, color="0.2", y=0.03)
    fig.tight_layout(rect=[0, 0.04, 1, 1]); _save(fig, "octaves")


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

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(5.5, 1.45),
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
                fontsize=6.5, ha="center",
                arrowprops=dict(arrowstyle="->", lw=0.8, color="0.3"))
    ax.annotate("pulled down toward\nprevious semitone", xy=(30, -13), xytext=(50, -44),
                fontsize=6.5, ha="center",
                arrowprops=dict(arrowstyle="->", lw=0.8, color="0.3"))
    ax.set_xlim(0, 100); ax.set_ylim(-55, 55)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("cents above nearest 12-TET pitch", fontsize=8)
    ax.set_ylabel("residual (cents)", fontsize=8)
    ax.set_title("(a) folded residual, EnCodec 3 kbps", fontsize=7.5)
    ax.tick_params(labelsize=7); ax.grid(alpha=0.2)

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
    ax2.axhline(0, color="0.55", ls=":", lw=1.2, label="slope 0: interval")
    ax2.plot(offs, phases, "o", color="black", ms=3.5, label="measured")
    ax2.set_xlim(-3, 100); ax2.set_ylim(-20, 460)
    ax2.set_xlabel("reference detuning (cents)", fontsize=8)
    ax2.set_ylabel("phase shift (deg)", fontsize=8)
    ax2.set_title("(b) phase against detuning",
                  fontsize=8)
    ax2.legend(fontsize=6.5, loc="upper left", frameon=False); ax2.tick_params(labelsize=7); ax2.grid(alpha=0.2)
    fig.tight_layout(w_pad=0.4); _save(fig, "overview")
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
    """Every measurable registration condition, one panel each (appendix).

    Five columns by two rows fills the grid exactly, and the markers are
    coloured by codec family so the reader can group the panels without
    reading ten titles. Slopes and intervals are in Table A7; the titles
    carry only what the eye needs to sort the panels.
    """
    runs = [("detune_encodec3", "EnCodec 24k, 3 kbps", "enc"),
            ("detune_encodec24kbps", "EnCodec 24k, 24 kbps", "enc"),
            ("detune_encodec48", "EnCodec 48k, 6 kbps", "enc"),
            ("detune_vowel_encodec", "EnCodec 24k, vowels", "enc"),
            ("detune_mimi", "Mimi", "mimi"),
            ("detune_vowel_speechtok", "SpeechTokenizer, vowels", "spt"),
            ("detune_dac16", "DAC 16k", "dac"),
            ("detune_dac24", "DAC 24k", "dac"),
            ("detune_snac32", "SNAC 32k", "snac"),
            ("detune_snac44", "SNAC 44k", "snac")]
    fig, axes = plt.subplots(2, 5, figsize=(5.5, 2.7), sharey=True, sharex=True)
    for ax, (name, label, ck) in zip(axes.ravel(), runs):
        col = OKABE.get(ck, "black")
        p = RES / f"{name}.csv"
        if not p.exists():
            ax.set_title(f"{label}\n(not measured)", fontsize=5.8); continue
        d = load(p)
        keep = keep_mask(d) & np.isfinite(d["residual_coded_cents"])
        offs, phases, amps, rel, lo, hi = _phase_regression(d, keep)
        ax.plot([0, 100], [0, 360], color="0.62", ls="--", lw=1.0, zorder=1)
        ax.axhline(0, color="0.62", ls=":", lw=1.0, zorder=1)
        ax.plot(offs, phases, "o", color=col, ms=2.6, mec="white", mew=0.4, zorder=3)
        ax.set_title(f"{label}\n$\\sigma$ = {rel:.3f}, A = {amps.mean():.2f} c",
                     fontsize=5.6, color="0.15", linespacing=1.25)
        ax.set_xlim(-3, 100); ax.set_ylim(-25, 375)
        ax.tick_params(labelsize=5.5, colors="0.25", length=2.2, width=0.7)
        ax.grid(alpha=0.14, lw=0.6); ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("0.55"); ax.spines[side].set_linewidth(0.8)
        ax.set_xticks([0, 50, 100]); ax.set_yticks([0, 180, 360])
    fig.supxlabel("reference detuning (cents)", fontsize=6.8, color="0.2", y=0.02)
    fig.supylabel("phase shift (deg)", fontsize=6.8, color="0.2", x=0.015)
    axes[0, 0].annotate("slope 1: absolute pitch", xy=(72, 260), xytext=(8, 330),
                        fontsize=5.0, color="0.35",
                        arrowprops=dict(arrowstyle="-", color="0.6", lw=0.5))
    axes[0, 0].annotate("slope 0: the interval", xy=(60, 0), xytext=(8, 95),
                        fontsize=5.0, color="0.35",
                        arrowprops=dict(arrowstyle="-", color="0.6", lw=0.5))
    fig.tight_layout(h_pad=0.9, w_pad=0.5); 
    fig.tight_layout(h_pad=0.6, w_pad=0.4); _save(fig, "registration_all")


def _hist(path):
    rows = list(csv.DictReader(open(path)))
    lo = np.array([float(r["bin_lo_cents"]) for r in rows]); hi = np.array([float(r["bin_hi_cents"]) for r in rows])
    dens = np.array([float(r["density"]) for r in rows]); dens = dens / dens.mean()
    return 0.5 * (lo + hi), dens


def _arm_amps(arm):
    """Fitted residual amplitude per seed for one fine-tuning arm."""
    amps = []
    for seed in range(5):
        p = RES / f"ftm_{arm}_s{seed}.csv"
        if not p.exists():
            continue
        d = load(p)
        keep = keep_mask(d) & np.isfinite(d["residual_coded_cents"])
        amps.append(float(_phase_regression(d, keep)[2].mean()))
    return amps


def fig_mechanism():
    """Main-text Figure 4.

    (a) the residual over one semitone for three codecs and the bypass;
    (b) the same reading on whole polyphonic clips, on the SAME y axis, so
        that "a fifth as large" is something the reader sees rather than
        something the text asserts;
    (c) the causal experiment as a decomposition of the stock amplitude
        into the part any fine-tuning removes, the part the corpus's tuning
        removes, and the part that survives both.
    """
    fig, axes = plt.subplots(1, 2, figsize=(5.5, 1.80),
                             gridspec_kw={"width_ratios": [1.0, 1.0]})
    axes = list(axes)
    for a_ in axes:
        for side in ("top", "right"):
            a_.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            a_.spines[side].set_color("0.55"); a_.spines[side].set_linewidth(0.8)
        a_.tick_params(labelsize=6.2, colors="0.25", length=2.5, width=0.7)
        a_.set_axisbelow(True)

    YLIM = (-24, 34)
    gx = np.linspace(0, 100, 300)

    # ---- (a) synthetic tones ---------------------------------------------
    ax = axes[0]
    runs = [("detune_encodec3", "EnCodec 3k", "enc"), ("mech_bypass", "bypass", "grey"),
            ("detune_mimi", "Mimi", "mimi"), ("detune_dac16", "DAC 16k", "dac")]
    for name, label, ck in runs:
        p_ = RES / f"{name}.csv"
        if not p_.exists():
            continue
        d = load(p_)
        theta, rc = d["theta_cents"], d["residual_coded_cents"]
        m = keep_mask(d) & np.isfinite(rc) & base_reference_mask(d)
        amp, ph, r2 = fit_sinusoid(theta[m], rc[m])
        fold = theta[m] % 100.0
        edges = np.arange(0, 101, 5)
        bx = [0.5 * (a + b) for a, b in zip(edges[:-1], edges[1:])]
        by = [float(np.median(rc[m][(fold >= a) & (fold < b)])) if ((fold >= a) & (fold < b)).sum() > 5 else np.nan
              for a, b in zip(edges[:-1], edges[1:])]
        ax.plot(bx, by, "o", color=OKABE[ck], ms=1.6, alpha=0.45, zorder=2)
        yfit = amp * np.sin(2 * np.pi * gx / 100 + np.radians(ph))
        ax.plot(gx, yfit, color=OKABE[ck], lw=1.5,
                ls="-" if ck != "grey" else "--", zorder=3)
        ax.plot([], [], color=OKABE[ck], lw=1.5,
                ls="-" if ck != "grey" else "--", label=label)
    ax.axhline(0, color="0.7", lw=0.8)
    ax.set_xlim(0, 100); ax.set_xticks([0, 50, 100]); ax.set_ylim(*YLIM)
    ax.set_yticks([-20, -10, 0, 10, 20])
    ax.set_xlabel("cents above the 12-TET pitch", fontsize=6.8, color="0.2")
    ax.set_ylabel("residual (cents)", fontsize=6.8, color="0.2")
    ax.set_title("(a) synthetic tones", fontsize=7, loc="left", color="0.12")
    ax.legend(fontsize=5.4, loc="upper left", frameon=True, framealpha=0.95,
              edgecolor="none", facecolor="white", handlelength=1.3,
              labelspacing=0.2, borderpad=0.3)
    ax.grid(alpha=0.13, lw=0.6)

    # ---- (b) real music, on the same scale --------------------------------
    ax = axes[1]
    for name, label, ck, ls, mk in [("corpus_pull_encodec3", "EnCodec, GTZAN", "enc", "-", "o"),
                                    ("corpus_pull_saraga_encodec3", "EnCodec, Carnatic", "enc", ":", "^"),
                                    ("corpus_pull_dac166", "DAC 16k", "dac", "-", "s"),
                                    ("corpus_pull_opus12", "Opus 12k", "opus", "--", "D")]:
        p_ = RES / f"{name}.csv"
        if not p_.exists():
            continue
        rows = list(csv.DictReader(open(p_)))
        pos = np.array([float(r["position_cents"]) for r in rows])
        res = np.array([float(r["residual_cents"]) for r in rows])
        din = np.array([float(r["disagreement_in"]) for r in rows])
        dout = np.array([float(r["disagreement_out"]) for r in rows])
        files = np.array([r["file"] for r in rows])
        k = (np.nan_to_num(din, nan=1e9) <= 20) & (np.nan_to_num(dout, nan=1e9) <= 20) & (np.abs(res) <= 200)
        pos, res, files = pos[k], res[k], files[k]
        edges = np.arange(0, 101, 10); xs, ys, los, his = [], [], [], []
        for a, b in zip(edges[:-1], edges[1:]):
            m = (pos >= a) & (pos < b)
            if m.sum() > 50:
                lo, hi = _clip_ci(res[m], files[m])
                xs.append(0.5 * (a + b)); ys.append(float(np.median(res[m])))
                los.append(lo); his.append(hi)
        ax.fill_between(xs, los, his, color=OKABE[ck], alpha=0.16, lw=0)
        ax.plot(xs, ys, marker=mk, color=OKABE[ck], ls=ls, lw=1.2, ms=2.4,
                mec="white", mew=0.4, label=label)
    ax.axhline(0, color="0.7", lw=0.8)
    ax.set_xlim(0, 100); ax.set_xticks([0, 50, 100]); ax.set_ylim(*YLIM)
    ax.set_yticks([-20, -10, 0, 10, 20]); ax.set_yticklabels([])
    ax.set_xlabel("cents above the 12-TET pitch", fontsize=6.8, color="0.2")
    ax.set_title("(b) real music, same scale", fontsize=7, loc="left", color="0.12")
    ax.legend(fontsize=5.4, loc="upper left", frameon=True, framealpha=0.95,
              edgecolor="none", facecolor="white", handlelength=1.3,
              labelspacing=0.2, borderpad=0.3)
    ax.grid(alpha=0.13, lw=0.6)

    fig.tight_layout(w_pad=1.4)
    _save(fig, "mechanism")


if __name__ == "__main__":
    print("figures:")
    fig_overview(); fig_mechanism(); fig_registration_all(); fig_residual_shape(); fig_rate(); fig_octaves()

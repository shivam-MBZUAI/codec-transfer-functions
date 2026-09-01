"""Turn a sweep CSV into the go/no-go answer.

    python analyze_sweep.py ../results/pilot_encodec3.csv --fig ../figures/pilot.png

Reports, per reference condition:

  noise floor          median |residual| on uncoded stimuli, same trials
  on/off-grid error    median |residual| for |theta - g(theta)| <= 10 and >= 30
  grid bias            median of sign(g(theta) - theta) * residual
  sinusoid fit         amplitude, period, phase of the best single sinusoid
  sawtooth fit         amplitude and phase of the best 100-cent sawtooth

The last two are the discriminating test, and they are why this script fits
both shapes rather than assuming one. A Bennett-type density correction (the
paper's Proposition 1) predicts a SINUSOID. Coarse cell assignment, where the
codebook simply has a reconstruction level near each grid point, predicts a
SAWTOOTH. Both produce "period 100 cents, zero at grid points, negative just
above", so reporting only that the residual is periodic cannot tell them apart.
Whichever fits better is the mechanism, and they scale differently with rate
(sawtooth ~ Delta, sinusoid ~ Delta**2), so getting this wrong flips the
predicted C3 slope from -1 to -2.

The phase-shift test between reference conditions is printed last. It is the
one that decides whether the paper exists.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

PERIOD = 100.0
DISAGREE_CENTS = 5.0


def grid(theta: np.ndarray) -> np.ndarray:
    return PERIOD * np.round(theta / PERIOD)


def load(path: Path) -> dict:
    cols = defaultdict(list)
    with path.open() as fh:
        for row in csv.DictReader(fh):
            for k, v in row.items():
                if k == "reference_label":
                    cols[k].append(v)
                else:
                    try:
                        cols[k].append(float(v))
                    except ValueError:
                        cols[k].append(float("nan"))
    return {k: (np.array(v) if k != "reference_label" else np.array(v, dtype=object))
            for k, v in cols.items()}


def fit_sinusoid(theta: np.ndarray, r: np.ndarray) -> tuple[float, float, float]:
    """Least squares fit of a*sin(2pi*theta/100) + b*cos(...). Returns
    (amplitude, phase in degrees, fraction of variance explained)."""
    w = 2.0 * math.pi / PERIOD
    design = np.column_stack([np.sin(w * theta), np.cos(w * theta), np.ones_like(theta)])
    coef, *_ = np.linalg.lstsq(design, r, rcond=None)
    pred = design @ coef
    amp = float(math.hypot(coef[0], coef[1]))
    phase = float(math.degrees(math.atan2(coef[1], coef[0])))
    ss_tot = float(np.sum((r - r.mean()) ** 2))
    r2 = 1.0 - float(np.sum((r - pred) ** 2)) / ss_tot if ss_tot > 0 else float("nan")
    return amp, phase, r2


def fit_sawtooth(theta: np.ndarray, r: np.ndarray) -> tuple[float, float, float]:
    """Fit s * (g(theta + phi) - (theta + phi)) over a grid of phase offsets.
    Returns (peak amplitude, best phase offset in cents, variance explained)."""
    best = (float("nan"), float("nan"), -np.inf)
    ss_tot = float(np.sum((r - r.mean()) ** 2))
    for phi in np.arange(-50.0, 50.0, 0.5):
        shifted = theta + phi
        basis = grid(shifted) - shifted
        design = np.column_stack([basis, np.ones_like(theta)])
        coef, *_ = np.linalg.lstsq(design, r, rcond=None)
        pred = design @ coef
        r2 = 1.0 - float(np.sum((r - pred) ** 2)) / ss_tot if ss_tot > 0 else float("nan")
        if r2 > best[2]:
            best = (float(abs(coef[0]) * 50.0), float(phi), r2)
    return best


def bootstrap_median_ci(v: np.ndarray, n_boot: int = 4000, seed: int = 0
                        ) -> tuple[float, float]:
    """Percentile bootstrap CI for the MEDIAN, resampling trials with
    replacement. This is not the same thing as the 2.5/97.5 percentiles of the
    values themselves: those describe how spread the per-trial biases are, and
    are wide by construction even when the median is pinned down. Reporting the
    latter as a confidence interval would overstate the uncertainty on the
    quantity actually being claimed."""
    v = v[np.isfinite(v)]
    if v.size < 8:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, v.size, size=(n_boot, v.size))
    meds = np.median(v[idx], axis=1)
    return float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def summarise(theta, r_coded, r_uncoded, keep, label: str) -> dict:
    dist_all = np.abs(theta - grid(theta))
    ok = np.isfinite(r_coded) & np.isfinite(theta) & keep

    # An exclusion rule that fired more often off-grid would manufacture the
    # effect on its own, so the correlation between exclusion and grid distance
    # is reported, not assumed away.
    excl_corr = float("nan")
    if 0 < (~ok).sum() < len(ok):
        excl_corr = float(np.corrcoef(dist_all, (~ok).astype(float))[0, 1])
    excl_rate = 100.0 * float((~ok).mean())

    theta, r_coded = theta[ok], r_coded[ok]
    dist = dist_all[ok]
    floor = float(np.median(np.abs(r_uncoded[np.isfinite(r_uncoded)])))

    on, off = dist <= 10.0, dist >= 30.0
    bias = np.sign(grid(theta) - theta) * r_coded

    sin_amp, sin_phase, sin_r2 = fit_sinusoid(theta, r_coded)
    saw_amp, saw_phase, saw_r2 = fit_sawtooth(theta, r_coded)

    return dict(
        label=label, n=int(ok.sum()), floor=floor,
        excl_rate=excl_rate, excl_corr=excl_corr,
        on_grid=float(np.median(np.abs(r_coded[on]))) if on.any() else float("nan"),
        off_grid=float(np.median(np.abs(r_coded[off]))) if off.any() else float("nan"),
        bias=float(np.median(bias)),
        bias_ci=bootstrap_median_ci(bias),
        bias_spread=(float(np.percentile(bias, 2.5)), float(np.percentile(bias, 97.5))),
        sin_amp=sin_amp, sin_phase=sin_phase, sin_r2=sin_r2,
        saw_amp=saw_amp, saw_phase=saw_phase, saw_r2=saw_r2,
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv", type=Path)
    p.add_argument("--fig", type=Path, default=None)
    p.add_argument("--exclusion", choices=["full", "gate", "none"], default="full",
                   help="full: octave gate AND estimator cross-check (default). "
                        "gate: octave gate only, for codecs where one coarse "
                        "estimator fails systematically while the reported "
                        "estimate stays accurate. none: no exclusions.")
    args = p.parse_args()

    d = load(args.csv)
    theta = d["theta_cents"]
    r_coded = d["residual_coded_cents"]
    r_uncoded = d["residual_uncoded_cents"]
    labels = d["reference_label"]

    # Trials the estimator could not be trusted on. Recorded by run_sweep.py,
    # applied here, and reported rather than silently dropped.
    disagree = np.maximum(np.abs(d.get("disagreement_f1_cents", np.zeros_like(theta))),
                          np.abs(d.get("disagreement_f2_cents", np.zeros_like(theta))))
    keep = np.ones_like(theta, dtype=bool)
    if args.exclusion in ("full", "gate") and "octave_flag" in d:
        keep &= d["octave_flag"] < 0.5
    if args.exclusion == "full":
        keep &= np.nan_to_num(disagree, nan=1e9) <= DISAGREE_CENTS
    if args.exclusion != "full":
        print(f"  [exclusion scheme: {args.exclusion}] "
              f"{100 * (1 - keep.mean()):.1f}% of trials dropped")

    results = []
    for label in sorted(set(labels.tolist())):
        m = labels == label
        results.append(summarise(theta[m], r_coded[m], r_uncoded[m], keep[m], label))

    for s in results:
        # A ratio of near-zero over near-zero is noise, not an effect.
        ratio = (s["off_grid"] / s["on_grid"]
                 if s["on_grid"] > max(3.0 * s["floor"], 1e-9) else float("nan"))
        print(f"\n=== {s['label']}  (n={s['n']}) ===")
        print(f"  estimator noise floor      {s['floor']:8.3f} cents")
        corr = ("n/a" if not np.isfinite(s["excl_corr"])
                else f"{s['excl_corr']:+.3f}")
        print(f"  excluded trials            {s['excl_rate']:7.1f}%   "
              f"corr with grid distance {corr}")
        print(f"  median |r| on-grid         {s['on_grid']:8.3f} cents")
        print(f"  median |r| off-grid        {s['off_grid']:8.3f} cents   ratio {ratio:.2f}x")
        print(f"  grid bias b (median)       {s['bias']:8.3f} cents   "
              f"95% CI [{s['bias_ci'][0]:.2f}, {s['bias_ci'][1]:.2f}]  "
              f"(per-trial spread [{s['bias_spread'][0]:.1f}, {s['bias_spread'][1]:.1f}])")
        print(f"  sinusoid fit  amp {s['sin_amp']:6.2f}c  phase {s['sin_phase']:+7.1f} deg"
              f"  R2 {s['sin_r2']:.3f}")
        print(f"  sawtooth fit  amp {s['saw_amp']:6.2f}c  phase {s['saw_phase']:+7.1f}c"
              f"  R2 {s['saw_r2']:.3f}")
        better = "sawtooth" if s["saw_r2"] > s["sin_r2"] else "sinusoid"
        print(f"  -> better fit: {better}")

    if len(results) >= 2:
        a, b = results[0], results[1]
        print("\n=== detuned-reference test ===")
        # Phase is undefined when there is no oscillation to take the phase of.
        # Without this guard the test reports a confident, meaningless angle on
        # pure noise, which is the most dangerous possible failure mode here.
        weak = [r["label"] for r in (a, b)
                if not (r["sin_amp"] > 3.0 * r["floor"] and r["sin_r2"] > 0.2)]
        if weak:
            print("  UNDEFINED: no significant oscillation to take a phase of "
                  f"({', '.join(weak)}).")
            print("  A phase difference is only meaningful once the sinusoid fit "
                  "clears 3x the noise floor with R2 > 0.2.")
        else:
            shift = (b["sin_phase"] - a["sin_phase"]) % 360.0
            print(f"  phase({b['label']}) - phase({a['label']}) = {shift:.1f} deg")
            print("  ~180 deg: residual is locked to an absolute learned grid, "
                  "which is the paper's claim.")
            print("  ~0 deg:   residual is locked to the interval, i.e. an "
                  "analysis artefact, and the framing dies here.")

    strongest = max(results, key=lambda s: abs(s["bias"]))
    print("\n=== gate ===")
    if abs(strongest["bias"]) < 3.0 * strongest["floor"]:
        print("  NULL: grid bias does not clear 3x the estimator noise floor.")
        print("  Per PREDICTIONS.md, do not attempt to rescue the microtonal framing.")
    else:
        print(f"  Grid bias {strongest['bias']:.2f} cents clears the "
              f"{strongest['floor']:.2f} cent floor. Proceed, and check the phase test above.")

    if args.fig:
        _plot(theta, r_coded, r_uncoded, labels, results, keep, args.fig)
        print(f"\nwrote {args.fig}")


def _plot(theta, r_coded, r_uncoded, labels, results, keep, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    uniq = sorted(set(labels.tolist()))
    fig, axes = plt.subplots(1, len(uniq), figsize=(5.5 * len(uniq), 3.6), squeeze=False)
    floor = float(np.median(np.abs(r_uncoded[np.isfinite(r_uncoded)])))

    for ax, label, s in zip(axes[0], uniq, results):
        m = (labels == label) & np.isfinite(r_coded) & keep
        folded = theta[m] % PERIOD
        ax.axhspan(-floor, floor, color="0.85", zorder=0, label="estimator floor")
        ax.axhline(0, color="0.5", lw=0.7)
        ax.scatter(folded, r_coded[m], s=5, alpha=0.45, color="#0072B2", zorder=2)
        grid_x = np.linspace(0, PERIOD, 400)
        w = 2 * np.pi / PERIOD
        ax.plot(grid_x, s["sin_amp"] * np.sin(w * grid_x + np.radians(s["sin_phase"])),
                color="#D55E00", lw=1.6, label=f"sinusoid R2={s['sin_r2']:.2f}")
        shifted = grid_x + s["saw_phase"]
        ax.plot(grid_x, (s["saw_amp"] / 50.0) * (grid(shifted) - shifted),
                color="#009E73", lw=1.6, ls="--", label=f"sawtooth R2={s['saw_r2']:.2f}")
        ax.set_title(label, fontsize=10)
        ax.set_xlabel("theta mod 100 (cents from grid point)")
        ax.legend(fontsize=7, loc="upper right")
    axes[0][0].set_ylabel("residual (cents)")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=180)


if __name__ == "__main__":
    main()

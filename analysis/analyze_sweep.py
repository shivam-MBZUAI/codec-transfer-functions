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

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "experiments", _ROOT / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


PERIOD = 100.0
DISAGREE_CENTS = 5.0


def grid(theta: np.ndarray) -> np.ndarray:
    # Half-to-even at the midpoint, so theta = 50 and 150 round to 0 and 200.
    # At |delta| = 50 the tone is equidistant from two grid points and the
    # direction "toward the grid" is a convention, not a fact; Section 2.2
    # says so, and those trials are 5% of a sweep. Every reported number uses
    # this rounding, so do not change it without regenerating the results.
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
    return fit_sinusoid_se(theta, r)[:3]


def fit_sinusoid_se(theta: np.ndarray, r: np.ndarray
                    ) -> tuple[float, float, float, float]:
    """fit_sinusoid plus the standard error of the phase, in degrees.

    The fit is OLS on [sin, cos, 1], so the coefficient covariance is
    sigma^2 (X'X)^-1 with sigma^2 the residual variance on n-3 degrees of
    freedom. The phase is atan2(b, a); its gradient in (a, b) is
    (-b, a) / (a^2 + b^2), and the delta method gives var(phase) = g' Cov g."""
    ok = np.isfinite(theta) & np.isfinite(r)
    theta, r = theta[ok], r[ok]
    if r.size < 3:
        return float("nan"), float("nan"), float("nan"), float("nan")
    w = 2.0 * math.pi / PERIOD
    design = np.column_stack([np.sin(w * theta), np.cos(w * theta), np.ones_like(theta)])
    with np.errstate(all="ignore"):   # Accelerate BLAS warns on some shapes; the values are finite
        with np.errstate(all="ignore"):
            coef, *_ = np.linalg.lstsq(design, r, rcond=None)
            pred = design @ coef
    amp = float(math.hypot(coef[0], coef[1]))
    phase = float(math.degrees(math.atan2(coef[1], coef[0])))
    ss_tot = float(np.sum((r - r.mean()) ** 2))
    ss_res = float(np.sum((r - pred) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    phase_se = float("nan")
    if r.size > 3 and amp > 0:
        cov = ss_res / (r.size - 3) * np.linalg.inv(design.T @ design)
        g = np.array([-coef[1], coef[0]]) / (amp * amp)
        phase_se = float(math.degrees(math.sqrt(g @ cov[:2, :2] @ g)))
    return amp, phase, r2, phase_se


def fit_sawtooth(theta: np.ndarray, r: np.ndarray) -> tuple[float, float, float]:
    """Fit s * (g(theta + phi) - (theta + phi)) over a grid of phase offsets.
    Returns (peak amplitude, best phase offset in cents, variance explained)."""
    best = (float("nan"), float("nan"), -np.inf)
    ok = np.isfinite(theta) & np.isfinite(r)
    theta, r = theta[ok], r[ok]
    if r.size < 3:
        return best
    ss_tot = float(np.sum((r - r.mean()) ** 2))
    for phi in np.arange(-50.0, 50.0, 0.5):
        shifted = theta + phi
        basis = grid(shifted) - shifted
        design = np.column_stack([basis, np.ones_like(theta)])
        with np.errstate(all="ignore"):
            coef, *_ = np.linalg.lstsq(design, r, rcond=None)
            pred = design @ coef
        r2 = 1.0 - float(np.sum((r - pred) ** 2)) / ss_tot if ss_tot > 0 else float("nan")
        if r2 > best[2]:
            best = (float(abs(coef[0]) * 50.0), float(phi), r2)
    return best


def bootstrap_medians(v: np.ndarray, n_boot: int = 4000, seed: int = 0) -> np.ndarray:
    """Bootstrap draws of the MEDIAN, resampling trials with replacement.
    Returned as an array so that intervals at several levels (the 95% one and
    the Bonferroni-adjusted one) come from the same draws. Empty when there
    are too few trials for a median to mean anything."""
    v = v[np.isfinite(v)]
    if v.size < 8:
        return np.array([])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, v.size, size=(n_boot, v.size))
    return np.median(v[idx], axis=1)


def percentile_ci(draws: np.ndarray, level: float = 0.95) -> tuple[float, float]:
    """Two-sided percentile interval of bootstrap draws at the given level."""
    if draws.size == 0:
        return float("nan"), float("nan")
    tail = (100.0 - 100.0 * level) / 2.0
    return float(np.percentile(draws, tail)), float(np.percentile(draws, 100.0 - tail))


def bootstrap_median_ci(v: np.ndarray, n_boot: int = 4000, seed: int = 0,
                        level: float = 0.95) -> tuple[float, float]:
    """Percentile bootstrap CI for the MEDIAN, resampling trials with
    replacement. This is not the same thing as the 2.5/97.5 percentiles of the
    values themselves: those describe how spread the per-trial biases are, and
    are wide by construction even when the median is pinned down. Reporting the
    latter as a confidence interval would overstate the uncertainty on the
    quantity actually being claimed."""
    return percentile_ci(bootstrap_medians(v, n_boot, seed), level)


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
    p.add_argument("--exclusion", choices=["full", "gate", "none"], default="gate",
                   help="gate: octave gate only (default, and the scheme every "
                        "number in the paper uses). The gate removes no trial of the "
                        "headline run, under 10% on most reported runs and 65% on "
                        "DAC 16k, whose slope survives with --exclusion=none; "
                        "guard_sensitivity.py lists every run. full: additionally drop trials on which the two "
                        "independent estimators disagree; reported as a "
                        "robustness variant, since that rule fires preferentially "
                        "30 to 50 cents from a grid point. none: no exclusions.")
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

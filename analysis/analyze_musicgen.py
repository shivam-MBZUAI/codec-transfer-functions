"""Summarise musicgen_pull.py output.

text mode:     pools every per-frame within-semitone position over all
               generated clips and reports the density's peak-to-mean ratio
               (GTZAN gives 1.788, a flat density sampled at this size about
               1.05), the circular-mean position of the peak relative to A440,
               and the circular concentration.
continue mode: regresses the continuation's tuning offset on the prompt's
               known offset d. The offsets are circular (period 100 cents), so
               the fit is done on the residual (out - d) mod 100 folded into
               (-50, 50]: a continuation that keeps the prompt's tuning gives
               residuals near 0; one that re-grids to 12-TET gives residuals
               near -d, i.e. out near 0 regardless of d. The slope of out on d
               is fitted by least squares after unwrapping out around d.

    python analyze_musicgen.py ../results/musicgen_text.csv
    python analyze_musicgen.py ../results/musicgen_continue.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
from scipy import stats


def fold(x):
    return ((np.asarray(x) + 50.0) % 100.0) - 50.0


def main() -> int:
    rows = list(csv.DictReader(Path(sys.argv[1]).open()))
    mode = rows[0]["mode"]
    pos_all = np.concatenate([np.array([float(v) for v in r["positions"].split(";") if v])
                              for r in rows if r["positions"]])
    hist, _ = np.histogram(pos_all, bins=50, range=(0, 100), density=True)
    ratio = hist.max() / hist.mean()
    ang = 2 * np.pi * pos_all / 100.0
    c, s = np.cos(ang).mean(), np.sin(ang).mean()
    peak = (np.degrees(np.arctan2(s, c)) % 360) / 3.6
    R = float(np.hypot(c, s))
    rng = np.random.default_rng(0)
    null = np.mean([np.bincount(rng.integers(0, 50, pos_all.size), minlength=50).max() /
                    (pos_all.size / 50) for _ in range(200)])
    # density CSV in the format of pitch_histogram.py, for plot_histograms.py
    out_csv = Path(sys.argv[1]).with_name(f"hist_{Path(sys.argv[1]).stem}.csv")
    edges = np.linspace(0, 100, 51)
    with out_csv.open("w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["bin_lo_cents", "bin_hi_cents", "density"])
        for lo, hi, dd in zip(edges[:-1], edges[1:], hist):
            w.writerow([f"{lo:.2f}", f"{hi:.2f}", f"{dd:.6f}"])
    print(f"  {len(rows)} clips, {pos_all.size} F0 estimates  (density written to {out_csv.name})")
    print(f"  within-semitone density: peak/mean {ratio:.3f}  (flat-sampling expectation {null:.3f}; GTZAN 1.788)")
    print(f"  circular mean position {peak:.1f} cents above the 12-TET pitch below, resultant length {R:.3f}")
    if mode == "text":
        per = np.array([float(r["resultant"]) for r in rows])
        print(f"  per-clip concentration: median resultant {np.median(per):.2f}, "
              f"{100*np.mean(per > 0.5):.0f}% of clips above 0.5")
        return 0
    d = np.array([float(r["offset_cents"]) for r in rows])
    out = np.array([float(r["out_offset_cents"]) for r in rows])
    pm = np.array([float(r["prompt_offset_measured"]) for r in rows])
    res_c = np.array([float(r["resultant"]) for r in rows])
    ok = np.isfinite(out) & np.isfinite(d)
    d, out, pm, res_c = d[ok], out[ok], pm[ok], res_c[ok]
    # The prompt's tuning is its own offset plus the shift d (GTZAN clips are
    # not exactly on the grid), so the reference is the prompt as READ by the
    # same estimator, pm, not d; d is reported for the record.
    print(f"  median |measured prompt offset - d| folded = {np.median(np.abs(fold(pm - d))):.1f} cents "
          f"(the clips' own tuning offsets)")
    rel = fold(out - pm)         # continuation relative to the prompt's measured tuning
    absr = fold(out)             # continuation relative to the 12-TET grid
    print(f"  continuation offset relative to prompt: median {np.median(rel):+.1f} cents, "
          f"IQR [{np.percentile(rel, 25):+.1f}, {np.percentile(rel, 75):+.1f}]")
    print(f"  continuation offset relative to grid:   median {np.median(absr):+.1f} cents, "
          f"IQR [{np.percentile(absr, 25):+.1f}, {np.percentile(absr, 75):+.1f}]")
    def slope_fit(x, y):
        # unwrap y around x, then ordinary least squares
        un = x + fold(y - x)
        A = np.vstack([x, np.ones_like(x)]).T
        sl, ic = np.linalg.lstsq(A, un, rcond=None)[0]
        pred = A @ [sl, ic]
        ss = ((un - pred) ** 2).sum(); tot = ((un - un.mean()) ** 2).sum()
        se = np.sqrt(ss / max(len(x) - 2, 1) / ((x - x.mean()) ** 2).sum())
        tq = stats.t.ppf(0.975, max(len(x) - 2, 1))
        return sl, sl - tq * se, sl + tq * se, 1 - ss / tot if tot else float("nan")
    pres = np.array([float(r["prompt_resultant"]) for r in rows])[ok]
    # A linear slope of continuation offset on prompt offset is NOT the right
    # summary: a pull toward the two grid points at 0 and 100 makes an S-shape
    # whose least-squares slope can exceed 1. It is printed for completeness;
    # the grid-directed displacement below is the statistic that matters.
    sl, lo, hi, r2 = slope_fit(pm, out)
    print(f"  (linear slope of continuation offset on measured prompt offset: {sl:.3f} [{lo:.3f}, {hi:.3f}], "
          f"R2 {r2:.3f}; not a pull statistic, see comment)")
    # The grid-directed component of the continuation's displacement from the
    # prompt's tuning: positive means the continuation moved toward the grid.
    delta_p = fold(pm)                      # prompt's signed distance to the grid
    toward = -np.sign(delta_p) * rel
    off = np.abs(delta_p) >= 20
    rng2 = np.random.default_rng(0)
    boots = [np.median(toward[off][rng2.integers(0, off.sum(), off.sum())]) for _ in range(4000)]
    print(f"  grid-directed displacement of the continuation, prompts >= 20 cents off-grid (n={off.sum()}): "
          f"median {np.median(toward[off]):+.2f} cents, 95% CI [{np.percentile(boots, 2.5):+.2f}, {np.percentile(boots, 97.5):+.2f}]"
          f"  (median |prompt offset| in that set {np.median(np.abs(delta_p[off])):.1f} cents; "
          f"pull fraction {np.median(toward[off]) / np.median(np.abs(delta_p[off])):.2f})")
    on = np.abs(delta_p) < 20
    boots = [np.median(toward[on][rng2.integers(0, on.sum(), on.sum())]) for _ in range(4000)]
    print(f"  the same for prompts within 20 cents of the grid (n={on.sum()}): median {np.median(toward[on]):+.2f} "
          f"[{np.percentile(boots, 2.5):+.2f}, {np.percentile(boots, 97.5):+.2f}]")
    print("\n  measured prompt offset vs continuation offset, per clip (both relative to the grid):")
    for pi, oi, ri, qi in sorted(zip(pm, absr, res_c, pres)):
        print(f"    prompt {pi:5.1f} (R {qi:.2f})   continuation {oi:+6.1f} (R {ri:.2f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

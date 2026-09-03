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
               The grid-directed displacement (median of toward = -sign(delta_p)
               * rel over prompts >= 20 cents off-grid) is then compared with
               three null models, each 4000 draws with fixed seeds: a shuffle
               null that pairs each prompt with another clip's continuation
               (what the statistic gives if continuations revert to MusicGen's
               own grid-peaked output distribution regardless of prompt); a
               dispersion-matched tracking null that sets out = pm + e with e
               a resampled |rel| given a random sign (continuations follow the
               prompt with the observed scatter but no preferred direction);
               and a uniform-tuning null with out uniform on [0, 100). The
               bootstrap CI only reflects sampling noise; the nulls are the
               test of grid attraction. The prompt set is also re-selected on
               the applied shift fold(d) instead of the measured fold(pm) to
               remove regression to the mean from estimation error, and the
               displacement is decomposed into distance-to-grid, distance-to-
               prompt and a Spearman/circular tracking correlation.

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
    # ---- null models for the grid-directed displacement -------------------
    # The bootstrap CI above measures sampling noise only. Whether the
    # displacement reflects attraction to the grid, as opposed to reversion
    # to MusicGen's own grid-peaked output distribution, is tested against
    # the nulls below (all 4000 draws, fixed seeds).
    n = len(pm)
    N_NULL = 4000

    def toward_of(out_null):
        return -np.sign(delta_p) * fold(out_null - pm)

    def summarise(label, null, observed):
        null = np.asarray(null)
        print(f"    {label}: mean {null.mean():+.2f}, median {np.median(null):+.2f}, "
              f"2.5/97.5 pct [{np.percentile(null, 2.5):+.2f}, {np.percentile(null, 97.5):+.2f}], "
              f"P(null >= observed {observed:+.2f}) = {np.mean(null >= observed):.4f}")

    obs_off, obs_on = np.median(toward[off]), np.median(toward[on])
    print(f"\n  null models for the grid-directed displacement ({N_NULL} draws each):")
    # 1. shuffle null: each prompt paired with another clip's continuation
    rng3 = np.random.default_rng(1)
    sh_off, sh_on = [], []
    for _ in range(N_NULL):
        t = toward_of(out[rng3.permutation(n)])
        sh_off.append(np.median(t[off])); sh_on.append(np.median(t[on]))
    print("  1. shuffle null (continuation offsets permuted across prompts):")
    summarise(f"prompts >= 20 cents off-grid (n={off.sum()})", sh_off, obs_off)
    summarise(f"prompts within 20 cents (n={on.sum()})", sh_on, obs_on)
    # 2. dispersion-matched tracking null: out = pm + e, e a resampled |rel|
    #    with a random sign, i.e. the observed scatter about the prompt but
    #    no preferred direction
    rng4 = np.random.default_rng(2)
    tr_off, tr_on = [], []
    for _ in range(N_NULL):
        e = rng4.choice(np.abs(rel), n) * rng4.choice([-1.0, 1.0], n)
        t = toward_of(pm + e)
        tr_off.append(np.median(t[off])); tr_on.append(np.median(t[on]))
    print("  2. dispersion-matched tracking null (out = prompt + resampled |rel| with random sign):")
    summarise(f"prompts >= 20 cents off-grid (n={off.sum()})", tr_off, obs_off)
    summarise(f"prompts within 20 cents (n={on.sum()})", tr_on, obs_on)
    # 3. uniform-tuning null: continuation offset uniform on [0, 100)
    rng5 = np.random.default_rng(3)
    un_off, un_on = [], []
    for _ in range(N_NULL):
        t = toward_of(rng5.uniform(0.0, 100.0, n))
        un_off.append(np.median(t[off])); un_on.append(np.median(t[on]))
    print("  3. uniform-tuning null (continuation offset uniform on [0, 100)):")
    summarise(f"prompts >= 20 cents off-grid (n={off.sum()})", un_off, obs_off)
    summarise(f"prompts within 20 cents (n={on.sum()})", un_on, obs_on)
    # 4. selection on the applied shift d rather than the measured pm. Selecting
    #    on pm lets estimation error in pm regress toward the grid in a
    #    statistic that is itself computed relative to pm; d is noise-free.
    off_d = np.abs(fold(d)) >= 20
    rng6 = np.random.default_rng(4)
    boots_d = [np.median(toward[off_d][rng6.integers(0, off_d.sum(), off_d.sum())]) for _ in range(N_NULL)]
    obs_d = np.median(toward[off_d])
    print(f"  4. prompt set selected on the applied shift, |fold(d)| >= 20 (n={off_d.sum()}, "
          f"{(off_d & off).sum()} shared with the measured-offset set), toward still relative to pm:")
    print(f"    observed median {obs_d:+.2f} cents, 95% bootstrap CI "
          f"[{np.percentile(boots_d, 2.5):+.2f}, {np.percentile(boots_d, 97.5):+.2f}]")
    rng7 = np.random.default_rng(5)
    sh_d = [np.median(toward_of(out[rng7.permutation(n)])[off_d]) for _ in range(N_NULL)]
    summarise("shuffle null on that set", sh_d, obs_d)
    # 5. decomposition of the displacement for the >= 20-cent set
    print(f"  5. decomposition, prompts >= 20 cents off-grid (n={off.sum()}):")
    print(f"    median |prompt - grid| {np.median(np.abs(delta_p[off])):.1f} cents;  "
          f"median |continuation - grid| {np.median(np.abs(absr[off])):.1f} cents;  "
          f"median |continuation - prompt| {np.median(np.abs(rel[off])):.1f} cents")
    closer = np.abs(absr[off]) < np.abs(rel[off])
    print(f"    fraction of continuations closer to the grid than to the prompt's tuning: "
          f"{closer.mean():.2f} ({closer.sum()}/{off.sum()})")
    # 6. tracking: correlation between prompt and continuation offsets, all clips
    rho, pval = stats.spearmanr(delta_p, absr)
    #    Fisher-Lee T-linear circular correlation: built from pairwise angle
    #    differences, so it needs no mean direction (the prompt offsets have
    #    resultant ~0.05, which makes the Jammalamadaka-Sarma coefficient,
    #    which centres on the mean directions, meaningless here).
    a, b = 2 * np.pi * pm / 100.0, 2 * np.pi * out / 100.0
    i, j = np.triu_indices(n, 1)
    circ = ((np.sin(a[i] - a[j]) * np.sin(b[i] - b[j])).sum() /
            np.sqrt((np.sin(a[i] - a[j]) ** 2).sum() * (np.sin(b[i] - b[j]) ** 2).sum()))
    print(f"  6. tracking over all {n} clips: Spearman rho(fold(prompt), fold(continuation)) = {rho:.3f} "
          f"(p = {pval:.2e}); circular correlation (Fisher-Lee T-linear) = {circ:.3f}")
    print("\n  measured prompt offset vs continuation offset, per clip (both relative to the grid):")
    for pi, oi, ri, qi in sorted(zip(pm, absr, res_c, pres)):
        print(f"    prompt {pi:5.1f} (R {qi:.2f})   continuation {oi:+6.1f} (R {ri:.2f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

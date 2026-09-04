"""Summarise musicgen_swap.py output: same tokens, different decoders.

For each decoder and each estimator (yin, refined) the per-frame within-
semitone positions of every clip are pooled and the density's peak-to-mean
ratio over 50 bins is reported (GTZAN 1.788, MusicGen through its stock
decoder 4.28; a flat density sampled at this size about 1.05), with the
circular-mean position and resultant length.

Because every decoder saw the SAME token ids for a given prompt, the decoders
can be compared prompt by prompt. For each fine-tuned decoder against stock,
the per-clip resultant and the per-clip peak/mean (over --clip-bins bins,
fewer than the pooled 50 because a clip has only a few hundred frames) are
differenced within prompt; the mean difference gets a paired-bootstrap 95% CI
(4000 resamples of prompts, seed 0) and a Wilcoxon signed-rank p. A decoder
that carries the grid gives a positive stock-minus-flat difference; one that
merely renders the tokens gives differences near zero.

The pooled densities are written next to the input as
hist_<stem>_<decoder>_<estimator>.csv in the hist_*.csv format of
pitch_histogram.py (bin_lo_cents, bin_hi_cents, density), so plot_histograms.py
can show them beside the corpora.

    python analyze_musicgen_swap.py ../results/musicgen_swap.csv [--clip-bins 20]
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

N_BOOT = 4000
POOLED_BINS = 50


def parse_positions(s: str) -> np.ndarray:
    return np.array([float(v) for v in s.split(";") if v]) if s else np.array([])


def peak_over_mean(pos: np.ndarray, bins: int) -> float:
    if pos.size == 0:
        return float("nan")
    h, _ = np.histogram(pos, bins=bins, range=(0, 100))
    return float(h.max() / h.mean())


def circular(pos: np.ndarray) -> tuple[float, float]:
    if pos.size == 0:
        return float("nan"), float("nan")
    ang = 2 * np.pi * pos / 100.0
    c, s = np.cos(ang).mean(), np.sin(ang).mean()
    return float((np.degrees(np.arctan2(s, c)) % 360) / 3.6), float(np.hypot(c, s))


def flat_expectation(n: int, bins: int, rng: np.random.Generator, draws: int = 200) -> float:
    if n == 0:
        return float("nan")
    return float(np.mean([np.bincount(rng.integers(0, bins, n), minlength=bins).max() / (n / bins)
                          for _ in range(draws)]))


def paired(a: np.ndarray, b: np.ndarray, rng: np.random.Generator):
    """a - b over prompts: mean, 95% paired-bootstrap CI of the mean, Wilcoxon p."""
    d = a - b
    ok = np.isfinite(d)
    d = d[ok]
    if d.size < 2:
        return float("nan"), (float("nan"), float("nan")), float("nan"), int(d.size)
    boots = np.array([d[rng.integers(0, d.size, d.size)].mean() for _ in range(N_BOOT)])
    try:
        pw = float(stats.wilcoxon(d).pvalue) if np.any(d != 0) else 1.0
    except ValueError:
        pw = float("nan")
    return float(d.mean()), (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))), pw, int(d.size)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    ap.add_argument("--clip-bins", type=int, default=20, help="bins for the per-clip peak/mean")
    ap.add_argument("--stock", default="stock", help="name of the reference decoder")
    args = ap.parse_args()

    rows = list(csv.DictReader(args.csv.open()))
    if not rows:
        raise SystemExit("empty csv")
    # decoders in first-seen order, stock first
    decoders = []
    for r in rows:
        if r["decoder"] not in decoders:
            decoders.append(r["decoder"])
    if args.stock in decoders:
        decoders.remove(args.stock)
        decoders.insert(0, args.stock)
    estimators = []
    for r in rows:
        if r["estimator"] not in estimators:
            estimators.append(r["estimator"])

    # per (estimator, decoder): prompt_index -> positions
    clips: dict = defaultdict(dict)
    for r in rows:
        clips[(r["estimator"], r["decoder"])][int(r["prompt_index"])] = parse_positions(r["positions"])
    n_prompts = len({int(r["prompt_index"]) for r in rows})
    print(f"  {n_prompts} prompts, decoders {decoders}, estimators {estimators}")

    rng = np.random.default_rng(0)
    edges = np.linspace(0, 100, POOLED_BINS + 1)
    print(f"\n  pooled within-semitone density ({POOLED_BINS} bins), per decoder and estimator:")
    print(f"  {'estimator':9s} {'decoder':8s} {'frames':>7s} {'peak/mean':>9s} {'flat':>6s} "
          f"{'circ. mean':>10s} {'R':>6s}  {'median clip R':>13s}")
    for est in estimators:
        for dec in decoders:
            per = clips[(est, dec)]
            pooled = np.concatenate(list(per.values())) if per else np.array([])
            hist, _ = np.histogram(pooled, bins=POOLED_BINS, range=(0, 100), density=True)
            ratio = float(hist.max() / hist.mean()) if pooled.size else float("nan")
            mean_pos, R = circular(pooled)
            flat = flat_expectation(pooled.size, POOLED_BINS, rng)
            clip_R = np.array([circular(v)[1] for v in per.values()])
            print(f"  {est:9s} {dec:8s} {pooled.size:7d} {ratio:9.3f} {flat:6.3f} {mean_pos:10.1f} {R:6.3f}  "
                  f"{np.nanmedian(clip_R) if clip_R.size else float('nan'):13.2f}")
            out_csv = args.csv.with_name(f"hist_{args.csv.stem}_{dec}_{est}.csv")
            with out_csv.open("w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["bin_lo_cents", "bin_hi_cents", "density"])
                for lo, hi, dd in zip(edges[:-1], edges[1:], hist):
                    w.writerow([f"{lo:.2f}", f"{hi:.2f}", f"{dd:.6f}"])
    print(f"  (densities written to hist_{args.csv.stem}_<decoder>_<estimator>.csv)")

    if args.stock not in decoders or len(decoders) < 2:
        print(f"\n  no decoder to compare with {args.stock!r}; done")
        return 0

    print(f"\n  paired comparison across prompts (same tokens), {args.stock} minus each decoder;"
          f"\n  mean difference [95% paired-bootstrap CI, {N_BOOT} draws], Wilcoxon signed-rank p:")
    print(f"  {'estimator':9s} {'decoder':8s} {'n':>3s}  {'resultant: stock - dec':>34s}   "
          f"{'peak/mean (' + str(args.clip_bins) + ' bins): stock - dec':>40s}")
    for est in estimators:
        ref = clips[(est, args.stock)]
        for dec in decoders[1:]:
            other = clips[(est, dec)]
            idx = sorted(set(ref) & set(other))
            r_ref = np.array([circular(ref[i])[1] for i in idx])
            r_dec = np.array([circular(other[i])[1] for i in idx])
            p_ref = np.array([peak_over_mean(ref[i], args.clip_bins) for i in idx])
            p_dec = np.array([peak_over_mean(other[i], args.clip_bins) for i in idx])
            m1, ci1, pw1, n1 = paired(r_ref, r_dec, np.random.default_rng(1))
            m2, ci2, pw2, n2 = paired(p_ref, p_dec, np.random.default_rng(2))
            print(f"  {est:9s} {dec:8s} {n1:3d}  {m1:+.3f} [{ci1[0]:+.3f}, {ci1[1]:+.3f}] p={pw1:.3g}"
                  f"{'':>6s}{m2:+.3f} [{ci2[0]:+.3f}, {ci2[1]:+.3f}] p={pw2:.3g}")
            print(f"  {'':9s} {'':8s}      medians: R {np.nanmedian(r_ref):.3f} vs {np.nanmedian(r_dec):.3f};  "
                  f"clip peak/mean {np.nanmedian(p_ref):.2f} vs {np.nanmedian(p_dec):.2f};  "
                  f"frames/clip {np.median([ref[i].size for i in idx]):.0f} vs "
                  f"{np.median([other[i].size for i in idx]):.0f}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

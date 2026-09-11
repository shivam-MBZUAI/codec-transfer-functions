"""Flat-sampling null for the within-semitone peak/mean ratio.

pitch_histogram.py and analyze_musicgen.py summarise a corpus by the
peak-to-mean ratio of a 50-bin histogram of F0 modulo 100 cents (max bin over
mean bin, 1.0 = flat). Even a perfectly flat density does not give exactly 1.0
at a finite sample size: the maximum of 50 multinomial counts sits above their
mean by an amount that shrinks with n. This script simulates that expectation
for the sample sizes of the reported histograms, so the corpus ratios (GTZAN
1.788, detuned GTZAN 1.073, LibriSpeech 1.113) can be read against it. The
paper quotes the result as \\PeakNullSpeech and \\PeakNullMusic.

Sample sizes are taken from the `hist_*.meta.json` sidecars that
pitch_histogram.py writes (`n_f0_estimates`) when they are present next to
the CSVs; otherwise the counts recorded in docs/notes/FINDINGS.md are used as defaults
and can be overridden on the command line:

    python flat_sampling_null.py ../results
    python flat_sampling_null.py --sizes librispeech=53678 gtzan=180859
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# Counts recorded in docs/notes/FINDINGS.md section 6 and main.tex (\GenPeak comment).
DEFAULT_SIZES = {
    "librispeech": 53678,
    "gtzan": 180859,
    "gtzan_detuned": 175552,
    "musicgen_text": 17374,
}
N_BINS = 50
N_REPS = 500
SEED = 0


def sizes_from_sidecars(results: Path) -> dict[str, int]:
    """`hist_<name>.meta.json` -> n_f0_estimates, for every sidecar present."""
    found = {}
    for meta in sorted(results.glob("hist_*.meta.json")):
        try:
            n = json.loads(meta.read_text()).get("n_f0_estimates")
        except (OSError, ValueError):
            continue
        if isinstance(n, int) and n > 0:
            found[meta.name[len("hist_"):-len(".meta.json")]] = n
    return found


def peak_over_mean_null(n: int, n_reps: int = N_REPS, n_bins: int = N_BINS,
                        seed: int = SEED) -> np.ndarray:
    """Peak/mean of an n_bins histogram of n draws from a flat density, one
    value per replicate. The mean bin is n / n_bins exactly, so the ratio is
    max count over that."""
    rng = np.random.default_rng(seed)
    counts = rng.multinomial(n, np.full(n_bins, 1.0 / n_bins), size=n_reps)
    return counts.max(axis=1) / (n / n_bins)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("results", nargs="?", type=Path,
                   default=Path(__file__).resolve().parent.parent / "results")
    p.add_argument("--sizes", nargs="*", default=[], metavar="NAME=N",
                   help="sample sizes to simulate; override or extend the defaults")
    p.add_argument("--reps", type=int, default=N_REPS)
    p.add_argument("--seed", type=int, default=SEED)
    args = p.parse_args()

    sizes = dict(DEFAULT_SIZES)
    source = "docs/notes/FINDINGS.md defaults"
    sidecar = sizes_from_sidecars(args.results)
    if sidecar:
        sizes.update(sidecar)
        source = f"{len(sidecar)} sidecar(s) under {args.results}, defaults for the rest"
    for item in args.sizes:
        name, _, n = item.partition("=")
        sizes[name] = int(n)
    if args.sizes:
        source += ", command line overrides"

    print(f"  sample sizes from: {source}")
    print(f"  {args.reps} replicates per size, {N_BINS} bins over 100 cents, seed {args.seed}\n")
    print(f"  {'corpus':<16}{'n':>9}{'mean':>8}{'2.5%':>8}{'97.5%':>8}{'min':>8}{'max':>8}")
    for name, n in sorted(sizes.items(), key=lambda kv: kv[1]):
        r = peak_over_mean_null(n, args.reps, seed=args.seed)
        lo, hi = np.percentile(r, [2.5, 97.5])
        print(f"  {name:<16}{n:>9d}{r.mean():8.3f}{lo:8.3f}{hi:8.3f}{r.min():8.3f}{r.max():8.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

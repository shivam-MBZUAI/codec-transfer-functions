"""Isolated-note ecological test: displacement between grid points minus near them.

Consumes the per-measurement output of experiments/retune_real.py
(`retune_encodec3_big.csv`, `retune_dac16.csv`, `retune_synthetic.csv`). Each
row is one NSynth note resampled by a known offset so that its input pitch sits
at `within_semitone` cents above the 12-TET pitch below, coded, and read back:
`shift_cents` is the codec's displacement of the pitch, `toward_grid` the same
displacement signed positive when it moves the note toward the nearest grid
pitch, and `disagreement` the cents between the two refined F0 readings of the
coded output (YIN-seeded against harmonic-sum-seeded).

The paper's Table (isolated notes) was produced by an ad-hoc analysis that was
not committed with the data. This script is the closest reconstruction found:
it reproduces the usable counts exactly and the displacement statistic
approximately (EnCodec +0.007 [-0.232, +0.260] against the reported +0.011
[-0.199, +0.265]; DAC +0.011 [-0.018, +0.036] against +0.010 [-0.019,
+0.036]; synthetic control +7.07 [+4.71, +10.25] against +6.600 [+4.237,
+9.840]). The exact near/between thresholds and bootstrap design of the
original are not recoverable from the repository; --sensitivity shows how
little the conclusion depends on them.

  usable    |disagreement| <= 50 cents (the two readings of the coded output
            pick the same nearest grid pitch) and |shift_cents| <= 60 cents
            (the refinement's search window; beyond it the reading is not of
            the same note). This gives 884 / 3455 for EnCodec and 932 / 3443
            for DAC 16k, the counts reported.
  near      input pitch within 10 cents of a grid pitch
  between   input pitch at least 30 cents from the nearest grid pitch
            (positions 30 to 70 within the semitone)
  statistic median(toward_grid | between) - median(toward_grid | near)
  interval  percentile bootstrap of that difference, 4000 replicates, the
            two groups resampled independently, seed 0

A pull toward the grid gives a positive value. The near group is the control:
a note already on a grid pitch has nowhere to be pulled, so any displacement
there is estimator and codec noise, and subtracting it removes a common bias.

    python analyze_retune.py ../results/retune_encodec3_big.csv
    python analyze_retune.py ../results/retune_*.csv --sensitivity
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

AGREE_CENTS = 50.0
MAX_SHIFT_CENTS = 60.0
NEAR_CENTS = 10.0
BETWEEN_CENTS = 30.0
N_BOOT = 4000
SEED = 0


def load(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.DictReader(path.open()))
    d = {k: np.array([float(r[k]) for r in rows]) for k in rows[0] if k != "file"}
    d["file"] = np.array([r["file"] for r in rows])
    return d


def usable_mask(d, agree=AGREE_CENTS, max_shift=MAX_SHIFT_CENTS) -> np.ndarray:
    dis = np.abs(np.nan_to_num(d["disagreement"], nan=np.inf))
    return (dis <= agree) & (np.abs(d["shift_cents"]) <= max_shift)


def groups(d, keep, near=NEAR_CENTS, between=BETWEEN_CENTS):
    w = d["within_semitone"]
    dist = np.minimum(w, 100.0 - w)             # distance to the nearest grid pitch
    return keep & (dist < near), keep & (dist >= between)


def displacement(v_between, v_near, n_boot=N_BOOT, seed=SEED):
    """Difference of medians and its percentile bootstrap interval, resampling
    each group with replacement independently."""
    point = float(np.median(v_between) - np.median(v_near))
    rng = np.random.default_rng(seed)
    ib = rng.integers(0, v_between.size, size=(n_boot, v_between.size))
    inear = rng.integers(0, v_near.size, size=(n_boot, v_near.size))
    reps = np.median(v_between[ib], axis=1) - np.median(v_near[inear], axis=1)
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return point, float(lo), float(hi)


def clustered_displacement(d, near_m, between_m, n_boot=2000, seed=SEED):
    """The same statistic with notes (files) resampled instead of rows, for
    the reader who wants the interval to respect the twelve offsets per note.
    Not the interval the table reports."""
    files = np.unique(d["file"][near_m | between_m])
    idx = {f: np.flatnonzero(d["file"] == f) for f in files}
    tg = d["toward_grid"]
    rng = np.random.default_rng(seed)
    reps = []
    for _ in range(n_boot):
        pick = np.concatenate([idx[f] for f in rng.choice(files, files.size)])
        b, n = pick[between_m[pick]], pick[near_m[pick]]
        if b.size and n.size:
            reps.append(np.median(tg[b]) - np.median(tg[n]))
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return float(lo), float(hi)


def report(path: Path, args) -> None:
    d = load(path)
    keep = usable_mask(d, args.agree, args.max_shift)
    near_m, between_m = groups(d, keep, args.near, args.between)
    tg = d["toward_grid"]
    print(f"{path.name}: {keep.sum()} / {keep.size} usable "
          f"(|disagreement| <= {args.agree:g} c and |shift| <= {args.max_shift:g} c), "
          f"{len(np.unique(d['file'][keep]))} of {len(np.unique(d['file']))} notes")
    print(f"  near (< {args.near:g} c from a grid pitch): n = {near_m.sum()}, "
          f"median toward_grid {np.median(tg[near_m]):+.3f} c")
    print(f"  between (>= {args.between:g} c from a grid pitch): n = {between_m.sum()}, "
          f"median toward_grid {np.median(tg[between_m]):+.3f} c")
    pt, lo, hi = displacement(tg[between_m], tg[near_m], args.n_boot, args.seed)
    print(f"  displacement, between minus near: {pt:+.3f} c, "
          f"95% CI [{lo:+.3f}, {hi:+.3f}]  (percentile bootstrap, {args.n_boot} reps, seed {args.seed})")
    clo, chi = clustered_displacement(d, near_m, between_m)
    print(f"    bootstrap over notes instead of rows: [{clo:+.3f}, {chi:+.3f}]")
    print("  median toward_grid per 10-cent bin of input position (usable rows):")
    w = d["within_semitone"]
    cells = []
    for a in range(0, 100, 10):
        m = keep & (w >= a) & (w < a + 10)
        cells.append(f"{a:2d}-{a + 10:<3d}{np.median(tg[m]):+7.3f} (n={m.sum():3d})" if m.any()
                     else f"{a:2d}-{a + 10:<3d}     --")
    for i in (0, 5):
        print("    " + "   ".join(cells[i:i + 5]))


def sensitivity(paths, args) -> None:
    """The candidate rules tried while reconstructing the recipe, so the
    reader can see how much the count and the statistic depend on them."""
    rules = [("|dis|<=50, |shift|<=60 (reported)", 50, 60),
             ("|dis|<=20, no shift gate", 20, np.inf),
             ("|dis|<=20, |shift|<=200 (octave gate)", 20, 200),
             ("|dis|<=50, |shift|<=50", 50, 50),
             ("|dis|<=200, no shift gate", 200, np.inf),
             ("no gate", np.inf, np.inf)]
    splits = [(10, 30), (12.5, 30), (16, 25), (25, 25), (20, 40)]
    print("\nSensitivity of the usable count and the displacement to the gate and the near/between split")
    for path in paths:
        d = load(path)
        print(f"\n  {path.name}")
        print(f"    {'gate':<40}{'usable':>8}  " + "  ".join(f"near<{a:g}/betw>={b:g}" for a, b in splits))
        for label, agree, max_shift in rules:
            keep = usable_mask(d, agree, max_shift)
            cells = []
            for a, b in splits:
                nm, bm = groups(d, keep, a, b)
                cells.append(f"{np.median(d['toward_grid'][bm]) - np.median(d['toward_grid'][nm]):+16.3f}")
            print(f"    {label:<40}{keep.sum():>8}  " + "  ".join(cells))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv", nargs="+", type=Path)
    p.add_argument("--agree", type=float, default=AGREE_CENTS)
    p.add_argument("--max-shift", type=float, default=MAX_SHIFT_CENTS)
    p.add_argument("--near", type=float, default=NEAR_CENTS)
    p.add_argument("--between", type=float, default=BETWEEN_CENTS)
    p.add_argument("--n-boot", type=int, default=N_BOOT)
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--sensitivity", action="store_true")
    args = p.parse_args()
    for path in args.csv:
        report(path, args)
        print()
    if args.sensitivity:
        sensitivity(args.csv, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

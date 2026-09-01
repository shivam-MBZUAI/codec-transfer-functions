"""Where do the quantiser's code-assignment boundaries fall in pitch?

Every other measurement here infers the mechanism from reconstruction error.
This looks at the assignment itself: sweep pitch finely, record which code index
dominates each RVQ level, and find the pitches at which that index changes.

If the codebook absorbed the pitch statistics of Western training audio, its
cells should be arranged around 12-TET pitches, so the BOUNDARIES between cells
should avoid the grid points and fall preferentially between them. The residual
analysis says the same thing indirectly; this says it in the codec's own units.

The null is a flat distribution of boundary positions within the semitone. The
test is a Rayleigh test for circular concentration, treating position within the
100-cent semitone as an angle, which assumes no functional form.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


def main() -> int:
    path = Path(sys.argv[1])
    rows = list(csv.DictReader(path.open()))
    if not rows:
        raise SystemExit("no rows")

    qcols = sorted(c for c in rows[0] if c.endswith("_mode"))
    by_pitch = defaultdict(dict)
    for r in rows:
        c = float(r["cents"])
        for q in qcols:
            by_pitch[c].setdefault(q, []).append(int(r[q]))

    pitches = sorted(by_pitch)
    # Absolute pitch in cents relative to A440, so grid points are multiples
    # of 100 in the same frame the residual analysis uses.
    f_lo = float(rows[0]["f0"])
    abs_cents = np.array([1200 * np.log2(f_lo / 440.0) + p for p in pitches])

    print(f"  {len(pitches)} pitches, {len(qcols)} quantiser levels\n")
    print(f"  {'level':>6} {'boundaries':>11} {'mean |dist to grid|':>21} {'Rayleigh p':>11}")

    all_pos = []
    for q in qcols:
        modes = np.array([int(np.bincount(by_pitch[p][q]).argmax()) for p in pitches])
        changes = np.nonzero(np.diff(modes) != 0)[0]
        if len(changes) < 8:
            print(f"  {q:>6} {len(changes):11d}   (too few to test)")
            continue
        # Boundary sits between two sampled pitches.
        pos = ((abs_cents[changes] + abs_cents[changes + 1]) / 2.0) % 100.0
        all_pos.append(pos)
        dist = np.minimum(pos, 100.0 - pos)         # distance to nearest grid point

        ang = 2 * np.pi * pos / 100.0
        R = np.hypot(np.cos(ang).mean(), np.sin(ang).mean())
        n = len(ang)
        # Rayleigh test for uniformity on the circle.
        Z = n * R * R
        p_val = float(np.exp(-Z) * (1 + (2 * Z - Z * Z) / (4 * n)))
        print(f"  {q:>6} {n:11d} {dist.mean():21.2f} {p_val:11.2e}")

    if all_pos:
        pos = np.concatenate(all_pos)
        dist = np.minimum(pos, 100.0 - pos)
        ang = 2 * np.pi * pos / 100.0
        R = np.hypot(np.cos(ang).mean(), np.sin(ang).mean())
        n = len(ang); Z = n * R * R
        p_val = float(np.exp(-Z) * (1 + (2 * Z - Z * Z) / (4 * n)))
        mean_ang = np.degrees(np.arctan2(np.sin(ang).mean(), np.cos(ang).mean())) % 360
        print(f"\n  pooled: {n} boundaries")
        print(f"    mean distance to nearest grid point  {dist.mean():.2f} cents "
              f"(uniform expects 25.0)")
        print(f"    resultant length R                   {R:.4f} (0 = uniform)")
        print(f"    Rayleigh p                           {p_val:.3e}")
        print(f"    mean position within semitone        {mean_ang/3.6:.1f} cents")
        hist, edges = np.histogram(pos, bins=10, range=(0, 100))
        print(f"\n    position within semitone (10-cent bins):")
        for lo, h in zip(edges[:-1], hist):
            print(f"      {lo:3.0f}-{lo+10:3.0f}  {'#' * int(40 * h / max(hist.max(),1)):40} {h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

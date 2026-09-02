"""Is the effect manufactured by the exclusion rule?

analyze_sweep.py drops trials where the two blind estimators disagree, or where
the estimate lands more than 200 cents from nominal. The pilot showed that
exclusion rate correlating with distance from the grid at |r| ~ 0.3. If trials
are dropped preferentially off-grid, the surviving off-grid population is biased
and part of the headline ratio could be the estimator rather than the codec.

This recomputes every headline statistic three ways:

    all        no exclusions at all
    gate       octave gate only (>200 cents from nominal: unambiguous failures)
    full       the rule as used

If the effect holds under "all", the exclusion rule is not creating it. If it
appears only under "full", the result is an artefact and must not be reported.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from analyze_sweep import DISAGREE_CENTS, grid, load, summarise  # noqa: E402

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "experiments", _ROOT / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))



def main() -> int:
    path = Path(sys.argv[1])
    d = load(path)
    theta = d["theta_cents"]
    rc, ru = d["residual_coded_cents"], d["residual_uncoded_cents"]
    labels = d["reference_label"]

    dis = np.maximum(np.abs(d.get("disagreement_f1_cents", np.zeros_like(theta))),
                     np.abs(d.get("disagreement_f2_cents", np.zeros_like(theta))))
    octave = d.get("octave_flag", np.zeros_like(theta)) > 0.5
    disagree = np.nan_to_num(dis, nan=1e9) > DISAGREE_CENTS

    schemes = {
        "all  (no exclusions)": np.ones_like(theta, dtype=bool),
        "gate (octave only)  ": ~octave,
        "full (as used)      ": ~octave & ~disagree,
    }

    for label in sorted(set(labels.tolist())):
        m = labels == label
        print(f"\n=== {label} ===")
        print(f"  {'scheme':22} {'n':>6} {'on-grid':>9} {'off-grid':>9} "
              f"{'ratio':>7} {'bias':>8} {'95% CI':>16}")
        for name, keep in schemes.items():
            s = summarise(theta[m], rc[m], ru[m], keep[m], label)
            ratio = s["off_grid"] / s["on_grid"] if s["on_grid"] else float("nan")
            lo, hi = s["bias_ci"]
            print(f"  {name} {s['n']:6d} {s['on_grid']:9.3f} {s['off_grid']:9.3f} "
                  f"{ratio:7.2f} {s['bias']:8.3f}  [{lo:6.2f},{hi:6.2f}]")

        # Where do exclusions actually fall?
        dist = np.abs(theta[m] - grid(theta[m]))
        print(f"\n  exclusion rate by distance from grid point:")
        edges = [0, 10, 20, 30, 40, 50]
        for lo_e, hi_e in zip(edges[:-1], edges[1:]):
            b = (dist >= lo_e) & (dist < hi_e)
            if not b.any():
                continue
            n = int(b.sum())
            oct_r = 100.0 * float(octave[m][b].mean())
            dis_r = 100.0 * float(disagree[m][b].mean())
            print(f"    {lo_e:2d}-{hi_e:2d} cents  n={n:4d}  "
                  f"octave {oct_r:5.1f}%   disagree {dis_r:5.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())

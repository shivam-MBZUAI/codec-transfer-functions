"""Rate scaling: does the bias fall as the theory says, and to what floor?

Two candidate accounts of the residual predict different slopes against bits per
latent dimension:

  coarse cell assignment    bias ~ Delta      ~ 2^(-R/D)   slope -1
  Bennett density term      bias ~ Delta^2    ~ 4^(-R/D)   slope -2

so fitting log2(bias) against R/D discriminates them. The draft asserts -2 via
Proposition 1, but that proposition drops the O(Delta) term that dominates, and
the measured sawtooth-versus-sinusoid comparison already leans the other way.

The fit is also run against a floor: the quantiser-bypass measurement gives the
bias with no quantisation at all, and any component at that level cannot be
attributed to codebook resolution however the slope comes out. Subtracting it
before fitting is the honest version of the test.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from analyze_sweep import DISAGREE_CENTS, load, summarise  # noqa: E402

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "experiments", _ROOT / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


# EnCodec 24 kHz: 75 Hz frames, latent dimension 128, 1024-entry codebooks.
FRAME_HZ, LATENT_D = 75.0, 128


def bias_of(path: Path) -> tuple[float, int]:
    d = load(path)
    theta, rc, ru = d["theta_cents"], d["residual_coded_cents"], d["residual_uncoded_cents"]
    labels = d["reference_label"]
    dis = np.maximum(np.abs(d.get("disagreement_f1_cents", np.zeros_like(theta))),
                     np.abs(d.get("disagreement_f2_cents", np.zeros_like(theta))))
    keep = np.nan_to_num(dis, nan=1e9) <= DISAGREE_CENTS
    if "octave_flag" in d:
        keep &= d["octave_flag"] < 0.5
    # On-grid reference only: the metric is defined against the 12-TET grid.
    on = np.array([l.endswith("ongrid") for l in labels.tolist()])
    s = summarise(theta[on], rc[on], ru[on], keep[on], "ongrid")
    return s["bias"], s["n"]


def main() -> int:
    results_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../results")
    rates, biases, ns = [], [], []
    for kb in ("1.5", "3", "6", "12", "24"):
        p = results_dir / f"rate_encodec_{kb}.csv"
        if not p.exists():
            continue
        b, n = bias_of(p)
        rates.append(float(kb)); biases.append(b); ns.append(n)

    floor = None
    bp = results_dir / "mech_bypass.csv"
    if bp.exists():
        floor, _ = bias_of(bp)

    rates, biases = np.array(rates), np.array(biases)
    bits_per_frame = rates * 1000.0 / FRAME_HZ
    r_over_d = bits_per_frame / LATENT_D

    print(f"  EnCodec 24 kHz: {FRAME_HZ:.0f} Hz frames, latent D={LATENT_D}\n")
    print(f"  {'kbps':>6} {'R/D':>7} {'bias':>8} {'n':>6}")
    for kb, rd, b, n in zip(rates, r_over_d, biases, ns):
        print(f"  {kb:6.1f} {rd:7.3f} {b:8.3f} {n:6d}")
    if floor is not None:
        print(f"\n  quantiser-bypass bias (no quantisation at all): {floor:.3f} cents")

    def fit(y, tag):
        ok = np.isfinite(y) & (y > 0)
        if ok.sum() < 3:
            print(f"  {tag}: too few positive points to fit")
            return
        A = np.vstack([r_over_d[ok], np.ones(ok.sum())]).T
        slope, icept = np.linalg.lstsq(A, np.log2(y[ok]), rcond=None)[0]
        pred = A @ [slope, icept]
        resid = np.log2(y[ok]) - pred
        ss, tot = float((resid ** 2).sum()), float(((np.log2(y[ok]) - np.log2(y[ok]).mean()) ** 2).sum())
        se = float(np.sqrt(ss / max(ok.sum() - 2, 1) / ((r_over_d[ok] - r_over_d[ok].mean()) ** 2).sum()))
        print(f"  {tag}\n    slope {slope:+.3f}  95% CI [{slope-1.96*se:+.3f}, {slope+1.96*se:+.3f}]"
              f"   R2 {1-ss/tot if tot else float('nan'):.3f}")
        for name, target in (("coarse cell assignment", -1.0), ("Bennett density term", -2.0)):
            z = abs(slope - target) / max(se, 1e-9)
            print(f"      vs {name:24} ({target:+.0f}): {z:5.1f} sigma away")

    print()
    fit(biases, "raw bias against R/D")
    if floor is not None:
        print()
        fit(biases - floor, "bias with the bypass floor subtracted")
    return 0


if __name__ == "__main__":
    sys.exit(main())

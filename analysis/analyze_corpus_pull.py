"""Grid bias and residual shape on real music, from corpus_pull.py output.

Frames are kept when the estimator's own cross-check agrees within 20 cents on
both the input and the output (real music is polyphonic and the tracker will
sometimes lock to different partials before and after coding; those frames
carry no information about a small pull) and when the residual is within the
octave gate. Position within the semitone is the INPUT pitch's, so a pull
toward the grid appears as the same sign pattern as the synthetic sweeps:
negative residual just above a grid point, positive just below the next.

    python analyze_corpus_pull.py ../results/corpus_pull_encodec3.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "experiments", _ROOT / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from analyze_sweep import bootstrap_median_ci, fit_sinusoid  # noqa: E402

AGREE_CENTS = 20.0
GATE_CENTS = 200.0


def main() -> int:
    rows = list(csv.DictReader(Path(sys.argv[1]).open()))
    pos = np.array([float(r["position_cents"]) for r in rows])
    res = np.array([float(r["residual_cents"]) for r in rows])
    din = np.array([float(r["disagreement_in"]) for r in rows])
    dout = np.array([float(r["disagreement_out"]) for r in rows])
    keep = (np.nan_to_num(din, nan=1e9) <= AGREE_CENTS) & (np.nan_to_num(dout, nan=1e9) <= AGREE_CENTS) \
        & (np.abs(res) <= GATE_CENTS)
    print(f"  {len(rows)} frames, {keep.sum()} usable ({100*keep.mean():.0f}%)")
    pos, res = pos[keep], res[keep]
    # signed distance to the nearest grid point, in (-50, 50]
    delta = np.where(pos > 50, pos - 100, pos)
    bias = -np.sign(delta) * res
    on, off = np.abs(delta) <= 10, np.abs(delta) >= 30
    lo, hi = bootstrap_median_ci(bias[off])
    print(f"  input position within semitone: mean {pos.mean():.1f} cents (uniform expects 50)")
    print(f"  median |r| on-grid  {np.median(np.abs(res[on])):.3f} cents  (n={on.sum()})")
    print(f"  median |r| off-grid {np.median(np.abs(res[off])):.3f} cents  (n={off.sum()})")
    print(f"  grid bias, off-grid median {np.median(bias[off]):+.3f} cents  95% CI [{lo:+.3f}, {hi:+.3f}]")
    amp, ph, r2 = fit_sinusoid(pos, res)
    print(f"  100-cent sinusoid fit: amplitude {amp:.3f} cents, phase {ph:+.1f} deg, R2 {r2:.4f}")
    print("  (synthetic sweeps through EnCodec 3 kbps give phase about +155 deg and amplitude 13.9)")
    # binned residual, for the record
    edges = np.arange(0, 101, 10)
    print("\n  position   n     median r")
    for a, b in zip(edges[:-1], edges[1:]):
        m = (pos >= a) & (pos < b)
        if m.sum():
            print(f"  {a:3.0f}-{b:3.0f}  {m.sum():6d}  {np.median(res[m]):+8.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

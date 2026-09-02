"""Grid bias and residual shape on real music, from corpus_pull.py output.

Frames are kept when the estimator's own cross-check agrees within 20 cents on
both the input and the output (real music is polyphonic and the tracker will
sometimes lock to different partials before and after coding; those frames
carry no information about a small pull) and when the residual is within the
octave gate. Position within the semitone is the INPUT pitch's, so a pull
toward the grid appears as the same sign pattern as the synthetic sweeps:
negative residual just above a grid point, positive just below the next.

The confidence interval on the off-grid median is a percentile bootstrap that
resamples CLIPS, not frames: frames within a clip are strongly autocorrelated,
and a frame-level bootstrap understates the interval. The frame-level interval
is printed alongside for comparison. The exclusion rate is also reported per
10-cent bin of input position, because a selection that depended on where the
pitch sits within the semitone could sculpt a periodic residual on its own.

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


def clustered_median_ci(v: np.ndarray, cluster: np.ndarray, n_boot: int = 2000,
                        seed: int = 0) -> tuple[float, float]:
    """Percentile bootstrap of the median, resampling clusters (clips) with
    replacement and keeping every frame of each drawn clip."""
    units = np.unique(cluster)
    idx = {u: np.where(cluster == u)[0] for u in units}
    rng = np.random.default_rng(seed)
    meds = []
    for _ in range(n_boot):
        pick = rng.choice(units, units.size, replace=True)
        meds.append(np.median(np.concatenate([v[idx[u]] for u in pick])))
    return float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def main() -> int:
    rows = list(csv.DictReader(Path(sys.argv[1]).open()))
    pos = np.array([float(r["position_cents"]) for r in rows])
    res = np.array([float(r["residual_cents"]) for r in rows])
    din = np.array([float(r["disagreement_in"]) for r in rows])
    dout = np.array([float(r["disagreement_out"]) for r in rows])
    files = np.array([r["file"] for r in rows])
    keep = (np.nan_to_num(din, nan=1e9) <= AGREE_CENTS) & (np.nan_to_num(dout, nan=1e9) <= AGREE_CENTS) \
        & (np.abs(res) <= GATE_CENTS)
    print(f"  {len(rows)} frames from {len(set(files))} clips, {keep.sum()} usable "
          f"({100*keep.mean():.0f}%), from {len(set(files[keep]))} clips")
    # Exclusion per 10-cent bin of input position: flat means the selection
    # cannot be the source of a periodic residual.
    edges = np.arange(0, 101, 10)
    ex = [f"{100*(1-keep[(pos >= a) & (pos < b)].mean()):.0f}" for a, b in zip(edges[:-1], edges[1:])]
    print(f"  exclusion per 10-cent bin of input position (%): {' '.join(ex)}")
    pos, res, files = pos[keep], res[keep], files[keep]
    # signed distance to the nearest grid point, in (-50, 50]
    delta = np.where(pos > 50, pos - 100, pos)
    bias = -np.sign(delta) * res
    on, off = np.abs(delta) <= 10, np.abs(delta) >= 30
    lo, hi = clustered_median_ci(bias[off], files[off])
    flo, fhi = bootstrap_median_ci(bias[off])
    print(f"  input position within semitone: mean {pos.mean():.1f} cents (uniform expects 50)")
    print(f"  median |r| on-grid  {np.median(np.abs(res[on])):.3f} cents  (n={on.sum()})")
    print(f"  median |r| off-grid {np.median(np.abs(res[off])):.3f} cents  (n={off.sum()})")
    print(f"  grid bias, off-grid median {np.median(bias[off]):+.3f} cents  "
          f"95% CI [{lo:+.3f}, {hi:+.3f}] (bootstrap over clips)  "
          f"[{flo:+.3f}, {fhi:+.3f}] (over frames, for comparison)")
    amp, ph, r2 = fit_sinusoid(pos, res)
    print(f"  100-cent sinusoid fit: amplitude {amp:.3f} cents, phase {ph:+.1f} deg, R2 {r2:.4f}"
          f"  (R2 is against per-frame scatter and is small by construction)")
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

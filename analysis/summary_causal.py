"""Causal experiment summary over arms and seeds.

Reads results/ftm_<arm>_s<seed>.csv for every arm and seed present, fits the
registration regression to each (the same phase-and-amplitude fit as
analyze_detuning.py, octave gate only), and reports the mean residual
amplitude per arm with the seed-to-seed standard deviation, plus Welch t tests
of the flattened arm against each grid-preserving control.

Arms:
  grid     original clips
  gridres  every clip shifted up by exactly 100 cents (resampling control)
  gridmix  each clip shifted by 0 or 100 cents, mean 50 (magnitude-matched control)
  flat     each clip shifted by a uniform offset in [0, 100) cents (flattened grid)

    python summary_causal.py ../results                  # EnCodec arms, results/ftm_*
    python summary_causal.py ../results --prefix dacftm  # DAC 16 kHz arms, results/dacftm_*

Arms that have no files are skipped, so a prefix with only grid and flat
reports those two and the single flat-vs-grid test.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
from scipy import stats

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "experiments", _ROOT / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from analyze_sweep import fit_sinusoid, load  # noqa: E402

ARMS = ["grid", "gridres", "gridmix", "flat"]


def amplitude_and_slope(path: Path) -> tuple[float, float]:
    d = load(path)
    theta, rc = d["theta_cents"], d["residual_coded_cents"]
    keep = (d["octave_flag"] < 0.5) & np.isfinite(rc)
    offs = (1200.0 * np.log2(d["f1_nominal"] / 440.0)) % 100.0
    rows = []
    for k in sorted(set(np.round(offs, 3).tolist())):
        m = (np.round(offs, 3) == k) & keep
        if m.sum() < 50:
            continue
        amp, ph, _ = fit_sinusoid(theta[m], rc[m])
        rows.append((k, amp, ph))
    rows.sort()
    amps = np.array([r[1] for r in rows])
    x = np.array([r[0] for r in rows])
    phases = np.degrees(np.unwrap(np.radians([r[2] for r in rows])))
    phases -= phases[0]
    slope = np.polyfit(x, phases, 1)[0] / 3.6
    return float(amps.mean()), float(slope)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", nargs="?", type=Path, default=_ROOT / "results")
    ap.add_argument("--prefix", default="ftm",
                    help="file prefix: reads <prefix>_<arm>_s<seed>.csv (default ftm; "
                         "dacftm for the DAC 16 kHz arms)")
    opts = ap.parse_args()
    res = opts.results
    per_arm: dict[str, dict[int, tuple[float, float]]] = {a: {} for a in ARMS}
    pat = re.compile(rf"{re.escape(opts.prefix)}_([a-z]+)_s(\d+)\.csv")
    for p in sorted(res.glob(f"{opts.prefix}_*_s*.csv")):
        m = pat.match(p.name)
        if not m or m.group(1) not in per_arm:
            continue
        per_arm[m.group(1)][int(m.group(2))] = amplitude_and_slope(p)
    print(f"  {'arm':<8}{'seeds':>6}{'amplitude (c)':>16}{'sd':>7}{'slope range':>16}   per seed")
    means = {}
    for arm in ARMS:
        if not per_arm[arm]:
            continue
        seeds = sorted(per_arm[arm])
        a = np.array([per_arm[arm][s][0] for s in seeds])
        sl = np.array([per_arm[arm][s][1] for s in seeds])
        means[arm] = a
        print(f"  {arm:<8}{len(seeds):>6}{a.mean():16.2f}{a.std(ddof=1) if len(a) > 1 else 0:7.2f}"
              f"   [{sl.min():.3f}, {sl.max():.3f}]   " + " ".join(f"{v:.2f}" for v in a))
    if "flat" in means:
        print("\n  flattened arm against each grid-preserving control (Welch t):")
        for arm in ("grid", "gridres", "gridmix"):
            if arm not in means:
                continue
            t, p = stats.ttest_ind(means[arm], means["flat"], equal_var=False)
            v1, v2 = means[arm].var(ddof=1) / len(means[arm]), means["flat"].var(ddof=1) / len(means["flat"])
            df = (v1 + v2) ** 2 / (v1 ** 2 / (len(means[arm]) - 1) + v2 ** 2 / (len(means["flat"]) - 1))
            drop = 1 - means["flat"].mean() / means[arm].mean()
            print(f"    flat vs {arm:<8} drop {100*drop:5.1f}%   t = {t:6.2f}  df = {df:4.1f}  p = {p:.3g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

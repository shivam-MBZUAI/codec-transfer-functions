"""Is the vibrato trend a codec effect or an estimator artefact?

Vibrato increases the measured grid bias. That is the opposite of the
hypothesis it was meant to test, so before believing it we check the same
statistic on the UNCODED signal. If the estimator alone produces grid-aligned
structure on vibrato'd tones, the coded numbers cannot be attributed to the
codec, and the whole vibrato result is measurement.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np


def grid(t):
    return 100.0 * np.round(t / 100.0)


results = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../results")
print(f"  {'vibrato':<9}{'CODED bias':>12}{'UNCODED bias':>14}{'uncoded |r|':>13}{'n':>7}")
print("  " + "-" * 56)
for v in (0, 5, 10, 20, 40):
    p = results / f"vib_{v}.csv"
    if not p.exists():
        continue
    rows = [r for r in csv.DictReader(p.open())
            if r["reference_label"].endswith("ongrid")
            and r.get("octave_flag", "0") == "0"]
    th = np.array([float(r["theta_cents"]) for r in rows])
    rc = np.array([float(r["residual_coded_cents"]) for r in rows])
    ru = np.array([float(r["residual_uncoded_cents"]) for r in rows])
    ok = np.isfinite(rc) & np.isfinite(ru)
    th, rc, ru = th[ok], rc[ok], ru[ok]
    s = np.sign(grid(th) - th)
    print(f"  {str(v) + 'c':<9}{np.median(s * rc):12.3f}{np.median(s * ru):14.3f}"
          f"{np.median(np.abs(ru)):13.3f}{len(th):7d}")

print()
print("  A growing UNCODED bias means the estimator produces grid-aligned")
print("  structure on vibrato'd tones by itself, and the coded trend cannot be")
print("  attributed to the codec.")

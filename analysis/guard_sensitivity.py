"""Are the refusal guards doing the deciding, or the data?

analyze_detuning.py refuses to fit a phase regression when the per-condition
amplitude varies too much across detuning (cv > MAX_AMP_CV) or too few trials
survive the octave gate (retention < MIN_RETENTION). Both guards were written
after the SNAC 24 kHz run produced a slope from noise, so they are post hoc, and
the honest question is whether the reported table depends on where the limits
sit. This prints cv, retention and the octave-gate exclusion rate for every
detuning run, and the range of limits over which the set of measurable
conditions is unchanged.

    python guard_sensitivity.py ../results
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "experiments", _ROOT / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from analyze_sweep import fit_sinusoid, load  # noqa: E402
from analyze_detuning import MAX_AMP_CV, MIN_RETENTION  # noqa: E402

RUNS = ["detune_encodec3", "detune_encodec24kbps", "detune_encodec48", "detune_mimi",
        "detune_vowel_speechtok", "detune_dac16", "detune_snac32", "detune_vowel_encodec",
        "detune_dac24", "detune_snac44", "detune_dac44", "detune_snac"]


def guards(path: Path):
    d = load(path)
    theta, rc = d["theta_cents"], d["residual_coded_cents"]
    keep = d["octave_flag"] < 0.5
    offs = (1200.0 * np.log2(d["f1_nominal"] / 440.0)) % 100.0
    rows = []
    for k in sorted(set(np.round(offs, 3).tolist())):
        m = (np.round(offs, 3) == k) & keep & np.isfinite(rc)
        if m.sum() < 50:
            continue
        amp, _, _ = fit_sinusoid(theta[m], rc[m])
        rows.append((amp, int(m.sum())))
    amps = np.array([r[0] for r in rows])
    cv = float(amps.std() / amps.mean()) if amps.mean() else float("inf")
    retention = float(keep.mean())          # kept / total, so 1 - gated
    return cv, retention, 1.0 - float(keep.mean())


def main() -> int:
    res = Path(sys.argv[1]) if len(sys.argv) > 1 else _ROOT / "results"
    print(f"  {'run':<26}{'gate excl':>10}{'amp cv':>8}{'retention':>10}   verdict at "
          f"(cv <= {MAX_AMP_CV}, retention >= {MIN_RETENTION})")
    passed, refused = [], []
    for name in RUNS:
        p = res / f"{name}.csv"
        if not p.exists():
            continue
        cv, ret, ex = guards(p)
        ok = cv <= MAX_AMP_CV and ret >= MIN_RETENTION
        (passed if ok else refused).append((name, cv, ret))
        print(f"  {name:<26}{100*ex:9.1f}%{cv:8.3f}{ret:10.2f}   {'measurable' if ok else 'REFUSED'}")
    cv_lo = max(c for _, c, _ in passed)
    cv_hi = min(c for _, c, _ in refused if c > MAX_AMP_CV) if any(c > MAX_AMP_CV for _, c, _ in refused) else float("inf")
    r_hi = min(r for _, _, r in passed)
    r_lo = max(r for _, _, r in refused if r < MIN_RETENTION) if any(r < MIN_RETENTION for _, _, r in refused) else 0.0
    print(f"\n  the same set of conditions is measurable for any cv limit in "
          f"[{cv_lo:.2f}, {cv_hi:.2f}) and any retention limit in ({r_lo:.2f}, {r_hi:.2f}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())

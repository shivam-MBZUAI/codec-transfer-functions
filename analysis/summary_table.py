"""One table of every phase-lock measurement in the programme.

The phase regression is the paper's primary instrument, not the bias median.
DAC and SpeechTokenizer both read as null on the median and both show an
unambiguous unit-slope lock under the regression, so anyone repeating this with
aggregate error statistics would wrongly conclude high-fidelity and speech-only
codecs are unaffected.

Registration (slope near 1) and PULL (a grid-directed sign) are different
claims, so the table carries both: the on-grid phase of the fitted residual,
which for a pull sits near EnCodec's +155 degrees, and the off-grid median grid
bias with a bootstrap interval, which for a pull is positive. Conditions whose
amplitude is a cent or two register without a resolvable direction, and the
paper says so rather than calling every registered condition a pull. The
octave-gate exclusion rate is listed per run because it is not zero everywhere.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "experiments", _ROOT / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from analyze_sweep import bootstrap_median_ci, fit_sinusoid, load  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
ANA = ROOT / "analysis"

RUNS = [
    # (file stem, codec, operating point, stimulus family)
    ("detune_encodec3",           "EnCodec 24k",        "3 kbps",   "tones"),
    ("detune_encodec24kbps",      "EnCodec 24k",        "24 kbps",  "tones"),
    ("detune_encodec48",          "EnCodec 48k, music", "6 kbps",   "tones"),
    ("detune_mimi",               "Mimi",               "Q8",       "tones"),
    ("detune_dac16",              "DAC 16k",            "Q6",       "tones"),
    ("detune_dac24",              "DAC 24k",            "Q8",       "tones"),
    ("detune_dac44",              "DAC 44k",            "Q4",       "tones"),
    ("detune_snac",               "SNAC 24k",           "default",  "tones"),
    ("detune_snac32",             "SNAC 32k",           "default",  "tones"),
    ("detune_snac44",             "SNAC 44k",           "default",  "tones"),
    ("detune_vowel_speechtok",    "SpeechTokenizer",    "Q8",       "vowels"),
    ("detune_vowel_encodec",      "EnCodec 24k",        "3 kbps",   "vowels"),
    ("ftm_grid",                  "EnCodec, FT grid",   "3 kbps",   "tones"),
    ("ftm_flat",                  "EnCodec, FT flat",   "3 kbps",   "tones"),
]


def direction(name: str) -> dict:
    """On-grid phase, off-grid grid bias with interval, and gate exclusion."""
    d = load(ROOT / "results" / f"{name}.csv")
    theta, rc = d["theta_cents"], d["residual_coded_cents"]
    keep = d["octave_flag"] < 0.5 if "octave_flag" in d else np.ones_like(theta, dtype=bool)
    # The on-grid reference proper (440 Hz), not the 100-cent point that folds
    # onto it in the phase regression: the bias is a 440 Hz number in the paper.
    f1 = d["f1_nominal"]
    offs = (1200.0 * np.log2(f1 / 440.0)) % 100.0
    base = (np.round(offs, 3) == 0)
    on = base & (f1 < f1[base].min() + 0.01) & keep & np.isfinite(rc)
    amp, ph, _ = fit_sinusoid(theta[on], rc[on])
    g = 100.0 * np.round(theta[on] / 100.0)
    delta = theta[on] - g
    off = np.abs(delta) >= 30
    b = -np.sign(delta[off]) * rc[on][off]
    lo, hi = bootstrap_median_ci(b)
    return {"phase": ph, "bias": float(np.median(b)), "lo": lo, "hi": hi,
            "excl": 1.0 - float(keep.mean())}


def parse(name: str):
    p = ROOT / "results" / f"{name}.csv"
    if not p.exists():
        return None
    # Octave gate only, the scheme used throughout the paper. The estimator
    # cross-check would discard most trials for the speech-shaped stimuli and
    # trip the retention guard for reasons unrelated to what is measured.
    out = subprocess.run([sys.executable, str(ANA / "analyze_detuning.py"), str(p),
                          "--exclusion=gate"],
                         capture_output=True, text=True, cwd=str(ANA)).stdout
    if "REFUSING TO FIT" in out:
        why = "unstable amplitude" if "amplitude varies" in out else "estimator failing"
        return {"refused": why}
    got = {}
    for line in out.splitlines():
        if "relative slope" in line:
            got["slope"] = float(line.split()[2])
        elif line.strip().startswith("95% CI"):
            got["ci"] = line.split("[")[1].split("]")[0]
        elif line.strip().startswith("R2"):
            got["r2"] = float(line.split()[1])
        elif line.strip().startswith("amplitude"):
            parts = line.split()
            got["amp"] = float(parts[1]); got["amp_sd"] = float(parts[3])
    return got or None


print(f"{'codec':<20}{'rate':<10}{'stimulus':<9}{'amp (c)':>12}{'slope':>9}"
      f"{'95% CI':>18}{'R2':>9}{'phase':>7}{'off-grid bias (c)':>24}{'gated':>7}")
print("-" * 126)
for name, codec, rate, stim in RUNS:
    g = parse(name)
    if not g:
        print(f"{codec:<20}{rate:<10}{stim:<9}{'still running':>49}")
        continue
    if "refused" in g:
        print(f"{codec:<20}{rate:<10}{stim:<9}"
              f"{'NOT MEASURABLE: ' + g['refused']:>49}")
        continue
    dd = direction(name)
    print(f"{codec:<20}{rate:<10}{stim:<9}{g['amp']:8.2f}+-{g['amp_sd']:<4.2f}"
          f"{g['slope']:9.4f}{'[' + g['ci'] + ']':>18}{g['r2']:9.5f}{dd['phase']:+7.0f}"
          f"{dd['bias']:+8.2f} [{dd['lo']:+.2f}, {dd['hi']:+.2f}]{100*dd['excl']:6.1f}%")
print("\n  slope 1.0 = residual locked to the absolute 12-TET grid")
print("  slope 0.0 = locked to the interval, i.e. an analysis artefact")
print("  phase = on-grid-reference phase of the fitted residual; a pull toward the")
print("  grid sits near +155 deg (EnCodec). off-grid bias = median grid bias over")
print("  |delta| >= 30 cents at the on-grid reference, bootstrap 95% interval.")
print("  gated = share of trials the octave gate removes.")
print("\n  NOT MEASURABLE means the guard refused to fit: either the amplitude")
print("  swings across conditions when the theory says it should be flat, or")
print("  too few trials survive for the phases to mean anything. A slope fitted")
print("  through those phases is a confident number from noise.")

"""One table of every phase-lock measurement in the programme.

The phase regression is the paper's primary instrument, not the bias median.
DAC and SpeechTokenizer both read as null on the median and both show an
unambiguous unit-slope lock under the regression, so anyone repeating this with
aggregate error statistics would wrongly conclude high-fidelity and speech-only
codecs are unaffected.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "experiments"

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


def parse(name: str):
    p = ROOT / "results" / f"{name}.csv"
    if not p.exists():
        return None
    out = subprocess.run([sys.executable, str(EXP / "analyze_detuning.py"), str(p),
                          "--exclusion=gate"],
                         capture_output=True, text=True, cwd=str(EXP)).stdout
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
        elif "amplitude" in line:
            parts = line.split()
            got["amp"] = float(parts[1]); got["amp_sd"] = float(parts[3])
    return got or None


print(f"{'codec':<20}{'rate':<10}{'stimulus':<9}{'amp (c)':>12}{'slope':>9}"
      f"{'95% CI':>18}{'R2':>10}")
print("-" * 88)
for name, codec, rate, stim in RUNS:
    g = parse(name)
    if not g:
        print(f"{codec:<20}{rate:<10}{stim:<9}{'still running':>49}")
        continue
    if "refused" in g:
        print(f"{codec:<20}{rate:<10}{stim:<9}"
              f"{'NOT MEASURABLE: ' + g['refused']:>49}")
        continue
    print(f"{codec:<20}{rate:<10}{stim:<9}{g['amp']:8.2f}+-{g['amp_sd']:<4.2f}"
          f"{g['slope']:9.4f}{'[' + g['ci'] + ']':>18}{g['r2']:10.5f}")
print("\n  slope 1.0 = residual locked to the absolute 12-TET grid")
print("  slope 0.0 = locked to the interval, i.e. an analysis artefact")
print("\n  NOT MEASURABLE means the guard refused to fit: either the amplitude")
print("  swings across conditions when the theory says it should be flat, or")
print("  too few trials survive for the phases to mean anything. A slope fitted")
print("  through those phases is a confident number from noise.")

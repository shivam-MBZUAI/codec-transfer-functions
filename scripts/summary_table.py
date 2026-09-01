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
    ("detune_encodec3",           "EnCodec 24k",        "3 kbps",  "tones"),
    ("detune_mimi",               "Mimi",               "Q8",      "tones"),
    ("detune_dac16",              "DAC 16k",            "Q6",      "tones"),
    ("detune_vowel_speechtok",    "SpeechTokenizer",    "Q8",      "vowels"),
    ("detune_vowel_encodec",      "EnCodec 24k",        "3 kbps",  "vowels"),
]


def parse(name: str):
    p = ROOT / "results" / f"{name}.csv"
    if not p.exists():
        return None
    out = subprocess.run([sys.executable, str(EXP / "analyze_detuning.py"), str(p),
                          "--exclusion=gate"],
                         capture_output=True, text=True, cwd=str(EXP)).stdout
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


print(f"{'codec':<18}{'rate':<9}{'stimulus':<9}{'amp (c)':>10}{'slope':>9}"
      f"{'95% CI':>18}{'R2':>10}")
print("-" * 83)
for name, codec, rate, stim in RUNS:
    g = parse(name)
    if not g:
        print(f"{codec:<18}{rate:<9}{stim:<9}{'not yet measured':>47}")
        continue
    print(f"{codec:<18}{rate:<9}{stim:<9}{g['amp']:7.2f}+-{g['amp_sd']:<4.2f}"
          f"{g['slope']:9.4f}{'[' + g['ci'] + ']':>18}{g['r2']:10.5f}")
print("\n  slope 1.0 = residual locked to the absolute 12-TET grid")
print("  slope 0.0 = locked to the interval, i.e. an analysis artefact")

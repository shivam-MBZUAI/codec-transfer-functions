"""Build a tuning-smeared copy of a music corpus.

The causal experiment needs training audio whose pitch density differs in
exactly one respect: whether it is grid-peaked. Synthetic tones failed at this,
because any codec trained on them becomes too good at them and the effect
disappears regardless of pitch distribution.

Real music solves that, and the manipulation is simple. Resampling a clip by a
random factor within one semitone shifts every pitch in it by a constant offset.
Individually each clip is still ordinary tuned music; in aggregate, offsets drawn
uniformly across the semitone smear the 12-TET peaks flat. Instrument timbre,
spectral balance, note density, production and dynamics are untouched, so the
only thing that differs between the two corpora is the position of the tuning
grid.

    python make_detuned_corpus.py --src /workspace/corpora/gtzan \\
        --dst /workspace/corpora/gtzan_detuned
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import soundfile as sf


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", required=True, type=Path)
    p.add_argument("--dst", required=True, type=Path)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-files", type=int, default=400)
    args = p.parse_args()

    rng = np.random.default_rng(args.seed)
    files = sorted(q for ext in ("*.wav", "*.au", "*.flac", "*.mp3")
                   for q in args.src.rglob(ext))[: args.max_files]
    if not files:
        raise SystemExit(f"no audio under {args.src}")
    args.dst.mkdir(parents=True, exist_ok=True)

    n = 0
    for f in files:
        try:
            x, sr = sf.read(str(f), dtype="float64", always_2d=False)
        except Exception:
            continue
        if x.ndim > 1:
            x = x.mean(axis=1)
        # Offset uniform over the full semitone: individually a normal tuning
        # reference, in aggregate a flat within-semitone density.
        offset = float(rng.uniform(0.0, 100.0))
        ratio = 2.0 ** (offset / 1200.0)
        idx = np.arange(0, len(x) - 1, ratio)
        lo = idx.astype(int)
        frac = idx - lo
        y = x[lo] * (1 - frac) + x[lo + 1] * frac
        sf.write(str(args.dst / f"{f.stem}_{offset:05.1f}c.wav"), y, sr)
        n += 1
        if n % 100 == 0:
            print(f"  {n}/{len(files)}", flush=True)
    print(f"wrote {n} detuned clips to {args.dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Ecological test: real instrument recordings, shifted off the grid.

Synthetic stimuli isolate the mechanism but say nothing about real audio. The
makam corpus that would answer this is access-restricted, so this is the
unblocked route to the same claim.

Take real instrument notes at known pitches, resample each by a known offset so
it sits a controlled distance from the nearest 12-TET pitch, push it through the
codec, and measure where it comes back. If the codec carries a grid prior, notes
placed between grid points should be pulled toward them, and the displacement
should follow the same one-semitone period as the synthetic sweeps.

Unlike the synthetic tones these carry real instrument timbre, attack, decay and
recording conditions, none of which the measurement controls.

    python retune_real.py --audio-root /workspace/corpora/nsynth --codec encodec:3 \\
        --out ../results/retune_encodec3.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import codec_zoo  # noqa: E402
from estimator import estimate_f0  # noqa: E402
from stimuli import ratio_to_cents  # noqa: E402


def resample_by_cents(x: np.ndarray, cents: float) -> np.ndarray:
    """Shift pitch by resampling. Duration changes too, which does not matter
    here: the measurement is of steady-state pitch, not of timing."""
    ratio = 2.0 ** (cents / 1200.0)
    idx = np.arange(0, len(x) - 1, ratio)
    lo = idx.astype(int)
    frac = idx - lo
    return x[lo] * (1 - frac) + x[lo + 1] * frac


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--audio-root", required=True, type=Path)
    p.add_argument("--codec", default="encodec:3")
    p.add_argument("--offsets", type=float, nargs="+",
                   default=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90])
    p.add_argument("--max-files", type=int, default=120)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    import soundfile as sf
    import scipy.signal as sps

    codec = codec_zoo.build(args.codec)
    sr = codec.sample_rate
    files = sorted(q for ext in ("*.wav", "*.flac")
                   for q in args.audio_root.rglob(ext))[: args.max_files]
    if not files:
        raise SystemExit(f"no audio under {args.audio_root}")
    print(f"{len(files)} notes, {len(args.offsets)} offsets, codec {codec.name}",
          flush=True)

    rows = []
    for i, f in enumerate(files):
        try:
            x, file_sr = sf.read(str(f), dtype="float64", always_2d=False)
        except Exception:
            continue
        if x.ndim > 1:
            x = x.mean(axis=1)
        if file_sr != sr:
            x = sps.resample_poly(x, sr, file_sr)
        # Steady portion: skip the attack, which is inharmonic.
        n = len(x)
        x = x[int(0.15 * n): int(0.75 * n)]
        if len(x) < sr // 4:
            continue

        for off in args.offsets:
            shifted = resample_by_cents(x, off)
            peak = float(np.abs(shifted).max())
            if peak < 1e-6:
                continue
            shifted = shifted / peak * 0.7
            f_in, _ = estimate_f0(shifted, sr, n_partials=12)
            if not np.isfinite(f_in) or f_in <= 0:
                continue
            coded = codec(shifted)
            f_out, f_x = estimate_f0(coded, sr, n_partials=12)
            if not np.isfinite(f_out) or f_out <= 0:
                continue
            # Position of the INPUT note within the semitone, and how far the
            # codec moved it.
            cents_in = 1200.0 * np.log2(f_in / 440.0)
            within = cents_in % 100.0
            g = round(cents_in / 100.0) * 100.0
            shift = ratio_to_cents(f_out / f_in)
            toward_grid = np.sign(g - cents_in) * shift
            rows.append(dict(file=f.name, offset=off, f_in=f_in, f_out=f_out,
                             cents_in=cents_in, within_semitone=within,
                             shift_cents=shift, toward_grid=toward_grid,
                             disagreement=ratio_to_cents(f_out / f_x)
                             if f_x > 0 else float("nan")))
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(files)} notes, {len(rows)} measurements", flush=True)

    if not rows:
        raise SystemExit("no usable measurements")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {args.out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

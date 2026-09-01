"""F0 histograms of real corpora: is the training density actually grid-peaked?

Proposition 1 predicts the residual from p(theta), the pitch density of the
codec's training audio. No released codec publishes that audio, which is why the
draft treats the proposition as qualitative. But the corpora are named, and
histograms converge on a few thousand clips.

  LibriSpeech  SpeechTokenizer's ENTIRE training set. Speech F0 is smooth, not
               grid-peaked, so Proposition 1 predicts NO 12-TET structure there.
  GTZAN        Western popular music: the grid-peaked case, and a stand-in for
               the music fraction of EnCodec's and DAC's named mixtures.

The output is the distribution of F0 modulo 100 cents relative to A440. A
grid-peaked corpus concentrates near 0; a smooth one is flat.

    python pitch_histogram.py --corpus gtzan --out ../results/hist_gtzan.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
import tarfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from estimator import estimate_f0_yin  # noqa: E402


def frames(x: np.ndarray, sr: int, win: float = 0.064, hop: float = 0.032):
    n, h = int(win * sr), int(hop * sr)
    for i in range(0, max(0, len(x) - n), h):
        yield x[i:i + n]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--audio-root", required=True, type=Path)
    p.add_argument("--max-files", type=int, default=300)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    import soundfile as sf
    files = [q for ext in ("*.wav", "*.flac", "*.au", "*.mp3")
             for q in args.audio_root.rglob(ext)][: args.max_files]
    if not files:
        raise SystemExit(f"no audio under {args.audio_root}")
    print(f"{len(files)} files", flush=True)

    cents = []
    for i, f in enumerate(files):
        try:
            x, sr = sf.read(str(f), dtype="float64", always_2d=False)
        except Exception:
            continue
        if x.ndim > 1:
            x = x.mean(axis=1)
        for seg in frames(x, sr):
            if float(np.sqrt((seg ** 2).mean())) < 1e-3:
                continue
            f0 = estimate_f0_yin(seg, sr, fmin=70.0, fmax=1200.0)
            if np.isfinite(f0) and 70 < f0 < 1200:
                cents.append(1200.0 * np.log2(f0 / 440.0))
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(files)} files, {len(cents)} f0 estimates", flush=True)

    cents = np.array(cents)
    within = cents % 100.0
    hist, edges = np.histogram(within, bins=50, range=(0, 100), density=True)
    # A flat density is 0.01 per cent; the peak-to-mean ratio quantifies how
    # grid-peaked the corpus is without assuming a functional form.
    ratio = float(hist.max() / hist.mean()) if hist.mean() else float("nan")
    print(f"\n  {len(cents)} F0 estimates")
    print(f"  peak/mean of the within-semitone density: {ratio:.3f}  "
          f"(1.0 = flat, higher = grid-peaked)")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["bin_lo_cents", "bin_hi_cents", "density"])
        for lo, hi, d in zip(edges[:-1], edges[1:], hist):
            w.writerow([f"{lo:.2f}", f"{hi:.2f}", f"{d:.6f}"])
    print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Experiment 2: which phonological contrasts survive a codec round trip.

For each language we push FLEURS test utterances through a codec and measure two
quantities on the round trip:

  F0 contour error   in cents over VOICED frames, which is where lexical tone
                     lives, and is commensurable with the pitch experiments
  log-spectral dist  over all frames, for contrasts whose cues are spectral and
                     transient rather than pitch-borne

Ratios are always taken against the non-tonal control measured with the same
metric, never compared across metrics, since the two share no scale.

Two limitations to state rather than hide. Error is computed over voiced frames
rather than over forced-aligned contrast-bearing segments, so a localised effect
is diluted toward zero and these ratios are conservative. And FLEURS fixes
semantic content, not phonetic content, so speaker, recording condition and rate
vary; per-speaker aggregation is reported where FLEURS supplies gender, which is
a coarse proxy for speaker identity.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codec_zoo  # noqa: E402
from estimator import estimate_f0_yin  # noqa: E402
from fleurs_data import utterances  # noqa: E402
from languages import EXPLORATORY, GROUPS, group_of  # noqa: E402


def f0_contour(x: np.ndarray, sr: int, hop: float = 0.01, win: float = 0.04):
    n, h = int(win * sr), int(hop * sr)
    out = []
    for i in range(0, max(0, len(x) - n), h):
        seg = x[i:i + n]
        if float(np.sqrt((seg ** 2).mean())) < 5e-3:
            out.append(np.nan)
            continue
        f0 = estimate_f0_yin(seg, sr, fmin=60.0, fmax=500.0)
        out.append(f0 if np.isfinite(f0) and 60 < f0 < 500 else np.nan)
    return np.array(out)


def log_spectral_distance(a: np.ndarray, b: np.ndarray, sr: int, n_fft: int = 512):
    w = np.hanning(n_fft)
    h = n_fft // 4
    n = min(len(a), len(b))
    vals = []
    for i in range(0, n - n_fft, h):
        A = np.abs(np.fft.rfft(a[i:i + n_fft] * w)) + 1e-8
        B = np.abs(np.fft.rfft(b[i:i + n_fft] * w)) + 1e-8
        vals.append(np.sqrt(np.mean((20 * np.log10(A / B)) ** 2)))
    return float(np.median(vals)) if vals else float("nan")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--codec", default="encodec:3")
    p.add_argument("--per-language", type=int, default=40)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    import scipy.signal as sps

    codec = codec_zoo.build(args.codec)
    csr = codec.sample_rate
    langs = [l for v in GROUPS.values() for l in v] + \
            [l for v in EXPLORATORY.values() for l in v]

    rows = []
    for li, lang in enumerate(langs):
        got = 0
        for name, x, sr, meta in utterances(lang, limit=args.per_language):
            y = sps.resample_poly(x, csr, sr) if sr != csr else x
            coded = codec(y)
            back = sps.resample_poly(coded, sr, csr) if sr != csr else coded
            n = min(len(x), len(back))
            xa, ba = x[:n], back[:n]

            fa, fb = f0_contour(xa, sr), f0_contour(ba, sr)
            m = np.isfinite(fa) & np.isfinite(fb)
            cents = (1200.0 * np.log2(fb[m] / fa[m])) if m.sum() else np.array([])
            # Frames where the estimator jumps an octave are estimator failures,
            # not codec effects; the pitch experiments use the same 200-cent gate.
            cents = cents[np.abs(cents) < 200]

            rows.append(dict(
                lang=lang, group=group_of(lang) or "exploratory", file=name,
                gender=meta.get("gender", ""),
                voiced_frames=int(m.sum()),
                f0_err_cents=float(np.median(np.abs(cents))) if cents.size else float("nan"),
                lsd_db=log_spectral_distance(xa, ba, sr),
            ))
            got += 1
        print(f"  [{li+1}/{len(langs)}] {lang}: {got} utterances", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {args.out} ({len(rows)} utterances)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

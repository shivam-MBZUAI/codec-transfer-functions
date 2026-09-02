"""The transfer function on real, polyphonic music.

The ecological test of retune_real.py uses isolated NSynth notes, which are
arguably as unnatural as the synthetic tones. This script measures the same
thing on whole music clips: every clip is coded, F0 is tracked frame by frame
before and after coding with the same blind estimator, and the per-frame
residual r = 1200 log2(f_out / f_in) is studied as a function of where the
input pitch falls within the semitone, exactly as the sweeps do for theta.

Run it on the tuning-flattened corpus of make_detuned_corpus.py so the input
positions are uniform within the semitone; on the original corpus they pile up
near the grid and the off-grid band is thin.

Output is one row per voiced frame: position within the semitone, residual,
and the input and output F0, so analysis/analyze_corpus_pull.py can compute
the grid bias, the sinusoid fit, and its phase. A pull toward the grid on real
music gives the same period, sign and phase as the synthetic sweeps; a null
gives a flat residual.

    python corpus_pull.py --audio-root corpora/gtzan_detuned --codec encodec:3 \
        --out ../results/corpus_pull_encodec3.csv
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codec_zoo  # noqa: E402
from estimator import estimate_f0  # noqa: E402

WIN_S, HOP_S = 0.064, 0.032
FMIN, FMAX = 80.0, 1000.0


def load_mono(path: str, sr: int) -> np.ndarray:
    x, fs = sf.read(path, dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if fs != sr:
        g = np.gcd(int(fs), int(sr))
        x = resample_poly(x, sr // g, fs // g).astype(np.float32)
    peak = float(np.abs(x).max())
    return x * (0.7 / peak) if peak > 0 else x


def frame_f0(x: np.ndarray, sr: int):
    win, hop = int(WIN_S * sr), int(HOP_S * sr)
    out = []
    for start in range(0, len(x) - win, hop):
        seg = x[start:start + win].astype(np.float64)
        if float(np.sqrt((seg ** 2).mean())) < 1e-3:
            out.append((float("nan"), float("nan"))); continue
        a, b = estimate_f0(seg, sr, n_partials=6, fmin=FMIN, fmax=FMAX)
        out.append((a, b))
    return np.array(out, dtype=np.float64)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--audio-root", required=True, type=Path)
    p.add_argument("--codec", default="encodec:3")
    p.add_argument("--max-files", type=int, default=200)
    p.add_argument("--clip-seconds", type=float, default=10.0)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    codec = codec_zoo.build(args.codec)
    sr = codec.sample_rate
    files = sorted(f for ext in ("wav", "flac", "au", "mp3")
                   for f in glob.glob(str(args.audio_root / "**" / f"*.{ext}"), recursive=True))[: args.max_files]
    if not files:
        raise SystemExit(f"no audio under {args.audio_root}")
    print(f"{len(files)} clips through {codec.name} {codec.rate_label} at {sr} Hz", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    cols = ["file", "frame", "f_in", "f_out", "f_in_cross", "f_out_cross",
            "position_cents", "residual_cents", "disagreement_in", "disagreement_out"]
    t0 = time.time(); n_rows = 0
    with open(args.out, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(cols)
        for i, f in enumerate(files):
            x = load_mono(f, sr)[: int(args.clip_seconds * sr)]
            y = codec(x)
            fin, fout = frame_f0(x, sr), frame_f0(y, sr)
            n = min(len(fin), len(fout))
            for k in range(n):
                a_in, b_in = fin[k]; a_out, b_out = fout[k]
                if not (np.isfinite(a_in) and np.isfinite(a_out)) or a_in <= 0 or a_out <= 0:
                    continue
                pos = (1200.0 * np.log2(a_in / 440.0)) % 100.0
                res = 1200.0 * np.log2(a_out / a_in)
                dis_in = 1200.0 * abs(np.log2(b_in / a_in)) if np.isfinite(b_in) and b_in > 0 else float("nan")
                dis_out = 1200.0 * abs(np.log2(b_out / a_out)) if np.isfinite(b_out) and b_out > 0 else float("nan")
                w.writerow([Path(f).name, k, f"{a_in:.4f}", f"{a_out:.4f}",
                            f"{b_in:.4f}" if np.isfinite(b_in) else "nan",
                            f"{b_out:.4f}" if np.isfinite(b_out) else "nan",
                            f"{pos:.3f}", f"{res:.4f}",
                            f"{dis_in:.3f}" if np.isfinite(dis_in) else "nan",
                            f"{dis_out:.3f}" if np.isfinite(dis_out) else "nan"])
                n_rows += 1
            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{len(files)} clips, {n_rows} frames, {time.time()-t0:.0f}s", flush=True)
    meta = {"args": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
            "codec": codec.name, "rate_label": codec.rate_label, "sample_rate": sr,
            "frames": n_rows, "clips": len(files)}
    args.out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote {args.out} ({n_rows} frames)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

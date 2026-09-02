"""Observe the mechanism directly in the codec's own code assignments.

Everything else in this programme infers the mechanism from reconstruction
error. This looks at what the quantiser actually does: sweep pitch densely,
record which code indices fire at each RVQ level, and ask where the assignment
boundaries fall.

If a codec allocates its codes according to pitch statistics absorbed from
Western training audio, the boundaries between code assignments should cluster
near 12-TET grid points, and the number of distinct codes used per unit pitch
should peak there. That is a picture of the mechanism rather than an inference
from its consequences.

    python probe_codebook.py --codec encodec:3 --out ../results/probe_encodec3.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codec_zoo  # noqa: E402
from stimuli import harmonic_tone  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--codec", default="encodec:3")
    p.add_argument("--f-lo", type=float, default=220.0)
    p.add_argument("--f-hi", type=float, default=880.0)
    p.add_argument("--step-cents", type=float, default=2.0)
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    name, _, arg = args.codec.partition(":")
    if not name.startswith("encodec"):
        raise SystemExit("codebook probing is wired for EnCodec only so far")

    from transformers import EncodecModel
    device = codec_zoo._device()
    model = EncodecModel.from_pretrained("facebook/encodec_24khz").to(device).eval()
    sr = model.config.sampling_rate
    bandwidth = float(arg or 3.0)

    span = 1200.0 * np.log2(args.f_hi / args.f_lo)
    cents = np.arange(0.0, span, args.step_cents)
    rows = []
    for i, c in enumerate(cents):
        f0 = args.f_lo * 2.0 ** (c / 1200.0)
        for rep in range(args.reps):
            rng = np.random.default_rng(1000 * rep + i)
            x = harmonic_tone(f0, 0.5, sr, rng, n_partials=8)
            with torch.no_grad():
                wav = torch.from_numpy(x).float()[None, None, :].to(device)
                enc = model.encode(wav, bandwidth=bandwidth)
            # audio_codes: (n_chunks, batch, n_quantizers, n_frames)
            codes = enc.audio_codes.squeeze().cpu().numpy()
            if codes.ndim == 1:
                codes = codes[None, :]
            row = {"cents": float(c), "f0": float(f0), "rep": rep}
            for q in range(codes.shape[0]):
                vals, counts = np.unique(codes[q], return_counts=True)
                row[f"q{q}_mode"] = int(vals[int(np.argmax(counts))])
                row[f"q{q}_nuniq"] = int(len(vals))
            rows.append(row)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(cents)} pitches", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {args.out}  ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

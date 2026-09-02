"""Causal test by fine-tuning a working codec on a controlled pitch density.

Training an RVQ from scratch on this task turned out to be the wrong instrument.
Such a model either collapses to silence or reproduces only the fundamental
(h2/h1 falls from 0.500 to 0.003), and EnCodec shows no grid effect on pure
sinusoids either, so a codec that outputs near-sinusoids cannot exhibit the
phenomenon whatever it was trained on.

Fine-tuning sidesteps that entirely. EnCodec already reconstructs harmonic
complexes well and already carries the grid lock, at 13.8 cents amplitude. We
change exactly one thing, the pitch density of the audio it continues training
on, and measure whether the lock moves:

    uniform   pitches uniform in cents      -> lock should WEAKEN
    12tet     pitches on 12-TET semitones   -> lock should persist or strengthen
    53tet     pitches on a 53-tone division -> lock should shift to that grid

The 53-TET arm is the strongest form: a mechanism that merely degrades pitch
cannot move the lock to a different grid, while one that absorbs training
statistics must.

Low learning rate and few steps on purpose: the point is to shift the pitch
prior, not to retrain the codec into something else. The magnitude of the
reconstruction error is monitored so catastrophic forgetting is visible rather
than silently confounding the result.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_rvq import make_batch, stft_loss  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--distribution", default=None,
                   choices=["12tet", "uniform", "53tet"],
                   help="synthetic tone distribution (the confounded design)")
    p.add_argument("--audio-root", type=Path, default=None,
                   help="fine-tune on REAL audio from this directory instead. "
                        "This is the design that works: broad audio means the "
                        "codec cannot overfit the stimulus family, so the "
                        "training pitch density is the only thing that varies.")
    p.add_argument("--steps", type=int, default=3000)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--lr", type=float, default=1e-5)
    p.add_argument("--bandwidth", type=float, default=3.0)
    p.add_argument("--wave-weight", type=float, default=10.0)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    if (args.distribution is None) == (args.audio_root is None):
        raise SystemExit("give exactly one of --distribution or --audio-root")

    from transformers import EncodecModel
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = EncodecModel.from_pretrained("facebook/encodec_24khz").to(dev)
    sr = model.config.sampling_rate
    model.train()

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    rng = np.random.default_rng(0)

    clips = None
    if args.audio_root is not None:
        import soundfile as sf
        import scipy.signal as sps
        paths = sorted(q for ext in ("*.wav", "*.au", "*.flac")
                       for q in args.audio_root.rglob(ext))
        if not paths:
            raise SystemExit(f"no audio under {args.audio_root}")
        clips = []
        for q in paths:
            try:
                x, file_sr = sf.read(str(q), dtype="float64", always_2d=False)
            except Exception:
                continue
            if x.ndim > 1:
                x = x.mean(axis=1)
            if file_sr != sr:
                x = sps.resample_poly(x, sr, file_sr)
            if len(x) > sr:
                clips.append(x.astype(np.float32))
        print(f"loaded {len(clips)} clips from {args.audio_root}", flush=True)

    label = args.distribution or str(args.audio_root)
    print(f"fine-tuning EnCodec on '{label}', {args.steps} steps at lr {args.lr}",
          flush=True)

    def next_batch():
        if clips is None:
            return make_batch(args.distribution, args.batch, sr, 0.5, rng, device=dev)
        n = int(0.5 * sr)
        out = np.empty((args.batch, 1, n), dtype=np.float32)
        for i in range(args.batch):
            c = clips[rng.integers(len(clips))]
            j = int(rng.integers(0, max(1, len(c) - n)))
            seg = c[j:j + n]
            if len(seg) < n:
                seg = np.pad(seg, (0, n - len(seg)))
            peak = float(np.abs(seg).max())
            out[i, 0] = seg / peak * 0.7 if peak > 1e-6 else seg
        return torch.from_numpy(out).to(dev)

    for step in range(1, args.steps + 1):
        x = next_batch()
        enc = model.encode(x, bandwidth=args.bandwidth)
        y = model.decode(enc.audio_codes, enc.audio_scales,
                         last_frame_pad_length=enc.last_frame_pad_length).audio_values
        y = y[..., : x.shape[-1]]
        loss = stft_loss(y, x) + args.wave_weight * F.l1_loss(y, x)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if step % 500 == 0 or step == 1:
            with torch.no_grad():
                ratio = float(y.pow(2).mean().sqrt() / x.pow(2).mean().sqrt())
            print(f"  step {step:5d}/{args.steps}  loss {loss.item():.4f}  "
                  f"rms ratio {ratio:.3f}", flush=True)
            if step > 500 and ratio < 0.3:
                raise SystemExit("ABORT: fine-tuning destroyed reconstruction; "
                                 "a codec that reconstructs nothing has no "
                                 "transfer function to compare.")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    model.eval()
    model.save_pretrained(args.out)
    args.out.with_suffix(".json").write_text(json.dumps(
        {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
        indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

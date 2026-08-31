"""Train a small RVQ codec on a pitch distribution we control.

This is the causal experiment. Every released codec keeps its training audio
private, so p(theta) is unknown and the paper's proposition can only be tested
qualitatively. Here p(theta) is constructed, so the mechanism can be manipulated
rather than inferred:

    12tet     training pitches concentrated on 12-TET semitones
    uniform   training pitches uniform over the same range
    53tet     training pitches concentrated on a 53-tone division

If grid bias appears under 12tet, vanishes under uniform, and reappears at a
DIFFERENT grid under 53tet, then "codebooks absorb the pitch statistics of
training audio" is demonstrated rather than assumed. That is the difference
between "consistent with" and "caused by", and it does not depend on any
released codec's training data.

It is also a positive control. If released codecs turn out to show nothing, this
still shows the instrument detects the effect when it is present by
construction, which keeps the paper alive under a null result.

    python train_rvq.py --distribution 12tet --steps 20000 --out ../checkpoints/rvq_12tet.pt

The model is deliberately small and deliberately capacity-limited. It does not
need to sound good; it needs a codebook that learned a pitch distribution. If
the bottleneck is too generous the quantiser never binds and there is nothing to
measure, so codebook size and quantiser count are the parameters that matter
most here, not width or depth.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent))
from stimuli import harmonic_tone  # noqa: E402,F401  (CPU reference generator)

CENTS_PER_OCTAVE = 1200.0


# --------------------------------------------------------------------------
# Training pitch distributions. This is the independent variable.
# --------------------------------------------------------------------------
def sample_pitch_cents(dist: str, n: int, rng: np.random.Generator,
                       lo: float = 0.0, hi: float = 2400.0,
                       jitter_cents: float = 12.0) -> np.ndarray:
    """Pitches in cents above a reference.

    The jitter matters. Real music is not exactly in tune: vibrato, ensemble
    spread and differing tuning references smear each peak. Without jitter the
    density is a comb of delta functions, the quantiser can place one code per
    pitch exactly, and the result would not transfer to anything real.
    """
    if dist == "uniform":
        return rng.uniform(lo, hi, size=n)
    step = 100.0 if dist == "12tet" else CENTS_PER_OCTAVE / 53.0
    n_steps = int((hi - lo) / step)
    grid = lo + step * rng.integers(0, n_steps + 1, size=n)
    return np.clip(grid + rng.normal(0.0, jitter_cents, size=n), lo, hi)


def make_batch(dist: str, batch: int, sr: int, dur: float,
               rng: np.random.Generator, f_ref: float = 110.0,
               device: str = "cpu", n_partials: int = 8,
               ramp_s: float = 0.02) -> torch.Tensor:
    """Synthesise a batch of harmonic tones directly on the target device.

    The obvious loop over batch items in numpy made training CPU-bound: 11
    minutes of CPU for 41 seconds of wall clock, with the GPU mostly idle and
    the sweeps on the same machine starved of cores. The synthesis is a pure
    outer product, so it belongs on the device the training is on.

    Matches the CPU generator in stimuli.py: partial amplitudes fall as 1/n,
    onset phase is random per partial, gain is jittered per item, partials above
    Nyquist are dropped rather than aliased, and a raised-cosine ramp keeps the
    onset from smearing energy across the spectrum.
    """
    cents = torch.from_numpy(sample_pitch_cents(dist, batch, rng)).float().to(device)
    f0 = f_ref * torch.pow(2.0, cents / CENTS_PER_OCTAVE)          # (B,)

    n = int(round(dur * sr))
    t = torch.arange(n, device=device, dtype=torch.float32) / sr    # (T,)
    ks = torch.arange(1, n_partials + 1, device=device, dtype=torch.float32)

    freqs = f0[:, None] * ks[None, :]                               # (B, K)
    below_nyquist = (freqs < 0.95 * (sr / 2)).float()
    amps = (1.0 / ks)[None, :] * below_nyquist                      # (B, K)
    phase = torch.rand(batch, n_partials, device=device) * 2 * math.pi

    x = (amps[:, :, None]
         * torch.sin(2 * math.pi * freqs[:, :, None] * t[None, None, :]
                     + phase[:, :, None])).sum(dim=1)               # (B, T)

    peak = x.abs().amax(dim=1, keepdim=True).clamp_min(1e-12)
    gain = torch.empty(batch, 1, device=device).uniform_(0.55, 0.85)
    x = x * gain / peak

    n_ramp = int(round(ramp_s * sr))
    if 2 * n_ramp < n:
        w = 0.5 * (1 - torch.cos(torch.linspace(0, math.pi, n_ramp, device=device)))
        x[:, :n_ramp] *= w
        x[:, -n_ramp:] *= w.flip(0)
    return x.unsqueeze(1)


# --------------------------------------------------------------------------
# A minimal residual vector quantiser with EMA codebook updates.
# --------------------------------------------------------------------------
class VQ(nn.Module):
    def __init__(self, dim: int, size: int, decay: float = 0.99, eps: float = 1e-5):
        super().__init__()
        self.decay, self.eps = decay, eps
        self.register_buffer("embed", torch.randn(size, dim) * 0.1)
        self.register_buffer("cluster_size", torch.zeros(size))
        self.register_buffer("embed_avg", self.embed.clone())

    def forward(self, x):                      # x: (B, T, D)
        flat = x.reshape(-1, x.shape[-1])
        d = (flat.pow(2).sum(1, keepdim=True)
             - 2 * flat @ self.embed.t()
             + self.embed.pow(2).sum(1))
        idx = d.argmin(1)
        q = self.embed[idx].view_as(x)

        if self.training:
            with torch.no_grad():
                onehot = F.one_hot(idx, self.embed.shape[0]).type(flat.dtype)
                self.cluster_size.mul_(self.decay).add_(
                    onehot.sum(0), alpha=1 - self.decay)
                self.embed_avg.mul_(self.decay).add_(
                    onehot.t() @ flat, alpha=1 - self.decay)
                n = self.cluster_size.sum()
                cs = ((self.cluster_size + self.eps)
                      / (n + self.embed.shape[0] * self.eps) * n)
                self.embed.copy_(self.embed_avg / cs.unsqueeze(1))

        # straight-through: gradients flow to the encoder unchanged
        return x + (q - x).detach(), idx.view(x.shape[:-1]), F.mse_loss(q.detach(), x)


class RVQ(nn.Module):
    def __init__(self, dim: int, size: int, n_q: int):
        super().__init__()
        self.layers = nn.ModuleList([VQ(dim, size) for _ in range(n_q)])

    def forward(self, x, n_q: int | None = None):
        residual, out, codes, commit = x, 0.0, [], 0.0
        for layer in self.layers[: n_q or len(self.layers)]:
            q, idx, c = layer(residual)
            residual = residual - q
            out = out + q
            codes.append(idx)
            commit = commit + c
        return out, torch.stack(codes), commit


class Codec(nn.Module):
    def __init__(self, dim=64, width=32, codebook=256, n_q=4, ratios=(4, 4, 4, 4)):
        super().__init__()
        enc, ch = [], 1
        for r in ratios:
            enc += [nn.Conv1d(ch, width, 2 * r, stride=r, padding=r // 2), nn.ELU()]
            ch = width
            width = min(width * 2, 128)
        enc += [nn.Conv1d(ch, dim, 3, padding=1)]
        self.encoder = nn.Sequential(*enc)

        dec, ch = [nn.Conv1d(dim, ch, 3, padding=1), nn.ELU()], ch
        for r in reversed(ratios):
            nxt = max(ch // 2, 32)
            dec += [nn.ConvTranspose1d(ch, nxt, 2 * r, stride=r, padding=r // 2),
                    nn.ELU()]
            ch = nxt
        dec += [nn.Conv1d(ch, 1, 3, padding=1)]
        self.decoder = nn.Sequential(*dec)
        self.quantizer = RVQ(dim, codebook, n_q)
        self.hop = int(np.prod(ratios))

    def forward(self, x, n_q=None, bypass=False):
        # The strided conv stack only round-trips exactly when the input length
        # is a multiple of the total hop. Without this, a 12000-sample input
        # decodes to 11776 and every loss term silently compares misaligned
        # signals, or fails on a shape mismatch as this did.
        length = x.shape[-1]
        pad = (-length) % self.hop
        if pad:
            x = F.pad(x, (0, pad))

        z = self.encoder(x).transpose(1, 2)
        if bypass:
            y = self.decoder(z.transpose(1, 2))
            return y[..., :length], None, torch.zeros((), device=x.device)
        q, codes, commit = self.quantizer(z, n_q)
        return self.decoder(q.transpose(1, 2))[..., :length], codes, commit


def stft_loss(a, b, sizes=(512, 1024, 2048)):
    """Multi-resolution magnitude loss. Waveform MSE alone is a poor objective
    for pitch: it is dominated by phase, which we do not care about and the
    estimator ignores."""
    total = 0.0
    for n in sizes:
        w = torch.hann_window(n, device=a.device)
        A = torch.stft(a.squeeze(1), n, n // 4, window=w, return_complex=True).abs()
        B = torch.stft(b.squeeze(1), n, n // 4, window=w, return_complex=True).abs()
        total = total + F.l1_loss(torch.log(A + 1e-5), torch.log(B + 1e-5))
    return total / len(sizes)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--distribution", required=True,
                   choices=["12tet", "uniform", "53tet"])
    p.add_argument("--steps", type=int, default=20000)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--sr", type=int, default=24000)
    p.add_argument("--dur", type=float, default=0.5)
    p.add_argument("--codebook", type=int, default=256)
    p.add_argument("--n-quantizers", type=int, default=4)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--jitter", type=float, default=12.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    dev = ("cuda" if torch.cuda.is_available()
           else "mps" if torch.backends.mps.is_available() else "cpu")

    model = Codec(codebook=args.codebook, n_q=args.n_quantizers).to(dev)
    n_par = sum(p.numel() for p in model.parameters())
    rate = args.n_quantizers * math.log2(args.codebook) * args.sr / model.hop
    print(f"device {dev}  params {n_par/1e6:.2f}M  hop {model.hop}  "
          f"~{rate/1000:.1f} kbps", flush=True)

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    model.train()
    for step in range(1, args.steps + 1):
        x = make_batch(args.distribution, args.batch, args.sr, args.dur, rng,
                       device=dev)
        y, _, commit = model(x)
        loss = stft_loss(y, x) + F.mse_loss(y, x) + 0.25 * commit
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if step % 500 == 0 or step == 1:
            print(f"  step {step:6d}/{args.steps}  loss {loss.item():.4f}", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "args": vars(args),
                "sample_rate": args.sr, "hop": model.hop,
                "codebook": args.codebook, "n_quantizers": args.n_quantizers},
               args.out)
    args.out.with_suffix(".json").write_text(json.dumps(
        {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
        | {"params": n_par, "kbps": rate / 1000}, indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

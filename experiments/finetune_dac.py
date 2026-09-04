"""Decoder-only fine-tune of DAC 16 kHz on a controlled pitch density.

Second codec family for the causal experiment; finetune_encodec.py carries the
design rationale. Same recipe: the codec continues training for a few thousand
steps at a low learning rate on real clips, and the only thing that differs
between arms is the pitch density of those clips (grid: the original GTZAN
clips; flat: every clip resampled by a random offset within the semitone).

DECODER ONLY, enforced rather than incidental. In EnCodec the code assignment
is an argmin, so no gradient reaches the encoder anyway. DAC's residual VQ uses
a straight-through estimator, quantized = latent + (codebook - latent).detach(),
so a naive backward WOULD update the encoder and the quantiser projections. Two
guards make that impossible here: the encoder and quantiser parameters are
frozen (requires_grad False, optimiser over the decoder only) and the quantised
representation is detached before decoding, so the graph ends at the decoder
input. After training the encoder and quantiser state dicts are asserted
bit-identical to the stock checkpoint, in memory and after reloading the saved
directory.

The quantiser runs in eval mode throughout. DacResidualVectorQuantize.forward
ignores n_quantizers and applies quantiser dropout whenever self.training is
set, which would silently change the bitrate being fine-tuned from Q6 to Q12.
Only the decoder is put in train mode (it has no dropout or batch norm, so this
is a formality).

DAC's decoder is not length-exact: decode() returns a few samples fewer than
the input (8 samples for a 0.5 s clip at 16 kHz), because the stride-5 block
pads asymmetrically. The loss is computed on the common length. The sweep
side (codec_zoo.dac) zero-pads the tail, as it does for the stock model.
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
from codec_zoo import _rev  # noqa: E402
from train_rvq import stft_loss  # noqa: E402

MODEL_ID = "descript/dac_16khz"


def frozen_state(model) -> dict[str, torch.Tensor]:
    """CPU copies of every encoder and quantiser tensor, keyed as in the
    full state dict, so two checkpoints can be compared tensor by tensor."""
    out = {}
    for prefix, mod in (("encoder", model.encoder), ("quantizer", model.quantizer)):
        for k, v in mod.state_dict().items():
            out[f"{prefix}.{k}"] = v.detach().cpu().clone()
    return out


def assert_identical(stock: dict, other: dict, what: str) -> None:
    if set(stock) != set(other):
        raise AssertionError(f"{what}: key sets differ")
    changed = [k for k in stock if not torch.equal(stock[k], other[k])]
    if changed:
        raise AssertionError(f"{what}: {len(changed)} encoder/quantiser tensors "
                             f"changed, e.g. {changed[:3]}")
    print(f"encoder and quantiser bit-identical to stock {MODEL_ID} "
          f"({len(stock)} tensors, {what})", flush=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--audio-root", type=Path, required=True,
                   help="fine-tune on real audio from this directory")
    p.add_argument("--steps", type=int, default=4000)   # the paper's runs (infra/pod_run.sh causal_dac)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--lr", type=float, default=1e-5)
    p.add_argument("--n-quantizers", type=int, default=6,
                   help="codebooks used at encode time; Q6 is the paper's DAC operating point")
    p.add_argument("--wave-weight", type=float, default=10.0)
    p.add_argument("--seed", type=int, default=0,
                   help="seeds torch and the batch sampler; replicate seeds are "
                        "what gives the causal contrast a run-to-run variance")
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    torch.manual_seed(args.seed)

    from transformers import DacModel
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = DacModel.from_pretrained(MODEL_ID, revision=_rev(MODEL_ID)).to(dev)
    sr = model.config.sampling_rate

    # Guard 1: nothing outside the decoder is a leaf the optimiser can touch.
    for mod in (model.encoder, model.quantizer):
        for prm in mod.parameters():
            prm.requires_grad_(False)
    stock = frozen_state(model)
    stock_dec = {k: v.detach().cpu().clone() for k, v in model.decoder.state_dict().items()}

    # eval() for the encoder and quantiser (see the docstring on quantiser
    # dropout); train() for the decoder only.
    model.eval()
    model.decoder.train()
    dec_params = [q for q in model.decoder.parameters() if q.requires_grad]
    n_dec = sum(q.numel() for q in dec_params)
    n_all = sum(q.numel() for q in model.parameters())
    print(f"trainable: decoder {n_dec/1e6:.1f}M of {n_all/1e6:.1f}M parameters", flush=True)
    opt = torch.optim.AdamW(dec_params, lr=args.lr)
    rng = np.random.default_rng(args.seed)

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
    if not clips:
        raise SystemExit(f"no clip longer than 1 s under {args.audio_root}")

    print(f"fine-tuning DAC 16 kHz decoder (Q{args.n_quantizers}) on "
          f"'{args.audio_root}', {args.steps} steps at lr {args.lr}", flush=True)

    def next_batch():
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
        # Guard 2: the encoder runs without a graph and the quantised
        # representation is detached, so the straight-through path is cut.
        with torch.no_grad():
            enc = model.encode(x, n_quantizers=args.n_quantizers)
        q = enc.quantized_representation.detach()
        y = model.decode(quantized_representation=q).audio_values[:, None, :]
        n = min(x.shape[-1], y.shape[-1])
        x, y = x[..., :n], y[..., :n]
        loss = stft_loss(y, x) + args.wave_weight * F.l1_loss(y, x)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(dec_params, 1.0)
        opt.step()
        if step % 500 == 0 or step == 1:
            with torch.no_grad():
                ratio = float(y.pow(2).mean().sqrt() / x.pow(2).mean().sqrt())
            print(f"  step {step:5d}/{args.steps}  loss {loss.item():.4f}  "
                  f"rms ratio {ratio:.3f}  (codes {tuple(enc.audio_codes.shape)}, "
                  f"loss on {n} of {int(0.5 * sr)} samples)", flush=True)
            if step > 500 and ratio < 0.3:
                raise SystemExit("ABORT: fine-tuning destroyed reconstruction; "
                                 "a codec that reconstructs nothing has no "
                                 "transfer function to compare.")

    model.eval()
    assert_identical(stock, frozen_state(model), "in memory after training")
    n_changed = sum(not torch.equal(v, model.decoder.state_dict()[k].detach().cpu())
                    for k, v in stock_dec.items())
    print(f"decoder: {n_changed} of {len(stock_dec)} tensors changed", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.out)
    args.out.with_suffix(".json").write_text(json.dumps(
        {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
        | {"model_id": MODEL_ID, "revision": _rev(MODEL_ID)}, indent=2))
    reloaded = DacModel.from_pretrained(args.out)
    assert_identical(stock, frozen_state(reloaded), f"reloaded from {args.out}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

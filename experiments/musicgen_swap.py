"""Same tokens, different decoders: is MusicGen's grid the model's or the codec's?

MusicGen's text-prompted output has a sharply grid-peaked within-semitone F0
density (peak/mean 4.28 against 1.79 for GTZAN; musicgen_pull.py). Two things
could put it there: the token language model's prior over EnCodec codes, and
the EnCodec decoder that turns those codes into audio. Reading the audio alone
cannot separate them.

This script holds the model prior fixed. Each prompt is generated ONCE and the
post-processed token ids (what generate() hands to the codec, shape
(1, batch, codebooks, frames) after the delay pattern is undone) are captured.
The SAME ids are then decoded by several EnCodec 32 kHz decoders:

    stock   the decoder MusicGen ships with (facebook/encodec_32khz)
    grid    that decoder fine-tuned on GTZAN (finetune_encodec.py, arm grid)
    flat    that decoder fine-tuned on tuning-flattened GTZAN (arm flat)

Any difference between the within-semitone densities is the decoder's doing,
since the tokens, and hence the model's contribution, are identical across
arms. Two pitch readings are reported for every clip: the plain YIN reading of
the paper's histogram figure (musicgen_pull.positions_within_semitone) and the
refined estimator of the detuning sweep (estimator.estimate_f0, frames kept
only where its two blind seeds agree within 20 cents).

Token capture. generate() ends with `self.audio_encoder.decode(output_ids,
audio_scales=...)` (transformers 4.57 and 5.16 alike). The audio encoder's
decode method is wrapped for the duration of the call, so the ids and every
keyword generate() passes are recorded verbatim and replayed unchanged for each
decoder. The stock re-decode is checked against generate()'s own audio on every
freshly generated prompt (max abs difference, written to the meta sidecar).

Output CSV, one row per (prompt, decoder, estimator):
  prompt_index, prompt, decoder, estimator (yin | refined), n_candidates
  (non-silent frames), n_frames (frames with an accepted F0), out_offset_cents
  (circular mean of positions, in [0, 100)), resultant (circular
  concentration), positions (semicolon-separated per-frame positions)

    python musicgen_swap.py --n 40 --decoders stock=stock \
        grid=../checkpoints/encodec32_ftm_grid_s0 flat=../checkpoints/encodec32_ftm_flat_s0 \
        --tokens-cache /workspace/musicgen_tokens --out ../results/musicgen_swap.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estimator import estimate_f0  # noqa: E402
from musicgen_pull import PROMPTS, circular_summary, frames, load_model, positions_within_semitone  # noqa: E402

AGREE_CENTS = 20.0     # the refined estimator's two seeds must agree this closely
FMIN, FMAX = 70.0, 1200.0


def positions_refined(x: np.ndarray, sr: int) -> tuple[np.ndarray, int]:
    """Per-frame F0 from the refined estimator, same framing as the YIN reading.
    Returns the positions and the number of non-silent frames considered."""
    out, n_cand = [], 0
    for seg in frames(x, sr):
        if float(np.sqrt((seg ** 2).mean())) < 1e-3:
            continue
        n_cand += 1
        a, b = estimate_f0(seg, sr, fmin=FMIN, fmax=FMAX)
        if not (np.isfinite(a) and np.isfinite(b)) or a <= 0 or b <= 0:
            continue
        if abs(1200.0 * np.log2(a / b)) > AGREE_CENTS or not (FMIN < a < FMAX):
            continue
        out.append((1200.0 * np.log2(a / 440.0)) % 100.0)
    return np.array(out), n_cand


class DecodeCapture:
    """Records every call generate() makes to audio_encoder.decode.

    The wrapper is installed as an instance attribute, which shadows the class
    method for the duration of the `with` block and is removed afterwards, so
    the model is untouched outside it.
    """

    def __init__(self, audio_encoder):
        self.enc = audio_encoder
        self.calls: list[tuple[tuple, dict]] = []

    def __enter__(self):
        orig = self.enc.decode

        def wrapped(*a, **kw):
            self.calls.append((a, kw))
            return orig(*a, **kw)

        self.enc.decode = wrapped
        return self

    def __exit__(self, *exc):
        del self.enc.decode
        return False

    def tokens(self) -> tuple:
        """(audio_codes, decode kwargs) exactly as generate() passed them."""
        if len(self.calls) != 1:
            raise RuntimeError(f"expected one audio_encoder.decode call during generate, saw {len(self.calls)}")
        a, kw = self.calls[0]
        kw = dict(kw)
        codes = a[0] if a else kw.pop("audio_codes")
        if len(a) > 1:                       # positional audio_scales, should not happen but be safe
            kw.setdefault("audio_scales", a[1])
        if "audio_scales" not in kw:
            kw["audio_scales"] = [None] * int(codes.shape[1])
        return codes, kw


def _to_cpu(v):
    import torch
    if isinstance(v, torch.Tensor):
        return v.detach().cpu()
    if isinstance(v, dict):
        return {k: _to_cpu(u) for k, u in v.items()}
    if isinstance(v, (list, tuple)):
        return type(v)(_to_cpu(u) for u in v)
    return v


def _to_device(v, device):
    import torch
    if isinstance(v, torch.Tensor):
        return v.to(device)
    if isinstance(v, dict):
        return {k: _to_device(u, device) for k, u in v.items()}
    if isinstance(v, (list, tuple)):
        return type(v)(_to_device(u, device) for u in v)
    return v


def load_decoders(specs: list[str], model, device):
    """name=path entries -> {name: EncodecModel}. 'stock' is the audio encoder
    bundled with the MusicGen checkpoint, i.e. exactly what generate() uses."""
    from transformers import EncodecModel
    from codec_zoo import _rev
    decoders = {}
    stock_sd = {k: v.detach().cpu() for k, v in model.audio_encoder.state_dict().items()}
    for spec in specs:
        if "=" not in spec:
            raise SystemExit(f"--decoders entries are name=path, got {spec!r}")
        name, path = spec.split("=", 1)
        if path == "stock":
            decoders[name] = model.audio_encoder
            continue
        dec = EncodecModel.from_pretrained(path, revision=_rev(path)).to(device).eval()
        sd = dec.state_dict()
        # A decoder-only fine-tune leaves the encoder and quantiser bit-identical;
        # the two numbers below make that, and the size of the decoder change,
        # visible in the log.
        def maxdiff(prefixes):
            ds = [float((sd[k].detach().cpu().float() - stock_sd[k].float()).abs().max())
                  for k in sd if k in stock_sd and k.startswith(prefixes)]
            return max(ds) if ds else float("nan")
        print(f"  decoder {name}: {path}  |encoder+quantizer - stock| max {maxdiff(('encoder.', 'quantizer.')):.2e}"
              f"  |decoder - stock| max {maxdiff(('decoder.',)):.2e}", flush=True)
        decoders[name] = dec
    return decoders


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default="facebook/musicgen-small")
    p.add_argument("--n", type=int, default=40, help="text prompts, cycling musicgen_pull.PROMPTS")
    p.add_argument("--generate-seconds", type=float, default=10.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--guidance-scale", type=float, default=3.0)
    p.add_argument("--decoders", nargs="+", default=["stock=stock"],
                   help="name=path entries; path is 'stock' or an EncodecModel checkpoint")
    p.add_argument("--out", type=Path, default=Path("results/musicgen_swap.csv"))
    p.add_argument("--save-audio", type=Path, default=None, help="directory for the decoded wavs")
    p.add_argument("--tokens-cache", type=Path, default=None,
                   help="directory of per-prompt .pt files; generation is skipped for prompts found there")
    args = p.parse_args()

    device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
    proc, model, torch = load_model(args.model, device)
    sr = int(model.config.audio_encoder.sampling_rate)
    frame_rate = float(model.config.audio_encoder.frame_rate)
    decoders = load_decoders(args.decoders, model, device)
    if args.save_audio:
        args.save_audio.mkdir(parents=True, exist_ok=True)
    if args.tokens_cache:
        args.tokens_cache.mkdir(parents=True, exist_ok=True)

    prompts = [PROMPTS[i % len(PROMPTS)] for i in range(args.n)]
    rows, identity = [], []
    for i, text in enumerate(prompts):
        cache_file = args.tokens_cache / f"text_{i:03d}.pt" if args.tokens_cache else None
        ref_audio = None
        if cache_file is not None and cache_file.exists():
            blob = torch.load(cache_file, map_location="cpu", weights_only=False)
            if blob.get("prompt") != text:
                raise SystemExit(f"{cache_file} holds prompt {blob.get('prompt')!r}, expected {text!r}")
            codes, dec_kwargs = blob["audio_codes"], blob["decode_kwargs"]
            source = "cache"
        else:
            # seeded per prompt so a partially cached run regenerates the same ids
            torch.manual_seed(args.seed * 100003 + i)
            inputs = proc(text=[text], padding=True, return_tensors="pt").to(device)
            with torch.no_grad(), DecodeCapture(model.audio_encoder) as cap:
                audio = model.generate(**inputs, do_sample=True, guidance_scale=args.guidance_scale,
                                       max_new_tokens=int(args.generate_seconds * frame_rate))
            ref_audio = audio[0, 0].float().cpu().numpy()
            codes, dec_kwargs = cap.tokens()
            codes, dec_kwargs = _to_cpu(codes), _to_cpu(dec_kwargs)
            source = "generated"
            if cache_file is not None:
                torch.save({"prompt": text, "prompt_index": i, "model": args.model, "seed": args.seed,
                            "generate_seconds": args.generate_seconds, "audio_codes": codes,
                            "decode_kwargs": dec_kwargs}, cache_file)
        shape = tuple(int(s) for s in codes.shape)

        for name, dec in decoders.items():
            with torch.no_grad():
                y = dec.decode(_to_device(codes, device), **_to_device(dec_kwargs, device)).audio_values
            x = y[0, 0].float().cpu().numpy()
            if ref_audio is not None and dec is model.audio_encoder:
                n = min(len(x), len(ref_audio))
                d = float(np.abs(x[:n] - ref_audio[:n]).max()) if len(x) == len(ref_audio) else float("inf")
                identity.append({"prompt_index": i, "decoder": name, "max_abs_diff": d,
                                 "len_generate": int(len(ref_audio)), "len_redecode": int(len(x))})
                print(f"    identity check {name}: max |re-decode - generate()| = {d:.2e}", flush=True)
            pos_y = positions_within_semitone(x, sr)
            n_cand = sum(1 for seg in frames(x, sr) if float(np.sqrt((seg ** 2).mean())) >= 1e-3)
            pos_r, n_cand_r = positions_refined(x, sr)
            for est, pos, nc in (("yin", pos_y, n_cand), ("refined", pos_r, n_cand_r)):
                off, res = circular_summary(pos)
                rows.append(dict(prompt_index=i, prompt=text, decoder=name, estimator=est,
                                 n_candidates=int(nc), n_frames=int(pos.size),
                                 out_offset_cents=off, resultant=res,
                                 positions=";".join(f"{v:.1f}" for v in pos)))
            if args.save_audio:
                import soundfile as sf
                sf.write(str(args.save_audio / f"text_{i:03d}_{name}.wav"), x, sr)
            oy, ry = circular_summary(pos_y)
            orr, rr = circular_summary(pos_r)
            print(f"  prompt {i+1}/{len(prompts)} [{source}, codes {shape}] {name:>6s}  "
                  f"yin frames {pos_y.size:4d} offset {oy:5.1f} R {ry:.2f} | "
                  f"refined frames {pos_r.size:4d}/{n_cand_r} offset {orr:5.1f} R {rr:.2f}", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else ["prompt_index"]
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    meta = {"args": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
            "model": args.model, "sample_rate": sr, "frame_rate": frame_rate,
            "decoders": dict(s.split("=", 1) for s in args.decoders),
            "estimators": {"yin": "musicgen_pull.positions_within_semitone (64 ms frames, 32 ms hop, 70-1200 Hz)",
                           "refined": f"estimator.estimate_f0, same framing, seeds within {AGREE_CENTS} cents"},
            "identity_check": identity,
            "identity_check_max": (max(d["max_abs_diff"] for d in identity) if identity else None),
            "python": sys.version.split()[0], "packages": {}}
    for mod in ("torch", "transformers", "numpy", "scipy"):
        try:
            meta["packages"][mod] = __import__(mod).__version__
        except Exception:
            meta["packages"][mod] = None
    args.out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote {args.out} ({len(rows)} rows)")
    if identity:
        print(f"identity check over {len(identity)} generated prompts: max |re-decode - generate()| "
              f"= {meta['identity_check_max']:.2e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

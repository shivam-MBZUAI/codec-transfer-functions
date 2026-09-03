"""Does a token language model built on EnCodec inherit the grid?

MusicGen generates EnCodec tokens and decodes them with EnCodec's decoder, so
everything the codec does to pitch is applied to whatever the model produces.
Two measurements, both reading the generated audio's pitch density within the
semitone with the same blind estimator as pitch_histogram.py.

  text     Text-prompted generations. Reports the within-semitone F0 density
           of the generated audio: its peak-to-mean ratio against GTZAN's
           1.788 (and the flat-sampling floor), and where its peak sits
           relative to A440. A generator that reproduces the training grid
           gives a peaked density; one that sharpens it, a higher ratio.

  continue Audio-prompted continuation on tuning-flattened GTZAN clips. Each
           clip carries a known offset d in [0, 100) cents, written in its
           filename. The model is given the first `--prompt-seconds` of the
           clip as EnCodec tokens and continues it; the continuation's tuning
           offset (circular mean of within-semitone positions) is regressed
           on d. Slope 1 means the continuation keeps the prompt's tuning,
           slope 0 that it re-grids to 12-TET regardless of the prompt: the
           registration test of Section 3, applied to a generator.

Output CSV, one row per generated clip:
  mode, prompt (text or filename), offset_cents (prompt offset, nan for text),
  n_frames, out_offset_cents (circular mean of positions, in [0, 100)),
  resultant (circular concentration, 0 flat .. 1 all on one position),
  positions (semicolon-separated per-frame positions within the semitone)

    python musicgen_pull.py --mode text --n 60 --out ../results/musicgen_text.csv
    python musicgen_pull.py --mode continue --audio-root ../corpora/gtzan_detuned \
        --n 60 --out ../results/musicgen_continue.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estimator import estimate_f0_yin  # noqa: E402

PROMPTS = [
    "solo piano, slow ballad", "acoustic guitar fingerpicking", "string quartet, andante",
    "jazz trio with upright bass", "synth pop with a bright lead", "folk song with violin",
    "church organ chorale", "bluegrass with banjo and fiddle", "orchestral film theme",
    "ambient pad with slow melody", "flute and harp duet", "rock ballad with electric guitar",
    "brass band march", "lo-fi hip hop with piano loop", "country waltz with pedal steel",
    "classical guitar etude", "cello solo, adagio", "80s synthwave", "children's choir",
    "harpsichord baroque piece", "reggae with melodic bass", "trumpet solo over strings",
    "clarinet and piano sonata", "indie pop with vocals", "soul ballad with electric piano",
    "gospel choir with organ", "bossa nova guitar", "medieval lute", "music box melody",
    "marching band", "soft rock with harmonies", "vibraphone jazz", "accordion waltz",
    "solo violin caprice", "chamber choir hymn", "electric piano lounge", "epic trailer strings",
    "ukulele song", "mandolin folk dance", "oboe and strings pastoral",
]


def frames(x: np.ndarray, sr: int, win: float = 0.064, hop: float = 0.032):
    n, h = int(win * sr), int(hop * sr)
    for i in range(0, max(0, len(x) - n), h):
        yield x[i:i + n]


def positions_within_semitone(x: np.ndarray, sr: int) -> np.ndarray:
    """Per-frame F0 as cents above the nearest-below 12-TET pitch, A440 grid."""
    out = []
    for seg in frames(x, sr):
        if float(np.sqrt((seg ** 2).mean())) < 1e-3:
            continue
        f0 = estimate_f0_yin(seg, sr, fmin=70.0, fmax=1200.0)
        if np.isfinite(f0) and 70 < f0 < 1200:
            out.append((1200.0 * np.log2(f0 / 440.0)) % 100.0)
    return np.array(out)


def circular_summary(pos: np.ndarray) -> tuple[float, float]:
    if pos.size == 0:
        return float("nan"), float("nan")
    ang = 2 * np.pi * pos / 100.0
    c, s = np.cos(ang).mean(), np.sin(ang).mean()
    return float((np.degrees(np.arctan2(s, c)) % 360) / 3.6), float(np.hypot(c, s))


def load_model(model_id: str, device: str):
    import torch
    from transformers import AutoProcessor, MusicgenForConditionalGeneration
    from codec_zoo import _rev   # pinned Hugging Face revision (data/fetch_checkpoints.py)
    proc = AutoProcessor.from_pretrained(model_id, revision=_rev(model_id))
    model = MusicgenForConditionalGeneration.from_pretrained(model_id, revision=_rev(model_id)).to(device).eval()
    return proc, model, torch


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["text", "continue"], required=True)
    p.add_argument("--model", default="facebook/musicgen-small")
    p.add_argument("--audio-root", type=Path, default=None, help="flattened clips for --mode continue")
    p.add_argument("--n", type=int, default=60)
    p.add_argument("--prompt-seconds", type=float, default=5.0)
    p.add_argument("--generate-seconds", type=float, default=10.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--save-audio", type=Path, default=None, help="directory for the generated wavs")
    args = p.parse_args()

    device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
    proc, model, torch = load_model(args.model, device)
    sr = int(model.config.audio_encoder.sampling_rate)
    frame_rate = float(model.config.audio_encoder.frame_rate)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    if args.save_audio:
        args.save_audio.mkdir(parents=True, exist_ok=True)

    rows = []
    if args.mode == "text":
        prompts = [PROMPTS[i % len(PROMPTS)] for i in range(args.n)]
        for i, text in enumerate(prompts):
            inputs = proc(text=[text], padding=True, return_tensors="pt").to(device)
            with torch.no_grad():
                audio = model.generate(**inputs, do_sample=True, guidance_scale=3.0,
                                       max_new_tokens=int(args.generate_seconds * frame_rate))
            x = audio[0, 0].float().cpu().numpy()
            pos = positions_within_semitone(x, sr)
            off, res = circular_summary(pos)
            rows.append(dict(mode="text", prompt=text, offset_cents=float("nan"), n_frames=int(pos.size),
                             out_offset_cents=off, resultant=res,
                             positions=";".join(f"{v:.1f}" for v in pos)))
            if args.save_audio:
                import soundfile as sf
                sf.write(str(args.save_audio / f"text_{i:03d}.wav"), x, sr)
            print(f"  text {i+1}/{len(prompts)}  frames {pos.size:4d}  offset {off:5.1f}  R {res:.2f}", flush=True)
    else:
        import soundfile as sf
        import scipy.signal as sps
        files = sorted(args.audio_root.glob("*.wav"))
        rng.shuffle(files)
        files = files[: args.n]
        for i, f in enumerate(files):
            m = re.search(r"_(\d+\.\d)c\.wav$", f.name)
            d = float(m.group(1)) if m else float("nan")
            x, fsr = sf.read(str(f), dtype="float32", always_2d=False)
            if x.ndim > 1:
                x = x.mean(axis=1)
            if fsr != sr:
                x = sps.resample_poly(x, sr, fsr).astype(np.float32)
            n_prompt = int(args.prompt_seconds * sr)
            # take the prompt from the middle of the clip, where the music is going
            start = max(0, (len(x) - n_prompt) // 2)
            prompt = x[start:start + n_prompt]
            inputs = proc(audio=prompt, sampling_rate=sr, text=["continue the music"],
                          padding=True, return_tensors="pt").to(device)
            with torch.no_grad():
                audio = model.generate(**inputs, do_sample=True, guidance_scale=3.0,
                                       max_new_tokens=int((args.prompt_seconds + args.generate_seconds) * frame_rate))
            y = audio[0, 0].float().cpu().numpy()
            # the output begins with the (re-decoded) prompt; score only the continuation
            cont = y[n_prompt:]
            pos = positions_within_semitone(cont, sr)
            off, res = circular_summary(pos)
            # the prompt itself, re-read through the same estimator, for reference
            ppos = positions_within_semitone(prompt, sr)
            poff, pres = circular_summary(ppos)
            rows.append(dict(mode="continue", prompt=f.name, offset_cents=d, n_frames=int(pos.size),
                             out_offset_cents=off, resultant=res,
                             prompt_offset_measured=poff, prompt_resultant=pres,
                             positions=";".join(f"{v:.1f}" for v in pos)))
            if args.save_audio:
                sf.write(str(args.save_audio / f"cont_{i:03d}_{d:05.1f}c.wav"), y, sr)
            print(f"  cont {i+1}/{len(files)}  d {d:5.1f}  prompt measured {poff:5.1f} (R {pres:.2f})"
                  f"  continuation {off:5.1f} (R {res:.2f}, frames {pos.size})", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else ["mode"]
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    meta = {"args": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
            "model": args.model, "sample_rate": sr, "frame_rate": frame_rate,
            "python": sys.version.split()[0], "packages": {}}
    for mod in ("torch", "transformers", "numpy", "scipy"):
        try:
            meta["packages"][mod] = __import__(mod).__version__
        except Exception:
            meta["packages"][mod] = None
    args.out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote {args.out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

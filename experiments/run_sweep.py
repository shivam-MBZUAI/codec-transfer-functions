"""Run the pitch sweep through one codec and write a tidy CSV.

Pilot (the go/no-go gate, ~13 minutes of audio, minutes of wall clock):

    python run_sweep.py --codec encodec:3 --reps 3 --out ../results/pilot_encodec3.csv

Full sweep for the paper:

    python run_sweep.py --codec encodec:3 --reps 20 \
        --references 110 220 440 880 --out ../results/encodec3.csv

The noise floor is measured in the same run, at the same sample rate, on the
same trials. It is not a constant: resampling a stimulus to 16 kHz and back
changes the estimator's error, so a floor measured once at 24 kHz does not
transfer to SpeechTokenizer.

THE DETUNED REFERENCE IS THE POINT OF THE PILOT. --references 440 452.8929
runs one reference on the 12-TET grid and one 50 cents off it. If the residual
is locked to an absolute learned grid, its phase in interval space shifts by
half a period between the two. If the phase does not move, the effect is an
artefact of the analysis rather than a property of the codec, and the whole
microtonal framing dies here for the cost of thirteen minutes of audio.

Nothing in this file writes a number into the paper. It writes raw per-trial
estimates; every summary statistic is derived in analyze_sweep.py, so the
analysis can be rerun without recomputing the codec passes.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

import codec_zoo
from estimator import OCTAVE_GATE_CENTS, cents_between, estimate_f0  # noqa: E402
from stimuli import ratio_to_cents, sweep  # noqa: E402

FIELDS = [
    "codec", "rate_label", "sample_rate", "seed",
    "theta_cents", "f1_nominal", "f2_nominal", "reference_label", "rep",
    "f1_hat_coded", "f2_hat_coded", "f1_hat_uncoded", "f2_hat_uncoded",
    "f1_crosscheck_coded", "f2_crosscheck_coded",
    "disagreement_f1_cents", "disagreement_f2_cents", "octave_flag",
    "interval_coded_cents", "interval_uncoded_cents",
    "residual_coded_cents", "residual_uncoded_cents",
    "abs_residual_f2_coded_cents", "abs_residual_f2_uncoded_cents",
]


def reference_label(f1: float, grid_ref: float = 440.0) -> str:
    """How far this reference sits from the 12-TET grid anchored at A440.

    Reports the signed offset within the semitone, 0 to 100 cents, NOT folded to
    the nearer grid point. Folding made +60 and +40 share a label, which is
    exactly wrong for a detuning sweep where the whole point is that phase
    advances monotonically across a full semitone.
    """
    off = ratio_to_cents(f1 / grid_ref) % 100.0
    return f"{f1:.4g}Hz_{off:+05.1f}c" if off > 0.5 else f"{f1:.4g}Hz_ongrid"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--codec", required=True, help='e.g. "encodec:3", "dac:4", "mimi:8"')
    p.add_argument("--references", type=float, nargs="+", default=[440.0, 452.8929],
                   help="reference pitches in Hz; default is A440 and A440+50 cents")
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--theta-step", type=float, default=5.0)
    p.add_argument("--theta-stop", type=float, default=1200.0)
    p.add_argument("--partials", type=int, default=8)
    p.add_argument("--sinusoid", action="store_true", help="pure-tone control")
    p.add_argument("--vibrato-cents", type=float, default=0.0,
                   help="peak pitch deviation of an added 5.5 Hz vibrato")
    p.add_argument("--noise-db", type=float, default=None,
                   help="additive noise at this SNR in dB")
    p.add_argument("--vowel", action="store_true",
                   help="speech-shaped stimulus: harmonic source through formants. "
                        "Speech codecs treat isolated tones as out of distribution")
    p.add_argument("--seed", type=int, default=20260826)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    codec = codec_zoo.build(args.codec)
    sr = codec.sample_rate
    print(f"codec {codec.name} [{codec.rate_label}] at {sr} Hz", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)

    # Sidecar provenance. A CSV that cannot say which package versions produced
    # it is not reproducible evidence, whatever the reproducibility statement says.
    meta = {"args": {k: (str(v) if isinstance(v, Path) else v)
                     for k, v in vars(args).items()},
            "codec": codec.name, "rate_label": codec.rate_label, "sample_rate": sr,
            "python": sys.version.split()[0], "packages": {}}
    for mod in ("numpy", "torch", "transformers"):
        try:
            meta["packages"][mod] = __import__(mod).__version__
        except Exception:
            meta["packages"][mod] = None
    args.out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
    n_theta = int(round(args.theta_stop / args.theta_step)) + 1
    total = n_theta * len(args.references) * args.reps
    started = time.time()

    with args.out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()

        trials = sweep(
            sr,
            theta_stop=args.theta_stop,
            theta_step=args.theta_step,
            references=tuple(args.references),
            n_reps=args.reps,
            seed=args.seed,
            n_partials=args.partials,
            sinusoid=args.sinusoid,
            vowel=args.vowel,
            vibrato_cents=args.vibrato_cents,
            noise_db=args.noise_db,
        )

        for i, stim in enumerate(trials):
            coded = codec(stim.audio)

            n_est = 1 if args.sinusoid else (12 if args.vowel else args.partials)
            f1_c, f1_x = estimate_f0(coded[stim.tone1_slice], sr, n_partials=n_est)
            f2_c, f2_x = estimate_f0(coded[stim.tone2_slice], sr, n_partials=n_est)
            f1_u, _ = estimate_f0(stim.audio[stim.tone1_slice], sr, n_partials=n_est)
            f2_u, _ = estimate_f0(stim.audio[stim.tone2_slice], sr, n_partials=n_est)

            octave_flag = (abs(cents_between(f1_c, stim.f1)) > OCTAVE_GATE_CENTS
                           or abs(cents_between(f2_c, stim.f2)) > OCTAVE_GATE_CENTS)

            iv_c = ratio_to_cents(f2_c / f1_c) if f1_c > 0 and f2_c > 0 else float("nan")
            iv_u = ratio_to_cents(f2_u / f1_u) if f1_u > 0 and f2_u > 0 else float("nan")

            writer.writerow({
                "codec": codec.name,
                "rate_label": codec.rate_label,
                "sample_rate": sr,
                "seed": args.seed,
                "theta_cents": stim.theta_cents,
                "f1_nominal": stim.f1,
                "f2_nominal": stim.f2,
                "reference_label": reference_label(stim.f1),
                "rep": stim.meta["rep"],
                "f1_hat_coded": f1_c, "f2_hat_coded": f2_c,
                "f1_hat_uncoded": f1_u, "f2_hat_uncoded": f2_u,
                "f1_crosscheck_coded": f1_x, "f2_crosscheck_coded": f2_x,
                "interval_coded_cents": iv_c,
                "interval_uncoded_cents": iv_u,
                "residual_coded_cents": iv_c - stim.theta_cents,
                "residual_uncoded_cents": iv_u - stim.theta_cents,
                "abs_residual_f2_coded_cents": cents_between(f2_c, stim.f2),
                "abs_residual_f2_uncoded_cents": cents_between(f2_u, stim.f2),
                "disagreement_f1_cents": cents_between(f1_c, f1_x),
                "disagreement_f2_cents": cents_between(f2_c, f2_x),
                "octave_flag": int(octave_flag),
            })

            if (i + 1) % 100 == 0 or i + 1 == total:
                rate = (i + 1) / max(time.time() - started, 1e-9)
                eta = (total - i - 1) / max(rate, 1e-9)
                print(f"  {i + 1}/{total} trials  {rate:.1f}/s  eta {eta / 60:.1f} min",
                      flush=True)

    print(f"wrote {args.out}", flush=True)


if __name__ == "__main__":
    main()

"""Which partials does a codec move? The spectral check as a systematic sweep.

spectral_check.py showed, for EnCodec at 3 kbps and two references, that the
decoded fundamental stays within a fraction of a cent of the input while the
partials above roughly 1.3 kHz are regenerated near the harmonics of the
nearest 12-TET pitch. This script runs that same measurement over a list of
codecs, bitrates, registers, detunings and (optionally) real instrument notes,
and writes one CSV row per decoded partial so analysis/analyze_spectral.py can
locate the band edge per codec and build a table from it.

Per (codec, reference, delta, rep) one harmonic tone is synthesised delta cents
off the reference, coded, and the steady state of input and output is read
with a heavily zero-padded FFT. For every partial k = 1..12 below 0.45 x the
sample rate the row records where the decoded main line sits relative to the
input partial (peak_shift_cents), the same reading on the uncoded input
(in_peak_cents, the measurement floor), the -3 dB width, the level left at the
input frequency and at the nearest 12-TET frequency, and any secondary peak
within 20 dB. The blind estimator's reading of the whole decoded tone with 8
and with 2 partials is repeated on every row of that tone.

Real notes: --notes DIR points at NSynth wav files named
<instrument>_<source>_<id>-<midi>-<vel>.wav. Each selected note is pitch
shifted by resampling so it sits delta cents off its own 12-TET pitch, and
analysed exactly like a synthetic tone with f0 = the detuned MIDI frequency.
For notes in_peak_cents carries the note's own tuning and inharmonicity, so
the analysis reads shifts relative to it.

Rows are APPENDED to --out so codecs can be run separately and merged; the
.meta.json sidecar keeps one provenance entry per run.

    python experiments/spectral_sweep.py --codecs encodec:3 encodec:24
    python experiments/spectral_sweep.py --codecs dac16:6 --notes data/nsynth
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from estimator import cents_between, estimate_f0  # noqa: E402
from spectral_check import analyse_partial, hires_spectrum  # noqa: E402
from stimuli import _raised_cosine_ramp, cents_to_ratio, harmonic_tone  # noqa: E402

FIELDS = ["codec", "rate_label", "sample_rate", "stimulus", "reference_hz",
          "delta_cents", "rep", "f_in_hz", "k", "f_k_hz", "peak_shift_cents",
          "in_peak_cents", "width_cents", "zero_level_db", "grid_level_db",
          "second_cents", "second_level_db", "est8_cents", "est2_cents"]

SEED = 20260826
MAX_PARTIAL = 12
RAMP_S = 0.02
NOTE_MIDI_RANGE = (45, 81)   # A2 to A5, the registers the sweeps cover
NOTE_OFFSET_S = 0.25         # skip the attack of a real note


def midi_hz(midi: int) -> float:
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def partials_for(f_in: float, sr: int) -> list[int]:
    return [k for k in range(1, MAX_PARTIAL + 1) if k * f_in < 0.45 * sr]


def make_tone(f_in: float, sr: int, duration: float, i_ref: int, i_delta: int,
              rep: int, n_partials: int) -> np.ndarray:
    rng = np.random.default_rng(
        np.random.SeedSequence(SEED, spawn_key=(i_ref, i_delta, rep)))
    return harmonic_tone(f_in, duration, sr, rng, n_partials=n_partials, ramp_s=RAMP_S)


# ---- real notes ----------------------------------------------------------

def list_notes(note_dir: Path, n_notes: int) -> list[tuple[Path, int]]:
    """(path, midi) for up to n_notes files in the MIDI range, spread evenly
    over the sorted listing so instruments and pitches are both covered."""
    lo, hi = NOTE_MIDI_RANGE
    found = []
    for p in sorted(note_dir.glob("*.wav")):
        parts = p.stem.rsplit("-", 2)
        if len(parts) != 3:
            continue
        try:
            midi = int(parts[1])
        except ValueError:
            continue
        if lo <= midi <= hi:
            found.append((p, midi))
    if len(found) > n_notes:
        idx = np.unique(np.linspace(0, len(found) - 1, n_notes).round().astype(int))
        found = [found[i] for i in idx]
    return found


def load_note(path: Path, sr_out: int, delta: float, duration: float):
    """The note resampled to the codec rate and pitch shifted by delta cents.

    Playing a recording faster by a ratio r raises every partial by r. The
    conversion to the codec's rate and the pitch shift are folded into one
    resample_poly call so one anti-aliasing filter is applied. The ratio is
    rounded to a fraction, so the pitch ratio actually applied is returned
    and the caller uses it for f0 rather than the nominal delta.
    """
    import soundfile as sf
    from scipy.signal import resample_poly

    x, sr_in = sf.read(str(path), dtype="float64")
    if x.ndim > 1:
        x = x.mean(axis=1)
    frac = Fraction((sr_out / sr_in) / cents_to_ratio(delta)).limit_denominator(4000)
    y = resample_poly(x, frac.numerator, frac.denominator)
    pitch_ratio = (sr_out / sr_in) / float(frac)

    start, n = int(round(NOTE_OFFSET_S * sr_out)), int(round(duration * sr_out))
    seg = y[start:start + n]
    if len(seg) < n:
        return None, pitch_ratio
    seg = seg - seg.mean()
    peak = float(np.abs(seg).max())
    if peak <= 0.0:
        return None, pitch_ratio
    return _raised_cosine_ramp(seg * (0.7 / peak), sr_out, RAMP_S), pitch_ratio


# ---- one tone through one codec -------------------------------------------

def analyse_tone(codec, x: np.ndarray, f_in: float, nfft: int) -> list[dict]:
    """Rows for every analysable partial of one decoded tone."""
    sr = codec.sample_rate
    n = len(x)
    a, b = int(0.05 * n), int(0.95 * n)          # steady state, as spectral_check
    n_ramp = int(round(RAMP_S * sr))
    y = codec(x)

    db_in, df = hires_spectrum(x[a:b], sr, nfft)
    db_out, _ = hires_spectrum(y[a:b], sr, nfft)
    # Blind estimator on what run_sweep.py hands it: ramps off. YIN-seeded
    # reading, as in spectral_check.
    steady = y[n_ramp:n - n_ramp]
    est8 = cents_between(estimate_f0(steady, sr, n_partials=8)[0], f_in)
    est2 = cents_between(estimate_f0(steady, sr, n_partials=2)[0], f_in)

    rows = []
    for k in partials_for(f_in, sr):
        ri = analyse_partial(db_in, df, k * f_in)
        ro = analyse_partial(db_out, df, k * f_in)
        s = ro["second"]
        rows.append(dict(
            f_in_hz=round(f_in, 4), k=k, f_k_hz=round(k * f_in, 3),
            peak_shift_cents=round(ro["peak_cents"], 4),
            in_peak_cents=round(ri["peak_cents"], 4),
            width_cents=round(ro["width_cents"], 3),
            zero_level_db=round(ro["zero_level_db"], 3),
            grid_level_db=round(ro["grid_level_db"], 3),
            second_cents=round(s["cents"], 3) if s else float("nan"),
            second_level_db=round(s["level_db"], 3) if s else float("nan"),
            est8_cents=round(est8, 4), est2_cents=round(est2, 4)))
    return rows


# ---- output ---------------------------------------------------------------

def open_csv(out: Path):
    """Append if the file already has this header, else start it."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size > 0:
        with out.open(newline="") as fh:
            header = next(csv.reader(fh), [])
        if header != FIELDS:
            raise SystemExit(f"{out} has a different header; will not append")
        fh = out.open("a", newline="")
        return fh, csv.DictWriter(fh, fieldnames=FIELDS)
    fh = out.open("w", newline="")
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    return fh, w


def write_sidecar(out: Path, args, spec: str, codec, n_rows: int, seconds: float) -> None:
    """One provenance entry per codec run, in the run_sweep.py format, kept
    in a list so merged CSVs keep every run's record."""
    path = out.with_suffix(".meta.json")
    meta = json.loads(path.read_text()) if path.exists() else {"runs": []}
    run = {"args": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
           "codec_spec": spec, "codec": codec.name, "rate_label": codec.rate_label,
           "sample_rate": codec.sample_rate, "rows": n_rows, "seconds": round(seconds, 1),
           "finished": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "python": sys.version.split()[0], "packages": {}}
    for mod in ("numpy", "scipy", "torch", "transformers"):
        try:
            run["packages"][mod] = __import__(mod).__version__
        except Exception:
            run["packages"][mod] = None
    meta.setdefault("runs", []).append(run)
    path.write_text(json.dumps(meta, indent=2))


# ---- main -----------------------------------------------------------------

def run_codec(spec: str, args, writer):
    """Returns (codec, number of rows written)."""
    import codec_zoo
    codec = codec_zoo.build(spec)
    sr = codec.sample_rate
    base = dict(codec=codec.name, rate_label=codec.rate_label, sample_rate=sr)
    print(f"codec {codec.name} [{codec.rate_label}] at {sr} Hz "
          f"(bin {1200 * np.log2(1 + sr / args.nfft / 440):.3f} c at 440 Hz)", flush=True)
    n_rows = 0

    def emit(rows, **keys):
        nonlocal n_rows
        for r in rows:
            writer.writerow({**base, **keys, **r})
        n_rows += len(rows)

    def report(tag, rows):
        top = max(rows, key=lambda r: abs(r["peak_shift_cents"]))
        print(f"  {tag}: H1 {rows[0]['peak_shift_cents']:+6.2f} c, est8 {rows[0]['est8_cents']:+6.2f}, "
              f"est2 {rows[0]['est2_cents']:+6.2f}, largest shift {top['peak_shift_cents']:+6.1f} c "
              f"at k={top['k']} ({top['f_k_hz']:.0f} Hz)", flush=True)

    for i_ref, f_ref in enumerate(args.references):
        for i_d, delta in enumerate(args.deltas):
            f_in = f_ref * cents_to_ratio(delta)
            for rep in range(args.reps):
                x = make_tone(f_in, sr, args.duration, i_ref, i_d, rep, args.partials)
                rows = analyse_tone(codec, x, f_in, args.nfft)
                emit(rows, stimulus="tone", reference_hz=f_ref, delta_cents=delta, rep=rep)
                if rep == 0:
                    report(f"tone {f_ref:5.0f} Hz {delta:+4.0f} c", rows)

    if args.notes is not None:
        notes = list_notes(args.notes, args.n_notes)
        print(f"  {len(notes)} notes from {args.notes}", flush=True)
        for path, midi in notes:
            for delta in args.deltas:
                x, ratio = load_note(path, sr, delta, args.duration)
                if x is None:
                    print(f"  skip {path.name}: too short or silent")
                    continue
                f_in = midi_hz(midi) * ratio
                rows = analyse_tone(codec, x, f_in, args.nfft)
                emit(rows, stimulus="note", reference_hz=round(midi_hz(midi), 4),
                     delta_cents=delta, rep=0)
                if delta == args.deltas[0]:
                    report(f"note {path.stem} {delta:+4.0f} c", rows)
    return codec, n_rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--codecs", nargs="+",
                    default=["encodec:1.5", "encodec:3", "encodec:6", "encodec:12", "encodec:24"],
                    help="codec_zoo.build specs")
    ap.add_argument("--references", nargs="+", type=float, default=[110.0, 220.0, 440.0, 880.0])
    ap.add_argument("--deltas", nargs="+", type=float, default=[-40.0, -20.0, 0.0, 20.0, 40.0],
                    help="cents off the 12-TET reference")
    ap.add_argument("--reps", type=int, default=3, help="random phase/gain draws per tone")
    ap.add_argument("--duration", type=float, default=1.0)
    ap.add_argument("--partials", type=int, default=MAX_PARTIAL,
                    help="partials in the synthetic tone; the analysis reads up to 12")
    ap.add_argument("--nfft", type=int, default=1 << 20)
    ap.add_argument("--notes", type=Path, default=None,
                    help="directory of NSynth wavs <inst>_<src>_<id>-<midi>-<vel>.wav")
    ap.add_argument("--n-notes", type=int, default=60)
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parent.parent / "results" / "spectral_sweep.csv")
    args = ap.parse_args()

    fh, writer = open_csv(args.out)
    try:
        for spec in args.codecs:
            t0 = time.time()
            codec, n_rows = run_codec(spec, args, writer)
            fh.flush()
            write_sidecar(args.out, args, spec, codec, n_rows, time.time() - t0)
            print(f"  {n_rows} rows in {time.time() - t0:.0f} s -> {args.out}", flush=True)
    finally:
        fh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

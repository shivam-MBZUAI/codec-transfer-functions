"""Absolute bias of plain YIN against the refined estimator, in cents.

The corpus histograms (pitch_histogram.py), the MusicGen readings
(musicgen_pull.py, positions_within_semitone) and the phonology contours read
F0 with plain YIN on 64 ms frames, not with the validated three-stage
estimator (estimator.estimate_f0). Two absolute claims rest on that reading:
the GTZAN density peak sitting a few cents sharp of A440, and the MusicGen
output peak at 3.6 cents sharp. This script measures what plain YIN does on
signals of that kind, and whether its error depends on where the true pitch
sits within the semitone, which is the only way it could move a
within-semitone peak.

Part 1, synthetic. Harmonic tones (stimuli.harmonic_tone, eight partials at
1/k, raised-cosine ramps, plus a mild exponential decay) at fundamentals from
110 to 880 Hz in 5-cent steps, so every 5-cent position within the semitone
is visited once per semitone, 36 times in all, at 22050 and 32000 Hz. Each
tone is framed exactly as positions_within_semitone frames a clip (64 ms
window, 32 ms hop, RMS gate, YIN with fmin 70 / fmax 1200, 70 < f0 < 1200),
and the same frames are read with estimate_f0 (YIN + harmonic-sum cross-check
+ least-squares refinement), gated at 20 cents of cross-check agreement as
analyze_corpus_pull.py gates its frames. The whole steady tone is also read
with estimate_f0 once, which is how run_sweep.py and retune_real.py use it.

Part 2, corpus. If a directory of clips is given (or a GTZAN copy is found
under the usual paths), 40 clips are framed and read with both estimators and
the within-semitone density is summarised each way: circular-mean peak
position in cents above the 12-TET pitch, resultant length, and the 50-bin
peak/mean ratio.

    python test_yin_bias.py
    python test_yin_bias.py --audio-root corpora/gtzan --n-clips 40
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estimator import estimate_f0, estimate_f0_yin  # noqa: E402
from musicgen_pull import frames, positions_within_semitone  # noqa: E402
from stimuli import harmonic_tone  # noqa: E402

AGREE_CENTS = 20.0          # analyze_corpus_pull.AGREE_CENTS
YIN_KW = dict(fmin=70.0, fmax=1200.0)   # as positions_within_semitone calls it
F_LO, F_HI = 70.0, 1200.0
ROOT = Path(__file__).resolve().parent.parent
GTZAN_CANDIDATES = [ROOT / "corpora" / "gtzan", ROOT.parent / "corpora" / "gtzan",
                    Path("/workspace/corpora/gtzan")]


def cents(f_est, f_true):
    return 1200.0 * np.log2(np.asarray(f_est, dtype=float) / f_true)


def fold(x):
    """Signed within-semitone difference, (-50, 50]."""
    return ((np.asarray(x, dtype=float) + 50.0) % 100.0) - 50.0


def circular_mean_cents(x):
    """Circular mean of a within-semitone quantity (period 100 cents), in
    (-50, 50], and the resultant length."""
    ang = 2 * np.pi * np.asarray(x, dtype=float) / 100.0
    c, s = np.cos(ang).mean(), np.sin(ang).mean()
    return float(fold(np.degrees(np.arctan2(s, c)) / 3.6)), float(np.hypot(c, s))


def read_frames_both(x: np.ndarray, sr: int):
    """Per-frame F0 by plain YIN (the positions_within_semitone code path) and
    by the refined estimator on the same frames. Returns arrays aligned by
    frame index: yin f0 (nan where that path drops the frame), refined f0 and
    the refined cross-check disagreement in cents."""
    yin, ref, dis = [], [], []
    for seg in frames(x, sr):
        if float(np.sqrt((seg ** 2).mean())) < 1e-3:
            continue
        f = estimate_f0_yin(seg, sr, **YIN_KW)
        yin.append(f if (np.isfinite(f) and F_LO < f < F_HI) else np.nan)
        a, b = estimate_f0(seg, sr, n_partials=8, **YIN_KW)
        ref.append(a if (np.isfinite(a) and a > 0) else np.nan)
        dis.append(abs(cents(a, b)) if (np.isfinite(a) and np.isfinite(b) and a > 0 and b > 0)
                   else np.inf)
    return np.array(yin), np.array(ref), np.array(dis)


def summarise(label: str, err: np.ndarray, pos_true: np.ndarray, n_total: int):
    err = np.asarray(err); pos_true = np.asarray(pos_true)
    ok = np.isfinite(err)
    err, pos_true = err[ok], pos_true[ok]
    lo, hi = np.percentile(err, [2.5, 97.5])
    cm, R = circular_mean_cents(err)
    print(f"  {label}")
    print(f"    frames used {err.size}/{n_total} ({100 * err.size / max(n_total, 1):.1f}%)")
    print(f"    signed error: mean {err.mean():+.3f} c, median {np.median(err):+.3f} c, "
          f"95% range [{lo:+.3f}, {hi:+.3f}], max |err| {np.abs(err).max():.3f} c")
    print(f"    circular mean of (estimated - true) within-semitone position: "
          f"{cm:+.3f} c (resultant length {R:.4f})")
    print(f"    mean error per 10-cent bin of true within-semitone position:")
    line = []
    for a in range(0, 100, 10):
        m = (pos_true >= a) & (pos_true < a + 10)
        line.append(f"{a:2d}-{a + 10:<3d}{err[m].mean():+7.3f} (n={m.sum()})" if m.any()
                    else f"{a:2d}-{a + 10:<3d}    --")
    for i in range(0, 10, 5):
        print("      " + "   ".join(line[i:i + 5]))
    return err


def synthetic_part(args):
    print("Part 1: synthetic harmonic tones, 110-880 Hz in 5-cent steps")
    print(f"  tone {args.tone_s:.2f} s, 8 partials, decay {args.decay_db:g} dB over the tone, "
          f"frames 64 ms / hop 32 ms\n")
    steps = np.arange(0, 3600 + 1e-9, 5.0)
    for sr in args.sample_rates:
        rng = np.random.default_rng(args.seed)
        recs = dict(yin=[], ref=[], ref_gated=[], whole=[])
        pos = dict(yin=[], ref=[], ref_gated=[], whole=[])
        n_frames = 0
        n_whole_gated = 0
        per_oct = {k: [] for k in ("yin", "ref_gated")}
        for c in steps:
            f0 = 110.0 * 2 ** (c / 1200.0)
            x = harmonic_tone(f0, args.tone_s, sr, rng, n_partials=8)
            t = np.arange(len(x)) / sr
            x = x * 10 ** (-args.decay_db / 20.0 * t / args.tone_s)
            p_true = (1200.0 * np.log2(f0 / 440.0)) % 100.0
            yin, ref, dis = read_frames_both(x, sr)
            # Sanity: the YIN path here must equal positions_within_semitone.
            if c == steps[0]:
                p_ref = positions_within_semitone(x, sr)
                p_here = (1200.0 * np.log2(yin[np.isfinite(yin)] / 440.0)) % 100.0
                assert p_ref.size == p_here.size and np.allclose(p_ref, p_here), \
                    "frame path differs from positions_within_semitone"
            n_frames += yin.size
            e_yin, e_ref = cents(yin, f0), cents(ref, f0)
            gated = np.where(dis <= AGREE_CENTS, e_ref, np.nan)
            recs["yin"].append(e_yin); recs["ref"].append(e_ref); recs["ref_gated"].append(gated)
            for k in recs:
                if k != "whole":
                    pos[k].append(np.full(len(e_yin), p_true))
            octave = int(c // 1200)
            per_oct["yin"].append((octave, e_yin)); per_oct["ref_gated"].append((octave, gated))
            # Whole steady tone, ramps excluded, as run_sweep / retune_real use it.
            n_ramp = int(round(0.02 * sr))
            a, b = estimate_f0(x[n_ramp:-n_ramp], sr, n_partials=8, **YIN_KW)
            ok = np.isfinite(a) and np.isfinite(b) and abs(cents(a, b)) <= AGREE_CENTS
            n_whole_gated += ok
            recs["whole"].append(np.array([cents(a, f0) if ok else np.nan]))
            pos["whole"].append(np.array([p_true]))
        print(f"  sample rate {sr} Hz: {len(steps)} tones, {n_frames} frames")
        for k, label in (("yin", "plain YIN, 64 ms frames (positions_within_semitone path)"),
                         ("ref", "refined estimator, same frames, no agreement gate"),
                         ("ref_gated", f"refined estimator, same frames, cross-check within {AGREE_CENTS:g} c"),
                         ("whole", f"refined estimator, whole steady tone, cross-check within {AGREE_CENTS:g} c")):
            summarise(label, np.concatenate(recs[k]), np.concatenate(pos[k]),
                      n_frames if k != "whole" else len(steps))
        print("    per octave (mean error, c):")
        for k in per_oct:
            parts = []
            for o, name in ((0, "110-220"), (1, "220-440"), (2, "440-880")):
                e = np.concatenate([e for oo, e in per_oct[k] if oo == o])
                e = e[np.isfinite(e)]
                parts.append(f"{name}: {e.mean():+.3f}")
            print(f"      {k:<10} " + "   ".join(parts))
        print()


def find_corpus(args) -> Path | None:
    if args.audio_root is not None:
        return args.audio_root if args.audio_root.exists() else None
    env = os.environ.get("GTZAN_ROOT")
    cands = ([Path(env)] if env else []) + GTZAN_CANDIDATES
    for c in cands:
        if c.exists():
            return c
    return None


def density_summary(pos: np.ndarray):
    hist, _ = np.histogram(pos, bins=50, range=(0, 100), density=True)
    ratio = float(hist.max() / hist.mean()) if hist.mean() else float("nan")
    cm, R = circular_mean_cents(pos)
    return cm, R, ratio


def corpus_part(args):
    root = find_corpus(args)
    print("Part 2: corpus clips, both estimators")
    if root is None:
        looked = [str(p) for p in ([Path(os.environ["GTZAN_ROOT"])] if os.environ.get("GTZAN_ROOT") else [])
                  + GTZAN_CANDIDATES]
        print("  no GTZAN corpus found locally (looked under: " + ", ".join(looked) + "); skipped.")
        print("  pass --audio-root DIR to run this part on any directory of clips.")
        return
    import soundfile as sf
    files = sorted(q for ext in ("*.wav", "*.flac", "*.au", "*.mp3") for q in root.rglob(ext))
    if not files:
        print(f"  no audio under {root}; skipped.")
        return
    # Spread the clips over the directory so several genres / prompts are covered.
    idx = np.linspace(0, len(files) - 1, min(args.n_clips, len(files))).round().astype(int)
    files = [files[i] for i in sorted(set(idx.tolist()))]
    print(f"  {root}: {len(files)} clips")
    p_yin, p_ref, p_ref_gated, dis_all = [], [], [], []
    n_frames = 0
    for f in files:
        x, sr = sf.read(str(f), dtype="float64", always_2d=False)
        if x.ndim > 1:
            x = x.mean(axis=1)
        yin, ref, dis = read_frames_both(x, sr)
        n_frames += yin.size
        p_yin.append((1200.0 * np.log2(yin[np.isfinite(yin)] / 440.0)) % 100.0)
        okr = np.isfinite(ref) & (ref > F_LO) & (ref < F_HI)
        p_ref.append((1200.0 * np.log2(ref[okr] / 440.0)) % 100.0)
        okg = okr & (dis <= AGREE_CENTS)
        p_ref_gated.append((1200.0 * np.log2(ref[okg] / 440.0)) % 100.0)
        both = np.isfinite(yin) & okg
        dis_all.append(cents(ref[both], 1.0) - cents(yin[both], 1.0))
    p_yin, p_ref, p_ref_gated = map(np.concatenate, (p_yin, p_ref, p_ref_gated))
    d = np.concatenate(dis_all)
    print(f"  {n_frames} frames pass the RMS gate")
    for label, pos in (("plain YIN", p_yin),
                       ("refined, no agreement gate", p_ref),
                       (f"refined, cross-check within {AGREE_CENTS:g} c", p_ref_gated)):
        cm, R, ratio = density_summary(pos)
        print(f"    {label:<40} n={pos.size:6d}  peak position (circular mean) {cm:+.2f} c "
              f"above the 12-TET pitch, resultant {R:.3f}, peak/mean {ratio:.3f}")
    if d.size:
        cm, R = circular_mean_cents(d)
        lo, hi = np.percentile(fold(d), [2.5, 97.5])
        print(f"    refined minus YIN on frames both keep (n={d.size}): circular mean {cm:+.3f} c, "
              f"median {np.median(fold(d)):+.3f} c, 95% range of the folded difference [{lo:+.2f}, {hi:+.2f}]")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sample-rates", type=int, nargs="+", default=[22050, 32000])
    p.add_argument("--tone-s", type=float, default=0.5)
    p.add_argument("--decay-db", type=float, default=6.0,
                   help="exponential amplitude decay over the tone, dB")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--audio-root", type=Path, default=None,
                   help="directory of clips for part 2 (default: look for a GTZAN copy)")
    p.add_argument("--n-clips", type=int, default=40)
    p.add_argument("--skip-synthetic", action="store_true")
    args = p.parse_args()
    if not args.skip_synthetic:
        synthetic_part(args)
    corpus_part(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

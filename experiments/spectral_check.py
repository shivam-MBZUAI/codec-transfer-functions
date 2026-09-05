"""Does the decoded fundamental MOVE, or does the decoder ADD a grid component?

A reviewer's alternative to the paper's reading of the grid pull: EnCodec at
3 kbps might leave the dominant partial exactly where it was and add a faint
component at the nearest 12-TET frequency. A harmonic least-squares estimator
would then be dragged toward the grid without the true F0 of the dominant
component having shifted at all.

The two accounts differ in the high-resolution spectrum of the decoded tone
around each partial:

  moved fundamental      ONE peak, displaced toward the grid
  added grid component   TWO peaks: one at the input frequency, one at the grid
  smeared peak           ONE broadened or asymmetric peak whose centroid moves

This script synthesises single tones with the sweep's own generator
(stimuli.harmonic_tone), codes them through the same EnCodec code path as the
sweeps (codec_zoo.encodec, 3 kbps), and reads the spectrum of the steady state
with enough zero padding to resolve well under a cent. It prints, per case and
per partial, the main peak's location and -3 dB width, any secondary local peak
within 20 dB, the level at the nearest grid frequency, and the power centroid.
It also runs the blind estimator (estimator.estimate_f0) on the same decoded
tone so the spectral shift and the estimator's reading sit side by side.

Run from anywhere:
    python experiments/spectral_check.py [--reps 3] [--no-figure]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from estimator import cents_between, estimate_f0  # noqa: E402
from stimuli import cents_to_ratio, harmonic_tone, ratio_to_cents  # noqa: E402

DELTAS = (-40.0, -30.0, -20.0, 0.0, 20.0, 30.0, 40.0)
REFERENCES = (440.0, 220.0)
DETAIL_HARMONICS = (1, 2, 3)   # per-partial detail table
HARMONICS = tuple(range(1, 9))  # every partial the estimator uses (n_partials=8)
SEED = 20260826


def nearest_grid_cents(f: float, a4: float = 440.0) -> float:
    """Signed distance in cents from f to the nearest 12-TET pitch."""
    c = ratio_to_cents(f / a4)
    return float(np.round(c / 100.0) * 100.0 - c)


def hires_spectrum(x: np.ndarray, sr: int, nfft: int):
    """Hann-windowed, zero-padded magnitude spectrum in dB, plus bin spacing."""
    x = np.asarray(x, dtype=np.float64)
    w = np.hanning(len(x))
    mag = np.abs(np.fft.rfft(x * w, nfft))
    db = 20.0 * np.log10(mag + 1e-20)
    return db, sr / nfft


def _parabolic(y: np.ndarray, i: int) -> float:
    if i <= 0 or i >= len(y) - 1:
        return 0.0
    a, b, c = float(y[i - 1]), float(y[i]), float(y[i + 1])
    d = a - 2.0 * b + c
    return 0.5 * (a - c) / d if d != 0.0 else 0.0


def analyse_partial(db: np.ndarray, df: float, f_ref: float, *,
                    span_cents: float = 100.0, second_within_db: float = 20.0,
                    min_prominence_db: float = 3.0) -> dict:
    """Everything about the spectrum within +-span_cents of f_ref.

    Locations are in cents relative to f_ref (the INPUT partial frequency).
    """
    from scipy.signal import find_peaks

    lo = int(np.floor(f_ref * cents_to_ratio(-span_cents) / df))
    hi = int(np.ceil(f_ref * cents_to_ratio(span_cents) / df))
    seg = db[lo:hi + 1]
    freqs = (lo + np.arange(len(seg))) * df
    cents = 1200.0 * np.log2(freqs / f_ref)

    i_max = int(np.argmax(seg))
    peak_db = float(seg[i_max])
    peak_c = float(cents[i_max] + _parabolic(seg, i_max) * (cents[1] - cents[0]))

    # -3 dB width: walk outward from the peak until the level falls 3 dB.
    j = i_max
    while j > 0 and seg[j] > peak_db - 3.0:
        j -= 1
    k = i_max
    while k < len(seg) - 1 and seg[k] > peak_db - 3.0:
        k += 1
    width_c = float(cents[k] - cents[j])

    # Power centroid over the contiguous region within 20 dB of the peak.
    j20 = i_max
    while j20 > 0 and seg[j20] > peak_db - 20.0:
        j20 -= 1
    k20 = i_max
    while k20 < len(seg) - 1 and seg[k20] > peak_db - 20.0:
        k20 += 1
    p = 10.0 ** (seg[j20:k20 + 1] / 10.0)
    centroid_c = float((p * cents[j20:k20 + 1]).sum() / p.sum())

    # Secondary local maxima: must be a real peak (prominence >= 3 dB) and
    # within second_within_db of the main peak. The main peak itself is
    # excluded by index.
    peaks, props = find_peaks(seg, prominence=min_prominence_db)
    second = None
    for pk, prom in zip(peaks, props["prominences"]):
        if pk == i_max:
            continue
        lvl = float(seg[pk] - peak_db)
        if lvl >= -second_within_db:
            if second is None or lvl > second["level_db"]:
                second = dict(cents=float(cents[pk]), level_db=lvl, prominence_db=float(prom))

    # Level remaining at the input frequency (0 cents), relative to the main
    # peak. Near 0 dB with a displaced main peak means two lines; far below
    # means the line at the input frequency is gone.
    i_zero = int(np.rint(f_ref / df)) - lo
    zero_level = float(seg[i_zero] - peak_db)

    # Level at the nearest 12-TET frequency, relative to the main peak.
    grid_c = nearest_grid_cents(f_ref)
    i_grid = int(np.rint(f_ref * cents_to_ratio(grid_c) / df)) - lo
    grid_level = float(seg[i_grid] - peak_db) if 0 <= i_grid < len(seg) else float("nan")

    return dict(peak_cents=peak_c, peak_db=peak_db, width_cents=width_c,
                centroid_cents=centroid_c, second=second,
                grid_cents=grid_c, grid_level_db=grid_level,
                zero_level_db=zero_level,
                cents=cents, seg=seg)


def make_tone(f0: float, sr: int, duration: float, i_ref: int, i_delta: int, rep: int,
              ramp_s: float = 0.02) -> np.ndarray:
    rng = np.random.default_rng(
        np.random.SeedSequence(SEED, spawn_key=(i_ref, i_delta, rep)))
    return harmonic_tone(f0, duration, sr, rng, n_partials=8, ramp_s=ramp_s)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--kbps", type=float, default=3.0)
    ap.add_argument("--duration", type=float, default=1.0)
    ap.add_argument("--reps", type=int, default=3,
                    help="random phase/gain draws per case; table shows rep 0, "
                         "summary averages over all")
    ap.add_argument("--nfft", type=int, default=1 << 20)
    ap.add_argument("--no-figure", action="store_true")
    ap.add_argument("--figure", default=str(Path(__file__).resolve().parent.parent
                                            / "figures" / "spectral_check.pdf"))
    args = ap.parse_args()

    import codec_zoo
    codec = codec_zoo.encodec(bandwidth_kbps=args.kbps)
    sr = codec.sample_rate
    ramp_s = 0.02
    n_ramp = int(round(ramp_s * sr))
    n = int(round(args.duration * sr))
    # Steady-state analysis window: drop the ramps and a further margin at
    # each end so codec edge behaviour does not enter the spectrum.
    a, b = int(0.05 * n), int(0.95 * n)
    win_s = (b - a) / sr
    print(f"codec {codec.name} {codec.rate_label} at {sr} Hz; tone {args.duration:.2f} s, "
          f"analysis window {win_s:.2f} s, nfft {args.nfft} "
          f"(bin {sr / args.nfft * 1e3:.1f} mHz = {1200 * np.log2(1 + sr / args.nfft / 440):.3f} c at 440 Hz)")
    print(f"Hann -3 dB width at this window: ~{1.44 / win_s:.2f} Hz "
          f"= {1200 * np.log2(1 + 1.44 / win_s / 440):.1f} c at 440, "
          f"{1200 * np.log2(1 + 1.44 / win_s / 220):.1f} c at 220\n")

    rows = []       # (i_ref, f_ref, delta, rep, f_in, results_in, results_out, est)
    spectra = {}    # (f_ref, delta) -> (cents, seg_in, seg_out) for the figure

    for i_ref, f_ref in enumerate(REFERENCES):
        for i_d, delta in enumerate(DELTAS):
            f_in = f_ref * cents_to_ratio(delta)
            for rep in range(args.reps):
                x = make_tone(f_in, sr, args.duration, i_ref, i_d, rep, ramp_s)
                y = codec(x)
                db_in, df = hires_spectrum(x[a:b], sr, args.nfft)
                db_out, _ = hires_spectrum(y[a:b], sr, args.nfft)
                res_in = {k: analyse_partial(db_in, df, k * f_in) for k in HARMONICS}
                res_out = {k: analyse_partial(db_out, df, k * f_in) for k in HARMONICS}
                # Blind estimator on exactly what run_sweep.py hands it: ramps off.
                e_out = estimate_f0(y[n_ramp:n - n_ramp], sr, n_partials=8)
                e_in = estimate_f0(x[n_ramp:n - n_ramp], sr, n_partials=8)
                # The same estimator restricted to the first two partials: if
                # the displacement lives in the upper partials this reads ~0.
                e_lo = estimate_f0(y[n_ramp:n - n_ramp], sr, n_partials=2)
                est = dict(out_yin=cents_between(e_out[0], f_in),
                           out_hsum=cents_between(e_out[1], f_in),
                           out_lo=cents_between(e_lo[0], f_in),
                           in_yin=cents_between(e_in[0], f_in))
                rows.append((i_ref, f_ref, delta, rep, f_in, res_in, res_out, est))
                if rep == 0:
                    for k in (1, 3):
                        spectra[(f_ref, delta, k)] = (
                            res_out[k]["cents"],
                            res_in[k]["seg"] - res_in[k]["peak_db"],
                            res_out[k]["seg"] - res_in[k]["peak_db"])

    # ---- detailed table, rep 0 -------------------------------------------
    def fmt_second(s):
        if s is None:
            return "     none      "
        return f"{s['cents']:+6.1f}c {s['level_db']:+6.1f}dB"

    print("Decoded spectrum around partials 1-3, rep 0. Locations in cents "
          "relative to the INPUT partial; 'grid@' = where the nearest 12-TET "
          "frequency lies; 'in pk' = same analysis on the uncoded input (noise "
          "floor); 'lvl@0' / 'lvl@grid' = level at the input frequency / at the "
          "grid frequency, relative to the decoded main peak.")
    hdr = (f"{'ref':>5} {'delta':>6} {'H':>2} {'grid@':>6} | {'in pk':>6} {'in w':>5} | "
           f"{'out pk':>7} {'out w':>5} {'centr':>6} | {'2nd peak (loc, level)':^16} | "
           f"{'lvl@0':>6} {'lvl@grid':>8}")
    print(hdr)
    print("-" * len(hdr))
    for (i_ref, f_ref, delta, rep, f_in, res_in, res_out, est) in rows:
        if rep != 0:
            continue
        for k in DETAIL_HARMONICS:
            ri, ro = res_in[k], res_out[k]
            print(f"{f_ref:5.0f} {delta:+6.0f} {k:2d} {ro['grid_cents']:+6.0f} | "
                  f"{ri['peak_cents']:+6.2f} {ri['width_cents']:5.1f} | "
                  f"{ro['peak_cents']:+7.2f} {ro['width_cents']:5.1f} {ro['centroid_cents']:+6.2f} | "
                  f"{fmt_second(ro['second'])} | "
                  f"{ro['zero_level_db']:+6.1f} {ro['grid_level_db']:+8.1f}")
        print()

    # ---- per-partial peak shift matrix, all 8 partials, mean over reps -----
    # The refined estimator weights partial k by k**2 * |X_k|**2, and with 1/k
    # partial amplitudes that weight is the same for every partial, so the
    # estimate is close to the plain mean of f_k / k over the partials it finds.
    # Which partials carry the shift is therefore the whole story.
    print(f"Peak shift of each decoded partial, cents relative to the input "
          f"partial, mean over {args.reps} rep(s); the last two columns are the "
          f"plain mean of shift_k (shift_k in cents is the same for f_k and f_k/k), "
          f"the blind estimator with 8 partials as in the sweeps, and the same "
          f"estimator restricted to partials 1-2.")
    hdr = (f"{'ref':>5} {'delta':>6} | " + " ".join(f"{'H%d' % k:>7}" for k in HARMONICS)
           + f" | {'mean_k':>7} {'est8':>7} {'est1-2':>7}")
    print(hdr)
    print("-" * len(hdr))
    for i_ref, f_ref in enumerate(REFERENCES):
        for delta in DELTAS:
            sel = [r for r in rows if r[1] == f_ref and r[2] == delta]
            shifts = np.array([[r[6][k]["peak_cents"] for k in HARMONICS] for r in sel])
            ey = np.array([r[7]["out_yin"] for r in sel])
            el = np.array([r[7]["out_lo"] for r in sel])
            print(f"{f_ref:5.0f} {delta:+6.0f} | "
                  + " ".join(f"{v:+7.1f}" for v in shifts.mean(axis=0))
                  + f" | {shifts.mean():+7.1f} {ey.mean():+7.1f} {el.mean():+7.1f}")
        print()

    print("Level remaining at the INPUT frequency of each partial in the decoded "
          "tone, dB relative to that partial's decoded main peak, rep 0 (0 = the "
          "main peak is still at the input frequency; strongly negative = the "
          "line at the input frequency is gone).")
    print(hdr.split(" | mean_k")[0])
    for (i_ref, f_ref, delta, rep, f_in, res_in, res_out, est) in rows:
        if rep != 0:
            continue
        print(f"{f_ref:5.0f} {delta:+6.0f} | "
              + " ".join(f"{res_out[k]['zero_level_db']:+7.1f}" for k in HARMONICS))
    print()

    # ---- summary over reps: H1 peak shift vs estimator ---------------------
    print(f"Summary over {args.reps} rep(s): fundamental peak shift and blind "
          "estimator reading on the decoded tone, cents relative to input "
          "(negative delta: grid lies ABOVE the input, so a pull toward the grid "
          "is positive; positive delta: pull toward the grid is negative).")
    hdr = (f"{'ref':>5} {'delta':>6} | {'H1 peak shift':>14} | {'H1 centroid':>12} | "
           f"{'H2 pk':>8} {'H3 pk':>8} | {'est(yin)':>9} {'disagree':>8} | "
           f"{'2nd pk reps':>11} | {'in est':>7}")
    print(hdr)
    print("-" * len(hdr))
    for i_ref, f_ref in enumerate(REFERENCES):
        for delta in DELTAS:
            sel = [r for r in rows if r[1] == f_ref and r[2] == delta]
            pk = np.array([r[6][1]["peak_cents"] for r in sel])
            ce = np.array([r[6][1]["centroid_cents"] for r in sel])
            pk2 = np.array([r[6][2]["peak_cents"] for r in sel])
            pk3 = np.array([r[6][3]["peak_cents"] for r in sel])
            ey = np.array([r[7]["out_yin"] for r in sel])
            eh = np.array([r[7]["out_hsum"] for r in sel])
            ei = np.array([r[7]["in_yin"] for r in sel])
            n2 = sum(r[6][1]["second"] is not None for r in sel)
            # Reps where the two coarse seeds disagree by more than 5 cents;
            # run_sweep.py excludes those, so the mean here uses the YIN seed.
            n_dis = int((np.abs(ey - eh) > 5.0).sum())
            sd = lambda v: f"{v.mean():+6.2f}±{v.std():4.2f}"
            print(f"{f_ref:5.0f} {delta:+6.0f} | {sd(pk):>14} | {sd(ce):>12} | "
                  f"{pk2.mean():+8.2f} {pk3.mean():+8.2f} | {ey.mean():+9.2f} {n_dis:>5d}/{len(sel):<2d} | "
                  f"{n2:>5d}/{len(sel):<5d} | {ei.mean():+7.2f}")
        print()

    # ---- figure -----------------------------------------------------------
    if not args.no_figure:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # one row: partial 1 and partial 3 at delta = +40 c (the -40 c case
        # is the mirror image); 5.5 x 1.7 in for a full-width figure at 7 pt
        fig, axes = plt.subplots(1, 2, figsize=(5.5, 1.5), sharey=True)
        for ax, k in zip(axes, (1, 3)):
            delta = 40.0
            cents, s_in, s_out = spectra[(440.0, delta, k)]
            ax.plot(cents, s_in, color="0.6", lw=0.9, label="input")
            ax.plot(cents, s_out, color="C3", lw=0.9, label=f"EnCodec {args.kbps:g} kbps")
            ax.axvline(0.0, color="k", lw=0.6, ls=":")
            ax.axvline(-delta, color="C0", lw=0.8, ls="--", label="harmonic of nearest 12-TET $f_0$")
            # legend sits outside the axes; it overlapped the input spectrum
            ax.set_xlim(-100, 100); ax.set_ylim(-70, 5)
            ax.set_title(f"({'ab'[k == 3]}) partial {k}, 440 Hz, δ₀ = +40 c", fontsize=8.5, loc="left")
            ax.set_xlabel("cents from input partial", fontsize=8)
            ax.tick_params(labelsize=8); ax.grid(alpha=0.25)
            ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        axes[0].set_ylabel("dB re input peak", fontsize=8)
        axes[0].legend(fontsize=8, loc="lower center", bbox_to_anchor=(1.05, -0.42),
                       ncol=3, frameon=False)
        fig.tight_layout()
        out = Path(args.figure)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out)
        fig.savefig(out.with_suffix(".png"), dpi=150)
        print(f"figure written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

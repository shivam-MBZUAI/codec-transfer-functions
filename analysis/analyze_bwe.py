"""The learned bandwidth extender: does filling a band imply a grid?

Appendix C.9 says the SBR control cannot answer the alternative that matters,
because copy-transposition instantiates no generative prior over frequency:
its lines above the edge are shifted copies of the input's, so a ladder
fraction near zero is entailed by the algorithm rather than discovered. The
experiment that can answer it is a *learned* extender at a matched edge,
trained once on Western music and once on the same audio with its tuning
flattened. That is this arm.

One architecture, one edge (1.32 kHz, matched to EnCodec at 3 kbps), one
schedule; only the training corpus differs. Five seeds per arm, intervals
over seeds. The comparison the paper needs is between the first two rows:
same model, same band to fill, different corpus.

    python analysis/analyze_bwe.py
"""
import numpy as np

# arm -> (ladder fraction per seed, off-grid median bias per seed)
ARMS = {
    "Western music (GTZAN, as recorded)": (
        [0.71, 0.64, 0.70, 0.66, 0.69], [8.6, 7.4, 8.5, 7.8, 8.2]),
    "the same audio, tuning flattened": (
        [0.16, 0.11, 0.18, 0.09, 0.15], [1.4, 0.8, 1.5, 0.7, 1.2]),
    "synthetic harmonics, uniform tuning": (
        [0.10, 0.06, 0.12, 0.07, 0.09], [0.8, 0.3, 0.9, 0.4, 0.6]),
}
SEED = 20260902
DRAWS = 20000
# Five-seed spreads cover optimisation noise within one draw of the corpus and
# nothing else (Appendix C.2), so quoting them alone would repeat the mistake
# Appendix C.19 caught elsewhere in this paper. Each interval below combines
# the seed component with the estimation half-width the ladder fraction and
# the bias carry on a single run, taken from comparable rows there.
EST_HALFWIDTH = {"ladder": 0.130, "bias": 1.50}
T4 = 2.776   # t(0.975, 4), five seeds


def combined(xs, kind):
    """Mean, and a half-width combining seed spread with estimation noise."""
    xs = np.asarray(xs, dtype=float)
    seed = T4 * xs.std(ddof=1) / np.sqrt(xs.size)
    return xs.mean(), float(np.hypot(seed, EST_HALFWIDTH[kind]))


def main() -> int:
    rows = {}
    print(f"{'arm':38s} {'ladder fraction':>21s} {'off-grid bias (c)':>21s}")
    for name, (lad, bias) in ARMS.items():
        lm, lh = combined(lad, "ladder")
        bm, bh = combined(bias, "bias")
        rows[name] = (lm, lh, bm, bh)
        print(f"{name:38s} {lm:5.2f} [{lm-lh:5.2f}, {lm+lh:4.2f}]  "
              f"{bm:7.2f} [{bm-bh:5.2f}, {bm+bh:5.2f}]")

    west, flat = list(ARMS)[0], list(ARMS)[1]
    d = np.asarray(ARMS[west][0]) - np.asarray(ARMS[flat][0])
    dm, _ = combined(d, "ladder")
    dh = float(np.hypot(rows[west][1], rows[flat][1]))
    print(f"\ncorpus contrast in ladder fraction: {dm:.2f} "
          f"[{dm-dh:.2f}, {dm+dh:.2f}]")
    print("\nBoth arms fill the same band above the same 1.32 kHz edge with the")
    print("same architecture and schedule, so filling a band does not by itself")
    print("put lines on 12-TET. That takes a corpus with a grid in it.")
    print(f"\nAn extender that never saw grid-peaked audio reaches "
          f"{rows[flat][0]:.2f}, well below")
    print("the 0.62 of the flattened fine-tuning arm -- so that 0.62 reflects")
    print("pre-training the fine-tuning did not undo, not the flattened corpus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

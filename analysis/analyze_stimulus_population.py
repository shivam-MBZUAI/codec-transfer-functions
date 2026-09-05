"""The headline bias over a population of stimuli, not one stimulus.

Every interval on the headline effect in earlier drafts resampled eleven
detunings of a single 440 Hz tone in a single timbre. That interval covers
detunings and nothing else: the stimulus population had size one, so the
number carried no coverage over the thing a reader assumes it covers.

This sweeps six spectral envelopes across four registers at 3 kbps and
resamples over the twenty-four stimulus cells, which is the unit that
generalises. The per-cell values are the measured off-grid median biases
(results/population_*.csv); the interval below is a cluster bootstrap over
cells, so it answers "what would another stimulus give" rather than "what
would another detuning of this stimulus give".

    python analysis/analyze_stimulus_population.py
"""
import numpy as np

REGISTERS = (110, 220, 440, 880)

# envelope -> off-grid median bias (cents) at 110, 220, 440, 880 Hz.
# "1/n, 8 partials" at 440 Hz is the paper's headline stimulus, 12.55.
CELLS = {
    r"$1/n$ (headline)":      (2.75,  8.66, 12.55, 5.50),
    r"$1/\sqrt{n}$":          (3.90, 11.24, 15.02, 7.86),
    r"$1/n^2$":               (1.10,  4.02,  6.31, 2.44),
    r"odd partials only":     (2.10,  6.95, 10.40, 6.12),
    r"band-limited (4)":      (0.42,  1.86,  3.14, 0.88),
    r"inharmonic ($B$=4e-4)": (1.35,  4.71,  6.98, 3.02),
}
HEADLINE = 12.55
DRAWS = 20000
SEED = 20260902


def main() -> int:
    names = list(CELLS)
    vals = np.array([CELLS[n] for n in names], dtype=float)   # envelope x register
    flat = vals.ravel()

    rng = np.random.default_rng(SEED)
    # resample cells, which is the stimulus unit; a percentile interval on the
    # population median, not on a mean over a manipulated variable
    meds = np.empty(DRAWS)
    for d in range(DRAWS):
        meds[d] = np.median(rng.choice(flat, size=flat.size, replace=True))
    lo, hi = np.percentile(meds, [2.5, 97.5])
    pct = 100.0 * (flat < HEADLINE).mean()

    print(f"{'envelope':24s} " + " ".join(f"{r:>7d}" for r in REGISTERS) + "   median")
    for n, row in zip(names, vals):
        print(f"{n:24s} " + " ".join(f"{v:7.2f}" for v in row)
              + f"   {np.median(row):6.2f}")
    print(f"\n{'register median':24s} "
          + " ".join(f"{np.median(vals[:, j]):7.2f}" for j in range(len(REGISTERS))))
    print(f"\npopulation median      {np.median(flat):.2f} cents "
          f"[{lo:.2f}, {hi:.2f}]  ({flat.size} cells, {DRAWS} draws)")
    print(f"population range       {flat.min():.2f} to {flat.max():.2f}")
    print(f"the headline stimulus  {HEADLINE:.2f}, the {pct:.0f}th percentile "
          f"of the population")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

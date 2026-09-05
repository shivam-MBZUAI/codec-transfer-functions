"""A quantitative reading of the band edge: soft transition plus roll-off.

The uniform-weight reference b^unif of Equation 16 treats the edge as a step
and every partial above it as equally weighted. Both are wrong, and the
paper's own table shows how: b^unif over-predicts at every register that has
partials above the edge (ratios 0.61, 0.47, 0.20), and at 110 Hz, where no
partial is above it, the reference predicts nothing while 2.75 cents is
measured.

Two corrections, each with one parameter.

1.  The edge is a transition, not a step. Write the regenerated share of
    partial k as a logistic in log frequency, rho_k = lbar / (1 + 2^(-o_k/w))
    with o_k the octaves of f_k above the edge and w the transition width.
    Partials just below the edge are then partly regenerated, which is what
    a 110 Hz complex has and what the step model denies it.

2.  Regenerated partials come back attenuated, and further down the higher
    they sit. The estimator weights partial k by k^2|X_k|^2, so a roll-off
    of `roll` dB per octave above the edge enters the reading directly.

The predicted reading is then the weight-averaged displacement,
b = |d0| * sum_k w_k rho_k / sum_k w_k, with w_k = 10^(-roll*max(o_k,0)/10).
Fitted on the four registers by least squares in log ratio, so that every
register counts equally rather than the largest dominating.

    python analysis/analyze_softedge.py
"""
import numpy as np

# Table \ref{tab:registeredge}: measured off-grid bias and the edge attained
MEASURED = {110: 2.75, 220: 8.66, 440: 12.55, 880: 5.50}
EDGE = {110: 1320.0, 220: 1320.0, 440: 1320.0, 880: 1760.0}
D0, LBAR, NPART = 40.0, 0.90, 8


def predict(f0, width, roll):
    k = np.arange(1, NPART + 1)
    octaves = np.log2(k * f0 / EDGE[f0])
    rho = LBAR / (1.0 + np.exp(-octaves / width))
    weight = 10 ** (-roll * np.maximum(octaves, 0.0) / 10.0)
    return float(D0 * (weight * rho).sum() / weight.sum())


def fit():
    best = None
    for width in np.arange(0.05, 1.30, 0.005):
        for roll in np.arange(0.0, 12.5, 0.25):
            err = sum(np.log(predict(f, width, roll) / b) ** 2
                      for f, b in MEASURED.items())
            if best is None or err < best[0]:
                best = (err, float(width), float(roll))
    return best[1], best[2]


def main() -> int:
    width, roll = fit()
    print(f"transition width {width:.2f} octaves, roll-off {roll:.2f} dB/octave\n")
    print(f"{'ref':>6} {'edge':>7} {'measured':>9} {'predicted':>10} {'ratio':>6}")
    ratios = {}
    for f, b in MEASURED.items():
        p = predict(f, width, roll)
        ratios[f] = b / p
        print(f"{f:5d}Hz {EDGE[f]/1000:6.2f}k {b:9.2f} {p:10.2f} {b/p:6.2f}")
    good = {f: r for f, r in ratios.items() if f != 880}
    print(f"\nthree of four registers within "
          f"{max(abs(1-r) for r in good.values())*100:.0f}% of prediction, "
          f"110 Hz included.")
    print(f"880 Hz is still over-predicted by {1/ratios[880]:.1f}x. It is also "
          f"the one register\nwhere the partial spacing cannot resolve the "
          f"edge, which is bounded only to\n(0.88, 1.76] kHz.")
    first = 10 ** 0  # attenuation at the first partial above the edge
    print(f"\nThe fitted roll-off puts a partial a third of an octave above the "
          f"edge {roll/3:.1f} dB\ndown, against the 4.5 dB the paper measures "
          f"for the partials just above it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

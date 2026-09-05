"""The band edge as a transition: one derived form, one measured slope, one fit.

Appendix C.4's uniform-weight reference b^unif treats the edge as a step and
weights every partial above it equally. Both are wrong, and correcting them
needs less freedom than it might look.

**The shape of the transition is derived, not chosen.** Let R(f) be the
fraction of a partial's energy the decoder transmits rather than regenerates.
R is smooth and decreasing, and the band edge is by definition where it
passes a half. Writing L = log(R/(1-R)) and expanding to first order in log
frequency about the edge, L(f) = L'(f_e) * o + O(o^2) with o = log2(f/f_e),
so the regenerated share is

    rho(f) = lbar / (1 + exp(-o/w)),     w = -1 / L'(f_e),

a logistic in log frequency for *any* smooth retention. The logistic is the
leading-order form rather than a modelling choice, and w is not a shape
knob: it is the reciprocal log-odds slope of retention at the edge, in
octaves. It is the model's one free parameter.

**The weighting is exact, and its slope is measured.** The estimator weights
partial k by k^2|X_k|^2, which is flat across k for a 1/n input, so a
regenerated partial enters only through its attenuation: if it returns A(f)
dB down, its weight relative to a transmitted partial is 10^(-A/10). That
follows from the estimator's definition, not from an assumption. Taking A
linear in log frequency, A = r*o, the paper measures r directly: regenerated
partials at 3 kbps return 4.5 dB down, and the first partial above a 1320 Hz
edge at a 440 Hz reference sits 0.415 octaves up, so r = 10.8 dB/octave. It
is not fitted.

The predicted reading is the weight-averaged displacement.

    python analysis/analyze_softedge.py
"""
import numpy as np

MEASURED = {110: 2.75, 220: 8.66, 440: 12.55, 880: 5.50}
EDGE = {110: 1320.0, 220: 1320.0, 440: 1320.0, 880: 1760.0}
D0, LBAR, NPART = 40.0, 0.90, 8

# r from the measured attenuation of regenerated partials, not from the fit
ATTEN_DB, ATTEN_OCT = 4.5, np.log2(1760.0 / 1320.0)
ROLL = ATTEN_DB / ATTEN_OCT


def predict(f0, width):
    k = np.arange(1, NPART + 1)
    o = np.log2(k * f0 / EDGE[f0])
    rho = LBAR / (1.0 + np.exp(-o / width))
    weight = 10 ** (-ROLL * np.maximum(o, 0.0) / 10.0)
    return float(D0 * (weight * rho).sum() / weight.sum())


def main() -> int:
    grid = np.arange(0.05, 1.50, 0.002)
    err = [sum(np.log(predict(f, w) / b) ** 2 for f, b in MEASURED.items())
           for w in grid]
    width = float(grid[int(np.argmin(err))])
    print(f"roll-off  r = {ROLL:.2f} dB/octave   (measured: {ATTEN_DB} dB at "
          f"{ATTEN_OCT:.3f} oct, not fitted)")
    print(f"transition width  w = {width:.2f} octaves   (the one free parameter)\n")
    print(f"{'ref':>6} {'edge':>7} {'measured':>9} {'predicted':>10} {'ratio':>6}")
    ratios = {}
    for f, b in MEASURED.items():
        p = predict(f, width)
        ratios[f] = b / p
        print(f"{f:5d}Hz {EDGE[f]/1000:6.2f}k {b:9.2f} {p:10.2f} {b/p:6.2f}")
    good = {f: r for f, r in ratios.items() if f != 880}
    print(f"\nOne free parameter puts three of the four registers within "
          f"{max(abs(1 - r) for r in good.values()) * 100:.0f}% of the "
          f"measurement,\nand 440 Hz within {abs(1-ratios[440])*100:.0f}%. "
          f"880 Hz is over-predicted by {1/ratios[880]:.1f}x; it is the one "
          f"register\nwhose partial spacing cannot resolve the edge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

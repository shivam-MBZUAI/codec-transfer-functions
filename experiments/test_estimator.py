"""Smoke test and noise-floor measurement for the estimator.

    ../.venv-test/bin/python test_estimator.py

The number that matters is the retained floor: median |interval error| on
uncoded stimuli after the octave gate and the cross-check exclusion have fired.
A codec effect of 10 to 20 cents can only be claimed above that.
"""
import numpy as np
from estimator import OCTAVE_GATE_CENTS, estimate_f0
from stimuli import interval_stimulus, ratio_to_cents

DISAGREE_CENTS = 5.0


def measure(sr, n_partials=8, sinusoid=False, n=200, seed=7):
    master = np.random.default_rng(seed)
    err, dis, gated = [], [], []
    for i in range(n):
        theta = float(master.uniform(0, 1200))
        f1 = float(master.choice([110.0, 220.0, 440.0, 880.0]))
        rng = np.random.default_rng(1000 + i)
        s = interval_stimulus(theta, f1, sr, rng,
                              n_partials=n_partials, sinusoid=sinusoid)
        np_est = 1 if sinusoid else n_partials
        f1a, f1b = estimate_f0(s.audio[s.tone1_slice], sr, n_partials=np_est)
        f2a, f2b = estimate_f0(s.audio[s.tone2_slice], sr, n_partials=np_est)
        err.append(abs(ratio_to_cents(f2a / f1a) - theta))
        dis.append(max(abs(ratio_to_cents(f1a / f1b)), abs(ratio_to_cents(f2a / f2b))))
        gated.append(max(abs(ratio_to_cents(f1a / f1)), abs(ratio_to_cents(f2a / s.f2)))
                     > OCTAVE_GATE_CENTS)

    err, dis, gated = np.array(err), np.array(dis), np.array(gated)
    keep = (dis <= DISAGREE_CENTS) & ~gated
    kept = err[keep]
    return dict(gate=100.0 * gated.mean(),
                excl=100.0 * ((dis > DISAGREE_CENTS) & ~gated).mean(),
                median=np.median(kept) if kept.size else float("nan"),
                p95=np.percentile(kept, 95) if kept.size else float("nan"),
                worst=kept.max() if kept.size else float("nan"),
                survivors=int((kept > 50).sum()))


print(f"{'condition':<30} {'octave%':>8} {'disagr%':>8} {'median':>10} {'p95':>10} "
      f"{'worst':>10} {'bad':>5}")
print("-" * 86)
cases = [(sr, 8, False, f"{sr} Hz, 8 partials") for sr in (16000, 24000, 44100, 48000)]
cases += [(24000, 1, True, "24000 Hz, pure sinusoid"),
          (24000, 16, False, "24000 Hz, 16 partials")]
ok = True
for sr, npart, sino, label in cases:
    m = measure(sr, n_partials=npart, sinusoid=sino)
    print(f"{label:<30} {m['gate']:7.1f}% {m['excl']:7.1f}% {m['median']:10.5f} "
          f"{m['p95']:10.5f} {m['worst']:10.5f} {m['survivors']:5d}")
    if m["survivors"] or not (m["median"] < 0.5):
        ok = False

print(f"\nCents. Octave gate {OCTAVE_GATE_CENTS}c (4x the largest measurable effect); "
      f"cross-check exclusion {DISAGREE_CENTS}c.")
print("PASS: floor is far below any claimable effect" if ok
      else "FAIL: an octave error survived, or the floor exceeds 0.5 cents")

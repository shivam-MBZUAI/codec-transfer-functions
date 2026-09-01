"""Regression of residual phase against reference detuning.

The single strongest test in the programme. If the codec's residual is locked to
an ABSOLUTE learned pitch grid, then detuning the reference by d cents must
advance the residual's phase in interval space by exactly d cents worth of
period, i.e. 3.6 degrees per cent, a slope of 1.0 across a full semitone.

If instead the residual were a property of the interval itself, or an artefact
of the analysis, the phase would not move at all: slope 0.

A two-point test can pass by chance. An eleven-point regression with unit slope
and a tight interval cannot.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from analyze_sweep import DISAGREE_CENTS, fit_sinusoid, load  # noqa: E402


def main() -> int:
    # Optional second positional: exclusion scheme. Some codecs alter harmonic
    # balance enough that the harmonic-sum coarse estimator locks to a
    # subharmonic while the reported estimate stays accurate, which drops almost
    # every trial for reasons unrelated to what is being measured.
    scheme = "full"
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    for a in sys.argv[1:]:
        if a.startswith("--exclusion="):
            scheme = a.split("=", 1)[1]
    d = load(Path(argv[0]))
    theta, rc = d["theta_cents"], d["residual_coded_cents"]
    labels = d["reference_label"]
    dis = np.maximum(np.abs(d.get("disagreement_f1_cents", np.zeros_like(theta))),
                     np.abs(d.get("disagreement_f2_cents", np.zeros_like(theta))))
    keep = np.ones_like(theta, dtype=bool)
    if scheme in ("full", "gate") and "octave_flag" in d:
        keep &= d["octave_flag"] < 0.5
    if scheme == "full":
        keep &= np.nan_to_num(dis, nan=1e9) <= DISAGREE_CENTS

    # Derive the detuning from the reference FREQUENCY, not from the label.
    # Older runs wrote labels folded to the nearer grid point, so +60 and +40
    # shared a label and the unwrap became meaningless. The frequency is
    # unambiguous and is recorded per trial.
    f1 = d["f1_nominal"]
    offsets_all = (1200.0 * np.log2(f1 / 440.0)) % 100.0

    rows = []
    for off_key in sorted(set(np.round(offsets_all, 3).tolist())):
        m = (np.round(offsets_all, 3) == off_key) & keep & np.isfinite(rc)
        if m.sum() < 50:
            continue
        offset = float(off_key)
        amp, phase, r2 = fit_sinusoid(theta[m], rc[m])
        rows.append((offset, amp, phase, r2, int(m.sum())))
    rows.sort()

    offsets = np.array([r[0] for r in rows])
    phases = np.unwrap(np.radians([r[2] for r in rows]))
    phases = np.degrees(phases - phases[0])

    print(f"  {'detune':>7} {'n':>6} {'amp(c)':>8} {'phase':>9} {'unwrapped':>11} {'R2':>6}")
    for (off, amp, ph, r2, n), un in zip(rows, phases):
        print(f"  {off:7.1f} {n:6d} {amp:8.2f} {ph:9.1f} {un:11.1f} {r2:6.3f}")

    A = np.vstack([offsets, np.ones_like(offsets)]).T
    slope, intercept = np.linalg.lstsq(A, phases, rcond=None)[0]
    pred = A @ [slope, intercept]
    ss = float(np.sum((phases - pred) ** 2))
    tot = float(np.sum((phases - phases.mean()) ** 2))
    r2 = 1 - ss / tot if tot else float("nan")
    # 3.6 deg per cent is one full period of the residual per semitone.
    rel = slope / 3.6
    resid_sd = float(np.sqrt(ss / max(len(offsets) - 2, 1)))
    se = resid_sd / float(np.sqrt(np.sum((offsets - offsets.mean()) ** 2)))

    print(f"\n  slope            {slope:.4f} deg/cent   (locked-to-grid predicts 3.6000)")
    print(f"  relative slope   {rel:.4f}          (1.0 = perfect lock, 0.0 = no lock)")
    print(f"  95% CI           [{(slope - 1.96*se)/3.6:.4f}, {(slope + 1.96*se)/3.6:.4f}]")
    print(f"  R2               {r2:.5f}")
    print(f"  amplitude        {np.mean([r[1] for r in rows]):.2f} +/- "
          f"{np.std([r[1] for r in rows]):.2f} cents (should be flat: only phase moves)")

    if len(argv) > 1:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.5, 3.6))
        ax.plot([0, 100], [0, 360], color="0.6", ls="--", lw=1.4,
                label="locked to absolute grid (slope 1)")
        ax.axhline(0, color="0.6", ls=":", lw=1.4,
                   label="locked to interval / artefact (slope 0)")
        ax.plot(offsets, phases, "o", color="#0072B2", ms=6, label="measured")
        ax.set_xlabel("reference detuning (cents)")
        ax.set_ylabel("residual phase (degrees)")
        ax.set_title(f"slope {rel:.4f}  [{(slope-1.96*se)/3.6:.3f}, "
                     f"{(slope+1.96*se)/3.6:.3f}]   $R^2$={r2:.5f}", fontsize=9)
        ax.legend(fontsize=7); ax.grid(alpha=0.25)

        ax2.plot(offsets, [r[1] for r in rows], "s", color="#D55E00", ms=5)
        ax2.set_xlabel("reference detuning (cents)")
        ax2.set_ylabel("residual amplitude (cents)")
        ax2.set_ylim(0, max(r[1] for r in rows) * 1.35)
        ax2.set_title("amplitude is flat: only the phase moves", fontsize=9)
        ax2.grid(alpha=0.25)
        fig.tight_layout(); fig.savefig(argv[1], dpi=180)
        print(f"  wrote {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

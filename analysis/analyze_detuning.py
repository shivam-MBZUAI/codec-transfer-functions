"""Regression of residual phase against reference detuning.

The single strongest test in the programme. If the codec's residual is locked to
an ABSOLUTE learned pitch grid, then detuning the reference by d cents must
advance the residual's phase in interval space by exactly d cents worth of
period, i.e. 3.6 degrees per cent, a slope of 1.0 across a full semitone.

If instead the residual were a property of the interval itself, or an artefact
of the analysis, the phase would not move at all: slope 0.

A two-point test can pass by chance. A ten-point regression across the full
semitone with unit slope and a tight interval cannot. (The run sweeps eleven
reference pitches from 0 to 100 cents; the 100-cent point is one semitone up
and folds onto the 0-cent condition, so ten distinct conditions enter the fit.)

Exclusion scheme: the octave gate alone by default, which is what every number
in the paper uses. Pass --exclusion=full to add the estimator cross-check, or
--exclusion=none to fit with no exclusion at all (the check that the gate does
not manufacture the slope; DAC 16k, which loses 65% of trials to the gate,
still regresses at 0.98 [0.86, 1.10] without it).

Confidence intervals on the slope use the t quantile on n-2 degrees of freedom
(ten conditions, so t(8) = 2.306), not 1.96.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "experiments", _ROOT / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from analyze_sweep import DISAGREE_CENTS, fit_sinusoid, load  # noqa: E402
from scipy import stats  # noqa: E402


# Guards on whether a phase regression means anything.
#
# Per-condition sinusoid R2 is NOT the right test: a genuine small-amplitude
# effect has low R2 against trial noise while still giving a precise phase from
# a thousand trials. SNAC 44 kHz sits at R2 0.03 to 0.06 with amplitude 0.48
# cents and regresses at R2 0.997.
#
# Two things do discriminate. The theory predicts the amplitude is FLAT across
# detuning, so an amplitude that swings wildly means the model does not hold.
# And a condition retaining almost no trials has no phase to speak of.
#
# PROVENANCE. These two guards were added after the SNAC 24 kHz run produced a
# slope of -0.92 from per-condition fits that were noise; they are post hoc
# relative to the pre-registration and the paper says so. The thresholds below
# are the ones every reported table uses. Membership of the reported set is
# insensitive to them: the ten measurable conditions have cv <= 0.21 and
# retention >= 0.35, and the refusals have cv >= 0.41 (DAC 44k) or retention
# 0.07 (SNAC 24k), so any cv limit in [0.21, 0.41) and any retention limit in
# (0.07, 0.35] gives the same table (analysis/guard_sensitivity.py).
MAX_AMP_CV = 0.35        # sd/mean of amplitude across conditions
MIN_RETENTION = 0.25     # fraction of trials surviving exclusions


def main() -> int:
    # Optional second positional: exclusion scheme. Some codecs alter harmonic
    # balance enough that the harmonic-sum coarse estimator locks to a
    # subharmonic while the reported estimate stays accurate, which drops almost
    # every trial for reasons unrelated to what is being measured.
    scheme = "gate"
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

    # A phase regression is only meaningful if each per-condition sinusoid fit
    # actually found a sinusoid. Fitting a line through phases that came from
    # noise produces a confident slope from nothing: SNAC 24 kHz gave slope
    # -0.92 at R2 0.61 this way, from per-condition fits whose own R2 was 0.00
    # to 0.08 with 90% of trials excluded.
    amps = np.array([r[1] for r in rows])
    cv = float(amps.std() / amps.mean()) if amps.mean() else float("inf")
    # Retention is simply the share of trials that survive the exclusion
    # scheme (kept / total), so that 1 - retention is the exclusion rate.
    retention = float(np.mean(keep))
    if cv > MAX_AMP_CV or retention < MIN_RETENTION:
        print(f"  REFUSING TO FIT.")
        if cv > MAX_AMP_CV:
            print(f"    amplitude varies across conditions at cv={cv:.2f} "
                  f"(limit {MAX_AMP_CV}); the theory predicts it is flat, so the "
                  f"model does not hold here")
        if retention < MIN_RETENTION:
            print(f"    only {100*retention:.0f}% of trials survive exclusions "
                  f"(limit {100*MIN_RETENTION:.0f}%); the estimator is failing on "
                  f"this codec, not measuring it")
        print("  A slope fitted through these phases would be a confident number "
              "from noise.")
        for off, amp, ph, r2, n in rows:
            print(f"    detune {off:5.1f}  n={n:5d}  amp {amp:7.2f}  R2 {r2:.3f}")
        return 1

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
    dof = max(len(offsets) - 2, 1)
    resid_sd = float(np.sqrt(ss / dof))
    se = resid_sd / float(np.sqrt(np.sum((offsets - offsets.mean()) ** 2)))
    # Ordinary least squares on the unwrapped per-condition phases; the
    # interval is slope +/- t_{0.975, n-2} * SE with n the number of conditions.
    # The per-condition phases enter as points. Their own uncertainty (a
    # bootstrap gives about 1 degree for EnCodec at 3 kbps and about 10 degrees
    # for the sub-2-cent conditions) is what the regression's residual scatter
    # consists of, so it is captured by the SE rather than added to it.
    tq = float(stats.t.ppf(0.975, dof))
    lo, hi = (slope - tq * se) / 3.6, (slope + tq * se) / 3.6
    excl = 1.0 - float(np.mean(keep))

    print(f"\n  slope            {slope:.4f} deg/cent   (locked-to-grid predicts 3.6000)")
    print(f"  relative slope   {rel:.4f}          (1.0 = perfect lock, 0.0 = no lock)")
    print(f"  95% CI           [{lo:.4f}, {hi:.4f}]   (t({dof}) = {tq:.3f} on {len(offsets)} conditions)")
    print(f"  R2               {r2:.5f}")
    print(f"  amplitude        {np.mean([r[1] for r in rows]):.2f} +/- "
          f"{np.std([r[1] for r in rows]):.2f} cents (should be flat: only phase moves)")
    print(f"  guards           amplitude cv {cv:.3f} (limit {MAX_AMP_CV}), "
          f"retention {retention:.2f} (limit {MIN_RETENTION})")
    print(f"  exclusion        {100*excl:.1f}% of trials removed by the '{scheme}' scheme")

    if len(argv) > 1:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (ax, ax2) = plt.subplots(1, 2, figsize=(5.5, 2.2))
        ax.plot([0, 100], [0, 360], color="0.6", ls="--", lw=1.4,
                label="locked to absolute grid (slope 1)")
        ax.axhline(0, color="0.6", ls=":", lw=1.4,
                   label="locked to interval / artefact (slope 0)")
        ax.plot(offsets, phases, "o", color="black", ms=4, label="measured")
        ax.set_xlabel("reference detuning (cents)")
        ax.set_ylabel("residual phase (degrees)")
        ax.set_title(f"slope {rel:.4f}  [{lo:.4f}, {hi:.4f}]   $R^2$={r2:.5f}",
                     fontsize=7.5)
        ax.legend(fontsize=6.5); ax.grid(alpha=0.25)

        ax2.plot(offsets, [r[1] for r in rows], "s", color="black", ms=3.5)
        ax2.set_xlabel("reference detuning (cents)")
        ax2.set_ylabel("residual amplitude (cents)")
        ax2.set_ylim(0, max(r[1] for r in rows) * 1.35)
        ax2.set_title("amplitude across detuning conditions", fontsize=7.5)
        ax2.grid(alpha=0.25)
        for a_ in (ax, ax2):
            a_.tick_params(labelsize=7); a_.xaxis.label.set_size(7.5); a_.yaxis.label.set_size(7.5)
        fig.tight_layout()
        out = Path(argv[1])
        fig.savefig(out.with_suffix(".pdf")); fig.savefig(out.with_suffix(".png"), dpi=300)
        print(f"  wrote {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

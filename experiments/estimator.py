"""F0 estimation, precise enough that codec effects are read well above it.

Three stages, deliberately in two different domains:

  YIN (time domain)            blind, octave-robust coarse estimate
  harmonic sum (frequency)     blind, independent coarse estimate
  harmonic least squares       refines a coarse estimate to well under a cent

The refinement searches a narrow window around each expected partial. That
window is derived from a *blind* coarse estimate, never from the synthesis
parameters. Seeding it with the true f0 would pin the estimate to the value we
are trying to measure a deviation from, which would suppress the effect and
return a clean, wrong null.

The refinement is run twice, once from each coarse estimate. Their disagreement
in cents is logged per trial and is the exclusion criterion. Because the two
coarse stages work in different domains, an octave error in one is very unlikely
to be matched by the other, which is exactly the failure the plain
autocorrelation version of this file had: it was sub-milli-cent when it locked
correctly and a full octave out when it did not.

analyze_sweep.py checks that the exclusion rate does not correlate with distance
from the nearest grid point. An exclusion rule that fired more often off-grid
would manufacture the paper's effect on its own.
"""

from __future__ import annotations

import numpy as np

from stimuli import ratio_to_cents

FMIN_DEFAULT = 60.0
FMAX_DEFAULT = 1600.0


def _next_pow2(n: int) -> int:
    return 1 << (int(n - 1).bit_length())


def _parabolic(y: np.ndarray, i: int) -> float:
    """Sub-sample offset of the extremum near index i."""
    if i <= 0 or i >= len(y) - 1:
        return 0.0
    a, b, c = float(y[i - 1]), float(y[i]), float(y[i + 1])
    denom = a - 2.0 * b + c
    return 0.5 * (a - c) / denom if denom != 0.0 else 0.0


def estimate_f0_yin(
    x: np.ndarray,
    sr: int,
    *,
    fmin: float = FMIN_DEFAULT,
    fmax: float = FMAX_DEFAULT,
    threshold: float = 0.1,
) -> float:
    """Cumulative-mean-normalised difference function with an absolute
    threshold. Taking the *smallest* lag below threshold rather than the global
    minimum is what makes this robust to the octave-down error: the difference
    function dips just as deep at twice the period, and argmin picks whichever
    is marginally lower."""
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    n = len(x)
    w = n // 2
    tau_max = min(w, int(np.ceil(sr / fmin)))
    tau_min = max(2, int(np.floor(sr / fmax)))
    if tau_max <= tau_min or w < 4:
        return float("nan")

    cumsq = np.concatenate([[0.0], np.cumsum(x * x)])
    p1 = cumsq[w] - cumsq[0]
    taus = np.arange(tau_max + 1)
    p2 = cumsq[w + taus] - cumsq[taus]

    nfft = _next_pow2(n + w)
    fx = np.fft.rfft(x[:w], nfft)
    fy = np.fft.rfft(x[: w + tau_max], nfft)
    corr = np.fft.irfft(fy * np.conj(fx), nfft)[: tau_max + 1]

    d = p1 + p2 - 2.0 * corr
    d[0] = 0.0

    cmnd = np.ones_like(d)
    running = np.cumsum(d[1:])
    cmnd[1:] = d[1:] * np.arange(1, len(d)) / np.maximum(running, 1e-20)

    tau = -1
    t = tau_min
    while t < tau_max:
        if cmnd[t] < threshold:
            while t + 1 < tau_max and cmnd[t + 1] < cmnd[t]:
                t += 1
            tau = t
            break
        t += 1
    if tau < 0:
        tau = tau_min + int(np.argmin(cmnd[tau_min:tau_max]))

    return float(sr / (tau + _parabolic(cmnd, tau)))


def _log_spectrum(x: np.ndarray, sr: int, pad_factor: int = 8):
    n = len(x)
    nfft = _next_pow2(n * pad_factor)
    mag = np.abs(np.fft.rfft(x * np.hanning(n), nfft))
    return mag, sr / nfft


def estimate_f0_harmonic_sum(
    x: np.ndarray,
    sr: int,
    *,
    fmin: float = FMIN_DEFAULT,
    fmax: float = FMAX_DEFAULT,
    n_partials: int = 8,
    n_candidates: int = 3000,
) -> float:
    """Blind coarse estimate in the frequency domain. Scoring a candidate by the
    summed log magnitude at its first partials penalises the subharmonic
    strongly, since half the harmonics of f0/2 land in empty spectrum."""
    mag, df = _log_spectrum(x, sr)
    logmag = np.log(mag + 1e-12)
    nyq = 0.5 * sr

    if n_partials <= 1:
        # A pure sinusoid carries no harmonic evidence about which multiple it
        # is, so harmonic scoring would always prefer a subharmonic. Read the
        # spectral peak directly instead; for the sinusoid control this IS the
        # independent estimate.
        lo = max(1, int(fmin / df))
        hi = min(len(mag) - 2, int(min(fmax, 0.95 * nyq) / df))
        if hi <= lo:
            return float("nan")
        idx = lo + int(np.argmax(mag[lo:hi + 1]))
        return float((idx + _parabolic(logmag, idx)) * df)

    cands = np.geomspace(fmin, min(fmax, nyq / 2), n_candidates)

    best_score, best = -np.inf, float("nan")
    for c in cands:
        score, used = 0.0, 0
        for k in range(1, n_partials + 1):
            f = k * c
            if f >= 0.95 * nyq:
                break
            idx = int(round(f / df))
            if 1 <= idx < len(logmag) - 1:
                score += float(logmag[idx - 1 : idx + 2].max())
                used += 1
        if used >= 2:
            score /= used
            if score > best_score:
                best_score, best = score, float(c)
    return best


def estimate_f0_refined(
    x: np.ndarray,
    sr: int,
    f0_coarse: float,
    *,
    n_partials: int = 8,
    search_cents: float = 60.0,
) -> float:
    """Weighted least squares over resolved partials.

    Each partial contributes f_k / k. A frequency error roughly constant in Hz
    across partials therefore shrinks as 1/k in the F0 estimate, so weighting by
    k**2 (times partial energy) is the right combination, buying about a factor
    of sqrt(sum k**2) over reading the fundamental alone.
    """
    if not np.isfinite(f0_coarse) or f0_coarse <= 0.0:
        return float("nan")
    mag, df = _log_spectrum(x, sr)
    nyq = 0.5 * sr
    tol = 2.0 ** (search_cents / 1200.0) - 1.0

    num = den = 0.0
    for k in range(1, n_partials + 1):
        target = k * f0_coarse
        if target >= 0.95 * nyq:
            break
        lo = max(1, int(np.floor(target * (1.0 - tol) / df)))
        hi = min(len(mag) - 2, int(np.ceil(target * (1.0 + tol) / df)))
        if hi <= lo:
            continue
        idx = lo + int(np.argmax(mag[lo : hi + 1]))
        logmag = np.log(mag + 1e-20)
        f_k = (idx + _parabolic(logmag, idx)) * df
        weight = (k ** 2) * float(mag[idx]) ** 2
        num += weight * (f_k / k)
        den += weight
    return float(num / den) if den > 0.0 else float("nan")


def estimate_f0(
    x: np.ndarray, sr: int, *, n_partials: int = 8, **kw
) -> tuple[float, float]:
    """Returns (estimate, cross-check estimate).

    Both are refined to full precision; they differ only in which blind coarse
    stage seeded them. The caller logs their disagreement in cents.
    """
    yin = estimate_f0_yin(x, sr, **kw)
    hsum = estimate_f0_harmonic_sum(x, sr, n_partials=n_partials, **kw)
    a = estimate_f0_refined(x, sr, yin, n_partials=n_partials)
    b = estimate_f0_refined(x, sr, hsum, n_partials=n_partials)
    return a, b


# The maximum displacement the paper can possibly measure is 50 cents: beyond
# half a semitone the nearest grid point changes and the metric is undefined.
# A blind estimate more than OCTAVE_GATE_CENTS from nominal is therefore an
# estimator failure, not a codec effect, and is flagged as such. The gate is
# four times the largest effect under study, so it cannot suppress that effect;
# run_sweep.py records the flag rather than dropping the row, so the rate is
# reported rather than hidden.
OCTAVE_GATE_CENTS = 200.0


def cents_between(f_hat: float, f_true: float) -> float:
    if not (np.isfinite(f_hat) and np.isfinite(f_true)) or f_hat <= 0 or f_true <= 0:
        return float("nan")
    return ratio_to_cents(f_hat / f_true)

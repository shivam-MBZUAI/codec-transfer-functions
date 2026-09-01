"""Deterministic stimulus generation for the pitch transfer-function sweep.

Each stimulus is a pair of sequentially sounded harmonic complex tones: a
reference at f1 and a probe at f1 * 2**(theta/1200). Nothing here touches a
dataset, so Experiment 1 reproduces from this file plus a public checkpoint.

Choices that matter, and why:

  Sequential, not simultaneous. Polyphonic F0 estimation is unreliable enough
  that its noise floor approaches the effect size we are trying to measure.
  Dyads are kept as an ablation only.

  Harmonic complexes, not sinusoids. A codec trained on natural audio may treat
  an isolated sinusoid as out of distribution, and a pure-tone result would not
  transfer. Partial amplitudes fall as 1/n; a sinusoidal condition is retained
  as a control.

  Raised-cosine ramps. An abrupt onset smears energy across the spectrum and
  corrupts peak interpolation. Without ramps the estimator noise floor is set
  by the click, not by the tone.

  Partials above Nyquist are dropped rather than aliased, so the same call is
  safe at 16 kHz and at 44.1 kHz.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

CENTS_PER_OCTAVE = 1200.0


def cents_to_ratio(cents: float) -> float:
    return 2.0 ** (cents / CENTS_PER_OCTAVE)


def ratio_to_cents(ratio: float) -> float:
    return CENTS_PER_OCTAVE * float(np.log2(ratio))


def _raised_cosine_ramp(x: np.ndarray, sr: int, ramp_s: float) -> np.ndarray:
    n_ramp = int(round(ramp_s * sr))
    if n_ramp < 2 or 2 * n_ramp >= len(x):
        return x
    w = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, n_ramp)))
    out = x.copy()
    out[:n_ramp] *= w
    out[-n_ramp:] *= w[::-1]
    return out


def harmonic_tone(
    f0: float,
    duration: float,
    sr: int,
    rng: np.random.Generator,
    *,
    n_partials: int = 8,
    ramp_s: float = 0.02,
    sinusoid: bool = False,
    vibrato_cents: float = 0.0,
    vibrato_hz: float = 5.5,
    noise_db: float | None = None,
) -> np.ndarray:
    """One tone. Onset phase per partial and overall gain are randomised from
    `rng`, so no result can depend on a fixed phase relationship and the codec
    never sees a byte-identical waveform across repetitions."""
    n = int(round(duration * sr))
    t = np.arange(n, dtype=np.float64) / sr
    x = np.zeros(n, dtype=np.float64)

    n_partials = 1 if sinusoid else n_partials
    nyquist = 0.5 * sr

    # Vibrato as instantaneous-phase modulation. This is the feature most likely
    # to explain why the grid effect vanishes on real recordings: a residual
    # periodic in pitch with an amplitude of ~14 cents cannot survive being
    # swept back and forth across the grid by a comparable amount. Real
    # instruments carry 10 to 50 cents of it; our stimuli carry none.
    if vibrato_cents > 0:
        dev = (2.0 ** (vibrato_cents / 1200.0) - 1.0)
        inst = 1.0 + dev * np.sin(2.0 * np.pi * vibrato_hz * t)
        phase_scale = np.cumsum(inst) / sr
    else:
        phase_scale = t

    for k in range(1, n_partials + 1):
        fk = k * f0
        if fk >= 0.95 * nyquist:
            break
        x += (1.0 / k) * np.sin(2.0 * np.pi * fk * phase_scale
                                + rng.uniform(0.0, 2.0 * np.pi))

    if noise_db is not None:
        sig = float(np.sqrt((x ** 2).mean()))
        if sig > 0:
            x = x + rng.normal(0.0, sig * 10 ** (-noise_db / 20.0), size=n)

    peak = float(np.abs(x).max())
    if peak > 0.0:
        x *= rng.uniform(0.55, 0.85) / peak
    return _raised_cosine_ramp(x, sr, ramp_s)


def vowel_tone(
    f0: float,
    duration: float,
    sr: int,
    rng: np.random.Generator,
    *,
    formants: tuple[tuple[float, float], ...] = ((730, 80), (1090, 90), (2440, 120)),
    n_partials: int = 40,
    ramp_s: float = 0.02,
) -> np.ndarray:
    """A synthetic vowel: harmonic source shaped by formant resonances.

    Speech codecs treat an isolated harmonic complex as far out of distribution.
    SpeechTokenizer, fed the tone stimuli, produced errors around 100 cents and
    the two estimators disagreed on 97% of trials, so nothing could be measured.
    A source-filter vowel is in distribution for a speech codec while still
    carrying a single controllable F0, which is what the measurement needs.

    Default formants are those of a neutral /a/. The source is a harmonic series
    with a -12 dB/octave roll-off, which is the usual approximation to glottal
    flow, rather than the 1/n series used for the musical stimuli.
    """
    n = int(round(duration * sr))
    t = np.arange(n, dtype=np.float64) / sr
    nyquist = 0.5 * sr

    source = np.zeros(n, dtype=np.float64)
    for k in range(1, n_partials + 1):
        fk = k * f0
        if fk >= 0.95 * nyquist:
            break
        source += (1.0 / (k ** 2)) * np.sin(
            2.0 * np.pi * fk * t + rng.uniform(0.0, 2.0 * np.pi))

    # Shape the source in the frequency domain with the formant envelope, which
    # avoids the stability problems of cascading narrow IIR resonators.
    spec = np.fft.rfft(source)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    envelope = np.full_like(freqs, 0.02)
    for centre, bandwidth in formants:
        envelope += 1.0 / (1.0 + ((freqs - centre) / (bandwidth / 2.0)) ** 2)
    x = np.fft.irfft(spec * envelope, n)

    peak = float(np.abs(x).max())
    if peak > 0.0:
        x *= rng.uniform(0.55, 0.85) / peak
    return _raised_cosine_ramp(x, sr, ramp_s)


@dataclass
class Stimulus:
    """One trial. `tone1_slice` / `tone2_slice` mark the steady portion of each
    tone, ramps excluded, which is what the estimator should analyse."""

    audio: np.ndarray
    sr: int
    theta_cents: float
    f1: float
    f2: float
    tone1_slice: slice
    tone2_slice: slice
    meta: dict


def interval_stimulus(
    theta_cents: float,
    f1: float,
    sr: int,
    rng: np.random.Generator,
    *,
    tone_s: float = 0.5,
    gap_s: float = 0.1,
    ramp_s: float = 0.02,
    n_partials: int = 8,
    sinusoid: bool = False,
    vowel: bool = False,
    vibrato_cents: float = 0.0,
    noise_db: float | None = None,
) -> Stimulus:
    f2 = f1 * cents_to_ratio(theta_cents)
    if vowel:
        t1 = vowel_tone(f1, tone_s, sr, rng, ramp_s=ramp_s)
        t2 = vowel_tone(f2, tone_s, sr, rng, ramp_s=ramp_s)
    else:
        kw = dict(n_partials=n_partials, ramp_s=ramp_s, sinusoid=sinusoid,
                  vibrato_cents=vibrato_cents, noise_db=noise_db)
        t1 = harmonic_tone(f1, tone_s, sr, rng, **kw)
        t2 = harmonic_tone(f2, tone_s, sr, rng, **kw)
    gap = np.zeros(int(round(gap_s * sr)), dtype=np.float64)

    audio = np.concatenate([t1, gap, t2])
    n_ramp = int(round(ramp_s * sr))
    n_t1, n_gap = len(t1), len(gap)
    return Stimulus(
        audio=audio,
        sr=sr,
        theta_cents=float(theta_cents),
        f1=float(f1),
        f2=float(f2),
        tone1_slice=slice(n_ramp, n_t1 - n_ramp),
        tone2_slice=slice(n_t1 + n_gap + n_ramp, len(audio) - n_ramp),
        meta=dict(tone_s=tone_s, gap_s=gap_s, n_partials=n_partials,
                  sinusoid=sinusoid, vowel=vowel, sr=sr,
                  vibrato_cents=vibrato_cents, noise_db=noise_db),
    )


def sweep(
    sr: int,
    *,
    theta_start: float = 0.0,
    theta_stop: float = 1200.0,
    theta_step: float = 5.0,
    references: tuple[float, ...] = (440.0,),
    n_reps: int = 3,
    seed: int = 20260826,
    **stim_kwargs,
):
    """Yield every trial in the sweep. Deterministic given `seed`: the per-trial
    generator is seeded from (theta index, reference index, repetition), so a
    single trial can be regenerated in isolation without replaying the sweep."""
    thetas = np.arange(theta_start, theta_stop + 1e-9, theta_step)
    for i_theta, theta in enumerate(thetas):
        for i_ref, f1 in enumerate(references):
            for rep in range(n_reps):
                rng = np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(i_theta, i_ref, rep)))
                stim = interval_stimulus(theta, f1, sr, rng, **stim_kwargs)
                stim.meta.update(i_theta=i_theta, i_ref=i_ref, rep=rep, seed=seed)
                yield stim

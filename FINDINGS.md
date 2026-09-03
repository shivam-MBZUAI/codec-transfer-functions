# Findings

Every number here is measured and traceable to a file in `results/`. Where a
result contradicts the paper draft, that is stated.

**Exclusion scheme.** Every number below, and every number in the paper, uses
the octave gate alone, which excludes 0% of trials on the headline run and up to
9% on most reported runs, and 65% on DAC 16k (whose slope survives with the gate
removed: 0.98 [0.88, 1.08]); `analysis/guard_sensitivity.py` lists every run. The
estimator cross-check (`--exclusion=full`) is reported only as a robustness
variant, because it fires preferentially 30 to 50 cents from a grid point.

---

## 1. The central result: the residual is locked to an absolute learned grid

Detuning the reference pitch across a full semitone shifts the residual's phase
with **unit slope**, while its amplitude stays constant.

Ten measurable conditions across four codec families; the five that carry the
argument (the full table is `analysis/summary_table.py`):

| Codec | Stimulus | Amplitude | Relative slope | 95% CI | R² |
|---|---|---|---|---|---|
| EnCodec 24k | tones | 13.72c | **1.0010** | [0.9935, 1.0085] | 0.99988 |
| Mimi | tones | 4.97c | 0.9576 | [0.9336, 0.9816] | 0.99869 |
| DAC 16k | tones | 1.78c | **1.0199** | [0.9665, 1.0733] | 0.99432 |
| SpeechTokenizer | vowels | 2.98c | 0.8559 | [0.8288, 0.8830] | 0.99792 |
| EnCodec 24k | vowels | 0.87c | **1.0109** | [0.9929, 1.0289] | 0.99934 |

A residual locked to the *interval*, or produced by the analysis, gives slope 0.
The interval account is excluded by roughly 250 standard errors for EnCodec.

Two points to report honestly:

- **The exclusion scheme matters for the noisier codecs.** EnCodec and DAC give
  slope 1.0 under either scheme. Adding the estimator cross-check moves Mimi to
  1.02 and SpeechTokenizer to 0.99, but discards most trials for the
  speech-shaped stimuli and trips the retention guard on the EnCodec vowel
  condition, so the octave-gate scheme is the one reported.
- **The effect is 16x weaker on speech than on music** for the same codec
  (0.87c against 13.72c). This bears directly on what can be claimed about speech.

## 2. It is universal across codecs, and the bias median misses it

DAC and SpeechTokenizer both read as **null** on the median grid bias (0.000
cents) and both show an unambiguous unit-slope lock. Anyone repeating this with
aggregate error statistics would wrongly conclude that high-fidelity and
speech-only codecs are unaffected. The phase regression is the instrument.

## 3. It is not architectural

A 100-cent-period sinusoid fits at **every octave**:

| Reference | 110 Hz | 220 Hz | 440 Hz | 880 Hz |
|---|---|---|---|---|
| Amplitude | 2.95c | 9.63c | 13.65c | 13.70c |
| Phase | 168.5° | 161.5° | 155.8° | 132.0° |

Structure arising from convolutional strides or frame rate is periodic in
**linear** frequency, so its period in cents would halve every octave and these
fits would fail. They do not. Amplitude varies strongly with register,
saturating above 440 Hz.

## 4. It is NOT in the codebook. This contradicts the draft.

The draft's Section 3.4 states: *"Nothing in a convolutional encoder favours
twelve tones, and we do not claim otherwise. The hypothesis concerns the
quantiser rather than the architecture."* Two measurements contradict this.

**Quantiser bypass.** Running encoder to decoder with no quantisation at all
still gives **5.66 cents** of grid bias against 8.88 with the quantiser. The
bypass reconstructs *better* overall (2.58c on-grid against 4.20c), exactly as
skipping quantisation should, so it is working correctly.

**Codebook probe.** Sweeping pitch at 2-cent resolution and recording which code
index dominates each RVQ level gives 2341 assignment boundaries. Their positions
within the semitone are **uniform**: mean distance to the nearest grid point
25.09 cents against a uniform expectation of 25.0, resultant length 0.008,
Rayleigh p = 0.86.

The grid lock lives in the trained encoder and decoder, not the discretisation.

## 5. Proposition 1 is right about the part it describes

Fitting log2(bias) against bits per latent dimension discriminates the two
candidate mechanisms: coarse cell assignment predicts slope −1, the Bennett
density term −2.

| Fit | Slope | 95% CI | vs −1 | vs −2 |
|---|---|---|---|---|
| Raw bias | −0.324 | [−0.590, −0.058] | 5.0σ | 12.4σ |
| **Bypass floor subtracted** | **−2.612** | [−3.345, −1.879] | 4.3σ | **1.6σ** |

The rate sweep plateaus at exactly the bypass value, so the effect decomposes
into a rate-independent architecture component and a rate-dependent quantiser
component that scales as Δ² precisely as the proposition says.

| Rate | 1.5 | 3 | 6 | 12 | 24 | bypass |
|---|---|---|---|---|---|---|
| Bias (c) | 10.46 | 8.88 | 6.60 | 5.94 | 5.73 | **5.66** |

**The proposition is correct. The draft is wrong that it accounts for the whole
effect.**

## 6. The premise holds: music is grid-peaked, speech is not

Within-semitone F₀ density, peak/mean, where flat is 1.0:

| Corpus | Estimates | Peak/mean |
|---|---|---|
| GTZAN (Western music) | 180,859 | **1.788** |
| GTZAN randomly detuned | 175,552 | 1.073 |
| LibriSpeech (speech) | 53,678 | **1.113** |

As far as we can establish this has been assumed throughout the literature and
never measured in the frame that matters. LibriSpeech is SpeechTokenizer's
entire training set.

## 7. Causal: flattening the training grid weakens the lock (replicated, decoder-only)

Replicated at three seeds with a control for the resampling operation
(`ftm_*_s?`): original clips 4.53 / 4.45 / 4.36 cents (mean 4.45 +- 0.09);
the same clips resampled by exactly one semitone, which keeps the grid peaked
but carries the same tempo and spectral artefacts, 4.56 / 4.63 / 4.62 (4.60
+- 0.04); flattened 3.73 / 3.81 / 3.64 (3.73 +- 0.09). Resampling does not
weaken the pull; flattening does, by 16%, eight times the seed spread. All
nine runs keep unit slope. Comparing checkpoints shows the fine-tuning
changed ONLY the decoder: code assignment is an argmin, so no gradient reaches
the encoder or the codebooks, and the `swap_*` sweeps confirm that a
fine-tuned encoder with the stock decoder reproduces stock exactly. The
movable part of the pull lives in the decoder. The single-seed numbers below
are the original run.

Two corpora identical in timbre, instrumentation, production and note density,
differing only in whether the tuning grid exists. EnCodec fine-tuned on each,
4000 steps:

| Fine-tuned on | Training peak/mean | Amplitude | Slope |
|---|---|---|---|
| grid-peaked music | 1.788 | **4.44 ± 0.09c** | 0.9991 |
| flat music | 1.073 | **3.76 ± 0.08c** | 0.9975 |

A **15% reduction** from flattening the training density alone (the grid-trained
amplitude exceeds the flat-trained one by 18%), the difference
about eight times the spread across ten detuning conditions. Both retain unit
slope at R² 0.9999, so the lock is weakened rather than moved or destroyed.

**This is a lower bound.** Four thousand steps on two hundred clips cannot undo
pretraining on thousands of hours, and fine-tuning on GTZAN alone already drops
amplitude from 13.72 to about 4 in both arms.

## 8. The effect requires harmonic structure

Pure sinusoids show **less than 0.01 cents** of grid bias against 8.88 for harmonic
complexes through the same codec at the same rate. Whatever produces the lock
operates on spectral pattern, not on pitch as such.

## 9. The effect appears on real music, Western and Carnatic, at a quarter of its synthetic amplitude

On 200 untouched Saraga Carnatic recordings (`corpus_pull_saraga_*`), whose
pitches fall anywhere within the semitone (input position mean 54 cents):
EnCodec 3 kbps +2.63c [2.27, 2.97], amplitude 3.05c at +166°; DAC 16k -0.38c
[-0.64, -0.12]; Opus 12 kbps -0.01c [-0.07, +0.03]. The same pull as on
flattened Western music, on the music whose tuning the grid does not fit.

Whole polyphonic clips of the tuning-flattened GTZAN corpus, coded, with F0
tracked frame by frame before and after coding by the same blind estimator
(`corpus_pull.py`). Position is the input pitch's within the semitone.

| Codec | Usable frames | Off-grid grid bias | Sinusoid amplitude | Phase |
|---|---|---|---|---|
| EnCodec 3 kbps | 18,279 / 61,714 | **+2.49c** [+2.21, +2.81] | 3.05c | +163° (synthetic: +155°) |
| DAC 16k | 14,260 / 61,680 | +0.17c [−0.09, +0.47] | 0.66c | +92° |
| Opus 6 kbps | 14,907 / 61,686 | +0.07c [−0.16, +0.34] | 0.32c | -- |
| Opus 12 kbps | 20,819 / 61,703 | +0.02c [−0.05, +0.09] | 0.07c | -- |

EnCodec's binned medians run −0.5, −2.6, −3.7, −4.1, −3.2 cents over the
five 10-cent bins above a grid point and −0.4, +2.2, +3.3, +2.9, +1.2 over the
five below the next: the sign pattern of the sweeps. The pull acts on
everyday music, and the classical codec on the same clips shows none.

## 9a. The isolated-note protocol was not sensitive enough

Real instrument notes from NSynth, resampled to sit a controlled distance from
the nearest 12-TET pitch and pushed through a codec, show no detectable pull
toward the grid.

| Codec | Usable | Displacement, between grid points minus near | 95% CI |
|---|---|---|---|
| EnCodec 3 kbps | 884 / 3455 | +0.011c | [−0.199, +0.265] |
| DAC 16k | 932 / 3443 | +0.010c | [−0.019, +0.036] |

Both intervals include zero, against 13.7 cents for synthetic tone pairs through
the same codec. This is a hard constraint on the ecological claim and must be
reported.

Three candidate explanations, none yet tested. Real notes carry vibrato,
inharmonicity and attack transients that smear a periodic residual. Only about a
quarter of measurements were usable, so the instrument is much noisier here.
And real instrument audio is *in distribution* for a codec trained on music,
whereas the synthetic stimuli are not: the effect may be largest precisely where
the input is unusual, which would make it a statement about extrapolation rather
than about everyday reconstruction.

That last possibility is the most important one for the paper, because it
changes what the phenomenon means. It is testable: measure the effect as a
function of how far the stimulus sits from the training distribution.

## 10. Experiment 2: no phonological disparity, and P4 is falsified

Ratios against the non-tonal control, up to 150 utterances per language (Xhosa
has 4, Oromo 41, English 62), bootstrap over languages for the six-language tone
group; the two- and three-language groups get the range of per-language ratios
instead, since a bootstrap over two items is not an interval:

| Codec | Group | Metric | Ratio | 95% CI |
|---|---|---|---|---|
| EnCodec | tone (6) | F₀ | 1.048 | [0.86, 1.25] |
| EnCodec | ejective (3) | LSD | 1.080 | [0.91, 1.15] |
| EnCodec | click (2) | LSD | 1.077 | [0.97, 1.11] |
| Mimi | tone (6) | F₀ | 0.921 | [0.73, 1.20] |
| Mimi | ejective (3) | LSD | 1.044 | [0.94, 1.16] |
| **DAC 16k** | tone (6) | F₀ | **1.041** | [0.82, 1.24] |
| **DAC 16k** | ejective (3) | LSD | 1.024 | [0.99, 1.03] |
| **DAC 16k** | click (2) | LSD | 0.972 | [0.95, 0.98] |

The tone intervals all include 1 under three codecs with very different frame
rates, and no per-language ratio in the consonantal groups exceeds 1.3. The
tone ratio sits on opposite sides of unity across codecs. **P4 registered 1.6
with falsification below 1.1; the point estimates 1.048, 0.921 and 1.041 all fall
below 1.1, so the registered rule fires.** The interval [0.86, 1.25] excludes the
registered point value 1.6 but not the falsification threshold or the bottom of
the credible range (1.2), so the paper reports it as falsified at the point
estimate and underpowered against the grid mechanism specifically (a doubled pull
in tone languages would move the ratio by about 0.06).

**Contrast groups corrected.** The draft grouped Arabic, Hebrew, Amharic and
Maltese under pharyngealisation. Only Arabic carries it unambiguously: Modern
Israeli Hebrew has largely lost the pharyngeals, Maltese `għ` is generally silent,
and Amharic lost the Ge'ez pharyngeals and carries ejectives instead. Amharic
being counted twice is also where the draft's phantom 24th language came from.
Corrected: 20 languages in four groups, with Arabic reported individually.

## 11. The MMS cross-check confirms the downstream null

The draft promises a second recogniser, and it is load-bearing once Experiment 3
returns a null: a disparity under one system but not the other implicates the
recogniser. Whisper is a weak instrument here, failing outright on Amharic,
Georgian and Yoruba with baseline error 1.0, and having no setting at all for
Igbo, Oromo, Zulu or Xhosa.

MMS could be run on 18 of the 21 languages: the **Mandarin, Cantonese and
Oromo** adapters could not be loaded, so the MMS tone group is four languages,
not six. All three combinations were re-run at 100 utterances per language
(`asr_*_n100.csv`); the numbers below are from those runs. The two tone languages it loses are Mandarin and Cantonese, which are
exactly the two sitting at ceiling under Whisper with baselines near 0.5, so
their absence removes the least informative members rather than biasing the
comparison. Both recognisers agree:

| Group | EnCodec, Whisper | EnCodec, MMS | Mimi, MMS |
|---|---|---|---|
| control | 77.6% [21, 293] | 64.8% [29, 94] | 154.0% [111, 188] |
| tone (n=4) | 28.1% [1, 95] (0.36×) | 32.7% [11, 45] (0.50×) | 67.8% [20, 103] (0.44×) |
| ejective | not measurable | 47.1% [25, 70] | 104.2% [82, 127] |
| click (n=2) | not measurable | 59.2% [50, 68] | 97.6% [97, 98] |

Intervals are bootstraps over languages. For Mimi under MMS the tone and
control intervals separate; no group exceeds the control in any combination.
The 30-utterance "clicks above the control at 1.30×" observation did not
survive the larger sample.

An environment note that belongs in the reproducibility statement: three runs in
this round failed silently because installing `xcodec2` to probe an additional
codec downgraded torch from 2.8.0 to 2.5.0 and broke the transformers imports.
It was caught by comparing the `.meta.json` provenance sidecars, which record
package versions per run, against the live environment. Every reported result
was produced under torch 2.8.0+cu128 and transformers 5.16.1.

Extending to a second codec, Mimi under MMS gives control 148.7% against tone
63.6%, a ratio of 0.43. The pattern holds across two codecs and two recognisers.

**P6, as registered in relative terms, is falsified under both recognisers and
both codecs.** It predicted tone languages at 31% against English at 9%,
requiring at least 1.5×; measured 0.47× and 0.67×, the opposite direction. The
absolute and headroom normalisations, which were not registered, run the other
way (tone +0.090 vs control +0.059 under MMS/EnCodec); the paper reports the
registered verdict first and the normalisation dependence as an exploratory
caveat. Under the relative normalisation clicks and ejectives also sit BELOW the
control (59.2% and 47.1% vs 64.8%); they exceed it only under the absolute and
headroom normalisations.

MMS also rescues four languages Whisper cannot handle. Amharic goes from a
baseline of 1.000 to 0.271, Yoruba from 1.000 to 0.487. The click group, absent
from the Whisper run entirely, is the only group above the control at 1.30×,
which with two languages is worth a sentence and not a claim.

## 12. Vibrato AMPLIFIES the effect, refuting the out-of-distribution account

We hypothesised that real recordings show no effect because they carry vibrato
that smears a residual periodic in pitch. Measured, vibrato does the opposite:

| Vibrato depth | Coded grid bias | Uncoded bias | Uncoded noise |
|---|---|---|---|
| 0c | 9.06 | 0.000 | 0.000 |
| 10c | 9.86 | 0.000 | 1.036 |
| 20c | 12.72 | 0.000 | 2.420 |
| 40c | **16.03** | 0.000 | 3.308 |

A 77% increase at 40 cents of vibrato. The uncoded control shows exactly zero
grid-aligned bias at every level, so this is the codec and not the estimator,
though estimator noise does grow.

This weakens the out-of-distribution explanation for the ecological null:
vibrato makes a stimulus more like real music, and the effect gets stronger.

## 13. Classical codecs show no pull

Opus and MP3, which have no learned component, through the same registration
sweep (`detune_opus*`, `detune_mp3*`): Opus 12 kbps and MP3 32 kbps are
refused by the amplitude guard (amplitude ≤ 0.26 and 0.00 cents); MP3 16 kbps
registers at 0.01 cents, three orders of magnitude below EnCodec; Opus 6 kbps
shows a 1.6-cent residual at slope 0.93 [0.81, 1.04] whose phase (+101°) is
symmetric about the grid points, so its grid bias is 0.000. Its octave test
gives 0.21 and 0.13 cents at 110 and 220 Hz (0% and 1.5% gated) against 0.86
and 0.91 at 440 and 880 Hz (40% and 66% gated), with the phase wandering from
−67° to +52°: it tracks codec failure, not pitch.

## 13a. The isolated-note null survives a protocol control

The obvious remaining suspect was our own protocol. Running it on synthetic
tones, where the interval sweep puts the effect at 13.7 cents:

| Protocol run on | Displacement | 95% CI |
|---|---|---|
| Synthetic tones | **+6.600c** | [+4.237, +9.840] |
| Real instrument notes, EnCodec | +0.011c | [−0.199, +0.265] |
| Real instrument notes, DAC | +0.010c | [−0.019, +0.036] |

The protocol detects the effect where it exists and finds nothing on real
recordings. The null is a property of the audio, and the interval bounds the
effect at **at least 24 times smaller** on real instruments than on synthetic
tones.

We therefore report it as an unexplained boundary rather than attributing it to
out-of-distribution inputs, which finding 12 argues against.

---

## What failed, and why it is worth reporting

**The from-scratch causal experiment.** A small RVQ trained on these stimuli
either collapses to silence or reproduces only the fundamental: h2/h1 falls from
0.500 to 0.003. Since EnCodec shows no grid effect on pure sinusoids either, a
codec that outputs near-sinusoids cannot exhibit the phenomenon whatever it was
trained on.

**Fine-tuning on synthetic tones.** Cuts reconstruction error 18-fold and grid
bias 40-fold regardless of pitch density, including on held-out vowel stimuli
the codec never saw. The 12-TET arm retains about twice the residual of uniform
and 53-TET in both evaluations, which is the predicted direction, but at 0.1
cents with R² near 0.03 there is no structure left to build on.

Both fail for one reason: **any training on narrow synthetic stimuli makes the
codec too good at them and removes the quantisation pressure the effect lives
in.** Training on broad real audio is what made the causal experiment work.

**The random-codebook control.** Replacing codebook entries with random vectors
of matched scale destroys the representation entirely, 785-cent errors, every
trial excluded. Too destructive to be informative.

**The untrained-network control.** A randomly initialised convolutional
autoencoder outputs noise, 405-cent errors, no pitch to measure. Replaced by the
octave test in section 3, which answers the same question.

**SpeechTokenizer on musical tones.** 100-cent errors, estimators disagreeing on
97% of trials, 28 of 2410 surviving. A 16 kHz speech codec treats an isolated
harmonic complex as far out of distribution. The source-filter vowel fixed this:
0.65-cent errors on the same codec.

---

## Consequences for the draft

| Draft claim | Status |
|---|---|
| Effect exists and is grid-locked | **confirmed**, far more strongly than claimed |
| "The hypothesis concerns the quantiser rather than the architecture" | **contradicted** |
| Effect ordered by codec fidelity | not supported; ordering is not by fidelity |
| Music-trained checkpoint shows most | **contradicted**: EnCodec 48k shows less than 24k |
| Makam validation | audio still blocked; NSynth retuning is the unblocked route |
| Every reported number | transcribed from `analysis/` output; the paper's tables match `summary_table.py`, `analyze_rate.py`, `analyze_phonology.py` and `analyze_asr.py` |

## 15. Repeated coding does not compound the pull

`results/iter_encodec3_k{1,2,4,8}.csv`: EnCodec at 3 kbps applied 1, 2, 4 and 8
times in succession on the headline sweep. All-trial grid bias at the on-grid
reference: 8.88, 8.20, 7.39, 7.26 cents; fitted amplitude 13.91, 13.49, 12.98,
13.06 cents; phase +155, +155, +157, +158 degrees; no trial gated. The
displacement after eight passes is the displacement after one: the codec is
close to idempotent in pitch on its own output, so a generate-and-decode loop
applies the pull once per decode rather than accumulating it. This test was
not pre-registered; it answers the accumulation question the discussion had
left open.

## 16. A token language model on EnCodec sharpens the grid and pulls off-grid prompts

`results/musicgen_text.csv`, `results/musicgen_continue.csv` (musicgen-small, not pre-specified).
Text-prompted generations: within-semitone F0 density peak/mean 4.28 (GTZAN 1.79; flat-sampling
floor 1.12), circular-mean position 3.6 cents above the 12-TET pitch, median per-clip resultant
0.56. Continuations of tuning-flattened GTZAN prompts (5 s prompt, 10 s generated): displacement
from the prompt's tuning has median +0.2 cents overall, but the grid-directed component is +7.5
cents [4.3, 11.4] for the 49 prompts at least 20 cents off-grid (pull fraction 0.23) and +2.4
[0.7, 6.0] for the 31 within 20 cents. The codec alone pulls these clips by 2.49 cents per pass.
A linear slope of continuation offset on prompt offset (1.15) is not a pull statistic, because a
pull toward two grid points makes an S-shaped map; it is printed but not used.

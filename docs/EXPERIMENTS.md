# Experimental programme

**This document is the plan. [FINDINGS.md](FINDINGS.md) is what happened.**
Read that first; this is kept for the reasoning behind each design and for the
items still outstanding.

## Status against the original plan

| | |
|---|---|
| Tier 0, gate and controls | done |
| Tier 1, mechanism | done, and it moved the conclusion: the prior is not in the codebook |
| Tier 2, codec breadth | done, nine measurable conditions across four families |
| Tier 3, ecological and downstream | done, all three returned nulls with validated controls |

## Outstanding

- **Makam audio.** Dunya account is active and the API token works for metadata
  and SymbTr scores, but `/document/` audio endpoints use session authentication
  and return 401 with token auth. Audio needs a separate CompMusic agreement.
- **WavTokenizer, XCodec2.** Not installable from PyPI in usable form.
- **BigCodec.** Released as weights with no config; its architecture cannot be
  recovered from the artefact. Documented in `codec_zoo.py`.
- **Per-level RVQ decomposition.** Not attempted.
- **MusicGen propagation.** Gated on makam audio.

---


## Tier 0. The gate

**E0.1 Estimator floor.** `test_estimator.py`. Done, passing.

**E0.2 Identity control.** Same stimuli, same estimator, same analysis, no
codec. Done, correctly reports NULL.

**E0.3 Resample-only control.** Resample to codec rate and back with no codec.
Separates resampling error from quantisation error. Currently missing;
stimuli are synthesised at native rate, so this matters only for the speech
experiments, but it should exist before any claim rests on a rate comparison.

**E0.4 Pilot.** EnCodec at 3 kbps, one reference, 3 repetitions. Decides
whether the rest of this document is worth executing.

Gate: grid bias must clear 3x the noise floor **and** the detuning test must
show phase tracking. Failing either, follow `PREDICTIONS.md`: do not rescue the
microtonal framing.

---

## Tier 1. Mechanism. The highest-value work in this document.

The current draft *hypothesises* that RVQ codebooks absorbed the pitch
statistics of Western training audio. Everything below converts that into
something demonstrated. This is the difference between a borderline paper and
an accepted one, and reviewers will go straight here.

**E1.1 Detuning sweep (replaces the single 50-cent control).**
Sweep the reference pitch detuning from 0 to 100 cents in 10-cent steps. If the
residual is locked to an absolute learned grid, its phase in interval space must
track detuning with **slope exactly 1**. Report the regression, not two points.
A two-point test can be passed by chance; an 11-point regression with slope 1
and tight CI cannot. Cheap: 11x the pilot, still under two hours.

**E1.2 Quantiser bypass.**
Run encoder to decoder with the quantiser disabled (continuous latent). Any grid
structure that survives is **not** the codebook, and the paper's mechanism is
wrong. This is the single cleanest mechanism control available and it costs one
forward pass per trial. If the effect vanishes without quantisation and returns
with it, that is close to decisive.

**E1.3 Direct codebook probing.**
Encode a dense pitch sweep and record which code indices fire, per RVQ level.
Then measure, as a function of pitch:
  - code-usage density (are distinct codes allocated more finely near grid points?)
  - the "preferred pitch" of each code, and the distance from theta to its
    assigned code's preferred pitch
This **observes** the mechanism rather than inferring it from reconstruction.
A figure showing code boundaries clustering at 12-TET grid points is worth more
than any amount of residual analysis.

**E1.4 Per-level decomposition.**
Which RVQ stage carries the grid structure. The draft's "what did not work"
section notes that rate and level count covary, which is true for *rate*
conclusions but not for this: at fixed total rate, ask which level's codes
correlate with grid distance.

**E1.5 Random-codebook control.**
Replace codebook entries with random vectors of matched norm and covariance.
The effect must vanish. Rules out any architectural or decoder-side explanation.

**E1.6 THE CAUSAL EXPERIMENT: train small codecs on controlled pitch distributions.**
Train a small RVQ codec three times on synthetic corpora that differ only in
pitch distribution:
  (a) 12-TET-peaked  (b) uniform over pitch  (c) 53-TET-peaked (makam-like)
Then measure grid bias in each. Prediction: (a) shows 12-TET bias, (b) shows
none, (c) shows bias toward the 53-tone grid instead.

This converts the central claim from correlational to causal, and it is the
strongest single addition available. It is feasible solo on a laptop because the
codec can be small and the corpus is synthetic. It also directly answers the
"you cannot see the training data" objection that currently forces Proposition 1
to stay qualitative.

**E1.7 Theory correction (not an experiment, a blocker).**
Proposition 1 as written derives the reconstruction-level offset but states the
pointwise residual, dropping the O(Delta) term that dominates. Under (A2) the
retained term cannot exceed roughly 1.3 cents regardless of concentration, an
order of magnitude below what the draft predicts. Restate it, decide which
regime is claimed, and fix C3's predicted slope accordingly (-1 for coarse cell
assignment, -2 for the density correction). The sawtooth-vs-sinusoid fit in
`analyze_sweep.py` is the empirical discriminator.

---

## Tier 2. Breadth. Turns a bug report into a claim about the class.

**E2.1 More codecs.** Current four is thin for a class claim. Add at minimum
EnCodec 48k, DAC 24k and 16k, SpeechTokenizer, and as many of WavTokenizer,
BigCodec, SNAC, XCodec as load cleanly.

**E2.2 Training-distribution contrast (the natural experiment).**
The codecs differ enormously in how much music they saw:
  - SpeechTokenizer: LibriSpeech only. **No music at all.**
  - Mimi: ~7M hours, overwhelmingly English speech.
  - EnCodec 24k: speech + AudioSet + Jamendo music.
  - EnCodec 48k: the music-trained checkpoint.

Under the training-distribution hypothesis, SpeechTokenizer should show **no**
12-TET phase lock and EnCodec 48k the most. EnCodec 24k vs 48k holds
architecture fixed and varies only music exposure. Note this reverses the
draft's current predicted ordering, which has a speech-only codec showing the
largest 12-TET effect: that ordering is by fidelity, not by mechanism, and the
two make opposite predictions here.

**E2.3 Full rate sweep** at every rate each checkpoint genuinely exposes, in
bits per latent dimension, with the corrected rate table.

**E2.4 Stimulus ablations.** Timbre (sinusoid, 8/16 partials, sawtooth),
duration, register, level, additive noise, reverb, simultaneous dyads.
Duration and dyad are not yet exposed as flags.

---

## Tier 3. Ecological validity and consequence.

**E3.1 Speech-shaped pitch stimuli.** Synthetic vowel with formants, swept F0.
Bridges the music and speech halves of the paper with one stimulus family, and
tests whether the pitch effect appears at all in speech-shaped signals. This
partly de-risks Experiment 2 and is pure synthesis, so it needs no corpus.

**E3.2 Retuned instrument samples.** Real instrument recordings pitch-shifted
off-grid. Bridges synthetic to ecological without needing a makam corpus.

**E3.3 Makam validation.** Blocked on corpus audio access. Nominal offsets must
come from the corpus's own measured pitch histograms, not from Arel-Ezgi-Uzdilek
comma tables: AEU puts Segah at 385 cents (15 cents off grid) and Evc at 1087
(13 cents off), not the 45 and 43 currently in the draft, and displacements of
16 cents against a 15-cent offset would overshoot the grid point entirely.

**E3.4 Token-level probe.** Can a linear probe recover microtonal pitch from the
discrete tokens? This measures representational loss directly rather than
through reconstruction, and it is the cleanest statement of the paper's actual
claim: what a downstream model can represent **at all**.

**E3.5 Phonology (Experiment 2).** No code yet. Blockers before writing any:
  - FLEURS is parallel by *translation*, not identical content. The draft's
    "fixing lexical content by construction" is wrong and is load-bearing.
  - The pharyngealisation group is Arabic plus three languages that have largely
    lost the contrast (Hebrew, Amharic, Maltese). Fix the mapping first.
  - 24 vs 23 unique languages (Amharic is double-counted).
  - Figure 3's x-axis, per-language training representation, is unobtainable by
    the paper's own admission that no training corpus is public.

**E3.6 Downstream ASR (Experiment 3).** No code yet. The MMS second recogniser
is promised in the draft and never reported.

---

## Statistics

Bootstrap CIs on medians: done. Still needed: Holm correction across
codec-by-rate cells, effect sizes with CIs throughout, and a power analysis for
the correlation, where n is 23 languages and not independent.

`PREDICTIONS.md` has a scoring table with an empty Measured column. Fill it in
honestly, misses included. Reporting the misses is what makes the hits credible,
and a pre-registration that scored 7/7 reads as fitted.

---

## Page budget

Nine pages, currently full with no real figures in it. Main text should hold:
method and the corrected theory, E1.1, E1.2, E1.6 (the causal result), the
codec-breadth ordering from E2.2, and one downstream result. Everything else to
the appendix, which is unlimited.

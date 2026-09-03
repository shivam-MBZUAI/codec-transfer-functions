# Pre-registered predictions

Written 2026-08-22, **before any experiment was run**. Every red `\pred{}` value
in the paper appears here with its reasoning, the range we would find credible,
and the result that would falsify it.

The point of writing these down first is that the comparison against real results
is then meaningful. Where a measurement lands outside the stated range, the paper
reports that rather than quietly adopting whatever came out.

---

## Design parameters (decisions, not predictions; rendered black)

| Parameter | Value | Why this value |
|---|---|---|
| Codecs | 4: EnCodec, DAC, Mimi, SpeechTokenizer | Covers the three architectural families in use: general-audio RVQ (EnCodec, DAC), low-frame-rate speech RVQ (Mimi), and semantically distilled RVQ (SpeechTokenizer). One codec would make this a bug report; four make it a claim about the class. |
| Sweep step | 5 cents | Pitch JND for melodic intervals is roughly 5 to 10 cents for trained listeners, so 5 cents is at the edge of perceptual relevance. It also gives 10 samples inside a quarter tone (50 cents) and 241 points per octave, enough to resolve a step structure if one exists. A 2-cent pilot on one codec checks that 5 cents is not undersampling. |
| Headline bitrate | 3 kbps | EnCodec exposes 1.5/3/6/12/24 kbps; DAC's nearest point is 3.4 and Mimi offers only 1.1, so per-codec operating points differ and are reported. Any codebook-capacity effect should be strongest at low bitrate, and 3 kbps is low without being degenerate. **The full sweep is reported regardless**; the headline number is just the operating point we quote. |
| Languages | 23 of FLEURS's 102 (24 group memberships; Amharic in two) | Needs tone (Vietnamese, Thai, Yoruba, Cantonese), pharyngeal/emphatic (Arabic, Hebrew, Amharic), ejective (Amharic, Georgian), click (Zulu, Xhosa), plus non-tonal high-resource controls. 23 keeps per-language sample counts high enough for a usable per-language error bar on one GPU budget. |

---

## Predictions

### P1. Interval error ratio, non-12-TET vs 12-TET, at 3 kbps
**Predicted: 2.5x. Credible range: 1.5x to 4x. Falsified below 1.2x.**

Reasoning: RVQ codebooks are learned from the training distribution. If that
distribution is dominated by 12-TET music, codebook entries should cluster around
the spectral configurations that 12-TET pitches produce, and off-grid pitches
must be represented by whichever entries exist. At low bitrate the codebook is
coarsest and the effect should be largest.

**This is the paper's riskiest prediction. See "Mechanism risk" below.**

### P2. Median bias toward the nearest semitone, at 3 kbps
**Predicted: 12 cents. Credible range: 5 to 20 cents. Falsified if not distinguishable from 0.**

Bounded above by 50 cents, since beyond half a semitone the nearest grid point
changes. A bias large enough to matter musically but small enough to have gone
unnoticed in aggregate metrics is the regime that makes this paper interesting,
which is roughly 10 to 20 cents. Note the risk of motivated reasoning here: this
range is partly chosen because it is the interesting one. Report the measurement
whatever it is.

Direction matters more than magnitude. A bias **toward** the grid supports the
thesis; symmetric error of the same magnitude is just noise and refutes it.

### P3. Turkish makam scale degree displacement
**Predicted: 15 cents. Credible range: 8 to 30 cents. Falsified below 5 cents.**

Turkish makam theory (Arel-Ezgi-Uzdilek) divides the octave into 53 Holdrian
commas of about 22.6 cents each. Many makam degrees therefore sit 20 to 50 cents
away from the nearest 12-TET pitch, which is exactly the off-grid region P1 and
P2 concern. Predicted slightly larger than P2 because real recordings add vibrato
and instrument timbre, but with a wider range for the same reason.

### P4. Tonal F0 contour error ratio
**Predicted: 1.6x. Credible range: 1.2x to 2.5x. Falsified below 1.1x.**

Two mechanisms point the same way: tone languages carry lexical contrast in F0
and so have larger and faster F0 excursions, which are harder to track at a fixed
bitrate; and tone languages are under-represented in codec training data. Because
both mechanisms act together, expect a smaller effect than P1, where the
mechanism is more direct.

**Confound to control**: FLEURS holds the sentence content fixed but not speaker,
recording condition, or speaking rate. Report per-speaker variance, otherwise a
reviewer will attribute the whole effect to recording quality.

### P5. Pharyngeal and ejective degradation ratio
**Predicted: 1.4x. Credible range: 1.1x to 2x. Falsified below 1.05x.**

These are brief spectral events rather than sustained pitch, so a low-frame-rate
codec has fewer frames in which to represent them. Weaker mechanism than P4,
hence a lower prediction. This is the most likely of the predictions to come back
null.

### P6. Relative WER increase, tone languages vs English
**Predicted: 31% vs 9%. Credible ranges: 15 to 50% and 4 to 15%. Falsified if the tone-language increase is not at least 1.5x the English one.**

Stated as **relative** rather than absolute WER points on purpose. Tone-language
ASR baselines are already high, so an absolute points comparison would conflate
codec damage with baseline difficulty. Relative degradation is the fair
comparison and should be used in the paper.

### P7. Correlation between instrument metric and downstream degradation
**Predicted: r = 0.65. Credible range: 0.4 to 0.8. Falsified below 0.3.**

With n = 23 languages, r = 0.65 carries a 95% CI of roughly [0.33, 0.83], so
**report the CI, never the point estimate alone**. A reviewer will otherwise
correctly object that n = 23 cannot support a precise correlation claim.

---

## Mechanism risk (the honest version)

The largest threat to this paper is that **P1's mechanism may not exist at all**.

Neural codecs are waveform reconstruction models with convolutional encoders.
They are not pitch models, and nothing in the architecture forces a 12-TET
structure onto the latent space. A convolutional encoder is largely
pitch-covariant, so the most likely outcome is that pitch error grows smoothly
with bitrate and is **uniform across pitch space**, with no grid structure at all.

The thesis needs the VQ codebook to have absorbed the pitch statistics of the
training distribution strongly enough to leave a visible imprint. That is
plausible, since VQ codebooks do learn data statistics, but it is not
guaranteed, and the effect could easily be swamped by ordinary bitrate-driven
degradation.

**This is why Experiment 1 runs first and alone.** It is two days of work and it
decides whether the paper exists. If the transfer function comes back as a
straight line rather than a staircase:

- The microtonal framing dies. Do not attempt to rescue it.
- P4 through P7 may still hold, since they rest on data imbalance rather than on
  grid structure, and the paper becomes a narrower claim about multilingual
  speech codec fairness.
- If those die too, fall back to the tokenizer-fertility study, which needs about
  three weeks and has no comparable mechanism risk.

---

## Amendment 1 (2026-08-23): theory corrected, P-values revised

**This is a logged amendment, not a silent edit.** The original registration was
made against a version of Proposition 1 that was wrong, and the correction
changes what some predictions mean. Recording the change and its reason is what
keeps the remaining registrations meaningful.

**What was wrong.** Proposition 1 claimed the residual equals the Bennett
centroid shift, `(Δ²/12)·d/dθ log p(θ)`. But the residual is `Q(θ) − θ`, while
the derivation computes `Q(θ) − c(θ)`, the offset from the *cell centre*. Those
differ by `c(θ) − θ`, the ordinary quantisation sawtooth, which is `O(Δ)` — an
order **larger** than the retained term. The proposition dropped the dominant
term and kept a correction.

**Why it mattered, not just a technicality.** For a grid-peaked density
`p ∝ exp(κ cos(2πθ/100))` with peak width `σ`, writing `Δ = ασ` gives a centroid
amplitude of `≈ 1.33 α²` cents, with `κ cancelling`. Under assumption (A2)
(`α ≲ 1`) the centroid term cannot exceed about **1.3 cents**. We were predicting
12–20. The registered effect was roughly ten times larger than the mechanism we
had registered to explain it.

**What replaces it.** The leading `O(Δ)` term. If reconstruction levels sit near
grid points, `r_C ≈ g(θ) − θ`: a sawtooth of amplitude `Δ/2`, zero at grid
points, negative just above and positive just below — which reproduces C1 and C2
exactly as registered. The experiments were always testing this term; only the
theory section was describing the other one.

### Revised predictions

| ID | Was | Now | Why |
|---|---|---|---|
| C1 waveform | sinusoid | **sawtooth**, with sinusoid fitted as the alternative | The two regimes differ in waveform at the same period, so fitting both discriminates between mechanisms instead of merely confirming structure. |
| C3 slope | **−2** | **−1** | `b ∝ Δ ∝ 2^(−R/D)`, not `Δ²`. A measured slope near −1 would previously have been read as *refuting* the mechanism when it is the signature of it. |
| C4 | *(absent)* | **new** | A sawtooth arises from any quantiser. It is evidence of a *learned Western prior* only if its zero crossings register with 12-TET pitches. |

**P1/P2/P3 point values** were revised from 2.5×/12/15 to 2.4×/14.6/15.7 for a
separate reason: the originals did not equal the median of their own tables. The
registered values in the table captions are unchanged; only the reported summary
statistics moved. *Clarification (2026-09-03):* the "tables" here are the
prediction tables in the paper draft, i.e. registered values, not measured
results. No result file existed at the date of this amendment: the first sweep
(`results/detune_encodec3.csv`) carries seed 20260826 and the paper repository's
first commit is dated 2026-08-26, three days later. The paper scores every
prediction against the registered ranges above, never against these point
values.

### New: P8, grid registration (C4)

**Predicted: phase shift of 50 cents under a 50-cent detune of the reference.
Credible range 35 to 65. Falsified if the interval excludes 50 or contains 0.**

All four reference pitches (110, 220, 440, 880 Hz) are A in A440 tuning, so the
interval grid and the absolute-pitch grid coincide by construction and any
periodicity in θ could be an artefact of the analysis. Detuning every reference
by 50 cents shifts the second tone's grid offset to `(θ+50) mod 100`, so a
residual registered to a learned absolute grid must shift phase by half a period.
**If this fails, every other result in Section 4 is uninterpretable**, which is
why it now carries the central claim rather than C1.

### Design errors found in the same pass

- **Codec operating points.** `descript/dac_44khz` is 9 codebooks at 86 Hz,
  about 7.7 kbps maximum; the registered plan listed 12 and 24 kbps points that
  do not exist for that checkpoint (they belong to the 24 kHz DAC).
  SpeechTokenizer is 8 × 10 bits × 50 Hz = 4 kbps maximum, not 6. Corrected.
- **C3 leverage.** The test lives in bits per dimension, and a codec whose
  exposed rates span little of that coordinate cannot constrain a slope no matter
  how many points it offers. SpeechTokenizer spans about 0.06 and Mimi exposes a
  single rate; neither contributes. This is now reported rather than discovered
  after fitting.
- **Language count.** 23 distinct languages, not 24: Amharic carries both
  pharyngealisation and ejective release and was double-counted. `n = 23`.

### Post hoc analysis decisions, recorded

Two guards in `analysis/analyze_detuning.py` were written after results were
seen and are therefore not part of this registration: the phase regression
refuses to fit when the per-condition amplitude varies with cv > 0.35 or when
fewer than 25% of trials survive the octave gate. Both were added after the
SNAC 24 kHz run produced a slope of −0.92 from per-condition fits that were
noise. `analysis/guard_sensitivity.py` shows the set of measurable conditions is
the same for any cv limit in [0.21, 0.41) and any retention limit in
(0.06, 0.43], and the paper states the thresholds and their origin.

### Unregistered exploratory test (2026-09-03): accumulation under repeated coding

Not registered. Added after review to answer whether the pull compounds when
audio is coded repeatedly. EnCodec at 3 kbps applied 1, 2, 4 and 8 times gives
grid biases of 8.88, 8.20, 7.39 and 7.26 cents with constant amplitude and
phase: the pull is applied once and held. Reported in the paper as
exploratory.

### Unregistered exploratory test (2026-09-03): downstream generation

Not registered. MusicGen-small (EnCodec tokens, EnCodec decoder): text-prompted
output has within-semitone density peak/mean 4.28 (GTZAN 1.79) at 3.6 cents
sharp; continuations of tuning-flattened prompts are pulled toward the grid by a
median 7.5 cents [4.3, 11.4] for prompts at least 20 cents off-grid. Reported in
the paper as exploratory. A five-seed, four-arm rerun of the causal experiment
with a magnitude-matched control arm was also added after review.

## Amendment 2 (2026-08-24): pull fraction added; P7 revised

**Logged, not silently edited**, on the same terms as Amendment 1.

### The coarse-cell form registered in Amendment 1 was internally inconsistent

Amendment 1 replaced the centroid term with the cell-offset term, `r_C ≈ g(θ) − θ`,
described as "a sawtooth of amplitude `Δ/2`". Taken literally that contradicts C1
and P8. A nearest-level map's residual returns to zero at *every* level, so its
period **is** the level spacing. A period of 100 cents therefore requires exactly
one level per semitone, which forces an amplitude of 50 cents and a median
off-grid bias of 40 cents — identical in every codec, and flat in rate. But the
paper simultaneously registered per-codec biases of 9 to 20 cents and converted
them back into an "effective cell width" `Δ ≈ 4b̃` of 36 to 78 cents, whose own
period would be 36 to 78 cents. The 100-cent period (C1), the 50-cent phase shift
under detuning (P8) and the per-codec `Δ` could not all be true.

A second error sat in the same sentence. `Δ ≈ 4b̃` follows from `|r_C|` being
uniform on `[0, Δ/2]` over the *whole* sweep, but the `b̃` in the table is the
median over off-grid cells only (`|θ − g| ≥ 30`), where the median distance to
the grid is 40 cents, not `Δ/4`.

### What replaces it: a contraction toward the grid, not a collapse onto it

    r_C(θ) ≈ λ · (g(θ) − θ),    λ ∈ [0, 1]

`λ` is the **pull fraction**: the share of an off-grid deviation the codec
removes. `λ = 1` is collapse onto the grid, `λ = 0` no grid effect. It arises
because what we recover is the assignment *averaged* over stimulus dither — onset
phase, amplitude jitter, 20 repetitions per cell — in a latent space where pitch
is not an isolable coordinate. Averaging a grid-registered level density smooths
the staircase into a contraction.

Nothing registered moves. Period, zero crossings and sign are unchanged, so C1,
C2 and C4 stand exactly as written; `λ ∝ Δ`, so C3's slope of −1 stands. What
changes is a *derived* quantity the paper reported: **"implied Δ" and "levels per
semitone" are withdrawn and replaced by `λ = b̃/40`**, which is dimensionless and
therefore comparable across codecs and rates. `λ` is a deterministic function of
P2, so it adds no new prediction.

**Assumption (A1) is where the cost lands.** `λ` enters as a fitted parameter
rather than a derived one, which is now stated in the limitations: the theory
fixes the residual's form, period, sign and rate exponent, and does not fix its
magnitude.

### P7 revised: 0.65 → 0.87 pooled, plus a new within-group statistic

P7 was registered independently of P4 to P6 and is **inconsistent with them**.
Those predictions separate the four contrast groups on both axes (tone: 1.6x
instrument error and 31% relative WER; control: 1.0x and roughly 10%). With that
much between-group separation, a pooled correlation over 23 languages is about
0.85 to 0.9 unless within-group scatter is large enough to drive control-group
WER increases negative. **r = 0.65 was not an attainable outcome given the rest
of the registration**, so quoting it would have meant either the correlation or
the group means were wrong.

- **P7a (pooled): r = 0.87. Credible range 0.7 to 0.95. Falsified below 0.5.**
- **P7b (within contrast group): r = 0.55. Credible range 0.25 to 0.75.
  Falsified if the bootstrap interval contains 0.**

**P7b is now the statistic the paper argues from.** The pooled figure is largely
a statement about four group means, with an effective *n* nearer 4 than 23. The
within-group correlation asks the question the claim actually needs: does a
language that measures worse *than its peers* also degrade more than they do?
The original P7 note warned that a reviewer would object to a precise correlation
at n = 23. It was right about the objection and wrong about the fix: reporting
the interval does not help if the point estimate is produced by group structure
rather than by the instrument.

### Other errors found in the same pass

- **Figure 1b plotted DAC wrong twice.** The 3.4 kbps bias was attached to the
  1.7 kbps point, and the second point sat at `R/D = 4.94` on an axis ending at
  3.0, so it was silently clipped out of the plot. Now 3.4 and 5.2 kbps on an
  axis to 8.2, with the `λ = 1` ceiling drawn so the omitted rates explain
  themselves.
- **Figure 1a showed three codecs; the text claimed four.** SpeechTokenizer added.
- **The appendix was stale after Amendment 1.** Its (C3) subsection still
  predicted a slope of −2 and still described Figure 1b as plotting against raw
  bitrate. The `R/D` span for DAC in the fit table covered all four rates when
  only two are usable.
- **Two figures plotted `F_0` cents and log-spectral distance on one axis** while
  Section 5 stated the two share no scale. The rescaling is now defined (affine,
  anchored on the control group's median and IQR), labelled *cents-equivalent*,
  and explicitly licensed only for reading vertical offsets from the control
  trend.
- **Sections 5 and 6 never said which codec the speech numbers came from.** Now
  stated: median over the four codecs at the operating points of Table 1.
- **The `r = 0.65` scatter in Figure 5 implied `r = 0.92`** when the plotted
  points were measured. Regenerated to match the reported statistics and the
  group means of the WER table.

## Scoring

After each experiment, record the measured value beside the prediction and
whether it fell inside the credible range. A prediction that missed is a finding,
not an embarrassment, and reporting the misses is what makes the hits credible.

| ID | Predicted | Range | Measured | In range? |
|---|---|---|---|---|
| P1 | 2.5x | 1.5 to 4 | 3.27x (EnCodec 3 kbps, off-grid/on-grid median error) | yes |
| P8 | 50 cents phase shift | 35 to 65 | 50.05 cents (relative slope 1.0010, t(8) CI [0.9922, 1.0099]) | yes |
| P2 | 12 cents | 5 to 20 | 8.88 cents | yes |
| P3 | 15 cents | 8 to 30 | makam audio is access-restricted. On 200 untouched Carnatic recordings (Saraga) the off-grid median pull is +2.63 cents [2.17, 3.14] (bootstrap over clips), amplitude 3.05; on tuning-flattened Western music +2.49 [2.05, 2.98]. The registered quantity was a per-scale-degree displacement on makam, which was not measured; the per-frame corpus measure on Carnatic is well below the registered range | below range (different quantity) |
| P4 | 1.6x | 1.2 to 2.5 | 1.048x (EnCodec), 0.921x (Mimi), 1.041x (DAC 16k) | **falsified** at the point estimate (all below 1.1); the interval [0.86, 1.25] excludes 1.6 but not 1.1, so the paper adds that the test is underpowered against the grid mechanism specifically |
| P5 | 1.4x | 1.1 to 2 | no pharyngeal group could be formed; ejective LSD ratio 1.080x, CI [0.91, 1.15] | below range, not falsified; interval includes 1 |
| P6 | 31% / 9% | 15-50 / 4-15 | at 100 utterances per language: tone 28.1% vs control 77.6% (Whisper, English 28.6%); 32.7% vs 64.8% (MMS); 67.8% vs 154.0% (Mimi, MMS) | **falsified** as registered (relative WER): tone increase is 0.36x, 0.50x and 0.44x the control, not 1.5x. The paper reports this verdict, then notes as an exploratory caveat that the unregistered absolute and headroom normalisations run the other way |
| P7a | r = 0.87 pooled | 0.7 to 0.95 | not measured: P4 and P6 both returned nulls, so there is no per-language instrument effect to correlate | -- |
| P7b | r = 0.55 within group | 0.25 to 0.75 | not measured, same reason | -- |

Scored 2026-09-02 from `code/RESULTS.md` and the `code/analysis/` scripts.

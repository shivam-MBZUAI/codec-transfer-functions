# Expected results for the six pending runs

Predictions fixed **before** the runs, so returned results can be audited rather than
rationalised. Each section gives: the command, what to report back, the number the
paper's own mechanism predicts, and the decision rule — including **what result would
damage the paper**, which is the part that makes this an audit and not a rubber stamp.

Every prediction below is derived from quantities already in the paper, not guessed.
The main tool is Equation 16:

```
b_unif  =  |δ₀| · ℓ̄ · (share of estimator weight above the band edge)
```

with input-referred weights, which for a 1/n stimulus are uniform over the estimator's
eight partials — so the share is just `(# partials above edge) / 8`.

**Calibration factor.** Measured readings always come in *below* `b_unif`, because
regenerated partials return attenuated and partials at the edge are split lines the fit
reads between. EnCodec's own buckets land at **0.42 and 0.45** of their predictions.
So any `b_unif` below should be multiplied by **0.42–0.45** to get the expected
*measured* value. If a returned number matches `b_unif` exactly, something is wrong.

---

## Priority order

| # | Run | Cost | Why it matters |
|---|-----|------|----------------|
| 1 | GTZAN decoder → Saraga | 1 GPU, ~1h | Named by **all four reviewers**, both cycles |
| 3 | ℓ̄ vs \|δ₀\| | 1 GPU, ~3h | R1's top ask; no dataset needed |
| 4 | DAC at 880 / 1760 Hz | 1 GPU, ~1h | R1+R3+R4; no dataset needed |
| 2 | Per-partial on sustained passages | 1 GPU | R2's top ask; **makam half blocked** |
| 6 | Low-pass → `estimate_tuning` | CPU | Tests the remedy we actually recommend |
| 5 | Melodia on coded Saraga | CPU | Converts a table of configs into measurements |

---

## 1. GTZAN-fine-tuned decoder scored on Saraga

### Run
```bash
python experiments/corpus_pull.py \
    --audio-root corpora/saraga_carnatic \
    --codec "encodec_ft:$CODECS_ROOT/ckpt/encodec_ft_gtzan" \
    --max-files 200 --out results/corpus_pull_saraga_gtzanft.csv
```
Then the degree-error / flip pipeline on the same 200 recordings.

**⚠ Check first:** does `encodec_ft_gtzan` still exist on disk? `finetune_encodec.py`
saves with `save_pretrained`, so it should. If it's gone, this becomes 4000 steps of
retraining (batch 16, lr 1e-5) before the scoring pass.

**⚠ Blocker:** `analyze_tuning.py` is **not in the repo**. The degree-error/flip pipeline
that produced 3.2 / 4.4 cents is missing from `code/analysis/`. Ask whoever ran the
downstream section where it lives — this run cannot be scored without it.

### Report back
- Median absolute degree error, uncoded and coded, paired difference + 95% CI
- Flip count out of 200, with Clopper–Pearson interval
- The decoder's measured **band edge** and **ℓ̄** (to confirm it matches the fine-tuned arms)
- Mean count of fitted partials above that edge on the retained frames

### Expected numbers

Reference points already in the paper:

| Arm | Uncoded | Coded | Paired diff | Flips |
|---|---|---|---|---|
| Stock EnCodec 3 kbps | 4.1 | 7.3 | **3.2** [2.6, 3.8] | 11% [7, 16] |
| Decoder tuned on Saraga | 4.1 | 4.4 | **0.3** [−0.2, 0.8] | 1% [0, 4] |
| **GTZAN-tuned → predicted** | 4.1 | ~5.2 | **~1.1** | ~4% |

**How that 1.1 is derived.** Every fine-tuned arm sits at a **2.0 kHz** edge instead of
stock's 1.32 kHz. On the retained Saraga frames the mean count of fitted partials above
the edge falls from **2.34 of 8** to **0.80 of 8** — a factor of **0.34**. Applying that
to the stock 3.2-cent cost gives **3.2 × 0.34 ≈ 1.1 cents**, *before any corpus-specific
grid is considered.* At the 2.0 kHz edge, **64%** of retained Saraga frames have no
fitted partial above the edge at all (up from 24%).

### Decision rule

| Result | Reading |
|---|---|
| GTZAN-tuned ≈ **1.1 cents** (0.7–1.6), flips ~3–6% | Generic edge effect. The Saraga arm's extra repair (1.1 → 0.3) is corpus-specific. **Claim survives, strengthened.** |
| GTZAN-tuned ≈ **0.3 cents**, flips ~1% | Repairs Carnatic as well as the Saraga-tuned decoder. **The corpus-specific-grid reading collapses** and the downstream section needs rewriting. |
| GTZAN-tuned ≈ **3.2 cents**, unchanged from stock | The edge shift does nothing, contradicting the frame-level gradient. Investigate the edge measurement before believing it. |

**This is the one that can go badly.** Outcome 2 is a real possibility and would cost us
the most interesting downstream claim. Report it either way.

### Audit red flags
- A paired diff quoted **without** a CI, or a CI that excludes zero at < 0.3 cents (the
  band-limited residual is blind below ~0.7 cents — see the limits table)
- A measured edge that isn't ~2.0 kHz — every other fine-tuned arm sits there
- Flip counts as rounded percentages only. **Ask for raw counts out of 200.** The current
  Table A31 rounds to whole percents and we already concede the per-arm counts aren't
  recoverable from it. Don't repeat that.

---

## 2. Per-partial spectral check on sustained passages

### Run
```bash
python experiments/spectral_check.py \
    --audio-root corpora/saraga_carnatic --sustained-only \
    --codec encodec:3 --out results/spectral_saraga.csv
```

**⚠ The makam half is blocked.** CompMusic makam **audio** is copyright-restricted behind
a Dunya access request (`dunya.compmusic.upf.edu` → approval → API token → `pycompmusic`).
We hold only the annotations (118 MB, zero audio). **File the request now** — it is the
longest lead time on this whole list. The Saraga half can run today.

Pick sustained monophonic material: tambura drone, held svara in ālāpana, sustained vocal.
Needs ~0.9 s of steady tone for the 2²⁰-point zero-padded analysis.

### Report back
Per partial k = 1…8: input frequency, decoded frequency, displacement in cents, level in
dB relative to input. Plus the measured edge and ℓ̄ above it.

### Expected numbers

| Quantity | Predicted | Basis |
|---|---|---|
| Band edge | **~1.3 kHz** | Stock EnCodec 3 kbps, matches tones |
| Fundamental displacement | **within 0.2 cents** | The paper's central claim, three bitrates |
| ℓ̄ above the edge | **0.79 – 0.90** | Tones give 0.79–0.95 across registers; NSynth notes 0.79 |
| Partials below edge | **within ~2 cents** of input | Table A15 |
| Partials clearing the edge at f₀ ≈ 209 Hz | **k = 7, 8 only** | 1320/209 = 6.3 |

**Note the register problem.** At Saraga's retained median f₀ of 209 Hz only the 7th and
8th partials clear a 1.32 kHz edge. Sustained low material (tambura ~ 100–150 Hz) may
clear **none**, in which case the check cannot run on that passage. Choose material at or
above ~180 Hz, and report the f₀ of every passage used.

### Decision rule
- **Fundamental unmoved + ℓ̄ ≈ 0.8 on real passages** → closes the mechanism-to-cost chain
  on the repertoire where the cost is claimed. R2 said this moves it to **8**.
- **Fundamental moves > 1 cent** → the codec behaves differently on real music than on
  tones; the localisation claim does not transfer and Contribution 1 needs narrowing.
- **ℓ̄ ≈ 0.3 or scattered** → the regridding does not survive real timbre. Serious.

### Audit red flags
- Results from passages whose f₀ puts no partial above the edge — that's a null by
  construction, not a measurement
- ℓ̄ computed over *all* partials rather than those at/above the edge (inclusive vs
  conditional — this is the ρ = 0.924 confound; **ask which one they used**)

---

## 3. ℓ̄ as a function of |δ₀|  — R1's top ask

### Run
```bash
python experiments/spectral_sweep.py --codec encodec:3 \
    --detunings 5 10 20 30 40 50 --reference 440 \
    --out results/spectral_sweep_delta.csv
```
Repeat for one non-EnCodec puller (WavTokenizer, once pinned).

**⚠ Prerequisite:** the existing `spectral_sweep.csv` **does not reproduce Table A15** at
the per-partial level. This needs a clean re-run, not reanalysis of the existing file.
That discrepancy is itself worth diagnosing — flag it to whoever owns that pipeline.

### Report back
ℓ̄ at each |δ₀|, **at both detuning signs separately**, with per-partial detail so it can
be reconciled against Table A15.

### Expected numbers

This is a **discriminating** test — the two accounts predict different curves:

| \|δ₀\| | Proportional pull | Cap at c = 22 | Cap at c = 26 |
|---|---|---|---|
| 5 | 0.90 | 1.00 | 1.00 |
| 10 | 0.90 | 1.00 | 1.00 |
| 20 | 0.90 | 1.00 | 1.00 |
| 30 | 0.90 | 0.73 | 0.87 |
| 40 | 0.90 | 0.55 | 0.65 |
| 50 | 0.90 | 0.44 | 0.52 |

The cap values come from `min(c/|δ₀|, 1)`; c = 22 [19, 26] is where the failed (P1)
prediction located its clipping knee.

### Decision rule
- **Flat at ~0.90 across all six** → the ladder is proportional. R1: this *"would convert
  the paper's title claim from 'consistent with regridding, cap not excluded' to
  established, and would raise my rating."* Removes a row from the limits table.
- **Falling like 1/|δ₀|** → it is a bounded displacement that happens to point gridward.
  **The paper must be rewritten throughout** — "ladder fraction" becomes the wrong name
  for the quantity. R1 says this "would not kill the paper" but is a major revision.
- **Flat above 20 but rising below** → something else again; report it, don't smooth it.

### Audit red flags
- Only |δ₀| = 20 and 40 returned. **The whole point is the low end** — 5 and 10 are where
  the two accounts diverge most, since a cap reads 1.00 there and proportional reads 0.90.
- ℓ̄ averaged across signs without the per-sign values. There is an unexplained per-sign
  asymmetry (the k=5/k=7 split) and averaging hides it.

---

## 4. DAC 16k at 880 and 1760 Hz

### Run
```bash
python experiments/run_sweep.py --codec dac16:6 \
    --references 880 1760 --reps 20 --out results/detune_dac16_high.csv
```

### Report back
Off-grid bias b̃ with CI at each reference, registration slope with CI, gate exclusion
rate, and ℓ̄ at each reference.

### Expected numbers

DAC's edge is 4.4 kHz, ℓ̄ = 0.85, and off-grid trials have |δ₀| ≈ 40:

| Reference | Partials ≥ 4.4 kHz | Share | `b_unif` | **Expected measured** (×0.42–0.45) |
|---|---|---|---|---|
| 440 Hz | 0 of 8 | 0.000 | 0.0 | **0.0** (this is the published null) |
| 880 Hz | 4 of 8 | 0.500 | 17.0 | **7.1 – 7.7 cents** |
| 1760 Hz | 6 of 8 | 0.750 | 25.5 | **10.7 – 11.5 cents** |

### ⚠ There is already tension here — read this before running

I probed this inside the existing 440 Hz sweep. The stimulus is a *pair*, and the second
tone sweeps the octave, so θ alone controls how many of *its* partials clear 4.4 kHz.
Split that way, DAC reads:

| Partials above edge | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| Bias (cents) | +0.67 | −0.51 | +0.03 | **−0.55** |

**DAC does not pull where its edge is reached.** Equation 16 predicts ~13 cents for that
three-partial bucket. EnCodec's equivalent buckets land at 0.42/0.45 of prediction;
DAC's lands at essentially **zero**.

So the honest prediction is a **fork**:
- If DAC reads **7–11 cents** at 880/1760 → my probe was underpowered or confounded, the
  mechanism holds, and DAC's null becomes *explained* (a scope statement about register).
  Good outcome.
- If DAC reads **~0** → confirms the probe. DAC regrids (ℓ̄ = 0.85) but produces no
  estimator-level pull even with partials above its edge. **The edge does not by itself
  decide pulling**, and the paper keeps DAC among the nulls it cannot explain.

Either way this is publishable and either way we report it. Do **not** let anyone quietly
prefer the first.

### Audit red flags
- Gate exclusion rate not reported. DAC loses 65% at 440 Hz; if it loses similarly at 880
  the null is uninterpretable, and we need the ungated reading alongside.
- Registration slope missing. Without it we cannot tell a pull from an estimator artefact —
  that is the whole point of the registration test.

---

## 5. Melodia / Essentia on the 200 coded Saraga recordings

### Run
Essentia's `PredominantPitchMelodia` (exposes `maxFrequency` and harmonic count) on the
same 200 recordings, uncoded and through EnCodec 3 kbps. CPU only; needs `pip install essentia`.

### Report back
Median absolute degree error uncoded/coded, paired diff + CI, flip count out of 200.

### Expected numbers

Table A33 gives estimator weight shares above the edge on a 1/n envelope:

| Estimator | Share above edge |
|---|---|
| Ours, 6 partials (produced the downstream table) | **0.67** |
| 20 partials, decay 0.8 (Melodia-like) | **0.30** |

Ratio 0.30 / 0.67 = **0.45**, so:

| Quantity | Ours (measured) | **Melodia predicted** |
|---|---|---|
| Paired degree-error diff | 3.2 cents | **~1.4 cents** |
| Flip rate | 11% (22/200) | **~5%** (≈ 10/200) |

**This prediction says Melodia is *less* exposed than we are** — the paper argues this
explicitly and corrected an earlier draft that had it backwards. If Melodia comes back
*worse* than 3.2 cents, our scoping claim is wrong and §F.5.2 needs rewriting.

### Decision rule
- **~1.4 cents, ~5%** → converts Table A32 from a table of *configurations* into a table of
  *measurements*. R2 called this more valuable to MIR than another synthetic condition.
- **> 3.2 cents** → we are not the exposed case; the "full-band harmonic fitting" scoping
  is wrong.
- **~0 cents** → salience tools are immune; the practitioner warning narrows sharply to
  our own estimator family.

---

## 6. Low-pass the 200 Saraga files, then `librosa.estimate_tuning`

### Run
Low-pass each decoded file below the measured 1.32 kHz edge, then rerun
`librosa.estimate_tuning` and count how many of 200 moved toward 12-TET.

This tests **the remedy we actually recommend to practitioners** — the paper currently
validates band-limiting only inside our own truncated fit, and argues the external
low-pass route without running it. It is a stated limit in Table A38.

### Expected numbers

| Condition | Count toward 12-TET, of 200 | p (two-sided binomial) |
|---|---|---|
| Coded, no remedy (**measured**) | **134** | 1.7 × 10⁻⁶ |
| Coded + low-pass (**predicted**) | **~100–110** | > 0.05, i.e. chance |

### Decision rule
- **Falls to ~100** → the remedy is validated outside our own estimator, on the one
  third-party tool we ran. Removes a limits-table row and materially strengthens the
  practitioner recommendation.
- **Stays near 134** → the recommendation is wrong as stated and must be qualified. Note
  `estimate_tuning` takes the *mode* of folded residuals, not the mean, so attenuating
  scattered peaks may not move it the way it moves an average — this outcome is genuinely
  possible and is not a failure of the mechanism.
- **Falls below ~85** → over-correction; investigate before celebrating.

### Audit red flag
The low-pass must be applied to the **decoded** audio at the **measured** edge for that
codec and operating point — not a fixed cutoff across the corpus. The paper is explicit
that a fixed cutoff is wrong, because the edge sits at a fixed frequency while these
traditions' tonics do not.

---

## Graphs worth asking for

| Run | Plot |
|---|---|
| 1 | Paired degree error, four arms side by side (stock / Saraga-tuned / GTZAN-tuned / band-limited), with CIs |
| 2 | Displacement vs partial index k, with the measured edge marked — the real-music twin of Figure 1 |
| 3 | **ℓ̄ vs \|δ₀\|**, with the flat line at 0.90 and the `min(c/\|δ₀\|,1)` curve overlaid. This single plot settles the question. |
| 4 | Off-grid bias vs reference (440 / 880 / 1760), with the Eq-16 prediction band |
| 5 | Flip rate by estimator (ours-8 / ours-6 / Melodia / pYIN) |
| 6 | Histogram of `estimate_tuning` offsets before and after low-pass |

---

## Two things to insist on across all six

**1. Raw counts, not rounded percentages.** We already concede that Table A31's whole-percent
rounding makes per-arm flip counts unrecoverable, and I could not fix it because the per-arm
records aren't archived. Don't recreate that problem.

**2. Every result file archived with its `.meta.json` sidecar**, matching the existing
convention (146 files / 117 sidecars). R4 escalated the WavTokenizer archive gap from a
caveat to *"a condition, not a caveat"* for camera-ready. Unarchived results are results
we cannot use.

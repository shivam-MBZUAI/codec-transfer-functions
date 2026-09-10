# Expected results for the six pending runs

Predictions fixed **before** the runs, so returned results can be audited rather than
rationalised. Each section gives: the command, what to report back, the number the
paper's own mechanism predicts, and the decision rule — including **what result would
damage the paper**, which is the part that makes this an audit and not a rubber stamp.

Every command below has been **checked against the actual argparse of the script it
calls**. Where a run needs code that does not exist yet, that is stated explicitly rather
than papered over with a plausible-looking command.

Every prediction is derived from quantities already in the paper. The main tool is
Equation 16:

```
b_unif  =  |δ₀| · ℓ̄ · (share of estimator weight above the band edge)
```

with input-referred weights, which for a 1/n stimulus are uniform over the estimator's
partials — so the share is just `(# partials above edge) / (# partials fitted)`.

**Two different partial counts are in play. Do not mix them.**

| Pipeline | Script | Partials |
|---|---|---|
| Pitch probe / interval sweep / corpus pull | `run_sweep.py`, `corpus_pull.py` | **8** |
| Per-partial spectral read | `spectral_sweep.py` (`MAX_PARTIAL`) | **12** |

**Calibration factor.** Measured readings come in *below* `b_unif`, because regenerated
partials return attenuated and partials at the edge are split lines the fit reads
between. EnCodec's own buckets land at **0.42 and 0.45** of prediction. Multiply any
`b_unif` by **0.42–0.45** to get the expected *measured* value. A returned number that
matches `b_unif` exactly is a red flag, not a success.

---

## Priority order

| # | Run | Cost | Blocked? | Why it matters |
|---|-----|------|---|----------------|
| 1 | GTZAN decoder → Saraga | 1 GPU, ~1h | needs `analyze_tuning.py` | **All four reviewers**, both cycles |
| 3 | ℓ̄ vs \|δ₀\| | 1 GPU, ~3h | needs clean sweep re-run | R1's top ask; no dataset |
| 4 | DAC at 880 / 1760 Hz | 1 GPU, ~1h | **no** — run today | R1+R3+R4; no dataset |
| 2 | Per-partial on sustained passages | 1 GPU + prep | makam audio blocked | R2's top ask |
| 6 | Low-pass → `estimate_tuning` | CPU | new script | Tests the remedy we recommend |
| 5 | Melodia on coded Saraga | CPU | new script | Configs → measurements |

**Run 4 is the only one with no prerequisite at all.** Start there if someone has cluster
time today.

---

## 1. GTZAN-fine-tuned decoder scored on Saraga

### Run

The GTZAN-fine-tuned decoder is the **`grid` arm** — fine-tuned on unmodified `corpora/gtzan`.
Checkpoints already exist at `checkpoints/encodec_ftm_grid_s{0..4}` (five seeds).

```bash
python3 experiments/corpus_pull.py \
    --audio-root corpora/saraga_carnatic \
    --codec "encodec_ft:checkpoints/encodec_ftm_grid_s0@3.0" \
    --max-files 200 \
    --out results/corpus_pull_saraga_gtzanft_s0.csv
```

**Run all five seeds** (`s0`…`s4`) and report the spread. The paper's causal arms are
quoted at seed-level spread, so a single seed is not comparable to them.

Then the degree-error / flip pipeline on the same 200 recordings.

> **⚠ Blocker.** `analyze_tuning.py` is **not in the repo**. The pipeline that produced
> the 3.2 / 4.4-cent degree errors and the flip counts is missing from `code/analysis/`.
> This run cannot be scored without it. Find it before starting.

### Report back
- Median absolute degree error, uncoded and coded; paired difference + 95% CI
- **Flip count out of 200 as a raw integer**, with Clopper–Pearson interval
- The decoder's measured **band edge** and **ℓ̄**
- Mean count of fitted partials (of 8) above that edge on the retained frames
- Spread across the five seeds

### Expected numbers

| Arm | Uncoded | Coded | Paired diff | Flips |
|---|---|---|---|---|
| Stock EnCodec 3 kbps | 4.1 | 7.3 | **3.2** [2.6, 3.8] | 11% (22/200) |
| Decoder tuned on Saraga | 4.1 | 4.4 | **0.3** [−0.2, 0.8] | 1% |
| **GTZAN-tuned → predicted** | 4.1 | ~5.2 | **~1.1** | **~4%** (≈8/200) |

**Derivation.** Every fine-tuned arm sits at a **2.0 kHz** edge instead of stock's
1.32 kHz. On the retained Saraga frames the mean count of fitted partials above the edge
falls from **2.34 of 8** to **0.80 of 8** — a factor of **0.34**. Applying that to the
stock 3.2-cent cost gives **3.2 × 0.34 ≈ 1.1 cents**, *before any corpus-specific grid is
considered*. At a 2.0 kHz edge, **64%** of retained Saraga frames have no fitted partial
above the edge at all, up from 24%.

Also expect: measured edge **≈ 2.0 kHz**, and amplitude dropping from stock's **13.72** to
**≈ 4.6 cents** (the generic fine-tuning effect).

### Decision rule

| Result | Reading |
|---|---|
| **~1.1 cents** (0.7–1.6), flips ~3–6% | Generic edge effect. The Saraga arm's extra repair (1.1 → 0.3) is corpus-specific. **Claim survives, strengthened.** |
| **~0.3 cents**, flips ~1% | GTZAN repairs Carnatic as well as the Saraga-tuned decoder. **The corpus-specific-grid reading collapses**; the downstream section needs rewriting. |
| **~3.2 cents**, unchanged | The edge shift did nothing, contradicting the frame-level gradient. Check the edge measurement before believing it. |

**This one can go badly.** Outcome 2 is a live possibility and costs us the most
interesting downstream claim. Report it either way.

### Audit red flags
- Paired diff with no CI, or a CI claimed significant below ~0.7 cents (the band-limited
  residual is blind below that)
- Measured edge that isn't ≈ 2.0 kHz — every other fine-tuned arm sits there
- **Flip rates as rounded percentages.** Table A31 already rounds to whole percents and we
  concede the per-arm counts are unrecoverable from it. Insist on integers.
- One seed reported as if it were the result

---

## 2. Per-partial spectral check on sustained passages

> **⚠ `spectral_check.py` is the wrong script.** It generates its own synthetic tones and
> has **no `--audio-root`** — its only arguments are `--kbps`, `--duration`, `--reps`,
> `--nfft`, `--figure`. Real audio goes through `spectral_sweep.py --notes`.

> **⚠ Preprocessing is required and does not exist yet.** `--notes DIR` scans `DIR` for
> **`.wav`** files named **`<name>-<midi>-<velocity>.wav`** and keeps those with
> **MIDI 45–81 (A2 110 Hz – A5 880 Hz)**. Saraga ships `.mp3` full performances. Someone
> must first: segment sustained monophonic passages, estimate each one's pitch, and export
> them as correctly-named `.wav`. Budget this as the real cost of the run.

> **⚠ The makam half is blocked.** CompMusic makam **audio** is copyright-restricted behind
> a Dunya access request (`dunya.compmusic.upf.edu` → approval → API token →
> `pycompmusic`). We hold only annotations (118 MB, zero audio). **File the request now** —
> longest lead time on this list. The Saraga half can proceed independently.

### Run
```bash
python3 experiments/spectral_sweep.py \
    --codecs encodec:3 \
    --notes corpora/saraga_sustained \
    --n-notes 60 \
    --out results/spectral_saraga.csv
```

### Report back
Per partial k = 1…12: input frequency, decoded frequency, displacement in cents, level in
dB relative to input. Plus the measured edge and ℓ̄ above it. **Report ℓ̄ over partials
at/above the edge (conditional), and say which convention was used** — inclusive vs
conditional is the ρ = 0.924 confound.

### Expected numbers

| Quantity | Predicted | Basis |
|---|---|---|
| Band edge | **≈ 1.3 kHz** | Stock EnCodec 3 kbps |
| Fundamental displacement | **within 0.2 cents** | Central claim, three bitrates |
| ℓ̄ above the edge | **0.79 – 0.90** | Tones 0.79–0.95; NSynth notes 0.79 |
| Partials below edge | **within ~2 cents** | Table A15 |
| Partials clearing edge at f₀ ≈ 209 Hz | **k = 7…12**, i.e. **6 of 12** | 1320 / 209 = 6.3 |

Note this uses **12** partials (`spectral_sweep.py`), not the 8 of the pitch probe.

### Decision rule
- **Fundamental unmoved + ℓ̄ ≈ 0.8 on real passages** → closes the mechanism-to-cost chain
  on the repertoire where the cost is claimed. R2 said this moves it to **8**.
- **Fundamental moves > 1 cent** → the codec behaves differently on real music than on
  tones; the localisation claim does not transfer and Contribution 1 must narrow.
- **ℓ̄ ≈ 0.3 or scattered** → regridding does not survive real timbre. Serious.

### Audit red flags
- Passages whose f₀ puts no partial above the edge — a null by construction. **Report the
  f₀ of every passage used.** Tambura at 100–150 Hz may clear nothing.
- ℓ̄ computed inclusively over all partials rather than those at/above the edge

---

## 3. ℓ̄ as a function of |δ₀| — R1's top ask

> **⚠ Prerequisite.** The existing `spectral_sweep.csv` **does not reproduce Table A15**
> at the per-partial level. This needs a clean re-run, not reanalysis. That discrepancy is
> itself worth diagnosing.

### Run

Arguments are `--codecs` (plural), `--references`, `--deltas` — **not** `--codec` or
`--detunings`. Deltas are **signed**, and both signs are needed because of the
unexplained per-sign asymmetry.

```bash
python3 experiments/spectral_sweep.py \
    --codecs encodec:3 \
    --references 440 \
    --deltas -50 -40 -30 -20 -10 -5 5 10 20 30 40 50 \
    --reps 5 \
    --out results/spectral_sweep_delta.csv
```
Repeat for one non-EnCodec puller (WavTokenizer, once pinned).

### Report back
ℓ̄ at each |δ₀|, **at both signs separately**, with per-partial detail so it can be
reconciled against Table A15.

### Expected numbers — this is a discriminating test

| \|δ₀\| | Proportional pull | Cap at c = 22 | Cap at c = 26 |
|---|---|---|---|
| 5 | 0.90 | **1.00** | **1.00** |
| 10 | 0.90 | **1.00** | **1.00** |
| 20 | 0.90 | 1.00 | 1.00 |
| 30 | 0.90 | 0.73 | 0.87 |
| 40 | 0.90 | 0.55 | 0.65 |
| 50 | 0.90 | 0.44 | 0.52 |

Cap values are `min(c/|δ₀|, 1)`; c = 22 [19, 26] is where the failed (P1) prediction put
its clipping knee.

### Decision rule
- **Flat at ~0.90 across all twelve** → the ladder is proportional. R1: *"would convert the
  paper's title claim from 'consistent with regridding, cap not excluded' to established,
  and would raise my rating."* Removes a limits-table row.
- **Falling like 1/|δ₀|** → a bounded displacement that happens to point gridward.
  **Requires rewriting the paper throughout** — "ladder fraction" becomes the wrong name.
- **Flat above 20, rising below** → something else. Report it; do not smooth it.

### Audit red flags
- Only |δ₀| = 20 and 40 returned. **The low end is the whole point** — a cap reads 1.00 at
  5 and 10 where proportionality reads 0.90.
- Signs averaged together without per-sign values

---

## 4. DAC 16k at 880 and 1760 Hz — no prerequisites, run today

### Run
```bash
python3 experiments/run_sweep.py \
    --codec dac16:6 \
    --references 880 1760 \
    --reps 20 \
    --out results/detune_dac16_high.csv
```

### Report back
Off-grid bias b̃ with CI at each reference, **registration slope with CI**, **gate
exclusion rate**, and ℓ̄ at each reference.

### Expected numbers

DAC's edge is 4.4 kHz, ℓ̄ = 0.85, off-grid trials have |δ₀| ≈ 40, estimator fits 8:

| Reference | Partials ≥ 4.4 kHz | Share | `b_unif` | **Expected measured** |
|---|---|---|---|---|
| 440 Hz | 0 of 8 | 0.000 | 0.0 | **0.0** — the published null |
| 880 Hz | 4 of 8 | 0.500 | 17.0 | **7.1 – 7.7 cents** |
| 1760 Hz | 6 of 8 | 0.750 | 25.5 | **10.7 – 11.5 cents** |

### ⚠ There is already tension here — read before running

I probed this inside the existing 440 Hz sweep. The stimulus is a *pair*; the second tone
sweeps the octave, so θ alone controls how many of *its* partials clear 4.4 kHz:

| Partials above edge | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| Bias (cents) | +0.67 | −0.51 | +0.03 | **−0.55** |

**DAC does not pull where its edge is reached.** Equation 16 predicts ~13 cents for that
three-partial bucket. EnCodec's equivalent buckets land at 0.42/0.45 of prediction;
DAC's lands at essentially **zero**.

So the prediction is a **fork**:
- **7–11 cents** → my probe was underpowered or confounded; the mechanism holds and DAC's
  null becomes *explained* as a scope statement about register.
- **~0 cents** → confirms the probe. DAC regrids (ℓ̄ = 0.85) yet produces no
  estimator-level pull even with partials above its edge. **The edge does not by itself
  decide pulling**, and DAC stays among the nulls we cannot explain.

Both are publishable. Do **not** let anyone quietly prefer the first.

### Audit red flags
- Gate exclusion rate not reported. DAC loses 65% at 440 Hz; if it loses similarly at 880
  the null is uninterpretable and we need the ungated reading too.
- Registration slope missing — without it a pull cannot be told from an estimator artefact.

---

## 5. Melodia / Essentia on the 200 coded Saraga recordings

> **⚠ No script exists.** Nothing in `code/` wraps Essentia. This is new code: run
> `PredominantPitchMelodia` (it exposes `maxFrequency` and harmonic count) over the 200
> recordings uncoded and through EnCodec 3 kbps, then feed the degree pipeline. CPU only;
> `pip install essentia`.

### Report back
Median absolute degree error uncoded/coded, paired diff + CI, **flip count out of 200 as
an integer**.

### Expected numbers

Table A33 weight shares above the edge, 1/n envelope:

| Estimator | Share above edge |
|---|---|
| Ours, 6 partials — produced the downstream table | **0.67** |
| 20 partials, decay 0.8 — Melodia-like | **0.30** |

Ratio 0.30 / 0.67 = **0.45**:

| Quantity | Ours (measured) | **Melodia predicted** |
|---|---|---|
| Paired degree-error diff | 3.2 cents | **~1.4 cents** |
| Flip rate | 11% (22/200) | **~5%** (≈10/200) |

**This predicts Melodia is *less* exposed than we are.** The paper argues this explicitly
and corrected an earlier draft that had it backwards. If Melodia comes back **worse** than
3.2 cents, our scoping claim is wrong and §F.5.2 needs rewriting.

### Decision rule
- **~1.4 cents, ~5%** → converts Table A32 from configurations into measurements. R2 called
  this more valuable to MIR than another synthetic condition.
- **> 3.2 cents** → we are not the exposed case; the "full-band harmonic fitting" scoping
  is wrong.
- **~0 cents** → salience tools are immune; the warning narrows to our own estimator family.

---

## 6. Low-pass the 200 Saraga files, then `librosa.estimate_tuning`

> **⚠ No script exists.** New code: low-pass each **decoded** file below that codec's
> **measured** edge, rerun `librosa.estimate_tuning`, count how many of 200 moved toward
> 12-TET. CPU only.

This tests **the remedy we actually recommend to practitioners**. The paper currently
validates band-limiting only inside our own truncated fit and argues the external
low-pass route without running it — a stated limit in Table A38.

### Expected numbers

| Condition | Count toward 12-TET, of 200 | p (two-sided binomial) |
|---|---|---|
| Coded, no remedy (**measured**) | **134** | 1.7 × 10⁻⁶ |
| Coded + low-pass (**predicted**) | **~100–110** | > 0.05, i.e. chance |

### Decision rule
- **Falls to ~100** → remedy validated outside our own estimator, on the one third-party
  tool we ran. Removes a limits-table row.
- **Stays near 134** → the recommendation is wrong as stated and must be qualified. Note
  `estimate_tuning` takes the **mode** of folded residuals, not the mean, so attenuating
  scattered peaks may not move it the way it moves an average. **This outcome is genuinely
  possible and is not a failure of the mechanism.**
- **Below ~85** → over-correction; investigate before celebrating.

### Audit red flag
The low-pass must use the **measured** edge for that codec and operating point, **not a
fixed cutoff across the corpus**. The paper is explicit that a fixed cutoff is wrong: the
edge sits at a fixed frequency while these traditions' tonics do not.

---

## Graphs worth asking for

| Run | Plot |
|---|---|
| 1 | Paired degree error, four arms side by side (stock / Saraga-tuned / GTZAN-tuned / band-limited) with CIs |
| 2 | Displacement vs partial index k with the edge marked — the real-music twin of Figure 1 |
| 3 | **ℓ̄ vs \|δ₀\|**, flat line at 0.90 and the `min(c/\|δ₀\|,1)` curve overlaid. This one plot settles the question. |
| 4 | Off-grid bias vs reference (440 / 880 / 1760) with the Eq-16 prediction band |
| 5 | Flip rate by estimator (ours-8 / ours-6 / Melodia / pYIN) |
| 6 | Histogram of `estimate_tuning` offsets before and after low-pass |

---

## Three smaller runs reviewers also asked for

Not in the six, but cheap and explicitly requested:

| Run | Asked by | Cost | Expected |
|---|---|---|---|
| **Per-sign ℓ̄ for HE-AAC** | R4 Q4 | ~1h | HE-AAC's ladder is zero by construction, so a per-sign asymmetry there would locate the asymmetry in Eq 4's reference rather than the decoder. Expect **≈ 0.04 at both signs**. |
| **Five SNAC 32k repetitions** | power floors | ~2h | SNAC 32k clears zero by 0.01 cents and sits below its own 0.71-cent floor. Repetitions would say whether it is a pull at all. |
| **Pin WavTokenizer + archive its sweep** | R2 Q8, R4 Q1 | trivial | **Not an experiment — a provenance fix.** R4 calls it *"a condition, not a caveat"* for camera-ready. |

---

## Two things to insist on across all six

**1. Raw counts, not rounded percentages.** We already concede Table A31's whole-percent
rounding makes per-arm flip counts unrecoverable, and I could not repair it because the
per-arm records were never archived. Do not recreate that.

**2. Every result file archived with its `.meta.json` sidecar**, matching the existing
convention (146 files / 117 sidecars). Unarchived results are results we cannot use.

---

## Cluster gotchas (from `docs/CLUSTER.md`)

- Use **`bash -lc`**. The outbound proxy is exported only by login shells; a plain
  `ssh host "cmd"` hangs with what looks like a firewall block.
- **Pre-fetch checkpoints on the login node**, then run jobs with `HF_HUB_OFFLINE=1`.
  Compute nodes may have no egress.
- Ask for **`--gres=gpu:1`**, not a whole node. Nothing here scales past one device, and
  the sbatch file notes the workload is largely **CPU-bound** (F0 estimation is numpy) —
  so runs 5 and 6 should drop the GPU entirely and will queue sooner.

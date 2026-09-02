# Data and model sources

Every input this project uses, where it comes from, and how to get it.

**Most of this project needs no data at all.** The pitch experiments synthesise
their own stimuli, and the causal experiment trains on a corpus generated in
process. Only the ecological-validity and downstream sections need external
inputs, and exactly one of those is not automatable.

| Stage | External input needed |
|---|---|
| Gate, controls, mechanism, codec breadth | **none beyond codec checkpoints** |
| Ecological validity | instrument samples, or makam audio |
| Downstream | FLEURS, ASR models |

---

## 1. Codec checkpoints — automatic

```bash
source /scratch/shivam.chauhan/codecs/env.sh
python cluster/fetch_checkpoints.py
```

| Codec | Repo | Role |
|---|---|---|
| EnCodec 24 kHz | [facebook/encodec_24khz](https://huggingface.co/facebook/encodec_24khz) | workhorse, widest rate range (1.5 to 24 kbps) |
| EnCodec 48 kHz | [facebook/encodec_48khz](https://huggingface.co/facebook/encodec_48khz) | **music-trained**; against 24 kHz it holds architecture fixed and varies music exposure |
| DAC 44.1 kHz | [descript/dac_44khz](https://huggingface.co/descript/dac_44khz) | highest fidelity; tops out near 8 kbps, not 24 |
| DAC 24 kHz | [descript/dac_24khz](https://huggingface.co/descript/dac_24khz) | the checkpoint that actually reaches 24 kbps |
| DAC 16 kHz | [descript/dac_16khz](https://huggingface.co/descript/dac_16khz) | third frame-rate point for the rate-scaling fit |
| Mimi | [kyutai/mimi](https://huggingface.co/kyutai/mimi) | 12.5 Hz frames, extreme low rate |
| SpeechTokenizer | [fnlp/SpeechTokenizer](https://huggingface.co/fnlp/SpeechTokenizer) | **the negative control** (see below) |

SpeechTokenizer additionally needs its own package, which is on PyPI:

```bash
uv pip install speechtokenizer     # source: github.com/ZhangXInFD/SpeechTokenizer
```

### Why SpeechTokenizer is the scientifically important one

It was trained on LibriSpeech alone: English audiobooks, no music. If the
mechanism under test is that residual-quantiser codebooks absorb the pitch
statistics of training audio, then a codec that never saw 12-tone equal
tempered music has nothing to absorb, and should show **no** grid structure.
A grid effect there is evidence against the mechanism, not for it.

That makes the codec set a natural experiment ordered by music exposure:

```
SpeechTokenizer  LibriSpeech only, no music        -> predict no effect
Mimi             ~7M h, overwhelmingly speech      -> predict weak
EnCodec 24 kHz   speech + AudioSet + Jamendo       -> predict moderate
EnCodec 48 kHz   music checkpoint                  -> predict strongest
```

---

## 2. Additional codecs — automatic, availability varies

```bash
python cluster/fetch_all.py
```

Repo identifiers for these move more than the core set, so the fetcher reports
failures rather than aborting. Check its output for what actually resolved.

All of these resolved and are cached:

| Codec | Repo | Cached |
|---|---|---|
| SNAC 24 kHz | [hubertsiuzdak/snac_24khz](https://huggingface.co/hubertsiuzdak/snac_24khz) | 76M |
| SNAC 32 kHz | [hubertsiuzdak/snac_32khz](https://huggingface.co/hubertsiuzdak/snac_32khz) | 209M |
| SNAC 44 kHz | [hubertsiuzdak/snac_44khz](https://huggingface.co/hubertsiuzdak/snac_44khz) | 209M |
| WavTokenizer | [novateur/WavTokenizer](https://huggingface.co/novateur/WavTokenizer) | 3.0G |
| WavTokenizer large, unify | [novateur/WavTokenizer-large-unify-40token](https://huggingface.co/novateur/WavTokenizer-large-unify-40token) | 1.7G |
| WavTokenizer large, speech | [novateur/WavTokenizer-large-speech-75token](https://huggingface.co/novateur/WavTokenizer-large-speech-75token) | 1.7G |
| X-Codec 2.0 | [HKUSTAudio/xcodec2](https://huggingface.co/HKUSTAudio/xcodec2) | 14G |
| BigCodec | [Alethia/BigCodec](https://huggingface.co/Alethia/BigCodec) | 609M |

**None of these has a wrapper in `codec_zoo.py` yet.** The weights are cached;
each still needs an adapter, since none loads through `transformers`.

### A trap this fetcher now guards against

`snapshot_download` returns **success when `allow_patterns` matched nothing**.
WavTokenizer ships `.ckpt`, which the original pattern list omitted, so it
reported OK having downloaded 8 KB and no weights at all. `fetch_all.py` now
counts weight files after each download and raises if the count is zero. Treat
any "ok" that is not backed by a file count as unverified.

---

## 3. Speech corpus and ASR — automatic

```bash
python cluster/fetch_fleurs.py
```

| Input | Source | Note |
|---|---|---|
| FLEURS | [google/fleurs](https://huggingface.co/datasets/google/fleurs) | 102 languages; we pull 23, test split only |
| Whisper | [openai/whisper-large-v3](https://huggingface.co/openai/whisper-large-v3) | primary recogniser |
| MMS | [facebook/mms-1b-all](https://huggingface.co/facebook/mms-1b-all) | second recogniser; a disparity under one but not the other implicates the recogniser rather than the codec |
| Forced alignment | `torchaudio.pipelines.MMS_FA` | **use this, not Montreal Forced Aligner**, which is conda-based and painful on macOS and on locked-down clusters |

### Two caveats that affect the science, not the download

**FLEURS is parallel by translation, not by identical content.** It is built
from FLoRes sentences read aloud, so languages share *meaning*, not words,
phonemes, syllable counts or duration. Any claim that it "holds lexical content
fixed by construction" is wrong. It controls semantic content and speaking
register; it cannot control phonetic content.

**The contrast-to-language mapping is not settled.** The current grouping puts
Arabic, Hebrew, Amharic and Maltese under pharyngealisation. Only Arabic is
solid: Modern Israeli Hebrew has largely lost the pharyngeals for most
speakers, Amharic lost the Ge'ez pharyngeals and belongs in the ejective group
only, and Maltese `għ` is generally silent or realised as vowel lengthening.
Fix the grouping before deriving any number from it.

---

## 4. Ecological validity — one automatic route, one blocked

### 4a. Instrument samples — cached

Real instrument recordings pitch-shifted off-grid. This answers the reviewer
objection that synthetic stimuli do not transfer, without any restricted
corpus, and is entirely under your control.

**Cached:** NSynth test split, 350 MB, via [confit/nsynth](https://huggingface.co/datasets/confit/nsynth).
Isolated instrument notes with pitch labels, which is exactly the shape this
experiment needs. Its canonical home is a Google Storage bucket that this
cluster's proxy blocks; the HuggingFace mirror works.

### 4a-old. Other instrument sources

Real instrument recordings pitch-shifted off-grid. This answers the reviewer
objection that synthetic stimuli do not transfer, without any restricted
corpus, and it is entirely under your control.

| Source | Where | Note |
|---|---|---|
| Philharmonia Orchestra samples | philharmonia.co.uk, "sound samples" resource | free, small, isolated single notes across many instruments |
| NSynth | [magenta.tensorflow.org/datasets/nsynth](https://magenta.tensorflow.org/datasets/nsynth) | far larger than needed; the *test* split alone is sufficient |
| Good-Sounds | Universitat Pompeu Fabra, MTG | single notes with quality annotations |

### 4b. Turkish makam corpus — BLOCKED, needs a human

**This is the only input that cannot be automated.** The CompMusic Turkish
makam corpus has open metadata and open scores, but its **audio is
copyright-restricted** and mediated through the Dunya platform behind an access
request. Turnaround is not under our control, so file the request early.

**Steps:**

1. Register at **https://dunya.compmusic.upf.edu/**
2. Generate an API token from your profile page once the account is approved
3. Install the client: **https://github.com/MTG/pycompmusic**
4. Store the token outside any repository, readable only by you. **Never commit
   it, and never paste it into a chat transcript.**

**Cached already, no request needed:**

| Archive | Zenodo | Contents |
|---|---|---|
| OTMM makam recognition dataset | [4883680](https://zenodo.org/records/4883680) | 101 MB, 2040 entries, **0 audio**, ~2000 JSON annotations |
| Turkish makam audio-score alignment | [1284501](https://zenodo.org/records/1284501) | 17 MB, 459 entries, **0 audio**, aligned note annotations |

Both are in `data/makam/`. **Neither contains audio**, which was expected from
their size. They carry pitch annotations, tonic annotations and aligned notes,
referenced to MusicBrainz IDs.

That splits the makam problem cleanly in two:

- **Scale-degree offsets: solved.** These annotations are a defensible measured
  source for how far each degree sits from the nearest 12-TET pitch, replacing
  the Arel-Ezgi-Uzdilek comma-table values the draft currently uses.
- **Audio to push through a codec: still blocked.** Needs Dunya, or the
  instrument-retuning route in 4a.

Zenodo *file* downloads are 403 through this cluster's proxy even though its
API responds. These were fetched on a laptop and pushed across.

**Further open resources:**

| Resource | Where | What it gives |
|---|---|---|
| SymbTr | **https://github.com/MTG/SymbTr** | machine-readable makam scores, fully open. Theory, not audio |
| OTMM datasets | search **zenodo.org** for "Ottoman-Turkish Makam Music" | pitch and tonic annotations, often openly downloadable. **Recommended fallback** |
| CompMusic corpora index | **https://compmusic.upf.edu/corpora** | overview of what exists across traditions |

### Scale degrees must come from measurement, not from theory

If makam data is used, the nominal offset of each scale degree from the nearest
12-TET pitch must be read from the **corpus's own measured pitch histograms**,
not from Arel-Ezgi-Uzdilek comma tables.

AEU divides the octave into 53 Holdrian commas of about 22.64 cents and places
the Rast scale at 0, 9, 17, 22, 31, 40, 48, 53 commas. That puts

- **Segah** at 17 x 22.64 = **385 cents**, which is **15 cents** below 400
- **Evc** at 48 x 22.64 = **1087 cents**, which is **13 cents** below 1100

Performance practice sits considerably flatter than AEU theory for the neutral
degrees, which is exactly why measured histograms are the right source. It also
matters arithmetically: a displacement of 16 cents measured against a nominal
offset of 15 cents would carry the degree *past* the grid point and out the
other side, which is not a coherent measurement.

---

## 5. Training-density estimation — cached

Proposition 1 predicts the residual from `p(theta)`, the pitch density of the
codec's training audio. No released codec publishes that audio, which is why the
draft treats the proposition as qualitative. But the corpora are **named** even
where the mixtures are not, and F0 histograms converge on a few thousand clips,
so bounded samples are enough.

| Sample | Repo | Size | Role |
|---|---|---|---|
| LibriSpeech dev-clean | [openslr/librispeech_asr](https://huggingface.co/datasets/openslr/librispeech_asr) | 342 MB | **SpeechTokenizer's entire training set.** `p` is knowable exactly |
| GTZAN | [marsyas/gtzan](https://huggingface.co/datasets/marsyas/gtzan) | 1.2 GB | Western music, grid-peaked F0 reference |
| MusicGen small | [facebook/musicgen-small](https://huggingface.co/facebook/musicgen-small) | 2.4 GB | codec-token music model for the propagation test |

SpeechTokenizer is the clean case. It was trained on LibriSpeech and nothing
else, so `p` can be computed rather than estimated, and speech F0 is smooth
rather than grid-peaked. Proposition 1 therefore predicts **no 12-TET structure
in it at all**, which turns the negative control from a qualitative expectation
into a quantitative prediction on a released codec.

GTZAN serves two purposes: a stand-in for the music fraction of EnCodec's and
DAC's named mixtures, and the comparison target for recovering a codec's implied
pitch prior from its codebook. Classical quantisation theory gives reconstruction
point density `lambda(theta)` proportional to `p(theta)^(1/3)`, so measuring
where the transfer function steps yields an estimate of `p` without ever seeing
the training data. Whether that recovered prior resembles Western music
statistics is then a falsifiable comparison.

**Genuinely unavailable:** Mimi's training data (~7M hours, undisclosed). For
Mimi the proposition stays qualitative.

## Disk footprint

Verified 2026-08-26 on the cluster cache:

| Component | Size |
|---|---|
| Python environment | 4.8 GB |
| 7 core codec checkpoints | 1.9 GB |
| 8 additional codec checkpoints | 21 GB |
| Whisper large-v3 | 8.7 GB |
| MMS-1B-all (1199 language adapters) | 14 GB |
| **Total model cache** | **46 GB** |
| FLEURS, 23 languages test split | 9.8 GB |
| MMS forced aligner | 1.3 GB |
| NSynth test split | 350 MB |
| Makam annotations | 118 MB |

Everything lives under `$CODECS_ROOT` on shared scratch storage. Nothing is
written to a home share or to a node-local `/tmp`.

---

## Network notes for this cluster

Outbound traffic goes through an authenticated proxy exported **only by login
shells**. A plain non-login `ssh host "cmd"` has no proxy, and downloads fail
with a connect timeout that looks like a firewall block. Always `bash -lc`.

**Reachable:** PyPI, files.pythonhosted.org, huggingface.co (models and
datasets), zenodo.org **API**.

**Blocked, 403 through the proxy:**

| Host | What it costs you |
|---|---|
| GitHub *releases* | `uv` cannot fetch a standalone interpreter |
| `download.pytorch.org` | the CUDA-specific wheel index |
| `dl.fbaipublicfiles.com` | `torchaudio.pipelines.MMS_FA` weights |
| `storage.googleapis.com` | NSynth's canonical home |
| zenodo.org *file* downloads | the makam annotation archives |

**The workaround that always applies:** almost everything is mirrored on
HuggingFace, which is reachable. Where it is not, fetch on a laptop and push
across with `tar | tsh ssh`. Fetch everything on a login node, then jobs can run
with `HF_HUB_OFFLINE=1` and never touch the network.

**A trap worth repeating:** `snapshot_download` returns success when
`allow_patterns` matched nothing. Always verify a file count after downloading,
which is what every fetcher in `cluster/` now does.

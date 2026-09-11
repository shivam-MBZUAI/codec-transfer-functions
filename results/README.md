# Result files

Every `*.csv` here is raw per-trial output. No file in this directory contains
a derived statistic; those live in [../RESULTS.md](../RESULTS.md), regenerated
by `analysis/make_results.py`. Each sweep CSV has a `.meta.json` sidecar
recording the full argument set and the package versions of the run that
produced it. `../paper/PAPER_TO_RESULTS.md` maps each element of the ICASSP
2027 paper to the files below.

| Prefix | What it is | Paper |
|---|---|---|
| `detune_*` | the registration sweep: eleven reference pitches spanning a semitone, one file per codec condition; `_220` and `_880` repeat the EnCodec 3 kbps sweep at other registers; `detune_opus*`, `detune_mp3*` are the classical-codec controls; `detune_vowel_*` the source-filter vowel stimulus | Table 1, Sec. 3.1 |
| `spectral_sweep`, `spectral_sweep_summary` | the twelve-partial spectral sweep read line by line around each input partial | Fig. 1, Table 2, Sec. 3.2 |
| `rate_encodec_*` | EnCodec at five bitrates | Sec. 3.2 (edge and bias against bitrate) |
| `mech_bypass` | encoder output fed straight to the decoder, quantiser removed | Fig. 2, Sec. 3.2 |
| `probe_encodec3` | code-assignment boundaries across a dense pitch sweep | Sec. 3.2 (Rayleigh test) |
| `octaves_encodec3`, `octaves_opus6` | the four-octave sweep | Sec. 2.4 |
| `ftm_{grid,gridres,gridmix,flat}_s{0..4}`, `ftm_grid`, `ftm_flat` | the decoder fine-tuning arms: unmodified GTZAN, resampled by one semitone, resampled by 0 or 100 cents per clip, tuning-flattened; five seeds each | Sec. 3.3 |
| `replication/` | an earlier instance's runs of seeds 0 to 2 for three arms; arm means agree within 0.05 cents | Sec. 3.3 |
| `swap_*` | encoder/decoder swap sweeps showing the fine-tuning changed only the decoder | Sec. 3.3 |
| `corpus_pull_*` | the frame-wise transfer function on whole recordings: tuning-flattened GTZAN and Saraga through EnCodec, Opus and DAC 16k | Sec. 3.4 |
| `hist_gtzan`, `hist_gtzan_detuned` | within-semitone F0 density of the fine-tuning corpus and its flattened version | Sec. 3.3 |
| `ctrl_identity`, `ctrl_sinusoid` | the null controls: no codec, and a pure sinusoid | Sec. 2.4 |
| `detune_snac.csv`, `detune_dac44.csv` | conditions the guards refuse to fit, kept so the refusal is reproducible | Table 1 |

Result families the paper reports that were produced on a second machine and
are not yet here are listed as *pending upload* in
`../paper/PAPER_TO_RESULTS.md`.

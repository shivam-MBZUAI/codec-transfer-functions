# Where every number in the paper comes from

The manuscript is `icassp2027_chauhan.pdf`. Every measured value it prints is a
macro in its LaTeX source; `values.csv` lists the ones the paper prints, with the group each belongs
to and the provenance note recorded beside it (script and result file). The three tables are transcribed in `tables/` with a `source_file`
column.

**Status legend.** *in repo*: the raw per-trial file is in `results/` with its
`.meta.json` sidecar. *pending upload*: produced on a second machine after the
files here were committed; listed so nothing is presented as reproducible that
is not yet checkable here.

| Paper element | Produced by | Raw files | Status |
|---|---|---|---|
| Registration slope, R^2, headline bias (Sec. 3.1, Table 1 EnCodec rows) | `analysis/analyze_detuning.py`, `analysis/analyze_sweep.py` | `results/detune_encodec3.csv`, `detune_encodec24kbps.csv`, `detune_encodec48.csv`, `detune_vowel_encodec.csv` | in repo |
| Table 1, other codec rows | same | `detune_mimi.csv`, `detune_dac16.csv`, `detune_dac24.csv`, `detune_dac44.csv`, `detune_snac.csv`, `detune_snac32.csv`, `detune_snac44.csv`, `detune_vowel_speechtok.csv` | in repo |
| Table 1, classical controls Opus and MP3 | same | `detune_opus6.csv`, `detune_opus12.csv`, `detune_mp316.csv`, `detune_mp332.csv` | in repo |
| Table 1, WavTokenizer, BigVGAN, HE-AAC SBR rows | same | | pending upload |
| Registration at 220 and 880 Hz | same | `detune_encodec3_220.csv`, `detune_encodec3_880.csv` | in repo |
| DAC 16k at 880 and 1760 Hz (Sec. 3.1) | same | | pending upload |
| Population median over 24 stimuli (Sec. 3.1) | `analysis/analyze_stimulus_population.py` | per-envelope sweeps | pending upload |
| Guards: amplitude CV and retention (Sec. 2.2) | `analysis/guard_sensitivity.py` | all `detune_*.csv` | in repo |
| Fig. 1 and Table 2, per-partial displacements | `experiments/spectral_sweep.py`, `analysis/analyze_spectral.py`, `analysis/fig_spectral_check.py` | `spectral_sweep.csv`, `spectral_sweep_summary.csv` | in repo |
| Band edge and ladder fraction per condition (Sec. 2.3, 3.2) | `analysis/analyze_spectral.py` | `spectral_sweep.csv`; other codecs' spectral sweeps | EnCodec in repo, others pending |
| Fig. 2 residual profiles; (P1) clipped-profile fit | `analysis/make_figures.py`, `analysis/analyze_sweep.py` | `detune_encodec3.csv`, `mech_bypass.csv` | in repo |
| Quantiser bypass (Sec. 3.2) | `analysis/analyze_rate.py` | `mech_bypass.csv`, `rate_encodec_*.csv` | in repo |
| Code-assignment boundaries, Rayleigh test (Sec. 3.2) | `analysis/analyze_probe.py` | `probe_encodec3.csv` | in repo (`rayleigh_floor.py` power calculation pending) |
| Fine-tuning arms: unmodified, semitone, 0-or-100, flattened, five seeds (Sec. 3.3) | `experiments/finetune_encodec.py`, `analysis/summary_causal.py` | `ftm_{grid,gridres,gridmix,flat}_s{0..4}.csv`, `ftm_grid.csv`, `ftm_flat.csv`, `replication/` | in repo |
| Encoder/decoder swap check that only the decoder changed | `analysis/summary_causal.py` | `swap_*.csv` | in repo |
| Retuned (+33 cent) and 24-TET arms; Mimi and WavTokenizer retuning; Saraga-tuned decoder (Sec. 3.3) | `experiments/finetune_encodec.py --retune`, `analyze_relocate.py` | | pending upload |
| Bandwidth extender trained from scratch (Sec. 3.3) | `analysis/analyze_bwe.py` | | pending upload |
| Held-out and registered checkpoint passes (Sec. 3.3) | | | pending upload |
| Frame-wise bias on real recordings (Sec. 3.4) | `experiments/corpus_pull.py`, `analysis/analyze_corpus_pull.py` | `corpus_pull_encodec3.csv`, `corpus_pull_saraga_encodec3.csv`, `corpus_pull_opus*.csv`, `corpus_pull_dac166.csv` | in repo |
| Register split of the real-recording bias | `analyze_register_split.py` | same | script pending |
| Table 3, scale-degree error and flips; matched Opus; band-limited fit; pYIN | `analyze_tuning.py` | | pending upload (script and files) |
| Corpus tuning histograms (GTZAN, flattened GTZAN) | `experiments/pitch_histogram.py`, `analysis/plot_histograms.py` | `hist_gtzan.csv`, `hist_gtzan_detuned.csv`, `hist_librispeech.csv` | in repo |
| Identity and sinusoid controls | `analysis/analyze_sweep.py` | `ctrl_identity.csv`, `ctrl_sinusoid.csv` | in repo |
| Pre-registration and its amendment log | | `../PREDICTIONS.md` | in repo |

Every file in `results/` serves a row of this table; `results/README.md`
describes each family. The pre-registration document also covers speech
tests that the ICASSP paper does not report; their result files are not
included here.

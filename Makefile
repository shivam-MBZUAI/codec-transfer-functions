# Reproduction targets. See REPRODUCE.md for the full command behind each.
PY      ?= python
# Eleven reference pitches, 0 to 100 cents above A440 in 10-cent steps. The
# 100-cent point folds onto the 0-cent condition, so ten distinct conditions
# enter the regression.
REFS    := 440 442.5489 445.1126 447.6911 450.2845 452.8930 455.5166 458.1553 460.8094 463.4789 466.1638

.PHONY: help gate checkpoints sweep detune rate figures results clean-figures

help:
	@echo "make gate         estimator floor, identity control, pilot sweep"
	@echo "make checkpoints  download the seven codec checkpoints (~1.9 GB)"
	@echo "make detune       the registration regression (the headline result)"
	@echo "make rate         rate sweep plus the quantiser-bypass control"
	@echo "make results      regenerate RESULTS.md from results/"
	@echo "make figures      regenerate every paper figure from results/"

checkpoints:
	$(PY) data/fetch_checkpoints.py

# Nothing below the gate means anything until the gate passes.
gate:
	@echo "== 1/3 estimator noise floor (must print PASS)"
	@cd experiments && $(PY) test_estimator.py | tail -3
	@echo "== 2/3 identity control, no codec in the loop (must report NULL)"
	@$(PY) experiments/run_sweep.py --codec identity:24000 --reps 2 --theta-step 25 \
		--out results/gate_identity.csv >/dev/null
	@$(PY) analysis/analyze_sweep.py results/gate_identity.csv | grep -A2 "=== gate"
	@echo "== 3/3 pilot sweep, EnCodec 3 kbps"
	@$(PY) experiments/run_sweep.py --codec encodec:3 --reps 3 \
		--references 440 452.8929 --out results/gate_pilot.csv >/dev/null
	@$(PY) analysis/analyze_sweep.py results/gate_pilot.csv | grep -E "grid bias|ratio"

detune:
	$(PY) experiments/run_sweep.py --codec encodec:3 --reps 5 --references $(REFS) \
		--out results/detune_encodec3.csv
	$(PY) analysis/analyze_detuning.py results/detune_encodec3.csv \
		figures/detuning_regression.png

rate:
	@for kb in 1.5 3 6 12 24; do \
		$(PY) experiments/run_sweep.py --codec encodec:$$kb --reps 5 \
			--references 440 452.8929 --out results/rate_encodec_$$kb.csv; \
	done
	$(PY) experiments/run_sweep.py --codec encodec_bypass --reps 5 \
		--references 440 452.8929 --out results/mech_bypass.csv
	$(PY) analysis/analyze_rate.py

results:
	$(PY) analysis/make_results.py

figures:
	$(PY) analysis/make_figures.py
	$(PY) analysis/plot_histograms.py
	$(PY) analysis/analyze_detuning.py results/detune_encodec3.csv \
		figures/detuning_regression.png

clean-figures:
	rm -f figures/*.png

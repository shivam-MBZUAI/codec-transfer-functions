"""Generate RESULTS.md from the result files. Never hand-write that document.

    python analysis/make_results.py

Every number in RESULTS.md is computed here from a CSV in results/. There is no
path by which a value that was not measured can appear in it. Experiments that
have not run show as "not yet measured" rather than as a plausible placeholder,
because a placeholder that looks like a result is how a draft ends up asserting
things nobody measured.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

import numpy as np  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "experiments", _ROOT / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from analyze_sweep import (  # noqa: E402
    DISAGREE_CENTS, grid, load, summarise,
)

# Every experiment the programme defines, so what is missing is as visible as
# what is present. Keys match EXPERIMENTS.md. The third field lists the result
# files (stems under results/) whose presence means the experiment has run;
# an empty tuple means it has not, and the row says so.
PROGRAMME = [
    ("E0.1", "Estimator noise floor", ("ctrl_identity",)),   # floor column of every run
    ("E0.2", "Identity control (no codec)", ("ctrl_identity",)),
    ("E0.3", "Resample-only control", ()),
    ("E0.4", "Pilot gate", ("pilot_encodec3",)),
    ("E1.1", "Detuning sweep, phase vs reference offset", ("detune_encodec3",)),
    ("E1.2", "Quantiser bypass", ("mech_bypass",)),
    ("E1.3", "Direct codebook probing", ("probe_encodec3",)),
    ("E1.4", "Per-RVQ-level decomposition", ()),
    ("E1.5", "Random-codebook control", ("mech_shuffled",)),
    ("E1.6", "Causal: RVQ trained on controlled pitch distributions", ("causal_12tet", "ftm_grid")),
    ("E2.1", "Codec breadth", ("detune_mimi", "detune_dac16", "detune_snac44")),
    ("E2.2", "Training-distribution contrast", ("detune_encodec48", "ftm_flat")),
    ("E2.3", "Rate sweep in bits per latent dimension", ("rate_encodec_3",)),
    ("E2.4", "Stimulus ablations", ("ctrl_sinusoid", "vib_20")),
    ("E3.1", "Speech-shaped pitch stimuli", ("detune_vowel_encodec", "detune_vowel_speechtok")),
    ("E3.2", "Retuned instrument samples", ("retune_encodec3_big",)),
    ("E3.3", "Makam validation", ()),
    ("E3.4", "Token-level probe", ()),
    ("E3.5", "Phonological survival (FLEURS)", ("phon_encodec3_big",)),
    ("E3.6", "Downstream ASR", ("asr_encodec3_v2", "asr_mms_encodec3")),
]

HEADER = """# Results

<!-- GENERATED FILE. Do not edit by hand.
     Regenerate with:  python analysis/make_results.py
     Every number below is computed from a CSV in results/. Nothing here is a
     prediction, a placeholder, or a value typed by a human.
     Exclusion scheme: octave gate only, as in the paper. -->

Every figure and table here is derived from a file in `results/`. Experiments
that have not run are listed as not yet measured rather than shown with
placeholder values.

"""


def fmt(v, nd=3, dash="--"):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return dash
    if v != 0 and abs(v) < 10 ** (-nd):
        return f"{v:.1e}"
    return f"{v:.{nd}f}"


def ratio_or_na(off, on, floor):
    """The off/on ratio is only meaningful once the effect clears the estimator.

    Dividing two numbers that are both at the noise floor produces a
    plausible-looking multiple out of pure noise, which is precisely the failure
    this file exists to prevent. The caption promises that nothing below the
    floor means anything; this enforces it.
    """
    if not (np.isfinite(off) and np.isfinite(on)) or on == 0:
        return None, "--"
    if off < 3 * max(floor, 1e-9):
        return None, "n/a, below floor"
    return off / on, None


def summarise_csv(path: Path):
    d = load(path)
    if not d or "theta_cents" not in d:
        return None
    theta = d["theta_cents"]
    r_coded, r_unc = d["residual_coded_cents"], d["residual_uncoded_cents"]
    labels = d["reference_label"]

    # Octave gate only: the scheme every number in the paper uses. The
    # estimator cross-check is a robustness variant (analyze_sweep.py
    # --exclusion=full), not the primary analysis, because it fires
    # preferentially 30 to 50 cents from a grid point.
    keep = np.ones_like(theta, dtype=bool)
    if "octave_flag" in d:
        keep &= d["octave_flag"] < 0.5

    meta_path = path.with_suffix(".meta.json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    rows = []
    for label in sorted(set(labels.tolist())):
        m = labels == label
        if int((m & keep & np.isfinite(r_coded)).sum()) < 20:
            continue        # too few surviving trials to summarise honestly
        rows.append(summarise(theta[m], r_coded[m], r_unc[m], keep[m], label))
    return (meta, rows) if rows else None


def main() -> int:
    results_dir = ROOT / "results"
    csvs = sorted(p for p in results_dir.glob("*.csv"))

    out = [HEADER]
    measured_keys = set()

    if not csvs:
        out.append("## No runs yet\n\nNothing in `results/`.\n")
    else:
        out.append("## Pitch transfer function\n")
        out.append(
            "| run | codec | rate | reference | n | floor (c) | on-grid (c) | "
            "off-grid (c) | ratio | grid bias (c) | 95% CI | sine R2 | saw R2 | better |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        )
        skipped = []
        for csv in csvs:
            # Sweeps may still be writing, and a run that failed early leaves a
            # header-only file. Neither should take down the whole report.
            try:
                got = summarise_csv(csv)
            except Exception as e:
                skipped.append((csv.stem, f"{type(e).__name__}: {e}"))
                continue
            if not got:
                skipped.append((csv.stem, "no usable rows"))
                continue
            meta, rows = got
            codec = meta.get("codec", "?")
            rate = meta.get("rate_label", "?")
            measured_keys.add(codec)
            for s in rows:
                ratio, ratio_note = ratio_or_na(s["off_grid"], s["on_grid"], s["floor"])
                # The shape comparison is equally meaningless on a null run.
                if s["bias"] < 3 * max(s["floor"], 1e-9):
                    better = "n/a, below floor"
                else:
                    better = "sawtooth" if s["saw_r2"] > s["sin_r2"] else "sinusoid"
                lo, hi = s["bias_ci"]
                out.append(
                    f"| `{csv.stem}` | {codec} | {rate} | {s['label']} | {s['n']} | "
                    f"{fmt(s['floor'])} | {fmt(s['on_grid'])} | {fmt(s['off_grid'])} | "
                    f"{ratio_note or fmt(ratio, 2)} | {fmt(s['bias'])} | "
                    f"[{fmt(lo,2)}, {fmt(hi,2)}] | {fmt(s['sin_r2'],2)} | "
                    f"{fmt(s['saw_r2'],2)} | {better} |\n"
                )
        if skipped:
            out.append("\n**Skipped:** " + ", ".join(
                f"`{n}` ({why})" for n, why in skipped) + "\n")
        out.append(
            "\n**Reading this table.** `floor` is the estimator's own error on "
            "uncoded stimuli in the same run: no effect below it means anything. "
            "`grid bias` is positive when the codec moved an interval *toward* "
            "the Western semitone grid, which is the directional claim; a "
            "symmetric residual of the same magnitude is ordinary degradation. "
            "`sine R2` against `saw R2` discriminates the two candidate "
            "mechanisms: a density correction predicts a sinusoid, coarse cell "
            "assignment predicts a sawtooth, and they scale differently with "
            "rate.\n\n"
        )

    figs = sorted(p for p in (ROOT.parent / "figures").glob("*.png"))
    out.append("## Figures\n\n")
    if figs:
        for f in figs:
            out.append(f"### `{f.name}`\n\n![{f.stem}](figures/{f.name})\n\n")
    else:
        out.append("None generated yet.\n\n")

    out.append("## Programme status\n\n| id | experiment | status |\n|---|---|---|\n")
    for eid, name, stems in PROGRAMME:
        done = any((results_dir / f"{s}.csv").exists() for s in stems)
        out.append(f"| {eid} | {name} | {'measured' if done else 'not yet measured'} |\n")
    out.append(
        "\nSee [EXPERIMENTS.md](EXPERIMENTS.md) for what each of these tests and "
        "why it is in the programme.\n"
    )

    (ROOT / "RESULTS.md").write_text("".join(out))
    print(f"wrote RESULTS.md from {len(csvs)} result file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Group-level summary of Experiment 3: relative WER increase after coding."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "experiments", _ROOT / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from languages import LANG_NAMES  # noqa: E402

import sys
from pathlib import Path



def main() -> int:
    rows = list(csv.DictReader(Path(sys.argv[1]).open()))
    per_lang = defaultdict(lambda: {"o": [], "c": [], "g": ""})
    dropped = set()
    for r in rows:
        if r.get("recogniser_failed", "0") == "1":
            dropped.add(r["lang"])
            continue
        try:
            o, c = float(r["wer_original"]), float(r["wer_coded"])
        except ValueError:
            continue
        if not (np.isfinite(o) and np.isfinite(c)):
            continue
        per_lang[r["lang"]]["o"].append(o)
        per_lang[r["lang"]]["c"].append(c)
        per_lang[r["lang"]]["g"] = r["group"]

    if dropped:
        print(f"  excluded, recogniser fails before coding: "
              f"{', '.join(sorted(dropped))}\n")
    print(f"  {'language':<12}{'group':<12}{'baseline':>10}{'coded':>9}"
          f"{'relative':>11}{'n':>5}")
    lang_rel = {}
    for l in sorted(per_lang, key=lambda x: (per_lang[x]["g"], x)):
        d = per_lang[l]
        o, c = float(np.median(d["o"])), float(np.median(d["c"]))
        rel = (c - o) / o if o > 0 else float("nan")
        lang_rel[l] = (rel, d["g"])
        print(f"  {LANG_NAMES.get(l, l):<12}{d['g']:<12}{o:10.3f}{c:9.3f}"
              f"{100*rel:10.1f}%{len(d['o']):5d}")

    # Per-language bootstrap over utterances: resample utterances, recompute
    # the median baseline and coded WER, and the relative increase.
    rng = np.random.default_rng(0)
    lang_ci = {}
    for l, d in per_lang.items():
        o, c = np.array(d["o"]), np.array(d["c"])
        if len(o) < 5 or np.median(o) <= 0:
            continue
        boots = []
        for _ in range(4000):
            idx = rng.integers(0, len(o), len(o))
            mo, mc = np.median(o[idx]), np.median(c[idx])
            if mo > 0:
                boots.append((mc - mo) / mo)
        if boots:
            lang_ci[l] = (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5)))
    print("\n  per-language 95% bootstrap intervals on the relative increase (over utterances)")
    for l in sorted(lang_ci, key=lambda x: (per_lang[x]["g"], x)):
        lo, hi = lang_ci[l]
        print(f"  {LANG_NAMES.get(l, l):<12}{per_lang[l]['g']:<12}[{100*lo:7.1f}%, {100*hi:7.1f}%]")

    groups = defaultdict(list)
    for l, (rel, g) in lang_rel.items():
        if np.isfinite(rel):
            groups[g].append(rel)

    # Three normalisations, because the sign of a group difference depends on
    # it when baselines differ several-fold: relative increase (coded-base)/base,
    # absolute increase coded-base, and headroom-normalised (coded-base)/(1-base).
    lang_stats = {}
    for l, d in per_lang.items():
        o, c = float(np.median(d["o"])), float(np.median(d["c"]))
        lang_stats[l] = (d["g"], o, c - o, (c - o) / (1 - o) if o < 1 else float("nan"),
                         (c - o) / o if o > 0 else float("nan"))
    print("\n  group medians under three normalisations (95% bootstrap over languages)")
    print(f"  {'group':<12}{'n':>3}{'baseline':>10}{'absolute':>22}{'headroom':>22}{'relative':>22}")
    for g in sorted(set(v[0] for v in lang_stats.values())):
        rows_g = [v for v in lang_stats.values() if v[0] == g]
        cols = []
        for j in (2, 3, 4):
            vals = np.array([r[j] for r in rows_g if np.isfinite(r[j])])
            if len(vals) == 0:
                cols.append("--"); continue
            b = [np.median(vals[rng.integers(0, len(vals), len(vals))]) for _ in range(4000)] if len(vals) > 1 else [np.median(vals)]
            cols.append(f"{np.median(vals):+.3f} [{np.percentile(b,2.5):+.3f},{np.percentile(b,97.5):+.3f}]")
        base = np.median([r[1] for r in rows_g])
        print(f"  {g:<12}{len(rows_g):>3}{base:>10.3f}{cols[0]:>22}{cols[1]:>22}{cols[2]:>22}")

    def _group_ci(vals):
        vals = np.array(vals)
        if len(vals) < 2:
            return float("nan"), float("nan")
        b = [np.median(vals[rng.integers(0, len(vals), len(vals))]) for _ in range(4000)]
        return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))
    print("\n  group 95% bootstrap intervals over languages")
    for g in sorted(groups):
        lo, hi = _group_ci(groups[g])
        print(f"  {g:<12}n={len(groups[g]):<3} median {100*np.median(groups[g]):6.1f}%  [{100*lo:6.1f}%, {100*hi:6.1f}%]")
    print(f"\n  {'group':<12}{'langs':>6}{'median relative increase':>26}")
    for g in sorted(groups):
        v = np.array(groups[g])
        print(f"  {g:<12}{len(v):6d}{100*float(np.median(v)):25.1f}%")

    ctrl = np.array(groups.get("control", []))
    if ctrl.size:
        cm = float(np.median(ctrl))
        print(f"\n  against the control's {100*cm:.1f}%:")
        for g in sorted(groups):
            if g == "control":
                continue
            r = float(np.median(groups[g])) / cm if cm else float("nan")
            print(f"    {g:<12}{r:6.2f}x")
        print("\n  Relative rather than absolute: tone-language baselines are")
        print("  already high, so a comparison in WER points would conflate codec")
        print("  damage with baseline difficulty.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

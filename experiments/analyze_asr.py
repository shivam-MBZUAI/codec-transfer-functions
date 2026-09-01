"""Group-level summary of Experiment 3: relative WER increase after coding."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from languages import LANG_NAMES  # noqa: E402


def main() -> int:
    rows = list(csv.DictReader(Path(sys.argv[1]).open()))
    per_lang = defaultdict(lambda: {"o": [], "c": [], "g": ""})
    for r in rows:
        try:
            o, c = float(r["wer_original"]), float(r["wer_coded"])
        except ValueError:
            continue
        if not (np.isfinite(o) and np.isfinite(c)):
            continue
        per_lang[r["lang"]]["o"].append(o)
        per_lang[r["lang"]]["c"].append(c)
        per_lang[r["lang"]]["g"] = r["group"]

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

    groups = defaultdict(list)
    for l, (rel, g) in lang_rel.items():
        if np.isfinite(rel):
            groups[g].append(rel)

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

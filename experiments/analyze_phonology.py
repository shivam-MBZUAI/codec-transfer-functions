"""Group-level summary of Experiment 2.

Every ratio is against the non-tonal control measured with the SAME metric.
F0 error in cents and log-spectral distance in dB share no scale, so a ratio
across metrics would be meaningless and is never formed.

Bootstrap intervals are over languages, not utterances. Utterances within a
language are not independent draws from the quantity of interest, which is a
per-language effect, so an utterance-level interval would be far too narrow.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from languages import LANG_NAMES  # noqa: E402


def boot_ratio(vals: list[float], ctrl: list[float], n_boot: int = 4000,
               seed: int = 0) -> tuple[float, float, float]:
    """Ratio of group median to control median, resampling LANGUAGES."""
    v, c = np.array(vals, float), np.array(ctrl, float)
    v, c = v[np.isfinite(v)], c[np.isfinite(c)]
    if v.size < 2 or c.size < 2:
        return float("nan"), float("nan"), float("nan")
    point = float(np.median(v) / np.median(c))
    rng = np.random.default_rng(seed)
    rs = [np.median(v[rng.integers(0, v.size, v.size)]) /
          np.median(c[rng.integers(0, c.size, c.size)]) for _ in range(n_boot)]
    return point, float(np.percentile(rs, 2.5)), float(np.percentile(rs, 97.5))


def main() -> int:
    rows = list(csv.DictReader(Path(sys.argv[1]).open()))
    per_lang: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    group_of = {}
    for r in rows:
        for m in ("f0_err_cents", "lsd_db"):
            try:
                v = float(r[m])
            except (ValueError, KeyError):
                continue
            if np.isfinite(v):
                per_lang[r["lang"]][m].append(v)
        group_of[r["lang"]] = r["group"]

    lang_med = {l: {m: float(np.median(v)) for m, v in d.items()}
                for l, d in per_lang.items()}

    print("  per-language medians\n")
    print(f"  {'language':<12}{'group':<12}{'F0 err (c)':>12}{'LSD (dB)':>10}{'n':>6}")
    for l in sorted(lang_med, key=lambda x: (group_of[x], x)):
        n = len(per_lang[l].get("f0_err_cents", []))
        print(f"  {LANG_NAMES.get(l, l):<12}{group_of[l]:<12}"
              f"{lang_med[l].get('f0_err_cents', float('nan')):12.3f}"
              f"{lang_med[l].get('lsd_db', float('nan')):10.3f}{n:6d}")

    groups = defaultdict(list)
    for l, g in group_of.items():
        groups[g].append(l)
    ctrl = groups.get("control", [])

    print(f"\n  ratios against the non-tonal control (bootstrap over languages)\n")
    print(f"  {'group':<12}{'langs':>6}{'metric':>14}{'ratio':>9}{'95% CI':>18}")
    for g in sorted(groups):
        if g == "control":
            continue
        for m, name in (("f0_err_cents", "F0 (cents)"), ("lsd_db", "LSD (dB)")):
            v = [lang_med[l][m] for l in groups[g] if m in lang_med[l]]
            c = [lang_med[l][m] for l in ctrl if m in lang_med[l]]
            pt, lo, hi = boot_ratio(v, c)
            flag = ""
            if np.isfinite(lo) and lo <= 1.0 <= hi:
                flag = "  interval includes 1: no reliable effect"
            print(f"  {g:<12}{len(groups[g]):6d}{name:>14}{pt:9.3f}"
                  f"{f'[{lo:.2f}, {hi:.2f}]':>18}{flag}")

    print("\n  Note: tone is the group for which F0 error is the meaningful metric;")
    print("  ejective and click are consonantal and LSD is theirs. Both are printed")
    print("  for completeness, not because both are interpretable for every group.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

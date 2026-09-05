"""Marginals-preserving null for the frozen-rule confirmatory pass.

The equiprobable-tier binomial in Appendix C.21 assumes a predictor that
guesses uniformly over three tiers. That is the wrong comparison: both the
predictions and the outcomes are lopsided (eleven of sixteen predictions
say "ladder"; only six outcomes are), so a predictor that always said
"ladder" would already beat 1/3. The honest null holds both margins fixed
and asks how often a random pairing does as well --- the Fisher-conditional
permutation of the assignment labels against the fixed prediction vector.

Reads the table out of the appendix so it cannot drift from what is printed.
"""
import re
import sys
from pathlib import Path

import numpy as np

APX = Path(__file__).resolve().parents[2] / "sections" / "09_appendix.tex"
DRAWS = 200_000
SEED = 20260902


def rows():
    src = APX.read_text()
    i = src.index("\\label{tab:confirmatory}")
    body = src[i:src.index("\\end{tabular}", i)]
    group, out = None, []
    for line in body.split("\\\\"):
        if "multicolumn" in line:
            group = "new" if "never measured" in line else "seen"
            continue
        cells = [c.strip() for c in line.split("&")]
        if len(cells) < 7 or "textbf" in line:
            continue
        if len(re.findall(r"-?\d\.\d\d", cells[4].replace("$-$", "-"))) != 3:
            continue
        out.append((group, cells[5].split()[0], cells[6].split()[0]))
    return out


def permutation_p(pred, got, rng):
    """P(a random relabelling of `got` matches `pred` at least as often)."""
    obs = sum(p == g for p, g in zip(pred, got))
    got = np.array(got)
    hits = np.empty(DRAWS, dtype=int)
    for d in range(DRAWS):
        hits[d] = (rng.permutation(got) == np.array(pred)).sum()
    # expected matches under the fixed margins, in closed form
    exp = sum(pred.count(c) * list(got).count(c) for c in set(pred) | set(got)) / len(pred)
    return obs, exp, float((hits >= obs).mean()), hits


def main():
    tab = rows()
    if len(tab) != 16:
        sys.exit(f"parsed {len(tab)} rows, expected 16")
    rng = np.random.default_rng(SEED)
    for name, sel in (("all sixteen", lambda r: True),
                      ("new families", lambda r: r[0] == "new"),
                      ("new operating points", lambda r: r[0] == "seen")):
        sub = [r for r in tab if sel(r)]
        pred, got = [r[1] for r in sub], [r[2] for r in sub]
        obs, exp, p, _ = permutation_p(pred, got, rng)
        print(f"{name:22s} {obs:2d}/{len(sub):2d} hits   "
              f"expected {exp:4.2f}   permutation p = {p:.3f}")
    print(f"\n({DRAWS} draws, seed {SEED}; margins of both the prediction and "
          f"the assignment column held fixed)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Check that claims about the paper are true of the built PDF.

Why this exists. On 2026-09-07 a commit message said a neighbour had been
"added to both" the boundary table and the caveat list. It had been added to
one. The claim was written from intent rather than from the artefact, and no
step in the workflow compared the two.

So: before a commit message asserts that the paper now says something, run the
assertion against `main.pdf`. Each claim is a literal string or a regex; the
script reports which hold and exits non-zero if any do not.

Usage:
    python3 code/analysis/verify_claims.py \\
        "seven of the 21 are load-bearing" \\
        --regex "95 bibliography entries, 74 carry"
    python3 code/analysis/verify_claims.py --absent "no codec we measure moves it past"

Options:
    --regex CLAIM    treat CLAIM as a regular expression
    --absent CLAIM   assert CLAIM does *not* appear (for retractions)

Text is taken from `pdftotext main.pdf -`, with runs of whitespace collapsed,
so claims can be written as they read on the page rather than as they wrap.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pdf_text(pdf: Path | None = None) -> str:
    pdf = pdf or (ROOT / "main.pdf")
    if not pdf.exists():
        raise SystemExit(f"no such file: {pdf}")
    out = subprocess.run(["pdftotext", str(pdf), "-"],
                         capture_output=True, text=True, check=True).stdout
    # The PDF hard-wraps and hyphenates. Joining a break removes the hyphen,
    # which also silently welds genuinely hyphenated words ("off-grid" that
    # happens to wrap becomes "offgrid") and made this script report a false
    # failure on correct text. So normalise both sides the same way: drop
    # every hyphen and collapse whitespace, and compare on that.
    return normalise(out)


# TeX renders ' and " as curly glyphs and -- as an en dash, so a claim typed
# with ASCII punctuation fails against a correct PDF. This cost a false
# failure on "a decoder's corpus" once already, the same way the hyphen
# joining did. Fold both sides onto ASCII before comparing.
_PUNCT = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u00a0": " ",
})


def normalise(s: str) -> str:
    # Case-folded: a claim quoted from mid-sentence differs from the same
    # words at the start of one only in capitalisation, and that produced two
    # false failures ("the identity is not violated" against "The identity
    # ..."). Case never distinguishes two different claims here.
    s = s.translate(_PUNCT).lower()
    return re.sub(r"\s+", " ", s.replace("-\n", "").replace("-", ""))


def main(argv: list[str]) -> int:
    claims: list[tuple[str, str, bool]] = []   # (kind, text, must_be_present)
    mode, present = "literal", True
    for a in argv:
        if a == "--regex":
            mode = "regex"
        elif a == "--literal":
            mode = "literal"
        elif a == "--absent":
            present = False
        elif a == "--present":
            present = True
        else:
            claims.append((mode, a, present))
            mode, present = "literal", True

    if not claims:
        print(__doc__)
        return 0

    text = pdf_text()
    bad = 0
    for kind, claim, want in claims:
        flat = normalise(claim).strip()
        hit = (re.search(flat, text) is not None) if kind == "regex" \
            else (flat in text)
        ok = (hit == want)
        bad += not ok
        verb = "present" if want else "absent"
        print(f"  {'ok ' if ok else 'FAIL'}  [{verb}] {flat[:72]!r}")

    if bad:
        print(f"\n{bad} claim(s) do not hold of main.pdf. "
              "Fix the paper or the claim -- do not commit the sentence.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

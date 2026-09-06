#!/usr/bin/env python3
"""Build a review packet for a batch of paper edits, for checking before commit.

Why this exists. Cycles 10 to 12 each landed a batch of summary-layer edits and
each batch introduced roughly four to five new defects -- a sentence changed in
the abstract but not the appendix, a count updated in one place and not the
other, a caption trimmed past the definition it carried. Five reviewers and a
full cycle were needed to surface them, by which time the next batch was
already on top. A reviewer scoped to the diff alone catches the same class for
one agent instead of five, before the damage is committed.

What the packet contains, for each changed passage:
  * the passage as it now reads, with its file and line;
  * the labels it cites (\\ref, \\citet, macros), so the checker can look them
    up rather than guess;
  * for every macro used, its definition;
  * for every table label cited, that table's rows.

Usage:
    python3 code/analysis/review_packet.py            # uncommitted changes
    python3 code/analysis/review_packet.py <rev>      # changes since <rev>
    python3 code/analysis/review_packet.py A B        # changes between A and B

Writes the packet to stdout. Hand it to a reviewer with the instruction to
check every changed sentence against the table it summarises.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEX = ["main.tex", "sections", "refs.bib"]


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True, check=True).stdout


def added_lines(rev_args: list[str]) -> list[tuple[str, str]]:
    """(file, added line) for every + line in the diff, excluding headers."""
    diff = git("diff", "-U0", *rev_args, "--", *TEX)
    out, cur = [], "?"
    for line in diff.split("\n"):
        if line.startswith("+++ b/"):
            cur = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            body = line[1:]
            if body.strip():
                out.append((cur, body))
    return out


def macro_defs() -> dict[str, str]:
    src = (ROOT / "main.tex").read_text(encoding="utf-8")
    return dict(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}\{([^{}]*)\}", src))


def table_rows(label: str) -> list[str]:
    for rel in ("sections/09_appendix.tex", "sections/04_pitch.tex",
                "sections/03_method.tex", "sections/01_intro.tex"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        tag = "\\label{" + label + "}"
        if tag not in src:
            continue
        i = src.index(tag)
        try:
            a = src.index("\\begin{tabular}", i)
            b = src.index("\\end{tabular}", a)
        except ValueError:
            return []
        rows = [r.strip() for r in src[a:b].split("\\\\")
                if "&" in r and "textbf" not in r]
        return [re.sub(r"\s+", " ", r)[:160] for r in rows if r.strip()]
    return []


def main(argv: list[str]) -> int:
    rev = argv or []
    if len(rev) == 2:
        rev = [f"{rev[0]}..{rev[1]}"]
    lines = added_lines(rev)
    if not lines:
        print("No changes to review.")
        return 0

    macros = macro_defs()
    used_macros, used_labels = set(), set()
    print("=" * 72)
    print("CHANGED PASSAGES")
    print("=" * 72)
    seen = set()
    for path, body in lines:
        if (path, body) in seen:
            continue
        seen.add((path, body))
        print(f"\n[{path}]  {body}")
        for m in re.findall(r"\\([A-Za-z]+)\{\}", body):
            if m in macros:
                used_macros.add(m)
        for m in re.findall(r"\\ref\{(tab:[A-Za-z0-9:-]+)\}", body):
            used_labels.add(m)

    if used_macros:
        print("\n" + "=" * 72)
        print("MACROS USED IN THE CHANGED TEXT (value each resolves to)")
        print("=" * 72)
        for m in sorted(used_macros):
            print(f"  \\{m:<20} = {macros[m].replace(chr(92)+'xspace','')}")

    if used_labels:
        print("\n" + "=" * 72)
        print("TABLES CITED BY THE CHANGED TEXT")
        print("=" * 72)
        for lab in sorted(used_labels):
            print(f"\n--- {lab} ---")
            for r in table_rows(lab):
                print("   ", r)

    print("\n" + "=" * 72)
    print(f"{len(seen)} changed line(s), {len(used_macros)} macro(s), "
          f"{len(used_labels)} table(s) cited.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Apply a batch of literal source edits atomically, then verify them.

Why this exists. On 2026-09-07 a batch of five appendix edits was applied by a
script that asserted each match *before* writing. One assertion failed, the
script aborted, and the four good edits were discarded with it. Only some were
noticed and re-applied, so a fix reported as done had never landed -- and the
commit message said it had.

Two rules follow, and this script enforces both:

  1. All or nothing. Every `old` must match exactly once across the batch
     before anything is written. A batch that cannot be applied whole is not
     applied at all, so there is no half-state to misread.
  2. Verify after writing, not before. Once written, each file is re-read from
     disk and each edit is confirmed present. Asserting a precondition is not
     evidence that a postcondition holds.

Usage:
    from edit import apply_edits
    apply_edits([
        ("sections/09_appendix.tex", "old text", "new text"),
        ...
    ])

Exits non-zero if any edit fails to apply or to verify, and prints a per-edit
table either way.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def apply_edits(edits, root: Path | None = None, quiet: bool = False) -> int:
    """Apply (path, old, new) triples atomically. Returns 0 on success."""
    root = root or ROOT
    originals: dict[Path, str] = {}
    staged: dict[Path, str] = {}
    problems: list[str] = []

    # --- pass 1: every edit must match exactly once, against the staged text
    # so that two edits to one file cannot silently overlap.
    for i, (rel, old, new) in enumerate(edits, 1):
        path = root / rel
        if path not in originals:
            if not path.exists():
                problems.append(f"edit {i}: {rel} does not exist")
                continue
            originals[path] = staged[path] = path.read_text(encoding="utf-8")
        n = staged[path].count(old)
        if n != 1:
            problems.append(
                f"edit {i}: {rel}: pattern matches {n} times, need exactly 1"
                f"  ->  {old.strip()[:60]!r}")
            continue
        staged[path] = staged[path].replace(old, new)

    if problems:
        if not quiet:
            print("NOT APPLIED -- the batch is atomic, so nothing was written:")
            for p in problems:
                print("  -", p)
        return 1

    # --- pass 2: write, then read back and confirm
    for path, text in staged.items():
        io.open(path, "w", encoding="utf-8").write(text)

    failures: list[str] = []
    for i, (rel, old, new) in enumerate(edits, 1):
        after = (root / rel).read_text(encoding="utf-8")
        if new not in after:
            failures.append(f"edit {i}: {rel}: replacement text is absent after writing")
        elif old in after and old not in new:
            failures.append(f"edit {i}: {rel}: original text still present after writing")
        elif not quiet:
            print(f"  ok  edit {i}: {rel}: {new.strip()[:64]!r}")

    if failures:
        # roll back rather than leave a partly-edited tree
        for path, text in originals.items():
            io.open(path, "w", encoding="utf-8").write(text)
        if not quiet:
            print("VERIFICATION FAILED after writing; rolled back:")
            for f in failures:
                print("  -", f)
        return 1

    if not quiet:
        print(f"applied and verified {len(edits)} edit(s) across "
              f"{len(staged)} file(s)")
    return 0


if __name__ == "__main__":
    print(__doc__)
    sys.exit(0)

#!/bin/sh
# Build the anonymised supplementary archive for review.
#
# The working tree carries a .git directory whose config and history name the
# authors, and the paper repository likewise. Neither may go to reviewers. This
# exports the tracked files only (so nothing .gitignored, no checkpoints, no
# corpora, no .git), then greps the export for identifying strings and refuses
# to package it if any survive.
#
# The identifying strings are NOT written in this file, which is itself
# tracked and exported. They come from an untracked file, infra/identity.txt
# (one extended-regex alternative per line; listed in .gitignore), or from the
# SUPPLEMENT_IDENTITY environment variable. The script refuses to run without
# one of them, so an unchecked export is impossible by construction.
#
#   sh infra/make_supplement.sh            # writes supplement.zip next to the repo
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/../supplement.zip}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ -n "${SUPPLEMENT_IDENTITY:-}" ]; then
  PATTERN="$SUPPLEMENT_IDENTITY"
elif [ -f "$ROOT/infra/identity.txt" ]; then
  PATTERN="$(grep -v '^#' "$ROOT/infra/identity.txt" | grep -v '^$' | paste -sd '|' -)"
else
  echo "no identity patterns: create infra/identity.txt (untracked) or set SUPPLEMENT_IDENTITY" >&2
  exit 1
fi

cd "$ROOT"
git archive --format=tar --prefix=code/ HEAD | tar -x -C "$TMP"
# The registration document lives in the paper repository; ship a copy so the
# pre-registration is checkable from the supplement alone.
[ -f "$ROOT/PREDICTIONS.md" ] || echo "warning: PREDICTIONS.md not in repo" >&2

if grep -rniE "$PATTERN" "$TMP/code" >/dev/null; then
  echo "identifying strings found in the export; not packaging:" >&2
  grep -rniE "$PATTERN" "$TMP/code" | cut -c1-160 | head -20 >&2
  exit 1
fi
if [ -d "$TMP/code/.git" ]; then
  echo ".git survived the export; not packaging" >&2
  exit 1
fi
(cd "$TMP" && zip -qr "$OUT" code)
echo "wrote $OUT ($(du -h "$OUT" | cut -f1)); no .git, no identifying strings"

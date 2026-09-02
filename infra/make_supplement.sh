#!/bin/sh
# Build the anonymised supplementary archive for review.
#
# The working tree carries a .git directory whose config and history name the
# authors, and the paper repository likewise. Neither may go to reviewers. This
# exports the tracked files only (so nothing .gitignored, no checkpoints, no
# corpora, no .git), then greps the export for identifying strings and refuses
# to package it if any survive.
#
#   sh infra/make_supplement.sh            # writes supplement.zip next to the repo
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/../supplement.zip}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cd "$ROOT"
git archive --format=tar --prefix=code/ HEAD | tar -x -C "$TMP"
rm -f "$TMP/code/infra/detached.sh.local" 2>/dev/null || true

# Names, handles and hosts that identify the authors. Extend before use.
PATTERN='shivam|chauhan|MBZUAI|mbzuai|0shivam33|github.com/shivam|claude\.ai'
if grep -rniE "$PATTERN" "$TMP/code" >/dev/null; then
  echo "identifying strings found in the export; not packaging:" >&2
  grep -rniE "$PATTERN" "$TMP/code" | head -20 >&2
  exit 1
fi
if [ -d "$TMP/code/.git" ]; then
  echo ".git survived the export; not packaging" >&2
  exit 1
fi
(cd "$TMP" && zip -qr "$OUT" code)
echo "wrote $OUT ($(du -h "$OUT" | cut -f1)); no .git, no identifying strings"

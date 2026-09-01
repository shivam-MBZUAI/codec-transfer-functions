"""Load FLEURS test audio from the HuggingFace dataset cache.

Reads the per-language tar.gz and tsv directly rather than through the datasets
library, whose FLEURS loader format has changed across versions.

A caveat that belongs in the paper: FLEURS is parallel by TRANSLATION, not by
identical content. It is built from FLoRes sentences read aloud, so languages
share meaning, not words, phonemes, syllable counts or duration. Any claim that
it "fixes lexical content by construction" is wrong. It controls semantic
content and speaking register; it cannot control phonetic content.
"""

from __future__ import annotations

import csv
import io
import tarfile
from functools import lru_cache
from pathlib import Path

import numpy as np

HF = Path("/workspace/.hf/hub/datasets--google--fleurs")


@lru_cache(maxsize=1)
def _snapshot() -> Path:
    snaps = sorted((HF / "snapshots").glob("*"))
    if not snaps:
        raise SystemExit(f"no FLEURS snapshot under {HF}")
    return snaps[-1]


def metadata(lang: str) -> dict[str, dict]:
    """filename -> row. FLEURS tsv is headerless; columns vary in count but the
    first is an id, the second the filename, and gender is the last field."""
    tsv = _snapshot() / "data" / lang / "test.tsv"
    if not tsv.exists():
        return {}
    out = {}
    # QUOTE_NONE matters: transcriptions contain apostrophes and quotation
    # marks, and the default dialect silently merges fields around them, which
    # made every lookup miss.
    with tsv.open(encoding="utf-8") as fh:
        for parts in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
            if len(parts) < 3:
                continue
            out[parts[1]] = {
                "id": parts[0],
                "transcription": parts[3] if len(parts) > 3 else "",
                "gender": parts[-1],
            }
    return out


def utterances(lang: str, limit: int = 60):
    """Yield (name, audio float64, sample_rate, meta). FLEURS audio is 16 kHz."""
    import soundfile as sf

    tar = _snapshot() / "data" / lang / "audio" / "test.tar.gz"
    if not tar.exists():
        return
    meta = metadata(lang)
    n = 0
    with tarfile.open(tar) as tf:
        for m in tf:
            if n >= limit:
                break
            if not m.name.endswith(".wav"):
                continue
            fh = tf.extractfile(m)
            if fh is None:
                continue
            try:
                x, sr = sf.read(io.BytesIO(fh.read()), dtype="float64",
                                always_2d=False)
            except Exception:
                continue
            if x.ndim > 1:
                x = x.mean(axis=1)
            if len(x) < sr:            # skip very short clips
                continue
            base = Path(m.name).name
            yield base, x, sr, meta.get(base, {})
            n += 1

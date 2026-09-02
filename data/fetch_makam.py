"""Fetch the open Turkish makam datasets from Zenodo.

These need no access request, unlike the Dunya-mediated CompMusic audio.

They are small, which means they almost certainly carry annotations rather than
recordings. That still solves half the problem. The paper's makam scale-degree
offsets are currently taken from Arel-Ezgi-Uzdilek comma tables, which put Segah
15 cents below the grid and Evc 13 cents below, not the 45 and 43 the draft
uses. Performance practice sits considerably flatter than AEU theory, and a
measured pitch distribution is the defensible source for those offsets. If these
archives contain per-makam pitch histograms, the offsets can be fixed without
any audio at all.

What they cannot do is supply audio to push through a codec. That still needs
Dunya, or the instrument-retuning route in E3.2.
"""

from __future__ import annotations

import os
import sys
import urllib.request
import zipfile

ROOT = os.environ.get("CODECS_ROOT", ".")
DEST = os.path.join(ROOT, "data", "makam")

RECORDS = [
    (4883680, "MTG/otmm_makam_recognition_dataset-dlfm2016-fix1.zip",
     "OTMM makam recognition dataset: pitch distributions and tonic annotations"),
    (1284501, "turkish_makam_music_audio-score_alignment_1.0.zip",
     "Turkish makam audio-score alignment dataset"),
]


def main() -> int:
    os.makedirs(DEST, exist_ok=True)
    ok = []
    for rid, key, why in RECORDS:
        url = f"https://zenodo.org/records/{rid}/files/{key}?download=1"
        out = os.path.join(DEST, os.path.basename(key))
        print(f"--- zenodo {rid}\n    {why}", flush=True)
        try:
            if not (os.path.exists(out) and os.path.getsize(out) > 1_000_000):
                urllib.request.urlretrieve(url, out)
            sz = os.path.getsize(out)
            if sz < 1_000_000:
                raise RuntimeError(f"suspiciously small: {sz} bytes")
            print(f"    OK  {sz/1e6:.0f} MB", flush=True)
            with zipfile.ZipFile(out) as z:
                names = z.namelist()
                audio = [n for n in names
                         if n.lower().endswith((".mp3", ".wav", ".flac", ".m4a"))]
                print(f"    {len(names)} entries, {len(audio)} audio files")
                for n in names[:8]:
                    print(f"      {n}")
            print(flush=True)
            ok.append(rid)
        except Exception as e:
            print(f"    FAILED  {type(e).__name__}: "
                  f"{str(e).split(chr(10))[0][:150]}\n", flush=True)
    return 0 if len(ok) == len(RECORDS) else 1


if __name__ == "__main__":
    sys.exit(main())

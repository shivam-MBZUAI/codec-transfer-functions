"""Fetch bounded corpus samples for estimating the training pitch density.

Proposition 1 predicts the residual from p(theta), the pitch density of the
codec's training audio. No released codec publishes that audio, which is why the
draft treats the proposition as qualitative. But the training corpora are
*named* even where the mixtures are not, and F0 histograms converge on a few
thousand clips, so a bounded sample is enough to estimate p.

  LibriSpeech  SpeechTokenizer's ENTIRE training set. This is the clean case:
               p is knowable exactly, and speech F0 is smooth rather than
               grid-peaked, so the proposition predicts NO 12-TET structure.
               That turns the negative control into a quantitative prediction.

  GTZAN        Western popular music across genres. Stands in for the music
               fraction of EnCodec's and DAC's training mixtures, and is the
               comparison target for recovering a codec's implied pitch prior
               from its codebook.

  MusicGen     for the appendix test of whether the loss propagates into
               generated music.

Samples only. LibriSpeech complete is ~60 GB and is not needed for a histogram.
"""

from __future__ import annotations

import os
import sys

from huggingface_hub import snapshot_download

PAYLOAD_EXT = (".parquet", ".tar.gz", ".tar", ".safetensors", ".bin", ".pt", ".zip")

TARGETS = [
    ("openslr/librispeech_asr", "dataset", ["clean/validation/*"],
     "LibriSpeech dev-clean: SpeechTokenizer's training distribution, p known"),
    ("marsyas/gtzan", "dataset", None,
     "GTZAN: Western music, grid-peaked F0 reference"),
    ("facebook/musicgen-small", "model",
     ["*.safetensors", "*.json", "*.txt", "*.model"],
     "MusicGen small: codec-token music model for the propagation test"),
]


def main() -> int:
    ok, failed = [], []
    for repo, rtype, patterns, why in TARGETS:
        print(f"--- {repo}\n    {why}", flush=True)
        try:
            kw = {"repo_id": repo, "repo_type": rtype}
            if patterns:
                kw["allow_patterns"] = patterns
            path = snapshot_download(**kw)
            files, sz = [], 0
            for r, _, fs in os.walk(path):
                for f in fs:
                    sz += os.path.getsize(os.path.realpath(os.path.join(r, f)))
                    if f.endswith(PAYLOAD_EXT):
                        files.append(f)
            if not files:
                raise RuntimeError("no payload files matched")
            print(f"    OK  {sz/1e6:.0f} MB, {len(files)} payload file(s)\n",
                  flush=True)
            ok.append(repo)
        except Exception as e:
            print(f"    FAILED  {type(e).__name__}: "
                  f"{str(e).split(chr(10))[0][:150]}\n", flush=True)
            failed.append(repo)

    print("=" * 62)
    for r in ok:
        print(f"  ok    {r}")
    for r in failed:
        print(f"  FAIL  {r}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

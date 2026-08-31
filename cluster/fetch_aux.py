"""Fetch the forced aligner and instrument samples, via HuggingFace only.

Both of these have canonical homes this cluster cannot reach. The aligner's
weights live on dl.fbaipublicfiles.com, which the proxy answers with 403, and
NSynth's canonical home is a Google Storage bucket. HuggingFace is reachable,
and both are mirrored there, so everything goes through snapshot_download.

The aligner locates contrast-bearing regions so error is computed over those
rather than over whole utterances, which would dilute a localised effect toward
zero.

Instrument samples are the unblocked route to ecological validity: real
recordings pitch-shifted off-grid answer the "synthetic stimuli do not
transfer" objection without needing the access-restricted makam corpus.
"""

from __future__ import annotations

import os
import sys

from huggingface_hub import snapshot_download

WEIGHT_EXT = (".safetensors", ".pt", ".ckpt", ".bin", ".tar.gz", ".parquet")

TARGETS = [
    # (repo, repo_type, allow_patterns, label)
    ("MahmoudAshraf/mms-300m-1130-forced-aligner", "model",
     ["*.safetensors", "*.json", "*.txt", "*.model"],
     "MMS forced aligner (mirror; fbaipublicfiles is 403 through the proxy)"),
    ("confit/nsynth", "dataset",
     ["nsynth-test.jsonwav.tar.gz"],
     "NSynth test split, 350 MB (mirror; canonical home is a GCS bucket)"),
]


def main() -> int:
    ok, failed = [], []
    for repo, rtype, patterns, label in TARGETS:
        print(f"--- {repo}\n    {label}", flush=True)
        try:
            path = snapshot_download(repo_id=repo, repo_type=rtype,
                                     allow_patterns=patterns)
            files, sz = [], 0
            for r, _, fs in os.walk(path):
                for f in fs:
                    sz += os.path.getsize(os.path.realpath(os.path.join(r, f)))
                    if f.endswith(WEIGHT_EXT):
                        files.append(f)
            # snapshot_download returns success when allow_patterns matched
            # nothing, so an empty result must be an error, not a pass.
            if not files:
                raise RuntimeError("no payload files matched the patterns")
            print(f"    OK  {sz/1e6:.0f} MB, {len(files)} file(s)\n", flush=True)
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

"""Fetch every model this project can use, reporting what is unreachable.

Run on a LOGIN node: outbound traffic goes through a proxy only login shells
export. Failures are reported rather than raised, because part of the point is
to find out what this cluster's egress blocks.

Downloads files only, never instantiates a model, so it stays light enough for
a login node.
"""

from __future__ import annotations

import os
import sys

from huggingface_hub import snapshot_download

# .ckpt matters: WavTokenizer ships checkpoints under that extension, and
# omitting it makes snapshot_download "succeed" having downloaded nothing.
WEIGHTS = ["*.safetensors", "*.pt", "*.ckpt", "*.bin", "*.json", "*.txt",
           "*.model", "*.yaml"]
WEIGHT_EXT = (".safetensors", ".pt", ".ckpt", ".bin")
# Whisper and MMS repos carry several formats of the same weights. Pulling one
# format is the difference between ~3 GB and ~18 GB.
ONE_FORMAT = ["*.safetensors", "*.json", "*.txt", "*.model"]

MANIFEST = [
    # (repo, allow_patterns, why, tier)
    ("openai/whisper-large-v3", ONE_FORMAT, "ASR for downstream WER", "T3"),
    ("facebook/mms-1b-all", ONE_FORMAT, "second ASR; a disparity under one but not the other implicates the recogniser", "T3"),
    # Extra codecs for the breadth claim. Repo ids are uncertain for several of
    # these, so failure here is expected and informative rather than fatal.
    ("hubertsiuzdak/snac_24khz", WEIGHTS, "SNAC 24k, extra codec", "T2"),
    ("hubertsiuzdak/snac_32khz", WEIGHTS, "SNAC 32k, extra codec", "T2"),
    ("hubertsiuzdak/snac_44khz", WEIGHTS, "SNAC 44k, extra codec", "T2"),
    ("novateur/WavTokenizer", WEIGHTS, "WavTokenizer, cited in related work", "T2"),
    ("novateur/WavTokenizer-large-unify-40token", WEIGHTS, "WavTokenizer large", "T2"),
    ("novateur/WavTokenizer-large-speech-75token", WEIGHTS, "WavTokenizer large speech", "T2"),
    ("HKUSTAudio/xcodec2", WEIGHTS, "X-Codec 2.0, extra codec", "T2"),
    ("Alethia/BigCodec", WEIGHTS, "BigCodec, cited in related work", "T2"),
]


def main() -> int:
    print(f"cache: {os.environ.get('HF_HUB_CACHE', '<unset>')}\n")
    ok, failed = [], []
    for repo, patterns, why, tier in MANIFEST:
        print(f"--- [{tier}] {repo}\n    {why}", flush=True)
        try:
            p = snapshot_download(repo_id=repo, allow_patterns=patterns)
            # snapshot_download returns success when allow_patterns matched
            # NOTHING, so "ok" on its own is not evidence that weights arrived.
            # Follow symlinks: the HF cache stores blobs and links snapshots to
            # them, so a naive walk that skips links reports 0 bytes for a
            # complete download.
            weights, sz = [], 0
            for r, _, fs in os.walk(p):
                for f in fs:
                    full = os.path.join(r, f)
                    sz += os.path.getsize(os.path.realpath(full))
                    if f.endswith(WEIGHT_EXT):
                        weights.append(f)
            if not weights:
                raise RuntimeError(
                    f"no weight files matched; repo may use another extension. "
                    f"patterns={patterns}")
            print(f"    OK  {sz/1e6:.0f} MB, {len(weights)} weight file(s)\n",
                  flush=True)
            ok.append(repo)
        except Exception as e:
            msg = str(e).split("\n")[0][:160]
            print(f"    FAILED  {type(e).__name__}: {msg}\n", flush=True)
            failed.append((repo, tier, type(e).__name__, msg))

    print("=" * 70)
    print(f"cached  {len(ok)}")
    for r in ok:
        print(f"  ok      {r}")
    print(f"failed  {len(failed)}")
    for r, tier, kind, msg in failed:
        print(f"  FAIL    [{tier}] {r}\n            {kind}: {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

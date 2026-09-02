"""Pre-fetch codec checkpoints into the shared HF cache.

Run on a LOGIN node: outbound traffic goes through a proxy that only login
shells export, and compute nodes may not share that egress. Once this has run,
jobs can set HF_HUB_OFFLINE=1 and never touch the network.

This only downloads files. It does not instantiate a model, so it stays light
enough for a login node under the no-heavy-processes policy.
"""

from __future__ import annotations

import os
import sys

from huggingface_hub import snapshot_download

# Weight formats only. These repos are small, but pulling every format would
# duplicate safetensors and bin for no benefit.
ALLOW = ["*.safetensors", "*.pt", "*.json", "*.txt", "*.model", "*.py"]

# Revision pins. Every result in the paper was produced against these commits;
# the last modification of each repo predates the runs, so the pin and the
# instrument coincide. codec_zoo.py passes the same pins to from_pretrained.
REVISIONS = {
    "facebook/encodec_24khz": "c1dbe2ae3f1de713481a3b3e7c47f357092ee040",
    "facebook/encodec_48khz": "c3def8e7185ac8c8efdce6eb8c4a651e487a503e",
    "descript/dac_16khz": "7c2fc5e759f1f501aefc6e7a0265cc57f5d17ba7",
    "descript/dac_24khz": "6ba020b5ba7d9d8076fb90db7e67f27e31980f6e",
    "descript/dac_44khz": "c1bc521685adf9cfe247bc39a5ca58917eda1ac4",
    "kyutai/mimi": "89091b3e466eb6a9d11e537bf26b144f194978f7",
    "fnlp/SpeechTokenizer": "4d54939beef00572fa7bfe41ee35a335c3732f51",
    "hubertsiuzdak/snac_24khz": "d73ad176a12188fcf4f360ba3bf2c2fbbe8f58ec",
    "hubertsiuzdak/snac_32khz": "c84c6ac842dc7a44a6fb0f3b576ce94b48a7780f",
    "hubertsiuzdak/snac_44khz": "873ebef9718b89660340c6f55a2b515e98cfa1d9",
}

REPOS = [
    ("facebook/encodec_24khz", "EnCodec 24 kHz, the workhorse, 1.5-24 kbps"),
    ("facebook/encodec_48khz", "EnCodec 48 kHz, the MUSIC-trained checkpoint"),
    ("descript/dac_44khz", "DAC 44.1 kHz, highest fidelity, tops out near 8 kbps"),
    ("descript/dac_24khz", "DAC 24 kHz, the one that actually reaches 24 kbps"),
    ("descript/dac_16khz", "DAC 16 kHz, third frame-rate point for the C3 fit"),
    ("kyutai/mimi", "Mimi, 12.5 Hz frames, extreme low rate"),
    # SpeechTokenizer ships a .pt rather than safetensors, and it is the
    # scientifically important one: trained on LibriSpeech alone, it saw no
    # music at all, so under the training-distribution hypothesis it is the
    # negative control that should show no 12-TET structure.
    ("fnlp/SpeechTokenizer", "SpeechTokenizer, LibriSpeech only, NO MUSIC: the negative control"),
    # SNAC: multi-scale RVQ, each quantiser level at its own frame rate. Loaded
    # through the `snac` package, which pulls from these repos.
    ("hubertsiuzdak/snac_24khz", "SNAC 24 kHz, 0.98 kbps, three levels at 12/23/47 Hz"),
    ("hubertsiuzdak/snac_32khz", "SNAC 32 kHz, 1.9 kbps, four levels at 10/21/42/83 Hz"),
    ("hubertsiuzdak/snac_44khz", "SNAC 44.1 kHz, 2.6 kbps, four levels at 14/29/57/115 Hz"),
]


def main() -> int:
    cache = os.environ.get("HF_HUB_CACHE", "<unset>")
    print(f"cache: {cache}\n")
    failed = []
    for repo, why in REPOS:
        print(f"--- {repo}\n    {why}", flush=True)
        try:
            path = snapshot_download(repo_id=repo, allow_patterns=ALLOW,
                                     revision=REVISIONS.get(repo))
            n = sum(len(f) for _, _, f in os.walk(path))
            print(f"    ok, {n} files\n", flush=True)
        except Exception as e:
            print(f"    FAILED {type(e).__name__}: {e}\n", flush=True)
            failed.append(repo)

    if failed:
        print(f"FAILED: {failed}")
        return 1
    print("all checkpoints cached")
    return 0


if __name__ == "__main__":
    sys.exit(main())

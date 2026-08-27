"""Fetch FLEURS test splits for the languages this project needs.

Pulls from the dataset repo directly rather than through the `datasets`
library: FLEURS has changed loader format across `datasets` versions, and
snapshot_download with explicit patterns is stable and resumable.

Test split only. The full FLEURS is ~12 hours per language; the test split is
enough for a pilot and for per-language error bars, and pulling 23 full
languages before the analysis plan is settled is wasted bandwidth.

IMPORTANT, unresolved science: the contrast groups below are the paper's
current mapping and at least one of them is wrong. Modern Israeli Hebrew has
largely lost the pharyngeals for most speakers, Amharic lost the Ge'ez
pharyngeals and belongs in the ejective group only, and Maltese <gh> is
generally silent or realised as vowel lengthening. Downloading them costs
nothing and keeps the option open, but the pharyngealisation group must be
fixed before any number derived from it goes in the paper.
"""

from __future__ import annotations

import os
import sys

from huggingface_hub import snapshot_download

REPO = "google/fleurs"

GROUPS = {
    "tone": ["vi_vn", "th_th", "yue_hant_hk", "cmn_hans_cn", "yo_ng", "ig_ng"],
    "pharyngeal_emphatic": ["ar_eg", "he_il", "mt_mt"],   # see docstring
    "ejective": ["am_et", "ka_ge", "om_et"],
    "click": ["zu_za", "xh_za"],
    "control_nontonal": ["en_us", "fr_fr", "de_de", "es_419", "it_it",
                          "pt_br", "pl_pl", "nl_nl", "cs_cz"],
}


def main() -> int:
    langs = sorted({l for v in GROUPS.values() for l in v})
    print(f"cache: {os.environ.get('HF_HOME', '<unset>')}")
    print(f"{len(langs)} languages (note: Amharic appears in one group only here, "
          f"so this is 23 unique, not the 24 the draft claims)\n")

    ok, failed = [], []
    for group, members in GROUPS.items():
        print(f"=== {group}")
        for lang in members:
            try:
                snapshot_download(
                    repo_id=REPO, repo_type="dataset",
                    allow_patterns=[f"data/{lang}/test.tsv",
                                    f"data/{lang}/audio/test.tar.gz"],
                )
                print(f"    OK      {lang}", flush=True)
                ok.append(lang)
            except Exception as e:
                msg = str(e).split("\n")[0][:140]
                print(f"    FAILED  {lang}  {type(e).__name__}: {msg}", flush=True)
                failed.append((lang, type(e).__name__, msg))
        print()

    print("=" * 70)
    print(f"ok {len(ok)} / failed {len(failed)}")
    for lang, kind, msg in failed:
        print(f"  FAIL  {lang}  {kind}: {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

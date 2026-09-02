import sys, os
sys.path.insert(0, "experiments")
from huggingface_hub import snapshot_download
from languages import all_languages
langs = all_languages()
print(f"{len(langs)} languages", flush=True)
ok, bad = [], []
for i, l in enumerate(langs):
    try:
        p = snapshot_download(repo_id="google/fleurs", repo_type="dataset",
                              allow_patterns=[f"data/{l}/test.tsv",
                                              f"data/{l}/audio/test.tar.gz"])
        tar = os.path.join(p, "data", l, "audio", "test.tar.gz")
        if not os.path.exists(tar):
            raise RuntimeError("archive absent after download")
        print(f"  [{i+1}/{len(langs)}] {l}  {os.path.getsize(os.path.realpath(tar))/1e6:.0f} MB", flush=True)
        ok.append(l)
    except Exception as e:
        print(f"  [{i+1}/{len(langs)}] {l}  FAILED {type(e).__name__}: {str(e)[:80]}", flush=True)
        bad.append(l)
print(f"ok {len(ok)}  failed {len(bad)} {bad}")

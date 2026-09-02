import glob, os, tarfile
from huggingface_hub import snapshot_download
p = snapshot_download(repo_id="confit/nsynth", repo_type="dataset",
                      allow_patterns=["nsynth-test.jsonwav.tar.gz"])
out = "/workspace/corpora/nsynth"; os.makedirs(out, exist_ok=True)
for t in glob.glob(os.path.join(p, "**", "*.tar.gz"), recursive=True):
    with tarfile.open(t) as tf:
        m = [x for x in tf.getmembers() if x.name.endswith(".wav")][:300]
        tf.extractall(out, members=m)
        print(f"extracted {len(m)} notes")

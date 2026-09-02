"""Pull the corpus samples needed for the training-density histograms."""
import os, tarfile, glob
from huggingface_hub import snapshot_download

dest = "/workspace/corpora"
os.makedirs(dest, exist_ok=True)

for repo, patterns, name in [
    ("marsyas/gtzan", None, "gtzan"),
    ("openslr/librispeech_asr", ["clean/validation/*"], "librispeech"),
]:
    print(f"--- {repo}", flush=True)
    p = snapshot_download(repo_id=repo, repo_type="dataset",
                          allow_patterns=patterns)
    print(f"    at {p}", flush=True)
    out = os.path.join(dest, name)
    os.makedirs(out, exist_ok=True)
    n = 0
    for tgz in glob.glob(os.path.join(p, "**", "*.tar.gz"), recursive=True):
        with tarfile.open(tgz) as t:
            members = [m for m in t.getmembers()
                       if m.name.lower().endswith((".wav", ".flac", ".au", ".mp3"))][:400]
            t.extractall(out, members=members)
            n += len(members)
    print(f"    extracted {n} audio files to {out}", flush=True)
    for ext in ("wav", "flac", "au", "mp3"):
        c = len(glob.glob(os.path.join(out, "**", f"*.{ext}"), recursive=True))
        if c: print(f"      {c} .{ext}")

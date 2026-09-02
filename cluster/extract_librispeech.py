"""LibriSpeech ships as parquet with embedded audio; decode a sample to flac."""
import glob, io, os
import pyarrow.parquet as pq
import soundfile as sf

out = "/workspace/corpora/librispeech"
os.makedirs(out, exist_ok=True)
files = glob.glob("/workspace/.hf/hub/datasets--openslr--librispeech_asr/snapshots/*/**/*.parquet", recursive=True)
print(f"{len(files)} parquet shards")
n = 0
for f in files:
    t = pq.read_table(f)
    col = next((c for c in t.column_names if "audio" in c.lower()), None)
    if col is None:
        print("  no audio column in", os.path.basename(f)); continue
    for rec in t.column(col).to_pylist():
        if n >= 400: break
        b = rec.get("bytes") if isinstance(rec, dict) else None
        if not b: continue
        try:
            x, sr = sf.read(io.BytesIO(b), dtype="float32")
            sf.write(os.path.join(out, f"ls_{n:04d}.flac"), x, sr)
            n += 1
        except Exception:
            pass
    if n >= 400: break
print(f"wrote {n} files to {out}")

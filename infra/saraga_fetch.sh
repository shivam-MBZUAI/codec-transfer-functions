#!/bin/bash
# Resumable Saraga Carnatic download (Zenodo record 4301737), unzip, corpus tests.
set -u
cd /workspace/codecs
mkdir -p corpora/saraga_carnatic
Z=corpora/saraga_carnatic/saraga1.5_carnatic.zip
for i in 1 2 3 4 5 6; do
  wget -c -q --tries=20 --retry-connrefused --timeout=60 \
    -O "$Z" "https://zenodo.org/record/4301737/files/saraga1.5_carnatic.zip?download=1" && break
  echo "retry $i"; sleep 30
done
ls -la "$Z"
unzip -q -o "$Z" -d corpora/saraga_carnatic && echo unzipped && find corpora/saraga_carnatic -name "*.mp3" | wc -l
for c in encodec:3 dac16:6 opus:12; do
  tag="corpus_pull_saraga_${c/:/}"
  python3 experiments/corpus_pull.py --audio-root corpora/saraga_carnatic --codec "$c" \
      --max-files 200 --out "results/${tag}.csv" > "logs/${tag}.log" 2>&1
  echo "== $c"; python3 analysis/analyze_corpus_pull.py "results/${tag}.csv"
done

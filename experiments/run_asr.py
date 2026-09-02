"""Experiment 3: does codec loss propagate to a downstream recogniser?

Transcribe FLEURS twice, once on the original audio and once after a codec round
trip, with the recogniser fixed and never fine-tuned so only the audio varies.
Report the RELATIVE increase in word error rate.

Relative rather than absolute is deliberate: tone-language baselines are already
high, so a comparison in WER points would conflate codec damage with baseline
difficulty and inflate the effect for any language the recogniser handles badly.

Whisper covers 17 of our 21 languages. Igbo, Oromo, Zulu and Xhosa are not in
its language set, which is precisely why a second recogniser matters: a
disparity visible under one system but not the other implicates the recogniser
rather than the codec. Those four are marked and left to MMS.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codec_zoo  # noqa: E402
from fleurs_data import utterances  # noqa: E402
from languages import EXPLORATORY, GROUPS, group_of  # noqa: E402

# FLEURS code -> Whisper language code. None means Whisper has no such language.
WHISPER_LANG = {
    "vi_vn": "vi", "th_th": "th", "yue_hant_hk": "yue", "cmn_hans_cn": "zh",
    "yo_ng": "yo", "ig_ng": None, "am_et": "am", "ka_ge": "ka", "om_et": None,
    "zu_za": None, "xh_za": None, "en_us": "en", "fr_fr": "fr", "de_de": "de",
    "es_419": "es", "it_it": "it", "pt_br": "pt", "pl_pl": "pl", "nl_nl": "nl",
    "cs_cz": "cs", "ar_eg": "ar",
}
# Languages without word boundaries: score by character, else WER is meaningless.
CHAR_LEVEL = {"th_th", "cmn_hans_cn", "yue_hant_hk"}


def normalise(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()


def error_rate(ref: str, hyp: str, char_level: bool) -> float:
    r = list(normalise(ref)) if char_level else normalise(ref).split()
    h = list(normalise(hyp)) if char_level else normalise(hyp).split()
    if not r:
        return float("nan")
    # Levenshtein
    prev = list(range(len(h) + 1))
    for i, rt in enumerate(r, 1):
        cur = [i] + [0] * len(h)
        for j, ht in enumerate(h, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rt != ht))
        prev = cur
    return prev[-1] / len(r)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--codec", default="encodec:3")
    p.add_argument("--model", default="openai/whisper-large-v3")
    p.add_argument("--per-language", type=int, default=25)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    import scipy.signal as sps
    import torch
    from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    proc = AutoProcessor.from_pretrained(args.model)
    asr = AutoModelForSpeechSeq2Seq.from_pretrained(
        args.model, dtype=torch.float16 if dev == "cuda" else torch.float32
    ).to(dev).eval()

    codec = codec_zoo.build(args.codec)
    csr = codec.sample_rate
    langs = [l for v in GROUPS.values() for l in v] + \
            [l for v in EXPLORATORY.values() for l in v]

    @torch.no_grad()
    def transcribe(x: np.ndarray, sr: int, lang: str) -> str:
        feats = proc(x, sampling_rate=sr, return_tensors="pt").input_features
        feats = feats.to(dev, dtype=asr.dtype)
        ids = asr.generate(feats, language=lang, task="transcribe",
                           max_new_tokens=200)
        return proc.batch_decode(ids, skip_special_tokens=True)[0]

    # Languages where the recogniser fails BEFORE any codec is applied cannot
    # measure codec damage: a baseline error rate near 1.0 leaves no headroom
    # and any "relative increase" is noise over noise. These are reported as
    # recogniser failures, not as codec results, and are exactly the case the
    # second recogniser exists for.
    BASELINE_FLOOR = 0.8

    rows = []
    for li, lang in enumerate(langs):
        wl = WHISPER_LANG.get(lang)
        if wl is None:
            print(f"  [{li+1}/{len(langs)}] {lang}: not in Whisper's language set, "
                  f"skipped (needs MMS)", flush=True)
            continue
        n = 0
        for name, x, sr, meta in utterances(lang, limit=args.per_language):
            ref = meta.get("transcription", "")
            if not ref.strip():
                continue
            # Normalise level before coding. FLEURS utterance levels span a
            # factor of ~100 (RMS 0.0008 to 0.08). A codec at 3 kbps cannot
            # represent near-silent input, and Whisper then emits its
            # silence hallucination ("Thank you."), which reads as catastrophic
            # codec damage when it is really an out-of-distribution input level.
            # Both conditions use the SAME normalised signal so the comparison
            # is of the codec and nothing else.
            peak = float(np.abs(x).max())
            if peak < 1e-6:
                continue
            xn = x / peak * 0.7
            y = sps.resample_poly(xn, csr, sr) if sr != csr else xn
            back = codec(y)
            back = sps.resample_poly(back, sr, csr) if sr != csr else back
            try:
                h_orig = transcribe(xn, sr, wl)
                h_code = transcribe(back[: len(xn)], sr, wl)
            except Exception as e:
                print(f"      {name}: {type(e).__name__}", flush=True)
                continue
            cl = lang in CHAR_LEVEL
            e0 = error_rate(ref, h_orig, cl)
            e1 = error_rate(ref, h_code, cl)
            rows.append(dict(lang=lang, group=group_of(lang) or "exploratory",
                             file=name, char_level=int(cl),
                             wer_original=e0, wer_coded=e1,
                             delta=e1 - e0,
                             relative=(e1 - e0) / e0 if e0 > 0 else float("nan")))
            n += 1
        done = [r for r in rows if r["lang"] == lang]
        m0 = np.nanmedian([r["wer_original"] for r in done]) if done else float("nan")
        m1 = np.nanmedian([r["wer_coded"] for r in done]) if done else float("nan")
        note = ""
        if np.isfinite(m0) and m0 >= BASELINE_FLOOR:
            note = "   RECOGNISER FAILS ON THIS LANGUAGE (baseline near 1.0)"
            for r in done:
                r["recogniser_failed"] = 1
        for r in done:
            r.setdefault("recogniser_failed", 0)
        print(f"  [{li+1}/{len(langs)}] {lang}: n={n}  ER {m0:.3f} -> {m1:.3f}{note}",
              flush=True)

    if not rows:
        raise SystemExit("no measurements")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {args.out} ({len(rows)} utterances)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

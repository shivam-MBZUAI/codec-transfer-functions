"""Experiment 3, second recogniser: MMS.

The draft promises this control and it is load-bearing now that the Whisper
result is a null: a disparity visible under one recogniser but not the other
implicates the recogniser rather than the codec. There is direct reason to
suspect Whisper here. It failed outright on Amharic, Georgian and Yoruba, with
baseline error rates of 1.0 before any codec was applied, and it has no language
setting at all for Igbo, Oromo, Zulu or Xhosa, which removes four of the click
and ejective languages from the design.

MMS covers over a thousand languages through per-language adapters, so it can
measure every language in our set. It is a CTC model rather than a
sequence-to-sequence one, which also means it does not hallucinate fluent text
on degraded input, the failure mode that corrupted the first Whisper run.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import codec_zoo  # noqa: E402
from fleurs_data import utterances  # noqa: E402
from languages import EXPLORATORY, GROUPS, group_of  # noqa: E402
from run_asr import CHAR_LEVEL, error_rate  # noqa: E402

# FLEURS code -> MMS adapter (ISO 639-3).
MMS_LANG = {
    "vi_vn": "vie", "th_th": "tha", "yue_hant_hk": "yue", "cmn_hans_cn": "cmn",
    "yo_ng": "yor", "ig_ng": "ibo", "am_et": "amh", "ka_ge": "kat",
    "om_et": "gaz", "zu_za": "zul", "xh_za": "xho", "en_us": "eng",
    "fr_fr": "fra", "de_de": "deu", "es_419": "spa", "it_it": "ita",
    "pt_br": "por", "pl_pl": "pol", "nl_nl": "nld", "cs_cz": "ces",
    "ar_eg": "ara",
}
BASELINE_FLOOR = 0.8


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--codec", default="encodec:3")
    p.add_argument("--model", default="facebook/mms-1b-all")
    p.add_argument("--per-language", type=int, default=30)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    import scipy.signal as sps
    import torch
    from transformers import AutoProcessor, Wav2Vec2ForCTC

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    proc = AutoProcessor.from_pretrained(args.model)
    asr = Wav2Vec2ForCTC.from_pretrained(args.model).to(dev).eval()

    codec = codec_zoo.build(args.codec)
    csr = codec.sample_rate
    langs = [l for v in GROUPS.values() for l in v] + \
            [l for v in EXPLORATORY.values() for l in v]

    @torch.no_grad()
    def transcribe(x: np.ndarray, sr: int) -> str:
        # MMS expects 16 kHz, which is FLEURS's native rate.
        inp = proc(x, sampling_rate=sr, return_tensors="pt")
        logits = asr(inp.input_values.to(dev)).logits
        return proc.batch_decode(logits.argmax(dim=-1).cpu().numpy())[0]

    rows = []
    for li, lang in enumerate(langs):
        adapter = MMS_LANG.get(lang)
        if adapter is None:
            print(f"  [{li+1}/{len(langs)}] {lang}: no adapter mapping", flush=True)
            continue
        try:
            proc.tokenizer.set_target_lang(adapter)
            asr.load_adapter(adapter)
        except Exception as e:
            print(f"  [{li+1}/{len(langs)}] {lang}: adapter '{adapter}' unavailable "
                  f"({type(e).__name__})", flush=True)
            continue

        n = 0
        for name, x, sr, meta in utterances(lang, limit=args.per_language):
            ref = meta.get("transcription", "")
            if not ref.strip():
                continue
            peak = float(np.abs(x).max())
            if peak < 1e-6:
                continue
            # Same level normalisation as the Whisper run: FLEURS levels span a
            # factor of ~100 and a codec cannot represent near-silent input.
            xn = x / peak * 0.7
            y = sps.resample_poly(xn, csr, sr) if sr != csr else xn
            back = codec(y)
            back = sps.resample_poly(back, sr, csr) if sr != csr else back
            try:
                h0, h1 = transcribe(xn, sr), transcribe(back[: len(xn)], sr)
            except Exception as e:
                print(f"      {name}: {type(e).__name__}", flush=True)
                continue
            cl = lang in CHAR_LEVEL
            e0, e1 = error_rate(ref, h0, cl), error_rate(ref, h1, cl)
            rows.append(dict(lang=lang, group=group_of(lang) or "exploratory",
                             file=name, char_level=int(cl),
                             wer_original=e0, wer_coded=e1, delta=e1 - e0,
                             relative=(e1 - e0) / e0 if e0 > 0 else float("nan"),
                             recogniser_failed=0))
            n += 1

        done = [r for r in rows if r["lang"] == lang]
        m0 = np.nanmedian([r["wer_original"] for r in done]) if done else float("nan")
        m1 = np.nanmedian([r["wer_coded"] for r in done]) if done else float("nan")
        note = ""
        if np.isfinite(m0) and m0 >= BASELINE_FLOOR:
            note = "   RECOGNISER FAILS ON THIS LANGUAGE"
            for r in done:
                r["recogniser_failed"] = 1
        print(f"  [{li+1}/{len(langs)}] {lang} ({adapter}): n={n}  "
              f"ER {m0:.3f} -> {m1:.3f}{note}", flush=True)

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

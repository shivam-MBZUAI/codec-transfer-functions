"""Prose sentence lengths in the main text, measured on the source.

Measuring on the extracted PDF merges captions, table cells and equation
text into the running prose and inflates every count, so this reads the
section sources, strips floats, captions, equations and macros, and reports
what is left. Presentation reviews have twice named sentence length as the
main text's largest remaining defect; this is how that gets tracked.

    python analysis/sentence_density.py [--top N]
"""
import re
import statistics
import sys
from pathlib import Path

SECTIONS = ["01_intro", "02_related", "03_method", "04_pitch", "05_phonology",
            "07_discussion"]
ROOT = Path(__file__).resolve().parents[2]


def prose(text):
    text = re.sub(r"\\begin\{(figure|table|tabular|equation|align|center)\*?\}"
                  r".*?\\end\{\1\*?\}", " ", text, flags=re.S)
    text = re.sub(r"%.*", " ", text)
    text = re.sub(r"\$[^$]*\$", "X", text)
    text = re.sub(r"\\(cite[tp]?|ref|label|input)\{[^}]*\}", "", text)
    text = re.sub(r"\\(section|subsection|paragraph)\{[^}]*\}", " . ", text)
    text = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\{?\}?", " ", text)
    text = text.replace("---", " ").replace("~", " ")
    return re.sub(r"\s+", " ", text)


def main() -> int:
    top = 12
    if "--top" in sys.argv:
        top = int(sys.argv[sys.argv.index("--top") + 1])
    found = []
    for name in SECTIONS:
        p = ROOT / "sections" / f"{name}.tex"
        if not p.exists():
            continue
        for s in re.split(r"(?<=[.!?]) +(?=[A-Z(])", prose(p.read_text())):
            n = len(s.split())
            if n > 4:
                found.append((n, name, s.strip()))
    lens = [f[0] for f in found]
    print(f"{len(lens)} sentences   median {statistics.median(lens):.0f}   "
          f"mean {statistics.mean(lens):.1f}   over 40 words: "
          f"{sum(1 for l in lens if l > 40)}   over 50: "
          f"{sum(1 for l in lens if l > 50)}")
    print(f"\nlongest {top}:")
    for n, name, s in sorted(found, reverse=True)[:top]:
        print(f"\n[{n}w  {name}] {s[:230]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

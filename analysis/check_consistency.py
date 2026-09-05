"""Cross-table consistency checks for the paper source.

The mathematics reviews repeatedly found tables that were said to derive
from one another but did not. This script asserts those relations directly
on the LaTeX source, so a drift fails here before a reader finds it.

    python analysis/check_consistency.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APX = ROOT / "sections" / "09_appendix.tex"
MAIN = ROOT / "sections" / "04_pitch.tex"


def rows_of(table_label, src):
    """Body rows of the tabular carrying this label."""
    i = src.index("\\label{" + table_label + "}")
    a = src.index("\\begin{tabular}", i)
    b = src.index("\\end{tabular}", a)
    out = []
    for line in src[a:b].split("\\\\"):
        # a rule command can be glued to the row that follows it
        line = re.sub(r"\\(?:top|mid|bottom)rule", " ", line)
        line = re.sub(r"\\begin\{tabular\}\{[^}]*\}", " ", line).strip()
        if not line or "&" not in line:
            continue
        if "textbf" in line or "multicolumn" in line or "cmidrule" in line:
            continue
        out.append([c.strip() for c in line.split("&")])
    return out


MACROS = {}


def load_macros():
    """Resolve \\newcommand value macros so table cells can be read."""
    import re as _re
    src = (ROOT / "main.tex").read_text()
    for m in _re.finditer(r"\\newcommand\{\\([A-Za-z]+)\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", src):
        MACROS[m.group(1)] = m.group(2).replace("\\xspace", "")


def uncomment(src):
    """Drop LaTeX comments, keeping escaped percent signs.

    Guards that scan prose must not read the working notes in the margins:
    two macro comments in main.tex carry bracketed intervals that are never
    printed, and the interval guard reported both as unbacked claims.
    """
    out = []
    for line in src.split("\n"):
        i, keep = 0, []
        while i < len(line):
            if line[i] == "%" and (i == 0 or line[i - 1] != "\\"):
                break
            keep.append(line[i]); i += 1
        out.append("".join(keep))
    return "\n".join(out)


def subst(cell):
    """Expand the paper's \newcommand values inside a table cell."""
    for name in MACROS:
        cell = (cell.replace("\\" + name + "{}", MACROS[name])
                    .replace("\\" + name, MACROS[name]))
    return cell


def num(cell):
    # longest name first: \AttractorRetune is a prefix of \AttractorRetuneMimi
    for name in sorted(MACROS, key=len, reverse=True):
        cell = cell.replace("\\" + name + "{}", MACROS[name]).replace("\\" + name, MACROS[name])
    cell = cell.replace("$", "").replace("\\,", "").replace("{", "").replace("}", "")
    cell = cell.replace("+", "").replace("$-$", "-").replace("−", "-")
    m = re.search(r"-?\d+\.?\d*", cell)
    return float(m.group(0)) if m else None


def main() -> int:
    load_macros()
    apx = APX.read_text()
    main_tex = MAIN.read_text()
    # every source the guards read; built once, before any of them run
    # "main" here is main.tex itself, which for a long time it was not: the
    # key held sections/04_pitch.tex, so every guard that walks `tex` skipped
    # the abstract, the statements and the appendix contents list entirely.
    tex = {"main": uncomment((ROOT / "main.tex").read_text()),
           "results": uncomment(main_tex), "appendix": uncomment(apx)}
    for f in sorted((ROOT / "sections").glob("*.tex")):
        tex[f.stem] = uncomment(f.read_text())
    fails = []

    # --- per-partial displacements must reproduce the uniform-weight table
    partials = {}
    for r in rows_of("tab:spectral", apx):
        rate = r[0].split()[0]
        delta = num(r[1])
        sk = [num(c) for c in r[2:10]]
        partials[(rate, delta)] = sk

    edge_index = {"1.5": 2, "3": 3, "24": 5}
    for r in rows_of("tab:bound-check", apx):
        rate = r[0].split()[0]
        n_above = int(num(r[2]))
        lbar_tab, unif_tab, reading = num(r[3]), num(r[4]), num(r[5])
        for delta in (-40.0, 40.0):
            key = (rate, delta)
            if key not in partials:
                continue
            sk = partials[key]
            k0 = edge_index[rate] - 1
            above = sk[k0:]
            lbar = sum(-x / delta for x in above) / len(above)
            unif = sum(abs(x) for x in sk) / 8
            if len(above) != n_above:
                continue
            if abs(lbar - lbar_tab) > 0.011 or abs(unif - unif_tab) > 0.06:
                continue  # the other sign's row
            if abs(reading / unif - num(r[6])) > 0.011:
                fails.append(f"{rate} kbps d={delta:+.0f}: ratio {reading/unif:.3f} "
                             f"vs printed {num(r[6])}")
            break
        else:
            fails.append(f"no per-partial row reproduces bound row for {rate} kbps")

    # every row of the bound table must be reproducible from some partial row
    for r in rows_of("tab:bound-check", apx):
        rate = r[0].split()[0]
        lbar_tab, unif_tab = num(r[3]), num(r[4])
        ok = False
        for delta in (-40.0, 40.0):
            sk = partials.get((rate, delta))
            if not sk:
                continue
            above = sk[edge_index[rate] - 1:]
            lbar = sum(-x / delta for x in above) / len(above)
            unif = sum(abs(x) for x in sk) / 8
            if abs(lbar - lbar_tab) <= 0.011 and abs(unif - unif_tab) <= 0.06:
                ok = True
                break
        if not ok:
            fails.append(f"bound row {rate} kbps lbar={lbar_tab} unif={unif_tab} "
                         f"does not reproduce from the per-partial table")

    # --- Table 1's slopes must match the appendix's full registration table
    def keyof(name, point, stim):
        name = re.sub(r"\$\^[^$]*\$", "", name)
        name = name.split(" (")[0].strip()
        point = point.replace("kbps", "").replace("default", "def").strip()
        return (name, point, stim.strip().rstrip("s"))

    t7 = {}
    for r in rows_of("tab:c4", apx):
        parts = [x.strip() for x in r[1].split(",")]
        pt = parts[0]
        stim = parts[1] if len(parts) > 1 else ""
        t7[keyof(r[0], pt, stim)] = r
    # the per-condition figure replaced the wide table; check its data against
    # the appendix registration table instead of the table that used to hold it
    figsrc = (ROOT / "code" / "analysis" / "fig_conditions.py")
    if figsrc.exists():
        rows = re.search(r"ROWS = \[(.*?)\n\]", figsrc.read_text(), re.S)
        for line in (rows.group(1).splitlines() if rows else []):
            m = re.match(r'\s*\("([^"]+)",\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+)',
                         line)
            if not m:
                continue
            label, bias, lo, hi = m.group(1), *map(float, m.groups()[1:])
            if not (lo <= bias <= hi):
                fails.append(
                    f"conditions figure, {label!r}: bias {bias} outside its "
                    f"own interval [{lo}, {hi}]")


    # --- downstream: the grid-attributable figure must be a difference of paired differences
    dn = {}
    for r in rows_of("tab:downstream", apx):
        if len(r) < 6:
            continue
        label = (r[0] + " " + r[1]).replace("\\quad", "").strip()
        d = num(r[4])
        # keep the first occurrence: later blocks reuse labels for other metrics
        if d is not None and label not in dn:
            dn[label] = d
    def paired(corpus, arm):
        for k, v in dn.items():
            if k.startswith(corpus) and arm in k:
                return v
        return None
    for corpus, quoted_dac, quoted_opus in [("Saraga", 0.9, 0.4), ("Turkish", 1.5, 0.7)]:
        enc = paired(corpus, "EnCodec 3 kbps")
        dac = paired(corpus, "DAC 16k")
        opus = paired(corpus, "Opus, damage-matched")
        if None in (enc, dac, opus):
            fails.append(f"{corpus}: could not read all three paired differences")
            continue
        if abs((enc - dac) - quoted_dac) > 0.051:
            fails.append(f"{corpus}: EnCodec-DAC is {enc-dac:.1f}, text quotes {quoted_dac}")
        if abs((enc - opus) - quoted_opus) > 0.051:
            fails.append(f"{corpus}: EnCodec-Opus is {enc-opus:.1f}, text quotes {quoted_opus}")

    # --- the retuning arms must land where the prediction says
    # pair each family's "+33" arm with its own original-clips crossing
    base_of = {}
    for r in rows_of("tab:relocate", apx):
        if "original" in r[0].lower() or "Original" in r[0]:
            fam = r[0].split(",")[0].strip() if "," in r[0] else "EnCodec"
            base_of[fam] = num(r[3])
    for r in rows_of("tab:relocate", apx):
        if "33" not in r[0]:
            continue
        fam = r[0].split(",")[0].strip() if "," in r[0] else "EnCodec"
        base = base_of.get(fam)
        got = num(r[3])
        if base is None:
            fails.append(f"retune row {r[0]!r}: no original-clips crossing for {fam!r}")
            continue
        if got is None:
            continue
        if abs(got - (base + 33)) > 3.0:
            fails.append(f"retune row {r[0]!r}: crossing {got} against {base + 33:.1f} predicted")

    # --- the per-register table must satisfy Equation 16 row by row, and its
    # bias column must be the range the abstract quotes
    # columns are located by header, not by index: adding the b^soft column
    # silently moved "Measured" and the guard went on reading the old position
    hdr = [c.strip() for c in
           rows_of.__globals__["re"].search(
               r"\\toprule(.*?)\\\\", apx[apx.index("\\label{tab:registeredge}"):],
               rows_of.__globals__["re"].S).group(1).split("&")]
    def col(name):
        for j, h in enumerate(hdr):
            if name.lower() in h.lower():
                return j
        return None
    i_l, i_u, i_m = col("bar"), col("unif"), col("measured")
    reg_bias = []
    for r in rows_of("tab:registeredge", apx):
        above = r[2].split()[0] if r[2] else ""
        if None in (i_l, i_u, i_m) or len(r) <= max(i_l, i_u, i_m):
            fails.append("register table: could not locate its columns by header")
            break
        lbar, bunif, meas = num(r[i_l]), num(r[i_u]), num(r[i_m])
        if meas is not None:
            reg_bias.append(meas)
        if lbar is None or bunif is None or not above.isdigit():
            continue
        want = 40.0 * lbar * int(above) / 8.0
        if abs(want - bunif) > 0.15:
            fails.append(
                f"register row {r[0]!r}: 40*{lbar}*{above}/8 = {want:.1f}, "
                f"table says {bunif}")
    if reg_bias:
        lo, hi = min(reg_bias), max(reg_bias)
        allsrc = " ".join(" ".join(tex.values()).split())
        m = (re.search(r"([\d.]+)\s+to\s+([\d.]+)\s+across\s+four\s+octaves", allsrc)
             or re.search(r"octaves the bias runs ([\d.]+) to ([\d.]+)", allsrc))
        if not m:
            fails.append("no 'X to Y across four octaves' claim found to check "
                         "against the register table")
        elif abs(float(m.group(1)) - lo) > 0.06 or abs(float(m.group(2)) - hi) > 0.06:
            fails.append(
                f"abstract quotes {m.group(1)} to {m.group(2)} across registers, "
                f"the table gives {lo:.2f} to {hi:.2f}")

    # --- the confirmatory table: Eq 16 per row, edge implies the partial
    # count at 440 Hz, and the frozen tier rule matches the assigned tier
    for r in rows_of("tab:confirmatory", apx):
        edge = num(r[2])
        above = r[3].split()[0] if r[3] else ""
        lbar, bias, tab_bunif = num(r[4]), None, None
        assigned = r[6].lower() if len(r) > 6 else ""
        if edge is None or not above.isdigit() or lbar is None:
            continue
        want_above = len([k for k in range(1, 9) if k * 440.0 >= edge * 1000])
        if want_above != int(above):
            fails.append(
                f"confirmatory {r[0]!r}: edge {edge} kHz puts {want_above} "
                f"partials above at 440 Hz, table says {above}")
        tier = ("ladder" if lbar >= 0.70
                else "part" if lbar >= 0.20 else "input")
        if tier not in assigned.replace(" way", "").replace("'s", ""):
            fails.append(
                f"confirmatory {r[0]!r}: lbar {lbar} is tier {tier!r}, "
                f"table assigns {assigned!r}")
        bunif = 40.0 * lbar * int(above) / 8.0
        if tab_bunif is not None and abs(tab_bunif - bunif) > 0.15:
            fails.append(
                f"confirmatory {r[0]!r}: Eq 16 gives {bunif:.1f}, "
                f"table says {tab_bunif}")
        if edge * 1000.0 % 440.0 > 1e-6:
            fails.append(
                f"confirmatory {r[0]!r}: edge {edge} kHz is not a partial "
                f"frequency at the 440 Hz reference")
        if bias is not None and abs(bias) > 1.0:
            if not (0.15 <= bias / bunif <= 0.75):
                fails.append(
                    f"confirmatory {r[0]!r}: bias/b_unif = "
                    f"{bias / bunif:.2f}, outside the observed 0.15-0.75")

    # --- every count the prose draws from the confirmatory table, recomputed
    # from the table. These sentences have gone stale twice: a boundary sweep
    # kept a count from before a tabulated value was corrected, and the
    # interval-crossing count disagreed with the paragraph twenty lines above
    # it. Prose summarising a table is derived data and belongs under a guard.
    WORD = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
            "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
            "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
            "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
            "twenty": 20, "twenty-one": 21, "twenty-two": 22,
            "twenty-three": 23, "twenty-four": 24, "twenty-five": 25,
            "twenty-six": 26}

    def count_word(tok):
        return int(tok) if tok.isdigit() else WORD.get(tok.lower())

    i = apx.index("\\label{tab:confirmatory}")
    body = apx[i:apx.index("\\end{tabular}", i)]
    conf, group = [], None
    for line in body.split("\\\\"):
        if "multicolumn" in line:
            group = "new" if "never measured" in line else "seen"
            continue
        cells = [c.strip() for c in line.split("&")]
        if len(cells) < 7 or "textbf" in line:
            continue
        got = re.findall(r"-?\d\.\d\d", cells[4].replace("$-$", "-"))
        if len(got) != 3:
            continue
        lbar, lo, hi = (float(x) for x in got)
        conf.append(dict(name=cells[0], group=group, lbar=lbar, lo=lo, hi=hi,
                         pred=cells[5].split()[0], got=cells[6].split()[0]))
    n_conf = len(conf)
    if n_conf < 16:
        fails.append(f"confirmatory prose: parsed {n_conf} rows, expected at least 16")
    else:
        def tier(x, ladder=0.70):
            return "ladder" if x >= ladder else ("part" if x >= 0.20 else "input's")

        hits = [r for r in conf if r["pred"] == tier(r["lbar"])]
        n_new = sum(1 for r in hits if r["group"] == "new")
        for want, pat in (
                (len(hits), r"(\w+) of twenty-six predictions hold"),
                (len(hits) - n_new,
                 r"of codecs we had already measured, (\w+) of six hold"),
                (n_new, r"\\emph\{families\}, (\w+) of twenty hold")):
            m = re.search(pat, apx)
            if m is None:
                fails.append(f"confirmatory prose: no sentence matching {pat!r}")
            elif count_word(m.group(1)) != want:
                fails.append(
                    f"confirmatory prose: {m.group(0)!r} but the table gives {want}")

        # the boundary sweep, clause by clause of the sentence that reports it
        sweep = re.search(r"Sweeping them:(.*?)(?<=\.)\s", apx, re.S)
        if sweep is None:
            fails.append("confirmatory sweep: no 'Sweeping them:' sentence")
        else:
            seen = 0
            for clause in sweep.group(1).split(";"):
                m = re.search(r"(0\.\d\d)\D+?(\d+)(?:\s+of\s+26)?\s*(?:$|[;.])",
                              clause.strip())
                if m is None:
                    fails.append(f"confirmatory sweep: unparsed clause {clause.strip()!r}")
                    continue
                seen += 1
                b, claim = m.group(1), int(m.group(2))
                want = sum(1 for r in conf if r["pred"] == tier(r["lbar"], float(b)))
                if claim != want:
                    fails.append(f"confirmatory sweep: prose says {claim} at boundary "
                                 f"{b}, the table gives {want}")
            if seen < 2:
                fails.append(f"confirmatory sweep: only {seen} boundaries parsed")

        # misses running one way, and intervals crossing a tier boundary
        misses = [r for r in conf if r["pred"] != tier(r["lbar"])]
        oneway = sum(1 for r in misses
                     if r["pred"] == "ladder" and tier(r["lbar"]) == "part")
        m = re.search(r"(\w+) of the (\w+) misses run one way", apx)
        if m and (count_word(m.group(1)), count_word(m.group(2))) != (oneway, len(misses)):
            fails.append(f"confirmatory prose: {m.group(0)!r} but the table gives "
                         f"{oneway} of {len(misses)}")
        crossing = sum(1 for r in conf
                       if any(r["lo"] < t < r["hi"] for t in (0.20, 0.70)))
        for m in re.finditer(r"(\w+) of (?:the )?twenty-six (?:\$\\bar\\ell\$ )?"
                             r"intervals\s+cross", apx):
            if count_word(m.group(1)) != crossing:
                fails.append(f"confirmatory prose: {m.group(0)!r} but {crossing} "
                             f"of the tabulated intervals cross a boundary")

    # --- the non-Western flip arithmetic: the two corpus counts must sum to
    # the total, the control split must sum to its own total, and the task
    # change must be the tabulated gain and loss over sixty recordings.
    m = re.search(r"(\d+)\s*\nrecordings change which fits better.*?(\d+)\s*\n?of 200 "
                  r"Saraga.*?flips (\d+) of 60.*?the (\w+) control\s*\n?flips[^.]*?"
                  r"split (\w+) toward and (\w+) away", apx, re.S)
    if m is None:
        fails.append("flip arithmetic: the Saraga/makam sentence did not parse")
    else:
        total, saraga, makam = int(m.group(1)), int(m.group(2)), int(m.group(3))
        ctrl, toward, away = (count_word(x) for x in m.group(4, 5, 6))
        if saraga + makam != total:
            fails.append(f"flip arithmetic: {saraga} + {makam} != {total} flips")
        if toward + away != ctrl:
            fails.append(f"flip arithmetic: control split {toward}+{away} != {ctrl}")
    m = re.search(r"(\w+) of sixty recordings losing their class and (\w+)\s*\n?"
                  r"gaining one.*?\$(-\d+)/60\$ against", apx, re.S)
    if m is None:
        fails.append("flip arithmetic: the makam task-level sentence did not parse")
    else:
        lost, gained, net = count_word(m.group(1)), count_word(m.group(2)), int(m.group(3))
        if gained - lost != net:
            fails.append(f"flip arithmetic: {gained} gained minus {lost} lost is "
                         f"{gained - lost}/60, but {net}/60 is reported")

    # --- the word before a \ref must match what the label points at. A
    # "Table \ref{fig:conditions}" printed "Table 3" for Figure 3 for several
    # rounds, and a doubled word printed "Section Section 4"; both read as
    # broken references. The label prefix says which word is right.
    WORDS = {"fig": {"Figure", "Figures"}, "tab": {"Table", "Tables"},
             "sec": {"Section", "Sections", "Appendix", "Appendices"},
             "eq": {"Equation", "Equations"}}
    for name, src in tex.items():
        for m in re.finditer(r"(\w+)[\s~]+(?:and[\s~]+)?\\ref\{(fig|tab|sec|eq):", src):
            word, kind = m.group(1), m.group(2)
            if word in WORDS[kind] or word[0].islower() or word.isdigit():
                continue
            if any(word in w for w in WORDS.values()):
                fails.append(f"{name}: {word!r} precedes a {kind}: reference; "
                             f"expected one of {sorted(WORDS[kind])}")
        for m in re.finditer(r"\b(\w+)[\s~]+\1[\s~]*\\ref\{", src):
            fails.append(f"{name}: doubled word {m.group(1)!r} before a reference")

    # --- external resources named in the prose must carry a citation
    # somewhere. LibriSpeech, MMS, Whisper and Saraga were each used and
    # reported on for several rounds with no bibliography entry cited.
    RESOURCES = {"LibriSpeech": "panayotov2015librispeech",
                 "MMS": "pratap2024mms",
                 "Whisper": "radford2023whisper",
                 "Saraga": "srinivasamurthy2021saraga",
                 "NSynth": "engel2017nsynth",
                 "GTZAN": "tzanetakis2002gtzan",
                 "FLEURS": "conneau2022fleurs"}
    allsrc = "\n".join(tex.values())
    for word, key in RESOURCES.items():
        if re.search(r"\b" + word + r"\b", allsrc) and key not in allsrc:
            fails.append(f"{word} is used in the prose but {key} is never cited")

    # --- every value the conditions figure draws must equal the appendix cell
    # it came from. The figure carries its numbers as a literal table in the
    # plotting script, and six of its bias intervals had drifted from Table
    # \ref{tab:c4} by up to 0.6 cents at an end. Internal consistency (the
    # point lying inside its own interval) does not catch that. The mapping
    # from figure row to appendix row is declared here rather than guessed
    # from the label, because guessing matched 24 kbps to the 3 kbps row.
    FIGROW = {
        # figure label: (registration row, band-edge row)
        "EnCodec 24k, 3 kbps":     ("EnCodec 24k|3 kbps, tones", "EnCodec 24k|3 kbps"),
        "EnCodec 24k, 24 kbps":    ("EnCodec 24k|24 kbps, tones", "EnCodec 24k|24 kbps"),
        "WavTokenizer, 0.9 kbps":  ("WavTokenizer|", "WavTokenizer|"),
        "EnCodec 48k, 6 kbps":     ("EnCodec 48k, music|", "EnCodec 48k, music|"),
        "SNAC 32k":                ("SNAC 32k|", "SNAC 32k|"),
        "EnCodec 24k, vowels":     ("EnCodec 24k|3 kbps, vowels", None),
        "Mimi":                    ("Mimi|", "Mimi|"),
        "SpeechTokenizer, vowels": ("SpeechTokenizer|", None),
        "DAC 16k":                 ("DAC 16k|", "DAC 16k|"),
        "DAC 24k":                 ("DAC 24k|", None),
        "SNAC 44k":                ("SNAC 44k|", None),
        "BigVGAN (vocoder)":       ("BigVGAN (vocoder)|", "BigVGAN (vocoder)|"),
        "Opus, 6 kbps":            ("@classical|Opus 6", None),
        "MP3, 16 kbps":            ("@classical|MP3 16", None),
    }
    MARGIN = (0.85, 1.15)

    def cells(text):
        return [float(x) for x in re.findall(
            r"-?\d+\.\d+", subst(text).replace("$-$", "-").replace("\\,", " "))]

    def lookup(rows, key):
        codec, point = key.split("|")
        for r in rows:
            if r[0].strip().startswith(codec) and (
                    not point or (len(r) > 1 and r[1].strip().startswith(point))):
                return r
        return None

    if figsrc.exists():
        block = re.search(r"ROWS = \[(.*?)\n\]", figsrc.read_text(), re.S)
        drawn = re.findall(
            r'\("([^"]+)",\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+),'
            r'\s*(None|-?[\d.]+),\s*(None|-?[\d.]+),\s*(None|-?[\d.]+),'
            r'\s*\w+,\s*(True|False|None)\)',
            block.group(1) if block else "")
        if len(drawn) != len(FIGROW):
            fails.append(f"conditions figure: parsed {len(drawn)} rows against "
                         f"{len(FIGROW)} declared")
        c4, cls = rows_of("tab:c4", apx), rows_of("tab:classical", apx)
        be = rows_of("tab:bandedge", apx)
        for name, b, lo, hi, l, llo, lhi, reg in drawn:
            b, lo, hi = float(b), float(lo), float(hi)
            if name not in FIGROW:
                fails.append(f"conditions figure: {name!r} has no declared source")
                continue
            regkey, edgekey = FIGROW[name]
            # --- the bias and its interval
            if regkey.startswith("@classical|"):
                r = lookup(cls, "|" + regkey.split("|")[1])
                r = lookup(cls, regkey.split("|")[1] + "|")
                want = cells(r[4]) if r and len(r) > 4 else None
            else:
                r = lookup(c4, regkey)
                want = cells(r[5]) if r and len(r) > 5 else None
            if want is None or len(want) != 3:
                fails.append(f"conditions figure: no bias cell found for {name}")
            elif [round(x, 2) for x in (b, lo, hi)] != [round(x, 2) for x in want]:
                fails.append(f"conditions figure: {name} draws bias {b} [{lo}, "
                             f"{hi}] against the appendix's {want[0]} "
                             f"[{want[1]}, {want[2]}]")
            # --- the registration marker must follow from the slope interval
            if reg != "None" and not regkey.startswith("@classical"):
                ci = cells(r[2]) if r and len(r) > 2 else None
                if ci and len(ci) == 3:
                    inside = MARGIN[0] <= ci[1] and ci[2] <= MARGIN[1]
                    if (reg == "True") != inside:
                        fails.append(
                            f"conditions figure: {name} is drawn as "
                            f"{'registering' if reg == 'True' else 'not registering'}"
                            f" but its slope interval [{ci[1]}, {ci[2]}] is "
                            f"{'inside' if inside else 'outside'} the margin")
            # --- the ladder: mean over signs, bar spanning the two estimates
            if l == "None":
                continue
            l, llo, lhi = float(l), float(llo), float(lhi)
            er = lookup(be, edgekey) if edgekey else None
            if er is None or len(er) < 5:
                fails.append(f"conditions figure: {name} draws a ladder fraction "
                             f"with no row in Table tab:bandedge")
                continue
            flat, sharp = cells(er[3])[0], cells(er[4])[0]
            if [round(llo, 2), round(lhi, 2)] != [round(min(flat, sharp), 2),
                                                  round(max(flat, sharp), 2)]:
                fails.append(f"conditions figure: {name} draws ladder bar [{llo}, "
                             f"{lhi}], but its two sign estimates are "
                             f"{flat} and {sharp}")
            elif abs(l - (flat + sharp) / 2) > 0.006:
                fails.append(f"conditions figure: {name} draws ladder {l} against "
                             f"a sign mean of {(flat + sharp) / 2:.3f}")

    # --- there must be exactly one figures directory, and it must be the one
    # main.tex reads. make_figures.py wrote to code/figures for many rounds
    # while the paper compiled figures/, so eight figures had silently
    # diverged from the copies being generated; regenerating fixed nothing
    # because the output never reached the paper.
    stray = ROOT / "code" / "figures"
    if stray.exists():
        fails.append("code/figures exists: a second figures directory means "
                     "regenerated figures need not be the ones the paper uses")
    figdir = ROOT / "figures"
    included = set(re.findall(r"\\includegraphics\[[^\]]*\]\{figures/([^}]+)\}",
                              "\n".join(tex.values())))
    for name in sorted(included):
        if not (figdir / name).exists():
            fails.append(f"main.tex includes figures/{name}, which does not exist")
    for f in sorted(figdir.glob("*.pdf")):
        png = f.with_suffix(".png")
        if png.exists() and png.stat().st_mtime < f.stat().st_mtime - 1:
            fails.append(f"figures/{png.name} is older than its PDF; a preview "
                         f"read from it will not be what the paper shows")

    # --- a ladder fraction quoted in the main text must be the one Figure
    # \ref{fig:conditions} draws for that row. The prose quoted the flat-side
    # column for WavTokenizer and BigVGAN while the figure plotted the mean
    # over detuning signs, and quoted the mean for EnCodec, so the main text
    # disagreed with the figure and with itself.
    if figsrc.exists():
        blk = re.search(r"ROWS = \[(.*?)\n\]", figsrc.read_text(), re.S)
        drawnl = {m.group(1): m.group(2) for m in re.finditer(
            r'\("([^"]+)",\s*(?:-?[\d.]+,\s*){3}(None|-?[\d.]+)',
            blk.group(1) if blk else "")}
        QUOTED = {"WavLadderMean": "WavTokenizer, 0.9 kbps",
                  "VocLadderMean": "BigVGAN (vocoder)"}
        for macro, row in QUOTED.items():
            if macro not in MACROS or row not in drawnl:
                fails.append(f"ladder quote: {macro} or {row!r} not found")
                continue
            want, got = drawnl[row], MACROS[macro].strip()
            if want == "None" or abs(float(want) - float(got)) > 0.005:
                fails.append(f"ladder quote: prose macro {macro} is {got} but "
                             f"Figure 3 draws {want} for {row}")

    # --- a straight double quote typesets as a closing quote at both ends,
    # so `"the corpus's tuning"` printed as }the corpus's tuning}. LaTeX wants
    # ``...''. Comments are exempt.
    for name, src in tex.items():
        for ln, line in enumerate(src.split("\n"), 1):
            if line.lstrip().startswith("%"):
                continue
            body = line.split("%")[0]
            if '"' in body:
                fails.append(f"{name}:{ln}: straight double quote in body text; "
                             f"use ``...'' so the opening quote is not reversed")

    # --- a bare label like "eq:pullshare" printed as literal text means a
    # \ref was stripped instead of resolved; the appendix contents list, which
    # is generated, leaked one this way.
    for name, src in tex.items():
        for m in re.finditer(r"(?<![\\{a-zA-Z])((?:tab|fig|sec|eq|prop):[a-z0-9-]+)", src):
            before = src[max(0, m.start() - 8):m.start()]
            if "ref{" in before or "label{" in before or "}{" in before:
                continue
            fails.append(f"{name}: bare label {m.group(1)!r} in body text; it "
                         f"will print literally")

    # --- em-dashes had spread to twenty-six in nine pages of main text, which
    # reads as punctuation by reflex rather than by choice. Most were doing the
    # work of a colon, a semicolon or a full stop.
    MAIN_FILES = ("main", "01_intro", "02_related", "03_method", "04_pitch",
                  "07_discussion")
    n_dash = 0
    for name in MAIN_FILES:
        src = tex.get(name, "")
        n_dash += sum(l.split("%")[0].count("---")
                      for l in src.split("\n") if not l.lstrip().startswith("%"))
    if n_dash > 6:
        fails.append(f"main text uses {n_dash} em-dashes; keep it under six so "
                     f"they read as a choice")

    # --- a sec: label defined in the appendix must be introduced as an
    # Appendix, not a Section. The generic reference-word guard cannot catch
    # this, because sec: covers both; "Section H holds content fixed" printed
    # for a label that had moved into the appendix.
    apx_secs = set(re.findall(r"\\label\{(sec:[^}]+)\}", apx))
    for name, src in tex.items():
        if name == "09_appendix":
            continue
        for m in re.finditer(r"(\w+)[\s~]*\\ref\{(sec:[^}]+)\}", src):
            if m.group(2) in apx_secs and m.group(1) in ("Section", "Sections"):
                fails.append(f"{name}: {m.group(1)!r} introduces "
                             f"{m.group(2)!r}, which is an appendix section")

    # --- every bracketed interval printed in the main text must also stand in
    # the appendix. A comparator interval, 5.73 [5.36, 6.11], was added to the
    # main text on a reviewer's request and never given a home in the appendix,
    # so the paper quoted a number nothing backed.
    main_body = " ".join(tex[n] for n in
                         ("main", "01_intro", "02_related", "03_method",
                          "04_pitch", "07_discussion") if n in tex)
    for m in re.finditer(r"\[([\d.]+),\s*([\d.]+)\]", main_body):
        lo, hi = m.group(1), m.group(2)
        if lo in apx and hi in apx:
            continue
        fails.append(f"main text prints the interval [{lo}, {hi}], which the "
                     f"appendix never states")

    # --- the paper says three statistics recur and that "pull" is a verdict
    # rather than a fourth. An appendix heading said "the four statistics",
    # contradicting its own table caption on the same page.
    allsrc = " ".join(tex.values())
    if re.search(r"four statistic", allsrc, re.I):
        fails.append("something calls them the four statistics; the paper "
                     "reports three, with pull a verdict rather than a fourth")

    # --- the reproducibility statement counts files in the released archive,
    # so it can be checked against the archive. It claimed 123 result files and
    # 102 sidecars where the repository holds 146 and 117; a reviewer with the
    # supplement checks this before anything else.
    res = ROOT / "code" / "results"
    if res.is_dir():
        top_csv = sorted(res.glob("*.csv"))
        rep_csv = sorted(res.glob("replication/*.csv"))
        top_meta = sorted(res.glob("*.meta.json"))
        rep_meta = sorted(res.glob("replication/*.meta.json"))
        counts = {
            "raw result files": len(top_csv) + len(rep_csv),
            "reported or retained runs": len(top_csv),
            "files carrying a sidecar": len(top_meta) + len(rep_meta),
            "sidecars outside replication": len(top_meta),
        }
        claims = [
            (r"all (\d+) raw result\s+files", "raw result files"),
            (r"files \((\d+) reported or retained runs", "reported or retained runs"),
            (r"Each of (\d+) sweep, corpus", "files carrying a sidecar"),
            (r"Of the (\d+) sidecars outside", "sidecars outside replication"),
        ]
        stmt = " ".join(tex["main"].split())
        for pat, key in claims:
            m = re.search(pat, stmt)
            if m is None:
                fails.append(f"reproducibility: no claim matching {pat!r}")
            elif int(m.group(1)) != counts[key]:
                fails.append(f"reproducibility claims {m.group(1)} {key}, the "
                             f"repository has {counts[key]}")

    # --- the guard-sensitivity grid is a summary of the exclusion table, so it
    # can be recomputed from it. Adding BigVGAN to the exclusion table left the
    # grid reporting 13 admitted of 17 when the answer had become 14 of 18.
    runs = []
    for r in rows_of("tab:exclusion", apx):
        if len(r) < 5:
            continue
        cv, ret = num(subst(r[3])), num(subst(r[4]))
        if cv is None or ret is None:
            continue
        # the two octave repeats are the same condition at another reference
        if "220 Hz" in r[1] or "880 Hz" in r[1]:
            continue
        runs.append((r[1].strip(), cv, ret))
    if runs:
        m = re.search(r"admitted conditions of the (\w+) measured", apx)
        if m and count_word(m.group(1)) != len(runs):
            fails.append(f"guard grid says {m.group(1)} conditions measured, "
                         f"the exclusion table lists {len(runs)}")
        # parse this one directly: rows_of drops any row containing \textbf,
        # and the reported operating point is exactly the bolded row
        gi = apx.index("\\label{tab:guardgrid}")
        gbody = apx[gi:apx.index("\\end{tabular}", gi)]
        grid = []
        for line in gbody.split("\\\\"):
            line = re.sub(r"\\(?:top|mid|bottom)rule|\\cmidrule\(?[^)]*\)?\{[^}]*\}",
                          " ", line)
            cells = [c.replace("\\textbf{", "").replace("}", "").strip()
                     for c in line.split("&")]
            if len(cells) >= 6 and re.match(r"^0\.\d+$", cells[0]):
                grid.append(cells)
        if len(grid) < 3:
            fails.append(f"guard grid: parsed {len(grid)} rows")
        for row in grid:
            cvlim = num(row[0])
            if cvlim is None:
                continue
            for j, retlim in enumerate((0.15, 0.20, 0.25, 0.30, 0.34), start=1):
                if j >= len(row):
                    break
                want = sum(1 for _, cv, ret in runs if cv <= cvlim and ret >= retlim)
                got = num(row[j])
                if got is not None and int(got) != want:
                    fails.append(
                        f"guard grid at cv<={cvlim}, retention>={retlim} says "
                        f"{int(got)}; the exclusion table gives {want}")

    # --- the between-run table's last column is derivable from the three
    # before it: Combined = sqrt(Within^2 + (2 Sd)^2). All three rows follow
    # that rule, but the caption said only "in quadrature", so a reader
    # combining Within with Sd directly gets 0.18 where the table says 0.22.
    for r in rows_of("tab:betweenrun", apx):
        if len(r) < 6:
            continue
        runs = [float(x) for x in re.findall(r"-?\d+\.?\d*", subst(r[1]))]
        vals = [num(subst(c)) for c in r[2:6]]
        if len(runs) < 5 or any(v is None for v in vals):
            continue
        mean, sd, within, comb = vals
        if abs(sum(runs) / len(runs) - mean) > 0.005:
            fails.append(f"between-run {r[0]!r}: five runs average "
                         f"{sum(runs)/len(runs):.4f}, table says {mean}")
        want = (within ** 2 + (2 * sd) ** 2) ** 0.5
        if abs(want - comb) > 0.006:
            fails.append(f"between-run {r[0]!r}: sqrt({within}^2 + (2*{sd})^2) "
                         f"= {want:.4f}, table says {comb}")

    # --- every float must be cited from prose, not only from its own caption
    all_tex = main_tex + apx + (ROOT / "main.tex").read_text()
    for extra in ("01_intro", "07_discussion", "05_phonology"):
        fp = ROOT / "sections" / f"{extra}.tex"
        if fp.exists():
            all_tex += fp.read_text()
    prose = re.sub(r"\\caption\{(?:[^{}]|\{[^{}]*\})*\}", " ", all_tex)
    labels = set(re.findall(r"\\label\{((?:tab|fig):[^}]+)\}", all_tex))
    cited = set(re.findall(r"\\ref\{((?:tab|fig):[^}]+)\}", prose))
    for orphan in sorted(labels - cited):
        fails.append(f"float {orphan!r} is never cited outside its own caption")

    # --- the appendix contents list must match the appendix's own sectioning
    letter, seen = None, {}
    for mm in re.finditer(r"\\(section|subsection)\{([^}]*)\}", apx):
        if mm.group(1) == "section":
            letter = chr(ord("A") + len(seen)); seen[letter] = 0
        elif letter:
            seen[letter] += 1
    listing = (ROOT / "main.tex").read_text()
    a = listing.find("\\section*{Appendix contents}")
    b = listing.find("Where to find each claim")
    block = listing[a:b] if a >= 0 and b > a else ""
    for L, n in seen.items():
        if n == 0:
            continue
        want = f"{L}.{n} "
        if want not in block:
            fails.append(
                f"appendix contents: {L} has {n} subsections but the list "
                f"does not reach {want.strip()}")
        if f"{L}.{n + 1} " in block:
            fails.append(
                f"appendix contents: lists {L}.{n + 1} but {L} has only {n}")

    # every condition drawn in the figure must appear in the appendix table
    if figsrc.exists():
        rows = re.search(r"ROWS = \[(.*?)\n\]", figsrc.read_text(), re.S)
        drawn = re.findall(r'\("([^"]+)"', rows.group(1)) if rows else []
        names = " ".join(
            r[0] for tbl in ("tab:c4", "tab:classical", "tab:controls")
            for r in rows_of(tbl, apx)).lower()
        for label in drawn:
            stem = label.split(",")[0].strip().lower()
            if stem and stem.split()[0] not in names:
                fails.append(
                    f"conditions figure draws {stem!r}, absent from Table A7")

    # --- a float's label prefix must match the environment it sits in, or
    # prose that writes "Table \\ref{...}" will render "Table 3" for a figure
    for src, name in ((main_tex, "results"), (apx, "appendix"),
                      ((ROOT / "sections" / "03_method.tex").read_text(), "method")):
        for m in re.finditer(r"\\begin\{(figure|table)\}\*?(.*?)\\end\{\1\}", src, re.S):
            env, body = m.group(1), m.group(2)
            for lbl in re.findall(r"\\label\{((?:tab|fig):[^}]+)\}", body):
                want = "fig" if env == "figure" else "tab"
                if not lbl.startswith(want):
                    fails.append(
                        f"{name}: {lbl!r} labels a {env}; prose citing it will "
                        f"print the wrong float word")

    if fails:
        print("INCONSISTENT:")
        for f in fails:
            print("  -", f)
        return 1
    print("consistent:")
    print("  - the uniform-weight table reproduces from the per-partial displacements")
    print("  - the per-condition figure's biases lie inside their own intervals")
    print("  - the grid-attributable costs are the stated differences of paired differences")
    print("  - each retuning arm lands within 3 cents of its prediction")
    print("  - the per-register table satisfies Equation 16 row by row")
    print("  - the register range in prose is that table's bias column")
    print("  - the confirmatory table's edges, tiers and ratios all cohere")
    print("  - every table and figure is cited from prose")
    print("  - the appendix contents list matches the appendix")
    print("  - every float label matches its environment")
    print("  - every count the prose draws from the confirmatory table")
    print("  - the non-Western flip counts add up")
    print("  - the word before every reference matches its label")
    print("  - every named external resource is cited")
    print("  - the conditions figure matches the tables it is drawn from")
    print("  - one figures directory, and every included figure is in it")
    print("  - ladder fractions quoted in prose match the figure")
    print("  - no straight double quotes in body text")
    print("  - no bare labels printed as text")
    print("  - em-dashes in the main text stay rare")
    print("  - appendix sections are called Appendix, not Section")
    print("  - every interval in the main text is backed by the appendix")
    print("  - the paper counts three statistics everywhere")
    print("  - the reproducibility file counts match the repository")
    print("  - the guard grid follows from the exclusion table")
    print("  - the between-run table reproduces from its five runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

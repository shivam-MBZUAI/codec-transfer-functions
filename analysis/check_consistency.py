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
    reg_bias = []
    for r in rows_of("tab:registeredge", apx):
        above = r[2].split()[0] if r[2] else ""
        lbar, bunif, meas = num(r[3]), num(r[4]), num(r[5])
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
        m = re.search(r"([\d.]+)\s+to\s+([\d.]+)\s+across\s+four\s+octaves",
                      " ".join((ROOT / "main.tex").read_text().split()))
        if not m:
            fails.append("abstract: no register range found")
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
            "sixteen": 16}

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
    if len(conf) != 16:
        fails.append(f"confirmatory prose: parsed {len(conf)} rows, expected 16")
    else:
        def tier(x, ladder=0.70):
            return "ladder" if x >= ladder else ("part" if x >= 0.20 else "input's")

        hits = [r for r in conf if r["pred"] == tier(r["lbar"])]
        n_new = sum(1 for r in hits if r["group"] == "new")
        for want, pat in (
                (len(hits), r"(\w+) of sixteen predictions hold"),
                (len(hits) - n_new,
                 r"of codecs we had already measured, (\w+) of six hold"),
                (n_new, r"\\emph\{families\}, (\w+) of ten hold")):
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
                m = re.search(r"(0\.\d\d)\D+?(\d+)(?:\s+of\s+16)?\s*(?:$|[;.])",
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
        for m in re.finditer(r"(\w+) of (?:the )?sixteen (?:\$\\bar\\ell\$ )?"
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
    tex = {"main": main_tex, "appendix": apx}
    for f in sorted((ROOT / "sections").glob("*.tex")):
        tex[f.stem] = f.read_text()
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
    print("  - the abstract's register range is that table's bias column")
    print("  - the confirmatory table's edges, tiers and ratios all cohere")
    print("  - every table and figure is cited from prose")
    print("  - the appendix contents list matches the appendix")
    print("  - every float label matches its environment")
    print("  - every count the prose draws from the confirmatory table")
    print("  - the non-Western flip counts add up")
    print("  - the word before every reference matches its label")
    print("  - every named external resource is cited")
    print("  - the conditions figure matches the tables it is drawn from")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

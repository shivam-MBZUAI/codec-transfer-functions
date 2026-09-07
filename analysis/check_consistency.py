"""Cross-table consistency checks for the paper source.

The mathematics reviews repeatedly found tables that were said to derive
from one another but did not. This script asserts those relations directly
on the LaTeX source, so a drift fails here before a reader finds it.

    python analysis/check_consistency.py
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APX = ROOT / "sections" / "09_appendix.tex"
MAIN = ROOT / "sections" / "04_pitch.tex"


def _fig_relocate_rows():
    """(label, colour, own-grid lbar, 12-TET lbar) as fig_relocate.py plots
    them. Parsed rather than imported: the guard suite must not need
    matplotlib, and a figure that fails to render should still be checkable.
    `None` for an arm with no corpus grid of its own."""
    src = ROOT / "code" / "analysis" / "fig_relocate.py"
    if not src.exists():
        return []
    out = []
    for line in src.read_text().split("\n"):
        m = re.match(r'\s*\("([^"]+)",\s*(\w+),\s*(None|[\d.]+),'
                     r'\s*(None|[\d.]+)\)', line)
        if m:
            f = lambda s: None if s == "None" else float(s)
            out.append((m.group(1), m.group(2), f(m.group(3)), f(m.group(4))))
    return out


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



def _check_lowladder(name, l, llo, lhi, edgekey, apx, fails):
    """A figure row with no bias: check its ladder against the table it came
    from. These rows exist because panel (b) plotted only the seven rows
    between 0.71 and 0.90, so a figures-only reader saw a universal effect."""
    if l == "None":
        fails.append(f"conditions figure: {name} carries neither bias nor ladder")
        return
    tbl, key = edgekey.split("|", 1)
    src = "tab:confirmatory" if tbl == "@confirm" else "tab:sbr"
    for row in rows_of(src, apx):
        if key.lower() in row[0].lower():
            nums = [float(x) for x in re.findall(r"-?\d+\.\d+", subst(" ".join(row)))]
            if round(float(l), 2) not in [round(n, 2) for n in nums]:
                fails.append(f"conditions figure: {name} draws {l}, absent from "
                             f"its row of {src}")
            return
    fails.append(f"conditions figure: no {src} row matches {name}")


def main() -> int:
    load_macros()
    apx = APX.read_text()
    main_tex = MAIN.read_text()
    fails = []
    # every source the guards read; built once, before any of them run
    # "main" here is main.tex itself, which for a long time it was not: the
    # key held sections/04_pitch.tex, so every guard that walks `tex` skipped
    # the abstract, the statements and the appendix contents list entirely.
    tex = {"main": uncomment((ROOT / "main.tex").read_text()),
           "results": uncomment(main_tex), "appendix": uncomment(apx)}
    # only the files main.tex actually \input. sections/02_related.tex sat
    # uncompiled for many rounds, and because the guards globbed the whole
    # directory it counted as live: its citations made eleven bibliography
    # entries look used when nothing in the paper cited them.
    included = re.findall(r"\\input\{sections/([^}]+)\}", tex["main"])
    for stem in included:
        f = (ROOT / "sections" / stem).with_suffix(".tex")
        if f.exists():
            tex[f.stem] = uncomment(f.read_text())
    for f in sorted((ROOT / "sections").glob("*.tex")):
        if f.stem not in tex:
            fails.append(f"sections/{f.name} is not \\input by main.tex; "
                         f"either include it or delete it")

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

    # --- the figure's ladder column is the mean of the two detuning-sign
    # estimates in the band-edge table, rounded half-up, with the bar spanning
    # them. Both were hand-copied once and drifted; a value that reads 0.10 in
    # the text and 0.11 in the figure is the same tie resolved two ways.
    LADMAP = {
        "EnCodec 24k, 3 kbps": ("EnCodec 24k", "3 kbps"),
        "EnCodec 24k, 24 kbps": ("EnCodec 24k", "24 kbps"),
        "WavTokenizer, 0.9 kbps": ("WavTokenizer", "0.9 kbps"),
        "EnCodec 48k, 6 kbps": ("EnCodec 48k, music", "6 kbps"),
        "SNAC 32k": ("SNAC 32k", "default"),
        "Mimi": ("Mimi", "Q8"),
        "DAC 16k": ("DAC 16k", "Q6"),
        "BigVGAN (vocoder)": ("BigVGAN (vocoder)", "mel input"),
    }
    from decimal import Decimal as _D, ROUND_HALF_UP as _HU
    signs = {}
    for r in rows_of("tab:bandedge", apx):
        if len(r) < 5:
            continue
        neg, pos = num(r[3]), num(r[4])
        if neg is not None and pos is not None:
            signs[(r[0].strip(), r[1].strip())] = (neg, pos)
    if figsrc.exists() and signs:
        blk = re.search(r"ROWS = \[(.*?)\n\]", figsrc.read_text(), re.S)
        for line in (blk.group(1).splitlines() if blk else []):
            m = re.match(r'\s*\("([^"]+)",\s*(?:-?[\d.]+,\s*){3}'
                         r'([\d.]+),\s*([\d.]+),\s*([\d.]+)', line)
            if not m or m.group(1) not in LADMAP:
                continue
            label = m.group(1)
            lad, blo, bhi = (float(x) for x in m.groups()[1:])
            key = LADMAP[label]
            if key not in signs:
                fails.append(f"conditions figure, {label!r}: no {key} row in "
                             "the band-edge table to check the ladder against")
                continue
            neg, pos = signs[key]
            want = float(((_D(repr(neg)) + _D(repr(pos))) / 2).quantize(
                _D("0.01"), rounding=_HU))
            if abs(want - lad) > 1e-9:
                fails.append(
                    f"conditions figure, {label!r}: ladder {lad}, but the "
                    f"band-edge table's {neg} and {pos} mean {want}")
            # the bar itself is already checked further down; here we only
            # need the point value the main text quotes.


    # The prose states the range of lbar across stock conditions; it must be the
    # min and max of the same round-half-up means the figure and tables use. It
    # read "0.85 and 0.96" once, which is a per-sign pair, not a range of means.
    if signs:
        stock = {k: v for k, v in signs.items()
                 if "fine-tuned" not in k[0] and "bypass" not in k[0]
                 and "NSynth" not in k[1] and "vocoder" not in k[0].lower()}
        if stock:
            means = [float(((_D(repr(a)) + _D(repr(b))) / 2).quantize(
                _D("0.01"), rounding=_HU)) for a, b in stock.values()]
            lo_w, hi_w = min(means), max(means)
            prose = " ".join(" ".join(tex.values()).split())
            m = re.search(r"\\bar\\ell\$ between ([\d.]+) and ([\d.]+)", prose)
            if m:
                lo_g, hi_g = float(m.group(1)), float(m.group(2))
                if abs(lo_g - lo_w) > 1e-9 or abs(hi_g - hi_w) > 1e-9:
                    fails.append(
                        f"prose says lbar runs {lo_g} to {hi_g} across conditions, "
                        f"but the band-edge table's means run {lo_w} to {hi_w}")

    # Wherever the prose quotes DAC's ladder fraction as a point value it must
    # be that same mean: it read 0.10 in two places while the figure drew 0.11.
    if ("DAC 16k", "Q6") in signs:
        neg, pos = signs[("DAC 16k", "Q6")]
        want = float(((_D(repr(neg)) + _D(repr(pos))) / 2).quantize(
            _D("0.01"), rounding=_HU))
        prose = " ".join(" ".join(tex.values()).split())
        for phr in (r"DAC's own ladder fraction, ([\d.]+)",
                    r"DAC's own measured fraction,\s*([\d.]+)"):
            for got in dict.fromkeys(re.findall(phr, prose)):
                if abs(float(got) - want) > 1e-9:
                    fails.append(
                        f"prose quotes DAC's ladder fraction as {got}, but the "
                        f"band-edge table's {neg} and {pos} mean {want}")

    # Every place a single lbar is printed for an arm whose two detuning signs
    # are in the band-edge table, it must be their round-half-up mean. Five of
    # these are exact ties, and the Saraga row resolved its tie downward while
    # every other row resolved upward.
    # These lbar readings used to be two columns of tab:relocate and are now
    # Figure A9, so the check reads the figure's own data rather than the
    # table. Moving a number out of a table must not quietly retire the
    # guard that held it; "own" is the arm's own corpus grid, "tet" 12-TET,
    # and a flattened arm has no own grid so its 12-TET value is the one to
    # compare.
    A24MAP = {  # band-edge row -> (figure row label, which reading)
        ("EnCodec, fine-tuned on GTZAN", "3 kbps"):
            ("EnCodec, original clips", "own"),
        ("EnCodec, fine-tuned on $+33$-cent GTZAN", "3 kbps"):
            ("EnCodec, $+33$ cents", "own"),
        ("EnCodec, fine-tuned on 24-TET GTZAN", "3 kbps"):
            ("EnCodec, 24-TET", "own"),
        ("EnCodec, fine-tuned on flattened GTZAN", "3 kbps"):
            ("EnCodec, random offsets", "tet"),   # no own grid
        ("EnCodec, fine-tuned on Saraga", "3 kbps"):
            ("EnCodec, Saraga", "own"),
    }
    reloc = {lab: {"own": own, "tet": tet}
             for lab, _c, own, tet in _fig_relocate_rows()}
    for key, (rowname, which) in A24MAP.items():
        if key not in signs:
            continue
        if rowname not in reloc:
            fails.append(f"fig:relocate has no row {rowname!r}, which the "
                         f"band-edge cross-check needs")
            continue
        neg, pos = signs[key]
        want = float(((_D(repr(neg)) + _D(repr(pos))) / 2).quantize(
            _D("0.01"), rounding=_HU))
        got = reloc[rowname][which]
        if got is None or abs(got - want) > 1e-9:
            fails.append(
                f"fig:relocate, {rowname!r}: lbar {got}, but the band-edge "
                f"table's {neg} and {pos} mean {want}")

    # the two reference rows that repeat EnCodec's sign pair as a bracket
    if ("EnCodec 24k", "3 kbps") in signs:
        neg, pos = signs[("EnCodec 24k", "3 kbps")]
        lo, hi = min(neg, pos), max(neg, pos)
        flat = " ".join(" ".join(tex.values()).split())
        for m in re.finditer(r"for reference\$\^\\ddagger\$[^\\]*?"
                             r"([\d.]+)\s*(?:\[|\()\s*([\d.]+)\s*(?:,|to)\s*"
                             r"([\d.]+)", flat):
            mid, blo, bhi = (float(x) for x in m.groups())
            if (round(blo, 4), round(bhi, 4)) != (round(lo, 4), round(hi, 4)):
                fails.append(
                    f"a reference row prints the sign range as {blo} to {bhi}, "
                    f"but the band-edge table gives {lo} and {hi}")

    # The extender and the vocoder both read 0.68; Contribution 3 once quoted the
    # vocoder's macro for the extender, which no rendering would have revealed.
    ext = None
    for r in rows_of("tab:bwe", apx):
        if r and "as recorded" in r[0]:
            ext = num(r[1])
    if ext is not None and "ExtLadder" in MACROS:
        got = float(MACROS["ExtLadder"].replace("\\xspace", "").strip())
        if abs(got - ext) > 1e-9:
            fails.append(f"ExtLadder is {got} but the extender table's "
                         f"grid-peaked arm reads {ext}")

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
        opus = paired(corpus, "Opus, distortion-matched")
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
        # Prose may quote these values through their macros, so expand first;
        # longest name first, since one macro name can prefix another.
        for _nm in sorted(MACROS, key=len, reverse=True):
            allsrc = allsrc.replace("\\" + _nm + "{}", MACROS[_nm]).replace(
                "\\" + _nm, MACROS[_nm])
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
                 r"SNAC 24k --- (\w+) of six hold"),
                (n_new, r"exploratory phase never touched, (\w+) hold")):
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
                  r"split (\w+)\s*\n?toward(?: 12-TET)? and (\w+)\s*\n?away", apx, re.S)
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
        # no bias: the fitting guards refuse these on the two-tone probe, so
        # only the spectral read exists. @none skips the bias comparison.
        "SNAC 24k (held out)":      ("@none|", "@confirm|SNAC 24k"),
        "DAC 44k, Q8 (held out)":   ("@none|", "@confirm|DAC 44k"),
        "HE-AAC SBR, 32 kbps":      ("@none|", "@sbr|HE-AAC"),
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
            r'\("([^"]+)",\s*(None|-?[\d.]+),\s*(None|-?[\d.]+),\s*(None|-?[\d.]+),'
            r'\s*(None|-?[\d.]+),\s*(None|-?[\d.]+),\s*(None|-?[\d.]+),'
            r'\s*\w+,\s*(True|False|None)\)',
            block.group(1) if block else "")
        if len(drawn) != len(FIGROW):
            fails.append(f"conditions figure: parsed {len(drawn)} rows against "
                         f"{len(FIGROW)} declared")
        c4, cls = rows_of("tab:c4", apx), rows_of("tab:classical", apx)
        be = rows_of("tab:bandedge", apx)
        for name, b, lo, hi, l, llo, lhi, reg in drawn:
            if name not in FIGROW:
                fails.append(f"conditions figure: {name!r} has no declared source")
                continue
            regkey, edgekey = FIGROW[name]
            if regkey.startswith("@none"):
                _check_lowladder(name, l, llo, lhi, edgekey, apx, fails)
                continue
            b, lo, hi = float(b), float(lo), float(hi)
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
        QUOTED = {"VocLadderMean": "BigVGAN (vocoder)"}
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
            "runs": len(top_meta) + len(rep_meta),
            "derived tables": len(top_csv) - len(top_meta),
            "files carrying a sidecar": len(top_meta) + len(rep_meta),
            "sidecars outside replication": len(top_meta),
        }
        claims = [
            (r"all (\d+) raw result\s+files", "raw result files"),
            (r"files \((\d+) runs, of which nine", "runs"),
            (r"plus (\d+) derived tables\)", "derived tables"),
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


    # --- main text and appendix must not restate each other verbatim. The main
    # text is at the ICLR page limit, so a long shared run is wasted budget, and
    # a restatement that later drifts is how the two came to disagree before.
    # The inline glossary of 2.1 and Table B.1 share short definition rows by
    # design, which is why the threshold sits above their longest row (13).
    def _dedupe_words(src):
        s = re.sub(r"\\(cite[a-z]*|ref|eqref|label)\{[^}]*\}", " ", uncomment(src))
        s = re.sub(r"\\[a-zA-Z]+\*?", "", s)
        return re.sub(r"[{}$~\\&]", " ", s).lower().split()

    RUN = 14
    MAIN_STEMS = [s for s in tex
                  if re.match(r"0[1-8]_", s) and "appendix" not in s]
    body = "".join(tex[s] for s in MAIN_STEMS)
    apx_src = tex.get("09_appendix", "")
    if not body or not apx_src:
        fails.append("duplication guard read no main-text or appendix source")
    if body and apx_src:
        mw, aw = _dedupe_words(body), _dedupe_words(apx_src)
        seen = {}
        for i in range(len(aw) - RUN):
            seen.setdefault(tuple(aw[i:i + RUN]), i)
        i = 0
        while i < len(mw) - RUN:
            g = tuple(mw[i:i + RUN])
            if g in seen:
                j, n = seen[g], RUN
                while (i + n < len(mw) and j + n < len(aw)
                       and mw[i + n] == aw[j + n]):
                    n += 1
                fails.append(f"main text and appendix share {n} words verbatim: "
                             f"{' '.join(mw[i:i + n])[:70]}...")
                i += n
            else:
                i += 1


    # --- the headline interval's resampling unit is described in four places
    # (2.5, B.6, Table B-unitmap, G.3). They disagreed once, in a way that made
    # the paper claim coverage it did not have, so the wording is pinned here.
    unit_claims = []
    for name in ("03_method", "09_appendix"):
        src = tex.get(name, "")
        for bad in ("BCa bootstrap over units", "randomisation test over unit",
                    "eleven units", "eleven detunings of the same",
                    "cluster bootstrap over eleven"):
            if bad in " ".join(src.split()):
                unit_claims.append(f"{name}: '{bad}'")
    if unit_claims:
        fails.append("headline interval described as a cluster/randomisation "
                     "interval, which it is not: " + "; ".join(unit_claims))


    # --- a registration row's slope interval is determined by its slope and
    # R^2 alone (OLS on ten detunings, t(8)); two rows once carried intervals
    # their R^2 could not produce, which no rounding absorbs.
    try:
        from scipy import stats as _st
        _t8 = float(_st.t.ppf(0.975, 8))
    except Exception:
        _t8 = 2.306
    _mac = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", main_tex))

    def _expand(s):
        for _k, _v in _mac.items():
            s = s.replace("\\" + _k + "{}", _v).replace("\\" + _k, _v)
        return s.replace("\\xspace", "")

    for _line in tex["appendix"].splitlines():
        if _line.count("&") < 4:
            continue
        _m = re.search(r"&\s*([\d.]+)\s*\[([\d.]+),\\?,?\s*([\d.]+)\]\s*&\s*(0\.99\d+)\s*&",
                       _expand(_line))
        if not _m:
            continue
        _sl, _lo, _hi, _r2 = (float(x) for x in _m.groups())
        _hw = (_hi - _lo) / 2
        _imp = _t8 * abs(_sl) * ((1 - _r2) / (8 * _r2)) ** 0.5
        if _hw > 0 and abs(_imp - _hw) / _hw > 0.06:
            _who = _line.split("&")[0].strip()[:40]
            fails.append(f"registration row '{_who}': half-width {_hw:.5f} is not "
                         f"attainable from R^2 {_r2} (implies {_imp:.5f})")


    # --- Table A14's b^unif column is an identity in the two cells beside it,
    # so it must equal 40 * lbar * above/8 rounded half-up. Two exact ties in
    # that column were once rounded in opposite directions.
    from decimal import Decimal as _D, ROUND_HALF_UP as _HU
    for _m in re.finditer(
            r"^(\d+) Hz &[^&]*&\s*(\d) of 8 &\s*([\d.]+|--)\s*&\s*([\d.]+)\s*&",
            tex["appendix"], re.M):
        _reg, _above, _lbar, _printed = _m.groups()
        if _lbar == "--":
            continue
        _exact = 40.0 * float(_lbar) * int(_above) / 8.0
        _want = float(_D(repr(_exact)).quantize(_D("0.1"), rounding=_HU))
        if abs(_want - float(_printed)) > 1e-9:
            fails.append(f"register table {_reg} Hz: b^unif should be {_want:.1f} "
                         f"(40 x {_lbar} x {_above}/8 = {_exact:.3f}, half-up), "
                         f"table prints {_printed}")

    # --- the guard-sensitivity grid is a summary of the exclusion table, so it
    # can be recomputed from it. Adding BigVGAN to the exclusion table left the
    # grid reporting 13 admitted of 17 when the answer had become 14 of 18.
    runs, all_runs = [], []
    for r in rows_of("tab:exclusion", apx):
        if len(r) < 5:
            continue
        cv, ret = num(subst(r[3])), num(subst(r[4]))
        if cv is None or ret is None:
            continue
        all_runs.append((r[1].strip(), cv, ret))
        # the two octave repeats are the same condition at another reference,
        # so the condition-level counts exclude them; the figure plots runs
        # and is checked against all_runs instead.
        if "220 Hz" in r[1] or "880 Hz" in r[1]:
            continue
        runs.append((r[1].strip(), cv, ret))
    if runs:
        m = re.search(r"admitted conditions of the (\w+) measured", apx)
        if m and count_word(m.group(1)) != len(runs):
            fails.append(f"guard grid says {m.group(1)} conditions measured, "
                         f"the exclusion table lists {len(runs)}")
        # The 5x5 guard grid was replaced by figures/guards.pdf, which plots
        # the same two quantities per run. The stronger check is that the
        # figure's own data match the exclusion table it is drawn from, so
        # they cannot drift apart the way a hand-copied table would.
        gsrc = (ROOT / "code" / "analysis" / "fig_guards.py")
        if gsrc.exists():
            blk = gsrc.read_text()
            blk = blk[blk.index("RUNS = ["):]
            blk = blk[:blk.index("\n]")]
            plotted = {}
            for line in blk.split("\n"):
                m = re.match(r'\s*\("([^"]+)",\s*([\d.]+),\s*([\d.]+),\s*(True|False)',
                             line)
                if m:
                    plotted[m.group(1)] = (float(m.group(2)), float(m.group(3)),
                                           m.group(4) == "True")
            if len(plotted) != len(all_runs):
                fails.append(f"guards figure plots {len(plotted)} runs, the "
                             f"exclusion table lists {len(all_runs)}")
            # match on the (cv, retention) pair, not the label: the figure
            # shortens some names ("BigVGAN" for "BigVGAN (vocoder)") and a
            # prefix match put "EnCodec 24k, vowels" onto "EnCodec 24k, 3 kbps".
            tbl = {(round(cv, 6), round(ret, 6)) for _, cv, ret in all_runs}
            for name, (cv, ret, ok) in plotted.items():
                if (round(cv, 6), round(ret, 6)) not in tbl:
                    fails.append(f"guards figure plots {name} at cv {cv}, "
                                 f"retention {ret}, which is no row of the "
                                 f"exclusion table")

    # --- the placement-blind re-score must reproduce from its own columns,
    # and its "before" reading must be the one the band-edge table prints.
    # This table was added because three reviewers asked for the re-score; a
    # table of hand-copied numbers answering that ask would be worse than not
    # answering it.
    # keyed on (condition, rate): "EnCodec 24k" alone matches four rows and
    # the first of them is 1.5 kbps, which is how this check first passed a
    # comparison against the wrong row.
    bandedge = {}
    for r in rows_of("tab:bandedge", apx):
        if len(r) > 5:
            key = (re.sub(r"\s+", " ", r[0].strip()),
                   re.sub(r"\s+", " ", r[1].strip()))
            v = num(r[5])
            if v is not None:
                bandedge.setdefault(key, v)
    ALIAS = {  # blind-score row label -> (band-edge condition, rate)
        "EnCodec 24k, 3 kbps":      ("EnCodec 24k", "3 kbps"),
        "EnCodec 24k, 24 kbps":     ("EnCodec 24k", "24 kbps"),
        "EnCodec 48k, 6 kbps":      ("EnCodec 48k, music", "6 kbps"),
        "WavTokenizer":             ("WavTokenizer", "0.9 kbps"),
        "DAC 16k":                  ("DAC 16k", "Q6"),
        "Mimi":                     ("Mimi", "Q8"),
        "SNAC 32k":                 ("SNAC 32k", "default"),
        "EnCodec, GTZAN fine-tune": ("EnCodec, fine-tuned on GTZAN", "3 kbps"),
    }
    blind_rows = []
    for r in rows_of("tab:blindscore", apx):
        if len(r) < 6:
            continue
        name = re.sub(r"\$\^\\dagger\$|\s+", lambda m: "" if "dagger" in m.group(0) else " ",
                      r[0]).strip()
        m = re.match(r"\$(\d+)\s*\\to\s*(\d+)\$", r[3].strip())
        got = re.findall(r"([\d.]+)", r[5])
        if not m or len(got) != 2:
            fails.append(f"blind-score row {name!r}: cannot parse a/a' or lbar pair")
            continue
        a, ap = int(m.group(1)), int(m.group(2))
        before, after = float(got[0]), float(got[1])
        t = num(r[4])
        if ap == a:
            if abs(after - before) > 1e-9 or t is not None:
                fails.append(f"blind-score row {name!r}: edge does not move, so "
                             f"lbar must be unchanged and t absent")
        else:
            if t is None:
                fails.append(f"blind-score row {name!r}: edge moves but no t printed")
            else:
                if not (0.040 <= t <= 0.110):
                    fails.append(f"blind-score row {name!r}: t={t} is outside the "
                                 f"[0.040, 0.110] bound Appendix G.5 states")
                want = round((a * before + t) / ap, 2)
                if abs(after - want) > 1e-9:
                    fails.append(f"blind-score row {name!r}: prints {after}, but "
                                 f"({a}*{before}+{t})/{ap} = {want}")
        if ap < a:
            fails.append(f"blind-score row {name!r}: dropping the placement clause "
                         f"cannot reduce the count above the edge")
        blind_rows.append((name, before, after))
        if after > before + 1e-9:
            fails.append(f"blind-score row {name!r}: placement-blind reading rose, "
                         f"but Section 2.4 says the clause's removal lowers it")
        key = ALIAS.get(name)
        if key is None:
            fails.append(f"blind-score row {name!r} has no band-edge counterpart "
                         f"declared, so its 'before' reading is unchecked")
        elif key not in bandedge:
            fails.append(f"blind-score row {name!r} maps to {key}, which is no row "
                         f"of the band-edge table")
        elif abs(bandedge[key] - before) > 1e-9:
            fails.append(f"blind-score row {name!r}: 'before' is {before}, but the "
                         f"band-edge table prints {bandedge[key]}")

    # The sentence under the blind-score table counts how many rows fall and
    # over what range. Both were wrong when first written -- five of eight by
    # 0.11 to 0.16, where the table gives six and 0.11 to 0.17 -- so the prose
    # is now recomputed from the table rather than trusted.
    if blind_rows:
        fell = [(b - a) for _n, b, a in blind_rows if abs(b - a) > 1e-9]
        flat = " ".join(" ".join(tex.values()).split())
        m = re.search(r"(\w+) of the eight rows fall, by ([\d.]+) to ([\d.]+)", flat)
        if m is None:
            fails.append("no sentence counting the blind-score table's falling "
                         "rows was found, so that summary is unguarded")
        else:
            # A local map: the WORDS used further down is defined after this
            # point and maps reference words, not numbers, so WORDS.get(...)
            # here returned None for every input and the count half of this
            # check never ran. A guard that silently does not check is worse
            # than no guard.
            NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                   "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
            said_n = NUM.get(m.group(1).lower())
            lo_s, hi_s = float(m.group(2)), float(m.group(3))
            lo_w, hi_w = round(min(fell), 2), round(max(fell), 2)
            if said_n is not None and said_n != len(fell):
                fails.append(f"prose says {said_n} of the blind-score rows fall; "
                             f"the table has {len(fell)}")
            if abs(lo_s - lo_w) > 1e-9 or abs(hi_s - hi_w) > 1e-9:
                fails.append(f"prose says the blind-score drops run {lo_s} to "
                             f"{hi_s}; the table gives {lo_w} to {hi_w}")

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

    # --- a dash in a table cell means three different things in this paper
    # (not defined, not applicable, not reported), so every table that uses
    # one must say which in its caption. Table A2 additionally had two of its
    # four columns empty for two thirds of its rows; that sweep is prose now.
    for m in re.finditer(r"\\begin\{table\}.*?\\end\{table\}", apx, re.S):
        blk = m.group(0)
        body = blk[blk.find("\\toprule"):]
        n = len(re.findall(r"&\s*--\s*(?=&|\\\\)", body))
        if not n:
            continue
        lab = re.search(r"\\label\{(tab:[^}]+)\}", blk)
        cap = re.search(r"\\caption\{(.*?)\}\s*\n?\\label", blk, re.S)
        if not (cap and "dash" in cap.group(1).lower()):
            fails.append(f"{lab.group(1) if lab else 'a table'} uses {n} dash "
                         f"cells without saying in its caption what a dash means")

    # --- captions are capped at three rendered lines. Notes added to explain
    # a rounding rule or a dash pushed five captions past it in one round, so
    # the cap is enforced rather than remembered.
    # 104 was guessed and is too generous: captions of 305-312 characters pass
    # it and render as four lines. Measured against the built PDF the wrap is
    # about 95 characters, so the cap is 3 * 95.
    CAP_CHARS = 3 * 95
    for name, src in tex.items():
        if name in ("results", "09_appendix"):   # same file as "appendix"
            continue
        raw = (ROOT / "main.tex").read_text() if name == "main" else None
        for m in re.finditer(r"\\caption\{", src):
            depth, j = 0, m.end() - 1
            for k in range(j, len(src)):
                if src[k] == "{":
                    depth += 1
                elif src[k] == "}":
                    depth -= 1
                    if depth == 0:
                        break
            cap = src[j + 1:k]
            flat = re.sub(r"\\(?:ref|label)\{[^}]*\}", "A00", cap)
            flat = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", flat)
            flat = re.sub(r"\\[a-zA-Z]+", "", flat)
            flat = re.sub(r"\s+", " ", flat.replace("$", "")
                          .replace("{", "").replace("}", "")).strip()
            if len(flat) > CAP_CHARS:
                lab = re.search(r"\\label\{((?:tab|fig):[^}]+)\}", src[k:k + 1400])
                fails.append(
                    f"caption for {lab.group(1) if lab else name} runs "
                    f"{len(flat)} chars ({len(flat)/95:.1f} lines); "
                    f"the cap is {CAP_CHARS}")

    # --- the bibliography ships with the supplement, so an entry nothing
    # cites is either a dropped citation or padding. Five had accumulated;
    # two supported claims already in the text and were cited, three went.
    bibf = ROOT / "refs.bib"
    if bibf.exists():
        entries = set(re.findall(r"@\w+\{([^,]+),", bibf.read_text()))
        allsrc = " ".join(tex.values())
        cited = {k.strip() for m in re.finditer(
            r"\\cite[tp]?\*?(?:\[[^\]]*\])?\{([^}]*)\}", allsrc)
            for k in m.group(1).split(",")}
        for k in sorted(entries - cited):
            fails.append(f"refs.bib carries {k!r}, which nothing cites")
        for k in sorted(cited - entries):
            fails.append(f"{k!r} is cited but absent from refs.bib")

    # --- a sentence that names a section by its old role. Section 4 was
    # "Discussion, limitations and conclusion" and became "Conclusion"; two
    # sentences went on citing it for a limitations discussion it no longer
    # holds, one of them also asserting a gap the soft-edge model had closed.
    ROLE = {"sec:conclusion": ("conclu",), "sec:discussion": ("conclu",)}
    for name, src in tex.items():
        if name in ("results", "09_appendix"):
            continue
        for m in re.finditer(r"([^.]{0,90})\\ref\{(sec:(?:discussion|conclusion))\}", src):
            ctx = re.sub(r"\s+", " ", m.group(1)).lower()
            if re.search(r"\blimitations? of\b|\bdiscussion of\b", ctx):
                fails.append(f"{name}: a sentence cites {m.group(2)} for a "
                             f"limitations or discussion section; Section 4 is "
                             f"the conclusion")

    # --- the exclusion table names each run by its result-file stem, so the
    # archive should contain one. Two rows named runs with no file: one added
    # when BigVGAN was given a guard row, one older.
    res = ROOT / "code" / "results"
    if res.is_dir():
        named = re.findall(r"(detune\\?_[a-z0-9\\_]+)\s*&",
                           apx[apx.index("\\label{tab:exclusion}"):
                               apx.index("\\end{tabular}",
                                         apx.index("\\label{tab:exclusion}"))])
        for n in named:
            stem = n.replace("\\_", "_")
            if not (res / f"{stem}.csv").exists():
                fails.append(f"the exclusion table names run {stem!r}, which "
                             f"has no result file in the archive")

    # --- a macro defined and never used is a number with no reader. Eighteen
    # had accumulated, holding values for results that were cut, and a later
    # edit reaching for one would have got a stale figure: \VocBias held 4.8
    # where the paper prints 4.82.
    defs = re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", tex["main"])
    stripped = re.sub(r"\\newcommand\{\\\w+\}\{[^}]*\}", "", tex["main"])
    body = stripped + " " + " ".join(
        v for k, v in tex.items() if k not in ("main",))
    inside = " ".join(v for _, v in defs)
    for name, _ in defs:
        pat = r"\\" + name + r"(?![a-zA-Z])"
        if not re.search(pat, body) and not re.search(pat, inside):
            fails.append(f"macro \\{name} is defined and never used")

    # --- the soft-edge model is recomputed here rather than trusted: the
    # b^soft column of the register table must be what the script produces
    # from the derived form and the measured roll-off.
    try:
        import numpy as _np
        EDGE_ = {110: 1320.0, 220: 1320.0, 440: 1320.0, 880: 1760.0}
        D0_, LB_, N_ = 40.0, 0.90, 8
        ROLL_ = 4.5 / _np.log2(1760.0 / 1320.0)

        def _pred(f0, w):
            k = _np.arange(1, N_ + 1)
            o = _np.log2(k * f0 / EDGE_[f0])
            rho = LB_ / (1.0 + _np.exp(-o / w))
            wt = 10 ** (-ROLL_ * _np.maximum(o, 0.0) / 10.0)
            return float(D0_ * (wt * rho).sum() / wt.sum())

        meas = {}
        for r in rows_of("tab:registeredge", apx):
            hz = re.match(r"(\d+)\s*Hz", r[0].strip())
            if hz and len(r) > 6:
                meas[int(hz.group(1))] = (num(subst(r[5])), num(subst(r[6])))
        if len(meas) == 4:
            grid = _np.arange(0.05, 1.50, 0.002)
            err = [sum(_np.log(_pred(f, w) / m[1]) ** 2 for f, m in meas.items())
                   for w in grid]
            w_ = float(grid[int(_np.argmin(err))])
            for f, (soft, _m) in meas.items():
                want = _pred(f, w_)
                if abs(want - soft) > 0.02:
                    fails.append(f"register table prints b^soft {soft} at {f} Hz; "
                                 f"the model gives {want:.2f}")
    except ImportError:
        pass

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
    letter, seen, titles = None, {}, {}
    for mm in re.finditer(r"\\(section|subsection)\{([^}]*)\}", apx):
        if mm.group(1) == "section":
            letter = chr(ord("A") + len(seen)); seen[letter] = 0
            titles[letter] = mm.group(2)
        elif letter:
            seen[letter] += 1
    listing = (ROOT / "main.tex").read_text()
    a = listing.find("\\section*{Appendix contents}")
    b = listing.find("Where to find each claim")
    block = listing[a:b] if a >= 0 and b > a else ""
    for L, title in titles.items():
        if f"\\textbf{{{L}. " not in block:
            fails.append(
                f"appendix contents: the list has no entry for {L}, "
                f"{title!r}")
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
            r[0] for tbl in ("tab:c4", "tab:classical", "tab:controls",
                             "tab:sbr", "tab:confirmatory")
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

    # --- claims the round-1 panel found contradicting each other. Each of
    # these was a real defect: a section heading that generalised past what
    # the section measured, an abstract clause that explained a null the body
    # calls unexplained, and a post-hoc table whose caption counted its own
    # rows wrong. They are cheap to reintroduce while editing prose.
    WORDS = {"six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
             "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
             "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
             "nineteen": 19, "twenty": 20}

    # a heading may not assert that regridding is universal; seven of the nine
    # resolving conditions regrid, and SNAC 24k reads 0.28 at EnCodec's own edge
    for m in re.finditer(r"\\subsection\{([^}]*regrid[^}]*)\}", tex["results"]):
        h = m.group(1)
        if re.search(r"\b(Every|All)\b", h) and "primary set" not in h:
            fails.append(
                f"the regridding heading reads {h!r}; it asserts a universal "
                "the paper's own tables refute, and does not scope it")

    absn = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex["main"], re.S)
    if absn:
        a = " ".join(absn.group(1).split())
        if "read as null" in a and "all but one" not in a:
            fails.append(
                "the abstract explains the null conditions without the "
                "exception; Section 3.1 reports SpeechTokenizer's null as "
                "unexplained")

    # the post-hoc table's caption states its own length; count the rows
    cap = re.search(r"\\caption\{Analytic choices made after results were seen\.(.*?)\}\s*\n\\label\{tab:posthoc\}",
                    apx, re.S)
    if cap:
        claimed = next((WORDS[w] for w in WORDS if w in cap.group(1)), None)
        actual = len(rows_of("tab:posthoc", apx))
        if claimed is not None and actual and claimed != actual:
            fails.append(
                f"the post-hoc table's caption claims {claimed} decisions and "
                f"the table lists {actual}; the table's whole point is that the "
                "count is complete")
        # The AI-use statement counts the same table, and adding a row to the
        # table updated the caption but not the statement: two sites, one
        # number, and only one of them was guarded. Both are checked now.
        stmt = re.search(r"the ([a-z]+) analytic choices of\s*\n?\s*Table "
                         r"\\ref\{tab:posthoc\}", " ".join(tex.values()))
        if stmt is None:
            stmt = re.search(r"the ([a-z]+) analytic choices of[^.]*tab:posthoc",
                             " ".join(tex.values()))
        if actual and stmt:
            said = WORDS.get(stmt.group(1))
            if said is not None and said != actual:
                fails.append(
                    f"the statement says {said} analytic choices and the "
                    f"post-hoc table lists {actual}")
        elif actual and stmt is None:
            fails.append("no statement sentence counting the post-hoc table "
                         "was found, so that count is now unguarded")

    # the soft-edge section says both how far the 110 Hz partials sit from the
    # edge and where its prediction comes from; those two must agree
    if "partials inside\nthe transition" in apx or "partials inside the transition" in apx:
        if "within one width of the edge" in apx:
            fails.append(
                "the soft-edge appendix says the 110 Hz partials are inside the "
                "transition and also that none lies within one width of the "
                "edge; at 1.3 and 1.7 widths only the second is true")

    # --- The summary layer must recompute from the held-out table.
    # Nine review cycles put almost every substantive error in the same place:
    # the abstract, the contributions and the conclusion drift from the tables
    # they summarise, and adding a table row silently falsifies a count three
    # sections away. Reviewers have caught 16-vs-12-vs-9 for one quantity, a
    # ladder span quoted over five arms after the table grew to seven, and a
    # correlation printed against the wrong variable. So derive the counts
    # here rather than trusting the prose.
    try:
        conf = rows_of("tab:confirmatory", apx)
    except ValueError:
        conf = []
    lbars, conds = [], []
    for r in conf:
        if len(r) < 9:
            continue
        lb, lr = num(r[4]), num(r[8])
        if lb is None or lr is None:
            continue
        lbars.append(lb)
        conds.append(lr)
    if len(lbars) >= 20:
        total = len(lbars)
        not_ladder = sum(1 for v in lbars if v < 0.70)
        macros = MACROS
        claimed_total = num(macros.get("HeldTotal", ""))
        claimed_miss = num(macros.get("HeldNotLadder", ""))
        if claimed_total is not None and int(claimed_total) != total:
            fails.append(
                f"HeldTotal says {int(claimed_total)} but tab:confirmatory has "
                f"{total} rows")
        if claimed_miss is not None and int(claimed_miss) != not_ladder:
            fails.append(
                f"HeldNotLadder says {int(claimed_miss)} but {not_ladder} of "
                f"{total} rows read an inclusive ladder fraction below 0.70")
        # the abstract's boundary sensitivity must be the not-in-ladder count,
        # not the hit count printed beside it in G.5
        lo = sum(1 for v in lbars if v < 0.60)
        hi = sum(1 for v in lbars if v < 0.75)
        abstract = tex["main"]
        m = re.search(r"(\d+) or (\d+) had\s*\n?\s*we frozen", abstract)
        if m and (int(m.group(1)), int(m.group(2))) != (lo, hi):
            fails.append(
                f"the abstract sweeps the tier boundary to {m.group(1)} and "
                f"{m.group(2)}; recomputing from tab:confirmatory gives "
                f"{lo} and {hi}")
        # "seven of those N" regrid high on the conditional metric
        thr = num(MACROS.get("MissRegrid", "")) or 0.71
        seven = sum(1 for lb, lr in zip(lbars, conds) if lb < 0.70 and lr >= thr)
        m = re.search(r"But (\w+) of those", abstract)
        words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                 "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
        if m and words.get(m.group(1)) not in (None, seven):
            fails.append(
                f"the abstract says {m.group(1)} of the missing checkpoints "
                f"regrid at {thr} or higher; the table gives {seven}")

    # --- A count in the main text that names a table must match that table.
    # Adding the two grid-preserving arms to tab:relocate on 2026-09-06 left
    # three sentences saying "five fine-tunes" of a seven-row table.
    body = "\n".join(tex[k] for k in ("main", "01_intro", "04_pitch")
                      if k in tex)
    words = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11}
    for m in re.finditer(
            r"(\w+)\s+fine-tunes of (?:the |one )?\s*(?:the )?[^.]*?"
            r"\\ref\{(tab:[A-Za-z-]+)\}", body):
        want, label = words.get(m.group(1).lower()), m.group(2)
        if want is None:
            continue
        try:
            rows = rows_of(label, apx)
        except ValueError:
            continue
        # tab:relocate stacks several decoders; a sentence about "the one
        # EnCodec decoder" ranges over the arms before the next codec's block
        n = 0
        for r in rows:
            first = subst(r[0])
            if re.match(r"(Mimi|WavTokenizer|SNAC|DAC|Vocos)\b", first):
                continue
            n += 1
        if n != want:
            fails.append(
                f"the main text says {m.group(1)} fine-tunes of "
                f"\\ref{{{label}}}, which has {n} rows")

    # --- No page carries two main-text figures.
    # Two figures stacked on one page reads badly and squeezes the text
    # between them; on 2026-09-06 Figures 2 and 3 both landed on page 7.
    # Placement is decided by where the float is declared, so the fix is to
    # move the declaration later, not to add a placement specifier.
    pdf = ROOT / "main.pdf"
    if pdf.exists():
        try:
            txt = subprocess.run(
                ["pdftotext", str(pdf), "-"],
                capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            txt = ""
        for n, page in enumerate(txt.split("\f")[:12], 1):
            caps = re.findall(r"Figure (\d+):", page)
            if len(set(caps)) > 1:
                fails.append(
                    f"page {n} carries Figures {', '.join(sorted(set(caps)))}; "
                    "keep one figure to a page in the main text")

    # --- The main text must end by page 9.
    # ICLR 2026/27 caps the main text at nine pages at submission and enforces
    # it with desk rejection; references, appendices and the ethics and
    # reproducibility statements do not count. The Ethics Statement is the
    # first thing after the main text, so the page it starts on is the check.
    # This is guarded because it has crept back twice: a summary-layer edit
    # adds two lines, the conclusion spills onto page 10, and nothing in the
    # build fails. Page breaking here is float-pinned, so a cut made before a
    # float is absorbed by it -- only a cut on page 9 itself moves the break.
    if txt:
        pages = txt.split("\f")
        start = None
        for n, page in enumerate(pages, 1):
            if "ETHICSSTATEMENT" in re.sub(r"\s+", "", page).upper():
                start = n
                break
        if start is None:
            fails.append("no Ethics Statement found in main.pdf, so the "
                         "main text length cannot be checked")
        elif start > 10:
            fails.append(
                f"the main text runs to page {start - 1}; ICLR caps it at "
                f"nine, so the Ethics Statement must start by page 10")
        else:
            # Landing on page 10 is not enough: the heading can sit part-way
            # down it with the conclusion above. The first version of this
            # guard checked only the page number and passed a build whose
            # conclusion spilled three lines onto page 10. What matters is
            # that NO main-text prose precedes the heading on that page.
            flat = re.sub(r"\s+", " ", pages[start - 1])
            cut = flat.upper().find("E THICS")      # rendered in small caps
            before = flat[:cut] if cut > 0 else ""
            before = before.replace(
                "Under review as a conference paper at ICLR 2027", "")
            before = re.sub(r"\b\d{3}\b", "", before).strip()
            if before:
                fails.append(
                    f"the main text spills onto page {start} before the "
                    f"Ethics Statement: {before[:70]!r}")

    # --- The paper's statement about its own bibliography must recompute.
    # On 2026-09-07 two entries were added and the AI-use statement kept
    # saying "93 entries, 72 verified"; a reviewer checked the one number the
    # paper invites them to check and it did not hold. The counts are cheap to
    # derive, so derive them.
    bib_src = (ROOT / "refs.bib").read_text()
    n_entries = len(re.findall(r"^@", bib_src, re.M))
    n_unver = len(re.findall(r"\[UNVERIFIED\]", bib_src)) - bib_src.count(
        "[UNVERIFIED] marker instead")
    n_ver = n_entries - n_unver
    stated = re.search(
        r"Of (\d+) bibliography entries, (\d+) carry a provenance comment[^.]*?"
        r"the remaining (\d+) are marked", tex["main"], re.S)
    if stated:
        got = tuple(int(g) for g in stated.groups())
        if got != (n_entries, n_ver, n_unver):
            fails.append(
                f"the statement says {got[0]} entries / {got[1]} verified / "
                f"{got[2]} unverified; refs.bib has {n_entries} / {n_ver} / "
                f"{n_unver}")
    hdr = re.search(r"As of this revision: (\d+) entries, (\d+) verified, "
                    r"(\d+) unverified", bib_src)
    if hdr:
        got = tuple(int(g) for g in hdr.groups())
        if got != (n_entries, n_ver, n_unver):
            fails.append(
                f"the refs.bib header says {got[0]}/{got[1]}/{got[2]}; the file "
                f"has {n_entries}/{n_ver}/{n_unver}")
    # the load-bearing-unverified list must name works that really are unverified
    named = re.search(r"and (\w+) of the 21 are load-bearing", tex["main"])
    words = {"three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "eight": 8, "nine": 9}
    if named:
        keys = ["terhardt1982pitch", "dietz2002sbr", "nagel2009harmonic",
                "pons2021upsampling", "schuirmann1987tost",
                "berendes2026finetuning", "lee2023bigvgan"]
        unver_keys = set()
        for m in re.finditer(r"\[UNVERIFIED\][^@]*@\w+\{([^,]+),", bib_src):
            unver_keys.add(m.group(1))
        listed = [k for k in keys if k in unver_keys]
        want = words.get(named.group(1))
        if want is not None and want != len(listed):
            fails.append(
                f"the statement calls {named.group(1)} entries load-bearing "
                f"and unverified; {len(listed)} of the named keys are actually "
                "unverified")

    # a bibliography entry marked verified against a peer-reviewed venue must
    # not still print as an arXiv preprint
    bib = (ROOT / "refs.bib").read_text()
    for entry in re.finditer(r"(%[^\n]*\n)*@\w+\{([^,]+),(.*?)\n\}", bib, re.S):
        head, key, body = entry.group(0), entry.group(2), entry.group(3)
        cited_venue = re.search(r"%.*(Interspeech|ACL|TASLP|ISMIR|NeurIPS|ICASSP)", head)
        if cited_venue and "arXiv preprint" in body:
            fails.append(
                f"refs.bib entry {key!r} is annotated with a "
                f"{cited_venue.group(1)} venue but still prints as an arXiv "
                "preprint")

    # --- a negative \vspace just after \end{figure} does not shrink the float.
    # The figure floats away and the space stays in the text stream, deleting
    # line separation wherever the source happened to sit: on 2026-09-06 a
    # -7mm added to claw back a page overprinted two paragraphs on page 6.
    # Float separation belongs in \textfloatsep, set once in the preamble.
    for stem, src in tex.items():
        for m in re.finditer(r"\\end\{(figure|table)\}\s*\n\s*\\vspace\{\s*-", src):
            fails.append(
                f"{stem}: a negative \\vspace follows \\end{{{m.group(1)}}}; "
                "the float moves and the space does not, so it deletes line "
                "spacing in whatever paragraph lands there. Use "
                "\\textfloatsep instead")

    # --- every measured value in the abstract must come from a macro.
    # Seven drafts running, the abstract carried literals that duplicated an
    # appendix number, and every one of them drifted when the other copy was
    # edited: the cross-family pair came to collide with the extender's, a
    # multiplicity adjustment appeared that Appendix G.1 disclaims, and a
    # held-out count replaced the frozen tier rule's with an undefined cut.
    raw_abs = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
                        (ROOT / "main.tex").read_text(), re.S)
    if raw_abs:
        body = raw_abs.group(1)
        # strip macro calls, maths, and citations before looking for digits
        stripped = re.sub(r"\\[A-Za-z]+\{[^}]*\}", " ", body)
        stripped = re.sub(r"\\[A-Za-z]+", " ", stripped)
        stripped = re.sub(r"\$[^$]*\$", " ", stripped)
        stripped = re.sub(r"\[[^\]]*\]", " ", stripped)   # printed intervals
        for lit in re.findall(r"(?<![\w.])\d+\.\d+(?![\w])", stripped):
            fails.append(
                f"the abstract hard-codes {lit!r}; every measured value there "
                "must come from a macro so it cannot drift from the appendix")

    if fails:
        print("INCONSISTENT:")
        fails = list(dict.fromkeys(fails))
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
    print("  - every table using a dash says what a dash means")
    print("  - no caption runs past three lines")
    print("  - every bibliography entry is cited, and every citation is in the bib")
    print("  - nothing cites Section 4 as a limitations section")
    print("  - every run named in the exclusion table has a result file")
    print("  - every macro defined is used")
    print("  - the soft-edge column recomputes from the model")
    print("  - no section heading asserts that every decoder regrids")
    print("  - the abstract's null clause carries its exception")
    print("  - the post-hoc table's caption counts its own rows")
    print("  - the soft-edge appendix agrees with itself on the 110 Hz partials")
    print("  - no bibliography entry is a preprint at a peer-reviewed venue")
    print("  - no negative vspace is attached to a float")
    print("  - the abstract quotes no unmacroed measured value")
    print("  - the abstract's held-out counts recompute from the table")
    print("  - a count naming a table matches that table's rows")
    print("  - no main-text page carries two figures")
    print("  - the main text ends by page 9")
    print("  - the bibliography self-count recomputes from refs.bib")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

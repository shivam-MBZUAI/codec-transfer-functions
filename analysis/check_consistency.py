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
    for r in rows_of("tab:universal", main_tex):
        m_stim = re.search(r"\(([a-z]+)\)", r[0])
        k = keyof(r[0], r[1], m_stim.group(1) if m_stim else "")
        if k not in t7:
            continue
        a, b = num(r[4]), num(t7[k][2])
        if a is None or b is None:
            continue
        if abs(a - b) > 0.0011:
            fails.append(f"slope for {k}: Table 1 {a} vs Table A7 {b}")


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
        m = re.search(r"([\d.]+) to ([\d.]+) across four registers", (ROOT / "main.tex").read_text())
        if not m:
            fails.append("abstract: no register range found")
        elif abs(float(m.group(1)) - lo) > 0.06 or abs(float(m.group(2)) - hi) > 0.06:
            fails.append(
                f"abstract quotes {m.group(1)} to {m.group(2)} across registers, "
                f"the table gives {lo:.2f} to {hi:.2f}")

    if fails:
        print("INCONSISTENT:")
        for f in fails:
            print("  -", f)
        return 1
    print("consistent:")
    print("  - the uniform-weight table reproduces from the per-partial displacements")
    print("  - Table 1 slopes agree with the full registration table")
    print("  - the grid-attributable costs are the stated differences of paired differences")
    print("  - each retuning arm lands within 3 cents of its prediction")
    print("  - the per-register table satisfies Equation 16 row by row")
    print("  - the abstract's register range is that table's bias column")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Where is each codec's band edge? Summary of results/spectral_sweep.csv.

For every codec in the CSV written by experiments/spectral_sweep.py this
prints and tabulates:

  1. the band edge: partial frequencies f_k are pooled over references, reps
     and nonzero detunings and sorted into 200 Hz bins; the edge is the lowest
     bin whose median |peak shift| exceeds 10 cents and stays above 10 cents
     in the next two populated bins. Alongside it, the fraction of partials
     below the edge that shifted by less than 2 cents and the fraction above
     it that shifted by more than 10. The first crossing without the
     hold-for-two-bins rule is reported too: the transition is not always
     monotonic, and a bin populated by a single register can sit flat
     between two shifted bins;
  2. for the shifted partials (|shift| > 10 c, delta != 0), the median of
     shift / (-delta): 1 means the partial landed exactly on the harmonic of
     the nearest 12-TET pitch, 0 means it stayed put;
  3. the blind estimator's reading of the decoded tone with 8 and with 2
     partials at |delta| = 40, medians per sign and pooled as a pull toward
     the grid;
  4. the largest |shift| of the fundamental over everything, including
     delta = 0.

Shifts are read relative to the input's own measured peak (peak_shift_cents
minus in_peak_cents). For synthetic tones that changes nothing beyond a few
hundredths of a cent; for real notes it removes the note's tuning and
inharmonicity.

Figures: figures/band_edge.pdf, one panel per codec, and
figures/band_edge_vs_rate.pdf for the EnCodec bitrate series.

    python analysis/analyze_spectral.py [results/spectral_sweep.csv]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent

OKABE = {"enc": "#0072B2", "dac": "#E69F00", "mimi": "#009E73", "spt": "#D55E00",
         "opus": "#CC79A7", "grey": "#666666"}
BIN_HZ = 200.0
EDGE_CENTS = 10.0     # a partial that moved this far is "shifted"
FLAT_CENTS = 2.0      # a partial that moved less than this is "in place"
FONT = 7

TEXT_COLS = ("codec", "rate_label", "stimulus", "sample_rate")
SUMMARY_FIELDS = ["codec", "rate_label", "stimulus", "sample_rate", "n_tones", "n_partials",
                  "edge_hz", "edge_first_fk_hz", "first_cross_hz", "frac_flat_below", "frac_shifted_above",
                  "n_shifted", "grid_fraction", "est8_m40", "est8_p40", "est2_m40", "est2_p40",
                  "est8_toward_grid", "est2_toward_grid", "h1_max_abs_shift"]


def load(path: Path) -> dict:
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit(f"{path} has no rows")
    cols = {}
    for name in rows[0]:
        vals = [r[name] for r in rows]
        if name in TEXT_COLS:
            cols[name] = np.array(vals)
        else:
            cols[name] = np.array([float(v) if v not in ("", "nan") else np.nan for v in vals])
    cols["label"] = np.array([f"{c} {r} @{int(float(sr))} Hz" for c, r, sr in zip(cols["codec"], cols["rate_label"], cols["sample_rate"])])
    cols["shift"] = cols["peak_shift_cents"] - cols["in_peak_cents"]
    return cols


def select(cols: dict, mask: np.ndarray) -> dict:
    return {k: v[mask] for k, v in cols.items()}


def colour(codec_name: str) -> str:
    for key, tag in (("encodec", "enc"), ("dac", "dac"), ("mimi", "mimi"),
                     ("speechtokenizer", "spt"), ("opus", "opus"), ("mp3", "opus")):
        if codec_name.startswith(key):
            return OKABE[tag]
    return OKABE["grey"]


# ---- the band edge --------------------------------------------------------

def bin_medians(f: np.ndarray, shift: np.ndarray, bin_hz: float, min_n: int):
    """Lower edge of every populated bin and the median |shift| in it."""
    b = np.floor(f / bin_hz).astype(int)
    edges, meds, counts = [], [], []
    for i in np.unique(b):
        m = b == i
        if m.sum() < min_n:
            continue
        edges.append(i * bin_hz)
        meds.append(float(np.median(np.abs(shift[m]))))
        counts.append(int(m.sum()))
    return np.array(edges), np.array(meds), np.array(counts)


def band_edge(f: np.ndarray, shift: np.ndarray, *, bin_hz: float = BIN_HZ,
              thresh: float = EDGE_CENTS, min_n: int = 1, hold: int = 2) -> tuple[float, float]:
    """(lower edge of the first bin that qualifies, lowest shifted f_k in it).

    Qualifies: median |shift| > thresh here and in the next `hold` populated
    bins. Empty bins (a high register's partials are 880 Hz apart) are
    skipped rather than counted as a failure of the "stays above" test.
    hold=0 gives the first crossing, which is what to compare when the
    transition is not monotonic: a bin populated by one register alone can
    sit flat between two shifted bins and push the held edge up by a bin
    or two.
    """
    edges, meds, _ = bin_medians(f, shift, bin_hz, min_n)
    for j in range(len(edges) - hold):
        if np.all(meds[j:j + hold + 1] > thresh):
            in_bin = (f >= edges[j]) & (f < edges[j] + bin_hz) & (np.abs(shift) > thresh)
            return float(edges[j]), float(f[in_bin].min()) if in_bin.any() else np.nan
    return np.nan, np.nan


# ---- per-codec summary ----------------------------------------------------

def per_tone(d: dict) -> dict:
    """One row per decoded tone (k == 1 carries the tone-level columns)."""
    return select(d, d["k"] == 1)


def med(v: np.ndarray) -> float:
    v = v[np.isfinite(v)]
    return float(np.median(v)) if v.size else np.nan


def summarise(d: dict, *, bin_hz: float, min_n: int) -> dict:
    """The table row for one (codec, stimulus) group."""
    nz = d["delta_cents"] != 0.0
    f, s = d["f_k_hz"][nz], d["shift"][nz]
    edge, first_fk = band_edge(f, s, bin_hz=bin_hz, min_n=min_n)
    first_cross, _ = band_edge(f, s, bin_hz=bin_hz, min_n=min_n, hold=0)
    below, above = f < edge, f >= edge
    shifted = nz & (np.abs(d["shift"]) > EDGE_CENTS)
    tones = per_tone(d)
    m40, p40 = tones["delta_cents"] == -40.0, tones["delta_cents"] == 40.0
    # Pull toward the grid: the grid harmonic sits at -delta, so a reading of
    # -delta is a full pull and the sign is folded out with sign(-delta).
    toward = -np.sign(tones["delta_cents"])
    big = np.abs(tones["delta_cents"]) == 40.0
    return dict(
        codec=d["codec"][0], rate_label=d["rate_label"][0], stimulus=d["stimulus"][0],
        sample_rate=int(d["sample_rate"][0]), n_tones=int(tones["k"].size), n_partials=int(d["k"].size),
        edge_hz=edge, edge_first_fk_hz=first_fk, first_cross_hz=first_cross,
        frac_flat_below=float((np.abs(s[below]) < FLAT_CENTS).mean()) if below.any() else np.nan,
        frac_shifted_above=float((np.abs(s[above]) > EDGE_CENTS).mean()) if above.any() else np.nan,
        n_shifted=int(shifted.sum()),
        grid_fraction=med(d["shift"][shifted] / (-d["delta_cents"][shifted])),
        est8_m40=med(tones["est8_cents"][m40]), est8_p40=med(tones["est8_cents"][p40]),
        est2_m40=med(tones["est2_cents"][m40]), est2_p40=med(tones["est2_cents"][p40]),
        est8_toward_grid=med((tones["est8_cents"] * toward)[big]),
        est2_toward_grid=med((tones["est2_cents"] * toward)[big]),
        h1_max_abs_shift=float(np.nanmax(np.abs(tones["shift"]))))


def fmt(v, spec: str = ".2f") -> str:
    return "  n/a" if v is None or (isinstance(v, float) and not np.isfinite(v)) else format(v, spec)


def print_group(row: dict, edges, meds, counts, show_bins: bool) -> None:
    print(f"\n{row['codec']} {row['rate_label']} ({row['stimulus']}, {row['sample_rate']} Hz): "
          f"{row['n_tones']} tones, {row['n_partials']} partials")
    print(f"  band edge          {fmt(row['edge_hz'], '.0f')} Hz bin (lowest shifted partial "
          f"{fmt(row['edge_first_fk_hz'], '.0f')} Hz); below: {fmt(100 * row['frac_flat_below'], '.0f')}% "
          f"within {FLAT_CENTS:g} c; above: {fmt(100 * row['frac_shifted_above'], '.0f')}% beyond {EDGE_CENTS:g} c")
    if row["first_cross_hz"] != row["edge_hz"] and np.isfinite(row["first_cross_hz"]):
        print(f"  first crossing     {row['first_cross_hz']:.0f} Hz bin: the median dips back below "
              f"{EDGE_CENTS:g} c between there and the held edge (see --show-bins)")
    print(f"  shifted partials   n = {row['n_shifted']}, median shift/(-delta) = "
          f"{fmt(row['grid_fraction'])} (1 = on the grid harmonic)")
    print(f"  estimator |delta|=40   est8: {fmt(row['est8_m40'], '+.2f')} c at -40, "
          f"{fmt(row['est8_p40'], '+.2f')} c at +40 (toward grid {fmt(row['est8_toward_grid'], '+.2f')});   "
          f"est2: {fmt(row['est2_m40'], '+.2f')} / {fmt(row['est2_p40'], '+.2f')} "
          f"(toward grid {fmt(row['est2_toward_grid'], '+.2f')})")
    print(f"  fundamental        max |shift| {fmt(row['h1_max_abs_shift'])} c over all tones and deltas")
    if show_bins:
        print("  bin medians (Hz: |shift| c, n): "
              + ", ".join(f"{e:.0f}: {m:.1f} ({n})" for e, m, n in zip(edges, meds, counts)))


# ---- figures --------------------------------------------------------------

def figure_band_edge(groups: list[tuple[dict, dict]], out: Path, bin_hz: float, min_n: int) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = len(groups)
    ncols = 3
    nrows = max(2, int(np.ceil(n / ncols)))
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.5, 3.6 * nrows / 2),
                             sharex=True, sharey=True, squeeze=False)
    y_max = 60.0
    for ax, (row, d) in zip(axes.ravel(), groups):
        nz = d["delta_cents"] != 0.0
        f, s = d["f_k_hz"][nz] / 1000.0, np.minimum(np.abs(d["shift"][nz]), y_max)
        ax.scatter(f, s, s=4, alpha=0.35, color=colour(row["codec"]), lw=0, rasterized=True,
                   label="partial")
        edges, meds, _ = bin_medians(d["f_k_hz"][nz], d["shift"][nz], bin_hz, min_n)
        if edges.size:
            ax.step(np.append(edges, edges[-1] + bin_hz) / 1000.0, np.append(meds, meds[-1]),
                    where="post", color="black", lw=1.0, label=f"{bin_hz:.0f} Hz bin median")
        ax.axhline(EDGE_CENTS, color="0.6", lw=0.6, ls=":")
        title = f"{row['codec']} {row['rate_label']}"
        if np.isfinite(row["edge_hz"]):
            ax.axvline(row["edge_hz"] / 1000.0, color="0.3", lw=0.9, ls="--", label="band edge")
            title += f", edge {row['edge_hz'] / 1000.0:.1f} kHz"
        else:
            title += ", no edge"
        ax.set_title(title, fontsize=FONT)
        ax.tick_params(labelsize=FONT - 1)
        ax.grid(alpha=0.2)
    for ax in axes.ravel()[n:]:
        ax.axis("off")
    # With sharex the tick labels live on the bottom row, which may be
    # switched off; put them on the lowest panel actually drawn per column.
    for c in range(ncols):
        drawn = [axes[r][c] for r in range(nrows) if r * ncols + c < n]
        if drawn:
            drawn[-1].set_xlabel("partial frequency (kHz)", fontsize=FONT)
            drawn[-1].tick_params(labelbottom=True)
    for ax in axes[:, 0]:
        ax.set_ylabel("|peak shift| (cents)", fontsize=FONT)
    axes[0][0].set_ylim(-1, y_max + 2)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=FONT - 1, frameon=False, loc="lower center", ncol=3)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    fig.savefig(out.with_suffix(".png"), dpi=200)
    print(f"\nfigure written to {out}")


def figure_edge_vs_rate(rows: list[dict], out: Path) -> None:
    """Band edge against bitrate for the plain EnCodec series (labels 'Xkbps')."""
    pts = sorted((float(r["rate_label"][:-4]), r["edge_hz"]) for r in rows
                 if r["codec"] == "encodec" and r["rate_label"].endswith("kbps")
                 and r["stimulus"] == "tone")
    if not pts:
        print("no EnCodec tone rows; band_edge_vs_rate skipped")
        return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rates = np.array([p[0] for p in pts])
    edges = np.array([p[1] for p in pts]) / 1000.0
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    ok = np.isfinite(edges)
    ax.plot(rates[ok], edges[ok], "o-", color=OKABE["enc"], lw=1.5, ms=4)
    for r, e in zip(rates[~ok], edges[~ok]):
        ax.annotate("no edge", (r, 0), fontsize=FONT - 1, ha="center", va="bottom")
    ax.set_xscale("log")
    ax.set_xticks(rates)
    ax.set_xticklabels([f"{r:g}" for r in rates])
    ax.set_xlabel("bitrate (kbps)", fontsize=FONT)
    ax.set_ylabel("band edge (kHz)", fontsize=FONT)
    ax.set_title("Band edge against bitrate, EnCodec 24 kHz", fontsize=FONT)
    ax.tick_params(labelsize=FONT - 1)
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out)
    fig.savefig(out.with_suffix(".png"), dpi=200)
    print(f"figure written to {out}")


# ---- main -----------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("csv", nargs="?", type=Path, default=ROOT / "results" / "spectral_sweep.csv")
    ap.add_argument("--stimulus", choices=("tone", "note", "all"), default="tone")
    ap.add_argument("--bin-hz", type=float, default=BIN_HZ)
    ap.add_argument("--min-n", type=int, default=1, help="partials a bin needs to count")
    ap.add_argument("--summary", type=Path, default=None,
                    help="summary CSV (default: <csv stem>_summary.csv next to the input)")
    ap.add_argument("--figdir", type=Path, default=ROOT.parent / "figures")
    ap.add_argument("--show-bins", action="store_true")
    ap.add_argument("--min-level-db", type=float, default=None,
                    help="keep only partials whose input level is within this many dB of the fundamental (needs the in_level_db column)")
    ap.add_argument("--no-figure", action="store_true")
    args = ap.parse_args()

    cols = load(args.csv)
    if args.min_level_db is not None:
        if "in_level_db" not in cols:
            raise SystemExit("--min-level-db needs the in_level_db column; rerun spectral_sweep.py")
        cols = select(cols, cols["in_level_db"] >= -abs(args.min_level_db))
    if args.stimulus != "all":
        cols = select(cols, cols["stimulus"] == args.stimulus)
        if cols["k"].size == 0:
            raise SystemExit(f"no rows with stimulus={args.stimulus!r} in {args.csv}")
    print(f"{args.csv}: {cols['k'].size} partial rows; edge = first {args.bin_hz:.0f} Hz bin "
          f"with median |shift| > {EDGE_CENTS:g} c that holds for two more populated bins")

    groups, rows = [], []
    keys = sorted(set(zip(cols["label"], cols["stimulus"])))
    for label, stim in keys:
        d = select(cols, (cols["label"] == label) & (cols["stimulus"] == stim))
        row = summarise(d, bin_hz=args.bin_hz, min_n=args.min_n)
        nz = d["delta_cents"] != 0.0
        edges, meds, counts = bin_medians(d["f_k_hz"][nz], d["shift"][nz], args.bin_hz, args.min_n)
        print_group(row, edges, meds, counts, args.show_bins)
        groups.append((row, d))
        rows.append(row)

    summary = args.summary or args.csv.with_name(args.csv.stem + "_summary.csv")
    with summary.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SUMMARY_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: (format(v, ".4f") if isinstance(v, float) else v) for k, v in r.items()})
    print(f"\nsummary written to {summary}")

    if not args.no_figure:
        figure_band_edge(groups, args.figdir / "band_edge.pdf", args.bin_hz, args.min_n)
        figure_edge_vs_rate(rows, args.figdir / "band_edge_vs_rate.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

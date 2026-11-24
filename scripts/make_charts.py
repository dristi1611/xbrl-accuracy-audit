"""
The two charts for the write-up, from output/check1_results.csv and output/error_log.csv.

  output/chart1_statements_with_error_by_size.png
  output/chart2_companies_by_cause.png

Run from the repository root, after build_error_log.py:
    python scripts/make_charts.py
"""

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"          # categorical slots 1 and 2 (validated pair)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})


def read(name):
    with open(OUT / name, newline="") as f:
        return list(csv.DictReader(f))


def rounded_barh(ax, y, width, height, color):
    """Horizontal bar, square at the baseline, 4px-ish rounded at the data end."""
    if width <= 0:
        return
    r = min(height * 0.18, width / 2)
    ax.add_patch(FancyBboxPatch((0, y - height / 2), width, height, boxstyle=f"round,pad=0,rounding_size={r}",
                                linewidth=0, facecolor=color, mutation_aspect=1))
    ax.add_patch(plt.Rectangle((0, y - height / 2), min(width, r * 2), height, linewidth=0, facecolor=color))


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_facecolor(SURFACE)


def chart1():
    # one row per Q2 FY27 statement (company x basis); flagged if any check-1 exception
    stmt = {}
    for r in read("check1_results.csv"):
        k = (r["symbol"], r["basis"])
        stmt.setdefault(k, [r["size_group"], False])
        if r["status"] not in ("match", "rounding"):
            stmt[k][1] = True
    groups = [("Large", "Nifty 50"), ("Mid", "Midcap 150"), ("Small", "Smallcap 250")]
    tot, bad = defaultdict(int), defaultdict(int)
    for g, flagged in stmt.values():
        tot[g] += 1
        bad[g] += flagged
    all_t, all_b = sum(tot.values()), sum(bad.values())

    fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    style(ax)
    rows = [(f"{lab}\n({g.lower()} companies)", bad[g], tot[g]) for g, lab in groups] + [("All 40 companies", all_b, all_t)]
    for i, (lab, b, t) in enumerate(rows):
        y = len(rows) - 1 - i
        share = 100 * b / t
        rounded_barh(ax, y, share, 0.56, BLUE if i < 3 else INK2)
        ax.text(share + 1.2, y, f"{share:.0f}%  ({b} of {t} statements)", va="center", color=INK, fontsize=9.5)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in reversed(rows)], fontsize=9.5, color=INK)
    ax.set_xlim(0, 82)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xticks([0, 20, 40, 60])
    ax.set_xticklabels(["0%", "20%", "40%", "60%"])
    fig.text(0.01, 0.97, "Q2 FY27 statements with at least one XBRL figure that differs from the PDF",
             fontsize=11, fontweight="bold", va="top")
    fig.text(0.01, 0.89, "Standalone and consolidated statements, by index size group. Sample of 40 NSE companies.",
             fontsize=9, color=INK2, va="top")
    fig.subplots_adjust(left=0.24, right=0.99, top=0.78, bottom=0.1)
    fig.savefig(OUT / "chart1_statements_with_error_by_size.png", facecolor=SURFACE)
    plt.close(fig)
    return rows


def chart2():
    cats = [("missing", "Missing (quarter not in XBRL)"), ("wrong_line", "Wrong line"),
            ("standalone_consolidated_swapped", "Standalone and consolidated\nswapped"),
            ("restated", "Restated (reason given in PDF)"), ("unexplained", "Unexplained")]
    comp = {("xbrl_vs_pdf", c): set() for c, _ in cats} | {("restatement", c): set() for c, _ in cats}
    for r in read("error_log.csv"):
        comp[(r["check"], r["category"])].add(r["symbol"])
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    style(ax)
    h, gap = 0.34, 0.04
    for i, (c, lab) in enumerate(cats):
        y = len(cats) - 1 - i
        for j, (chk, col) in enumerate((("xbrl_vs_pdf", BLUE), ("restatement", ORANGE))):
            n = len(comp[(chk, c)])
            yy = y + (h + gap) / 2 - j * (h + gap)
            rounded_barh(ax, yy, n, h, col)
            ax.text(n + 0.15, yy, str(n), va="center", fontsize=9, color=INK)
    ax.set_yticks(range(len(cats)))
    ax.set_yticklabels([lab for _, lab in reversed(cats)], fontsize=9.5, color=INK)
    ax.set_xlim(0, 11)
    ax.set_ylim(-0.6, len(cats) - 0.4)
    ax.set_xticks(range(0, 11, 2))
    ax.set_xlabel("Companies (of 40)", fontsize=9)
    fig.text(0.01, 0.97, "Why figures differed: companies affected, by cause", fontsize=11, fontweight="bold", va="top")
    fig.text(0.01, 0.905, "A company can appear under more than one cause.", fontsize=9, color=INK2, va="top")
    # legend (2 series): swatch + label, above the plot
    for k, (lab, col) in enumerate((("Check 1: XBRL vs PDF, Q2 FY27", BLUE),
                                    ("Check 3: earlier XBRL vs this quarter's PDF", ORANGE))):
        x = 0.01 + k * 0.38
        fig.patches.append(FancyBboxPatch((x, 0.815), 0.014, 0.03, boxstyle="round,pad=0,rounding_size=0.004",
                                          transform=fig.transFigure, facecolor=col, linewidth=0))
        fig.text(x + 0.022, 0.83, lab, fontsize=9, color=INK2, va="center")
    fig.subplots_adjust(left=0.40, right=0.97, top=0.76, bottom=0.14)
    fig.savefig(OUT / "chart2_companies_by_cause.png", facecolor=SURFACE)
    plt.close(fig)
    return {k: sorted(v) for k, v in comp.items() if v}


if __name__ == "__main__":
    for r in chart1():
        print(r)
    for k, v in chart2().items():
        print(k, len(v), v)

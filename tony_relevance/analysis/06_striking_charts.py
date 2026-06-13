"""
06_striking_charts.py — Charts in the "Fake Money" editorial house style (2026)
===============================================================================
Re-skinned to mirror the user's own Substack aesthetic (jharbour.substack.com,
"Fake Money"):
  * warm CREAM canvas (#F4EFE2)
  * elegant SERIF headlines, sentence case, left-aligned (Liberation Serif)
  * TYPEWRITER / monospace for data labels, axis numbers, reference-line tags
    and the source line (Liberation Mono)
  * muted EARTHY palette — taupe neutral bars, olive-green and brick-red
    highlights
  * subtle horizontal gridlines, dashed reference lines, dotted pandemic gap,
    and serif callouts with hand-drawn curved arrows

Updated through the 79th Tony Awards (2026): 5.06M linear, the best since 2019.

Outputs (charts/):
  striking_1_rollercoaster.png    Tony broadcast audience 2001–2026, annotated
  striking_2_everyone_fell.png    indexed vs peers (the "it's all of TV" chart)
  striking_3_measurement_mirage.png  how a +4% linear rise was reported as a 'dip'
  striking_4_oldest_room.png      median viewer age vs the typical American
  striking_5_shrinking_pie.png    Tony share of the big-four award audience

Run: python3 tony_relevance/analysis/06_striking_charts.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "tony_relevance.db"
CH = ROOT / "charts"; CH.mkdir(exist_ok=True)

# ---- THEME (the "Fake Money" palette — edit to re-skin) ----------------------
BG     = "#F4EFE2"     # warm cream canvas
INK    = "#2B2620"     # near-black warm brown (headlines)
SUBINK = "#46423A"     # subtitle
MUTED  = "#8C8678"     # notes, source, gridline labels
FAINT  = "#6E685C"     # reference-line text / arrows
GRID   = "#E3DCCC"     # very subtle horizontal gridlines
SPINE  = "#B8AF9C"     # thin axis lines
TAUPE  = "#C7BEAC"     # neutral bars / muted series
BRICK  = "#A6432C"     # subject / highlight (Tony)
OLIVE  = "#4C5A38"     # "good"/peak highlight
OCHRE  = "#A8842F"     # 4th series
SLATE  = "#5E6B6E"     # 3rd series

SERIF = "Liberation Serif"
MONO  = "Liberation Mono"

PEERCOL = {"Oscars": OLIVE, "Emmys": SLATE, "Grammys": OCHRE}
AWARDS  = ["Tony", "Oscars", "Emmys", "Grammys"]
US_MEDIAN_AGE = 38.5

plt.rcParams.update({
    "figure.dpi": 230, "savefig.dpi": 230,
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "font.family": "serif", "font.serif": [SERIF], "font.weight": "normal",
    "text.color": INK, "axes.labelcolor": SUBINK,
    "xtick.color": INK, "ytick.color": INK,
    "axes.edgecolor": SPINE, "axes.linewidth": 1.1,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 1.0,
    "axes.axisbelow": True,
})


# ---------------------------------------------------------------- helpers ----
def _new(figsize=(9.6, 6.0), top=0.78):
    fig, ax = plt.subplots(figsize=figsize)
    fig.subplots_adjust(top=top, bottom=0.15, left=0.085, right=0.95)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(SPINE)
    ax.tick_params(length=0)
    ax.grid(axis="x", visible=False)
    ax.grid(axis="y", visible=True)
    return fig, ax


def _titleblock(fig, title, subtitle, note=None):
    fig.text(0.085, 0.945, title, color=INK, fontsize=24, family=SERIF, va="top")
    fig.text(0.085, 0.882, subtitle, color=SUBINK, fontsize=13.5, family=SERIF, va="top")
    if note:
        fig.text(0.085, 0.836, note, color=MUTED, fontsize=11, family=SERIF,
                 style="italic", va="top")


def _footer(fig, text):
    fig.text(0.085, 0.035, text, color=MUTED, fontsize=8.4, family=MONO)


def _mono_ticks(ax, size=9.5):
    for lbl in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
        lbl.set_family(MONO)
        lbl.set_fontsize(size)


def _mlabel(ax, x, y, s, color=INK, size=9.5, ha="center", va="bottom", weight="bold"):
    ax.text(x, y, s, color=color, fontsize=size, family=MONO, ha=ha, va=va, fontweight=weight)


def load():
    con = sqlite3.connect(DB)
    lin = pd.read_sql(
        "SELECT award, ceremony_year AS year, viewers_m FROM award_broadcasts "
        "WHERE measurement='linear' AND viewers_m IS NOT NULL "
        "AND award IN ('Tony','Oscars','Emmys','Grammys') ORDER BY award, year", con)
    demo = pd.read_sql("SELECT * FROM audience_demographics", con)
    con.close()
    return lin, demo


# ---------------------------------------------------------------- chart 1 ----
def c1_rollercoaster(lin):
    t = lin[lin.award == "Tony"].sort_values("year")
    fig, ax = _new(top=0.76)
    ax.fill_between(t.year, t.viewers_m, color=BRICK, alpha=0.07, zorder=1)
    ax.plot(t.year, t.viewers_m, color=BRICK, lw=2.4, zorder=3,
            marker="o", ms=5, mfc=BRICK, mec=BG, mew=1.2)

    v2019 = float(t.loc[t.year == 2019, "viewers_m"].iloc[0])
    ax.axhline(v2019, color=FAINT, lw=1.0, ls=(0, (6, 4)), zorder=2)
    _mlabel(ax, 2001.4, v2019 + 0.12, f"2019 pre-pandemic level · {v2019:.1f}M",
            color=FAINT, size=8.6, ha="left", weight="normal")
    ax.axvline(2020, color=MUTED, lw=1.0, ls=(0, (1, 3)), zorder=2)

    for _, r in t.iterrows():
        _mlabel(ax, r.year, r.viewers_m + 0.22, f"{r.viewers_m:.1f}", size=8.0,
                weight="normal")
    ax.annotate("Hamilton —\nthe last monoculture moment",
                xy=(2016, 8.7), xytext=(2009.6, 9.5), color=INK, fontsize=10.5,
                family=SERIF, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=FAINT, lw=1.0,
                                connectionstyle="arc3,rad=0.2"))
    ax.annotate("pandemic low", xy=(2021, 2.62), xytext=(2021, 1.2), color=MUTED,
                fontsize=10, family=SERIF, style="italic", ha="center", va="top",
                arrowprops=dict(arrowstyle="-", color=FAINT, lw=1.0))
    ax.annotate("2026: 5.06M —\nbest since 2019", xy=(2026, 5.06), xytext=(2022.4, 7.7),
                color=BRICK, fontsize=11, family=SERIF, ha="center", va="center",
                arrowprops=dict(arrowstyle="-|>", color=BRICK, lw=1.6,
                                connectionstyle="arc3,rad=-0.35"))

    ax.set_ylim(0, 10.4); ax.set_xlim(2000, 2027)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}M"))
    ax.set_xticks(range(2002, 2027, 4))
    _mono_ticks(ax)
    _titleblock(fig, "The Tony rollercoaster",
                "U.S. linear-TV viewers per Tony Awards ceremony, by year.",
                "A pandemic crash, then a four-year climb back to a post-2019 high.")
    _footer(fig, "Source: Nielsen via trade press (Deadline / Variety / TheWrap / "
                 "BroadwayWorld) · Live+Same-Day linear · 2026 preliminary")
    fig.savefig(CH / "striking_1_rollercoaster.png")
    plt.close(fig)


# ---------------------------------------------------------------- chart 2 ----
def c2_everyone_fell(lin):
    fig, ax = _new(top=0.76)
    win = lin[(lin.year >= 2014) & (lin.year <= 2025)]
    ax.axhline(100, color=FAINT, lw=1.0, ls=(0, (6, 4)), zorder=2)
    _mlabel(ax, 2014.1, 103, "2014 = 100", color=FAINT, size=8.6, ha="left", weight="normal")
    for a in AWARDS:
        s = win[win.award == a].sort_values("year")
        base = s.loc[s.year == 2014, "viewers_m"]
        if base.empty:
            continue
        idx = 100 * s.viewers_m / float(base.iloc[0])
        col = BRICK if a == "Tony" else PEERCOL[a]
        ax.plot(s.year, idx, color=col, lw=2.8 if a == "Tony" else 1.8,
                zorder=5 if a == "Tony" else 3, marker="o", ms=3.5,
                mfc=col, mec=BG, mew=0.8)
        # nudge near-overlapping end labels (Emmys/Oscars both land ~45-47)
        yoff = {"Emmys": 3.2, "Oscars": -3.2}.get(a, 0)
        _mlabel(ax, s.year.iloc[-1] + 0.18, idx.iloc[-1] + yoff, f"{a} {idx.iloc[-1]:.0f}",
                color=col, size=9.5, ha="left", va="center")
    ax.set_xlim(2014, 2026.8); ax.set_ylim(0, 132)
    ax.set_xticks(range(2014, 2026, 2))
    _mono_ticks(ax)
    _titleblock(fig, "Everyone fell — the Tonys least of all",
                "Award-show linear audiences, indexed to 2014 = 100.",
                "By 2025 the Tony line (red) sits highest of the four.")
    _footer(fig, "Source: Nielsen via trade press · diff-in-diff vs peers: no "
                 "Tony-specific decline (+1.6%/yr, p=0.59)")
    fig.savefig(CH / "striking_2_everyone_fell.png")
    plt.close(fig)


# ---------------------------------------------------------------- chart 3 ----
def c3_mirage(lin):
    fig, ax = _new(figsize=(9.6, 6.0), top=0.76)
    labels = ["2025\nlinear", "2026\nlinear", "2025\ncross-platform"]
    vals   = [4.85, 5.06, 5.10]
    x = np.arange(3)
    ax.bar(x[0], vals[0], width=0.66, color=TAUPE, zorder=3)
    ax.bar(x[1], vals[1], width=0.66, color=OLIVE, zorder=3)
    ax.bar(x[2], vals[2], width=0.66, color=BG, edgecolor=TAUPE,
           hatch="////", lw=1.3, zorder=3)
    for xi, v in zip(x, vals):
        _mlabel(ax, xi, v + 0.07, f"{v:.2f}M", size=11)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    for lbl in ax.get_xticklabels():
        lbl.set_family(MONO); lbl.set_fontsize(9.5)
    ax.set_ylim(0, 6.2)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}M"))
    _mono_ticks(ax)
    ax.annotate("", xy=(1, 5.06), xytext=(0, 4.85),
                arrowprops=dict(arrowstyle="-|>", color=OLIVE, lw=2.2))
    ax.annotate("+4% like-for-like\n(linear → linear)", xy=(0.5, 4.96),
                xytext=(0.5, 5.78), color=OLIVE, fontsize=11, family=SERIF,
                ha="center", va="center")
    ax.annotate("the “dip” compared THIS bar\nto 2026 — different rulers",
                xy=(2, 5.16), xytext=(2.0, 5.95), color=BRICK, fontsize=10.5,
                family=SERIF, ha="center", va="center",
                arrowprops=dict(arrowstyle="-|>", color=BRICK, lw=1.5,
                                connectionstyle="arc3,rad=-0.2"))
    _titleblock(fig, "The measurement mirage",
                "Tony Awards viewers (millions): how a rise got reported as a fall.",
                "“Linear” home viewers and “across-platform” totals are different rulers.")
    _footer(fig, "Source: BroadwayWorld / Playbill / CBS, June 2026 · "
                 "linear vs across-platform are not comparable")
    fig.savefig(CH / "striking_3_measurement_mirage.png")
    plt.close(fig)


# ---------------------------------------------------------------- chart 4 ----
def c4_oldest_room(demo):
    snap = demo.sort_values("year").groupby("award", as_index=False).last()
    snap = snap[snap.award.isin(AWARDS)].copy()
    snap["delta"] = snap.median_viewer_age - US_MEDIAN_AGE
    snap = snap.sort_values("delta")
    fig, ax = _new(figsize=(9.6, 5.6), top=0.74)
    colors = [BRICK if a == "Tony" else TAUPE for a in snap.award]
    y = np.arange(len(snap))
    ax.barh(y, snap.delta, color=colors, zorder=3, height=0.62)
    ax.axvline(0, color=SPINE, lw=1.2)
    for yi, (_, r) in zip(y, snap.iterrows()):
        _mlabel(ax, r.delta + 0.4, yi, f"+{r.delta:.0f} yrs   age {r.median_viewer_age:.0f}",
                ha="left", va="center", size=10)
    ax.set_yticks(y); ax.set_yticklabels(snap.award)
    for lbl in ax.get_yticklabels():
        lbl.set_family(SERIF); lbl.set_fontsize(12); lbl.set_color(INK)
    ax.set_xlim(0, max(snap.delta) * 1.42)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"+{v:.0f}"))
    ax.set_xlabel(f"Years older than the typical American (U.S. median age {US_MEDIAN_AGE})",
                  family=SERIF, fontsize=11)
    ax.grid(axis="x", visible=True, color=GRID); ax.grid(axis="y", visible=False)
    _mono_ticks(ax)
    ax.annotate("≈ 23 years older than\nthe typical American",
                xy=(snap.delta.max(), len(snap) - 1),
                xytext=(snap.delta.max() * 0.52, len(snap) - 1.95),
                color=BRICK, fontsize=10.5, family=SERIF, ha="center", va="center",
                arrowprops=dict(arrowstyle="-|>", color=BRICK, lw=1.4,
                                connectionstyle="arc3,rad=-0.3"))
    _titleblock(fig, "The oldest room in entertainment",
                "Median award-show viewer age, minus the median American’s.",
                "The Tony broadcast audience skews oldest of any major award show.")
    _footer(fig, "Source: Ad Age / Statista median-age snapshots · U.S. Census median age "
                 "· sparse snapshots")
    fig.savefig(CH / "striking_4_oldest_room.png")
    plt.close(fig)


# ---------------------------------------------------------------- chart 5 ----
def c5_shrinking_pie(lin):
    wide = lin.pivot_table(index="year", columns="award", values="viewers_m")
    common = wide.dropna(subset=AWARDS, how="any")
    share = 100 * common["Tony"] / common[AWARDS].sum(axis=1)
    fig, ax = _new(top=0.76)
    ax.bar(share.index, share.values, width=0.66, color=TAUPE, zorder=3)
    ax.bar(share.index[0], share.iloc[0], width=0.66, color=OLIVE, zorder=3)
    ax.bar(share.index[-1], share.iloc[-1], width=0.66, color=BRICK, zorder=3)
    for x, yv in zip(share.index, share.values):
        _mlabel(ax, x, yv + 0.25, f"{yv:.0f}%", size=8.6)
    ax.set_ylim(0, max(share.values) * 1.5)
    ax.set_xticks(list(share.index)[::2])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    _mono_ticks(ax)
    ax.annotate("a bigger slice as\npeers fell faster",
                xy=(share.index[-1], share.iloc[-1]),
                xytext=(share.index[-4], share.values.max() * 1.3), color=BRICK,
                fontsize=10.5, family=SERIF, ha="center", va="center",
                arrowprops=dict(arrowstyle="-|>", color=BRICK, lw=1.4,
                                connectionstyle="arc3,rad=-0.3"))
    _titleblock(fig, "A bigger slice of a shrinking pie",
                "Tony viewers as a share of the big-four award-show audience.",
                "Tony ÷ (Tony + Oscars + Emmys + Grammys), years all four aired.")
    _footer(fig, "Source: Nielsen via trade press, 2014–2025 (years all four aired)")
    fig.savefig(CH / "striking_5_shrinking_pie.png")
    plt.close(fig)


def main():
    lin, demo = load()
    c1_rollercoaster(lin)
    c2_everyone_fell(lin)
    c3_mirage(lin)
    c4_oldest_room(demo)
    c5_shrinking_pie(lin)
    print("Wrote striking charts to", CH)
    for p in sorted(CH.glob("striking_*.png")):
        print("   ", p.name)


if __name__ == "__main__":
    main()

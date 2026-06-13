"""
06_striking_charts.py — High-impact "Media War & Peace"-style charts (2026 update)
==================================================================================
Re-skins the Nielsen analysis in the bold, annotation-forward house style of
Evan Shapiro's media-economics charts: dark canvas, neon-saturated series, a
big ALL-CAPS title with a colored kicker rule, data labels ON the marks, axes
stripped to the minimum, a source line in the gutter.

(The specific Substack post requested could not be opened by the build
environment; this mirrors Shapiro's recurring chart grammar across his work.
Swap THEME colors / fonts here to match any house palette exactly.)

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
from matplotlib import patheffects as pe

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "tony_relevance.db"
CH = ROOT / "charts"; CH.mkdir(exist_ok=True)

# ---- THEME (edit these to re-skin everything) -------------------------------
BG      = "#0E1116"      # near-black canvas
PANEL   = "#0E1116"
INK     = "#F4F6F8"      # primary text (near-white)
MUTED   = "#9AA1AB"      # secondary text
GRID    = "#202632"      # faint gridlines
TONY    = "#FF2D55"      # the subject — hot pink-red
OSCARS  = "#FFB000"      # amber
EMMYS   = "#22D3C5"      # teal
GRAMMYS = "#A78BFA"      # violet
POS     = "#22D3C5"      # gains
NEG     = "#FF2D55"      # losses
GHOST   = "#3A4150"      # de-emphasised / "wrong comparison"
PEERCOL = {"Oscars": OSCARS, "Emmys": EMMYS, "Grammys": GRAMMYS}
AWARDS  = ["Tony", "Oscars", "Emmys", "Grammys"]
US_MEDIAN_AGE = 38.5     # US median age (~2023, Census) — baseline for the age chart

plt.rcParams.update({
    "figure.dpi": 230, "savefig.dpi": 230,
    "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG,
    "font.family": "DejaVu Sans", "font.weight": "medium",
    "text.color": INK, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": GRID, "axes.linewidth": 1.0,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.9,
    "axes.axisbelow": True,
})
SHADOW = [pe.withStroke(linewidth=3, foreground=BG)]   # halo so labels read on lines


# ---------------------------------------------------------------- helpers ----
def _new(figsize=(9.2, 6.0), top=0.80):
    fig, ax = plt.subplots(figsize=figsize)
    fig.subplots_adjust(top=top, bottom=0.13, left=0.085, right=0.95)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(length=0)
    return fig, ax


def _titleblock(fig, kicker, title, subtitle, kcolor=TONY):
    fig.text(0.085, 0.945, kicker.upper(), color=kcolor, fontsize=11.5,
             fontweight="bold")
    # colored kicker rule
    fig.add_artist(plt.Line2D([0.085, 0.16], [0.927, 0.927], color=kcolor,
                              lw=3.2, solid_capstyle="butt"))
    fig.text(0.085, 0.875, title, color=INK, fontsize=23, fontweight="bold", va="top")
    fig.text(0.085, 0.808, subtitle, color=MUTED, fontsize=11.5, va="top")


def _footer(fig, text):
    fig.text(0.085, 0.035, text, color=MUTED, fontsize=8.0)
    fig.text(0.95, 0.012, "tony_relevance", color=MUTED, fontsize=8.0, ha="right",
             fontweight="bold")


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
    fig, ax = _new(top=0.78)
    ax.fill_between(t.year, t.viewers_m, color=TONY, alpha=0.16, zorder=1)
    ax.plot(t.year, t.viewers_m, color=TONY, lw=3.4, zorder=3,
            marker="o", ms=4.5, mfc=TONY, mec=BG, mew=1.2)

    def tag(year, txt, xytext, color=INK, va="bottom", ha="center"):
        v = float(t.loc[t.year == year, "viewers_m"].iloc[0])
        ax.annotate(txt, xy=(year, v), xytext=xytext, color=color,
                    fontsize=9.2, fontweight="bold", ha=ha, va=va,
                    path_effects=SHADOW,
                    arrowprops=dict(arrowstyle="-", color=color, lw=1.0, alpha=0.6))
    tag(2016, "HAMILTON\nlast monoculture moment", (2012.6, 9.2), INK, ha="center")
    tag(2021, "PANDEMIC LOW\n2.62M", (2021, 1.0), MUTED, va="top")
    tag(2026, "2026: 5.06M\nbest since 2019", (2024.7, 7.1), POS, ha="center")
    # endpoint value labels
    for yr in (2001, 2026):
        v = float(t.loc[t.year == yr, "viewers_m"].iloc[0])
        ax.text(yr, v + 0.25, f"{v:.1f}M", color=INK, fontsize=9, ha="center",
                fontweight="bold", path_effects=SHADOW)
    ax.set_ylim(0, 10.2); ax.set_xlim(2000, 2027)
    ax.set_ylabel("Linear TV viewers (millions)")
    ax.margins(x=0.02)
    _titleblock(fig, "Tony Awards · broadcast ratings",
                "The Tony rollercoaster",
                "US linear-TV viewers per ceremony, 2001–2026. A pandemic crash, then a four-year climb back.")
    _footer(fig, "Source: Nielsen via trade press (Deadline / Variety / TheWrap / "
                 "BroadwayWorld). Live+Same-Day linear; 2026 preliminary.")
    fig.savefig(CH / "striking_1_rollercoaster.png")
    plt.close(fig)


# ---------------------------------------------------------------- chart 2 ----
def c2_everyone_fell(lin):
    fig, ax = _new(top=0.78)
    win = lin[(lin.year >= 2014) & (lin.year <= 2025)]
    ax.axhline(100, color=GRID, lw=1.0, ls="--")
    for a in AWARDS:
        s = win[win.award == a].sort_values("year")
        base = s.loc[s.year == 2014, "viewers_m"]
        if base.empty:
            continue
        idx = 100 * s.viewers_m / float(base.iloc[0])
        col = TONY if a == "Tony" else PEERCOL[a]
        ax.plot(s.year, idx, color=col, lw=3.6 if a == "Tony" else 2.0,
                zorder=5 if a == "Tony" else 3, marker="o", ms=3.5,
                mfc=col, mec=BG, mew=0.8, alpha=1.0 if a == "Tony" else 0.9)
        ax.text(s.year.iloc[-1] + 0.15, idx.iloc[-1],
                f"{a}  {idx.iloc[-1]:.0f}", color=col, va="center", fontsize=10,
                fontweight="bold", path_effects=SHADOW)
    ax.set_xlim(2014, 2026.6); ax.set_ylim(0, 130)
    ax.set_ylabel("Viewers, indexed to 2014 = 100")
    _titleblock(fig, "the lazy take, debunked",
                "Everyone fell — the Tonys least of all",
                "Award-show linear audiences, indexed to 2014. The Tony line ends highest of the four.", kcolor=EMMYS)
    _footer(fig, "Source: Nielsen via trade press. Difference-in-differences vs peers: "
                 "no Tony-specific decline (+1.6%/yr, p=0.59).")
    fig.savefig(CH / "striking_2_everyone_fell.png")
    plt.close(fig)


# ---------------------------------------------------------------- chart 3 ----
def c3_mirage(lin):
    fig, ax = _new(figsize=(9.2, 6.0), top=0.78)
    labels = ["2025\nlinear", "2026\nlinear", "2025\ncross-platform"]
    vals   = [4.85, 5.06, 5.10]
    cols   = [TONY, TONY, GHOST]
    x = np.arange(3)
    bars = ax.bar(x[:2], vals[:2], width=0.62, color=cols[:2], zorder=3)
    ax.bar(x[2], vals[2], width=0.62, color=GHOST, zorder=3, hatch="//",
           edgecolor="#525a6b")
    for xi, v in zip(x, vals):
        ax.text(xi, v + 0.07, f"{v:.2f}M", ha="center", color=INK, fontsize=11,
                fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(labels, color=MUTED, fontsize=10.5)
    ax.set_ylim(0, 6.1); ax.set_ylabel("Viewers (millions)")
    ax.grid(axis="x", visible=False)
    # the honest like-for-like comparison (green, +4%)
    ax.annotate("", xy=(1, 5.06), xytext=(0, 4.85),
                arrowprops=dict(arrowstyle="-|>", color=POS, lw=2.6))
    ax.text(0.5, 5.55, "+4%  like-for-like\n(linear → linear)", color=POS,
            ha="center", fontsize=10.5, fontweight="bold")
    # the misleading headline comparison (apples to oranges)
    ax.annotate("", xy=(2, 5.10), xytext=(1, 5.06),
                arrowprops=dict(arrowstyle="-|>", color=GHOST, lw=2.0, ls=(0, (4, 3))))
    ax.text(1.5, 4.35, "the 'slight dip' headline\ncompared THESE two", color=MUTED,
            ha="center", fontsize=9.4)
    _titleblock(fig, "double-check the data",
                "The measurement mirage",
                "A +4% linear rise, reported as a 'dip' — by comparing it to last year's cross-platform number.", kcolor=OSCARS)
    _footer(fig, "Source: BroadwayWorld / Playbill / CBS, June 2026. Linear vs "
                 "across-platform figures are different units.")
    fig.savefig(CH / "striking_3_measurement_mirage.png")
    plt.close(fig)


# ---------------------------------------------------------------- chart 4 ----
def c4_oldest_room(demo):
    snap = (demo.sort_values("year").groupby("award", as_index=False).last())
    snap = snap[snap.award.isin(AWARDS)].copy()
    snap["delta"] = snap.median_viewer_age - US_MEDIAN_AGE
    snap = snap.sort_values("delta")
    fig, ax = _new(figsize=(9.2, 5.4), top=0.76)
    colors = [TONY if a == "Tony" else PEERCOL.get(a, MUTED) for a in snap.award]
    y = np.arange(len(snap))
    ax.barh(y, snap.delta, color=colors, zorder=3, height=0.6)
    ax.axvline(0, color=MUTED, lw=1.3)
    for yi, (_, r) in zip(y, snap.iterrows()):
        ax.text(r.delta + 0.4, yi, f"+{r.delta:.0f} yrs  (age {r.median_viewer_age:.0f})",
                va="center", color=INK, fontsize=10, fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels(snap.award, color=INK, fontsize=11,
                                         fontweight="bold")
    ax.set_xlim(0, max(snap.delta) * 1.35)
    ax.set_xlabel(f"Years older than the typical American (median age {US_MEDIAN_AGE})")
    ax.grid(axis="y", visible=False)
    _titleblock(fig, "the real red flag",
                "The oldest room in entertainment",
                "Award-show median viewer age minus the US median (38.5). Tony skews ~23 years older.", kcolor=TONY)
    _footer(fig, "Source: Ad Age / Statista median-age snapshots; US Census median age. "
                 "Sparse snapshots — backfill a full panel.")
    fig.savefig(CH / "striking_4_oldest_room.png")
    plt.close(fig)


# ---------------------------------------------------------------- chart 5 ----
def c5_shrinking_pie(lin):
    wide = lin.pivot_table(index="year", columns="award", values="viewers_m")
    common = wide.dropna(subset=AWARDS, how="any")
    share = 100 * common["Tony"] / common[AWARDS].sum(axis=1)
    fig, ax = _new(top=0.78)
    ax.fill_between(share.index, share.values, color=TONY, alpha=0.18, zorder=1)
    ax.plot(share.index, share.values, color=TONY, lw=3.4, marker="o", ms=5,
            mfc=TONY, mec=BG, mew=1.2, zorder=3)
    for x, yv in zip(share.index, share.values):
        ax.text(x, yv + 0.5, f"{yv:.0f}%", ha="center", color=INK, fontsize=9.2,
                fontweight="bold", path_effects=SHADOW)
    ax.set_ylim(0, max(share.values) * 1.7); ax.set_xlim(share.index.min(), share.index.max())
    ax.set_ylabel("Tony share of big-four award audience")
    _titleblock(fig, "share of voice",
                "A bigger slice of a shrinking pie",
                "Tony viewers ÷ all big-four award viewers. Small, but rose to ~10% as peers fell faster.", kcolor=GRAMMYS)
    _footer(fig, "Source: Nielsen via trade press, 2014–2025 (years all four aired).")
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

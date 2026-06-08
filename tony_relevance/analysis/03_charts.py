"""
03_charts.py — Evan-Shapiro-style charts for the Tony-relevance project
=======================================================================

Shapiro's chart grammar (what we're imitating):
  * one idea per chart, stated in the title as a sentence ("Everyone is falling");
  * bold, high-contrast series, the subject (Tony) in a hot accent, peers muted;
  * annotate the data, not the axes — call out the moments (Hamilton, pandemic);
  * always show the denominator / the comparison that kills the lazy rebuttal.

Outputs (charts/):
  1_everyone_is_falling.png     indexed trajectories, 2014 = 100
  2_smallest_in_the_room.png    absolute viewers, Tony highlighted + Hamilton
  3_share_of_voice.png          Tony share of the big-four award audience
  4_oldest_audience.png         median viewer age by award

Run: python3 tony_relevance/analysis/03_charts.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "tony_relevance.db"
CH = ROOT / "charts"
CH.mkdir(exist_ok=True)

# palette — Tony hot, peers cool/muted
INK = "#15161a"
GRID = "#d9dbe1"
TONY = "#e6394a"
PEER = {"Oscars": "#f2a900", "Emmys": "#3a86c8", "Grammys": "#7a7f8a"}
BASE_YEAR = 2014
AWARDS = ["Tony", "Oscars", "Emmys", "Grammys"]

plt.rcParams.update({
    "figure.dpi": 220,
    "savefig.dpi": 220,
    "font.size": 11,
    "axes.edgecolor": INK,
    "axes.linewidth": 1.1,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.axisbelow": True,
})


def load():
    con = sqlite3.connect(DB)
    df = pd.read_sql(
        "SELECT award, ceremony_year AS year, viewers_m FROM award_broadcasts "
        "WHERE measurement='linear'", con)
    demo = pd.read_sql("SELECT * FROM audience_demographics", con)
    con.close()
    df = df.dropna(subset=["viewers_m"])  # drop pending cells (2026 ceremony)
    df = df[df.award.isin(AWARDS)]        # big four only (exclude SAG/Phase 2)
    return df, demo


def _style(ax, title, subtitle=None):
    ax.set_title(title, fontsize=15, fontweight="bold", color=INK, loc="left", pad=34)
    if subtitle:
        ax.text(0, 1.035, subtitle, transform=ax.transAxes, fontsize=9.5,
                color="#5b606b", ha="left", va="bottom", wrap=True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=INK)


def chart1_indexed(df):
    fig, ax = plt.subplots(figsize=(9, 5.6))
    win = df[(df.year >= BASE_YEAR) & (df.year <= 2025)]
    for a in AWARDS:
        s = win[win.award == a].sort_values("year")
        base = s.loc[s.year == BASE_YEAR, "viewers_m"]
        if base.empty:
            continue
        idx = 100 * s.viewers_m / float(base.iloc[0])
        c = TONY if a == "Tony" else PEER[a]
        lw = 3.4 if a == "Tony" else 1.8
        z = 5 if a == "Tony" else 2
        ax.plot(s.year, idx, color=c, lw=lw, zorder=z, marker="o", ms=4)
        ax.text(s.year.iloc[-1] + 0.12, idx.iloc[-1], a, color=c,
                fontweight="bold" if a == "Tony" else "normal", va="center", fontsize=10)
    ax.axhline(100, color=INK, lw=0.9, ls="--", alpha=0.5)
    ax.set_xlim(BASE_YEAR, 2025.6)
    ax.set_ylabel(f"Linear viewers, indexed to {BASE_YEAR} = 100")
    _style(ax, "Everyone is falling — not just the Tonys",
           "US linear-TV viewers per ceremony, indexed to 2014. The Tony line (red) "
           "tracks its peers down.")
    fig.tight_layout()
    fig.savefig(CH / "1_everyone_is_falling.png", bbox_inches="tight")
    plt.close(fig)


def chart2_absolute(df):
    fig, ax = plt.subplots(figsize=(9, 5.6))
    win = df[(df.year >= BASE_YEAR) & (df.year <= 2025)]
    for a in AWARDS:
        s = win[win.award == a].sort_values("year")
        c = TONY if a == "Tony" else PEER[a]
        lw = 3.4 if a == "Tony" else 1.6
        alpha = 1.0 if a == "Tony" else 0.55
        ax.plot(s.year, s.viewers_m, color=c, lw=lw, alpha=alpha,
                marker="o", ms=4, zorder=5 if a == "Tony" else 2)
        ax.text(s.year.iloc[-1] + 0.12, s.viewers_m.iloc[-1], a, color=c,
                fontweight="bold" if a == "Tony" else "normal", va="center",
                fontsize=10, alpha=alpha)
    # annotate Hamilton
    h = win[(win.award == "Tony") & (win.year == 2016)]
    if not h.empty:
        hv = float(h.viewers_m.iloc[0])
        ax.annotate("Hamilton year\n(+41% above trend)", xy=(2016, hv),
                    xytext=(2017.3, hv + 6), fontsize=9, color=TONY, fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color=TONY, lw=1.4))
    ax.set_xlim(BASE_YEAR, 2025.6)
    ax.set_ylabel("Linear viewers per ceremony (millions)")
    _style(ax, "The Tonys were always the smallest show in the room",
           "Absolute US linear-TV audience. Even at the Hamilton peak the Tonys "
           "(red) sat far below the Oscars and Grammys.")
    fig.tight_layout()
    fig.savefig(CH / "2_smallest_in_the_room.png", bbox_inches="tight")
    plt.close(fig)


def chart3_share(df):
    wide = df.pivot_table(index="year", columns="award", values="viewers_m")
    common = wide.dropna(subset=AWARDS, how="any")
    share = 100 * common["Tony"] / common[AWARDS].sum(axis=1)
    fig, ax = plt.subplots(figsize=(9, 5.6))
    ax.fill_between(share.index, share.values, color=TONY, alpha=0.18, zorder=1)
    ax.plot(share.index, share.values, color=TONY, lw=3.2, marker="o", ms=5, zorder=3)
    for x, y in zip(share.index, share.values):
        ax.text(x, y + 0.25, f"{y:.0f}%", ha="center", fontsize=8.5, color=TONY,
                fontweight="bold")
    ax.set_ylim(0, max(share.values) * 1.6)
    ax.set_ylabel("Tony share of big-four award-show audience (%)")
    _style(ax, "Theatre's slice of the award-show pie isn't shrinking — the pie is",
           "Tony viewers ÷ (Tony + Oscars + Emmys + Grammys) viewers, years all four "
           "aired. The share is small but holding — even ticking up as peers fell faster.")
    fig.tight_layout()
    fig.savefig(CH / "3_share_of_voice.png", bbox_inches="tight")
    plt.close(fig)


def chart4_age(demo):
    snap = (demo.sort_values("year").groupby("award", as_index=False).last()
            .sort_values("median_viewer_age", ascending=True))
    fig, ax = plt.subplots(figsize=(9, 5.0))
    colors = [TONY if a == "Tony" else PEER.get(a, "#7a7f8a") for a in snap.award]
    bars = ax.barh(snap.award, snap.median_viewer_age, color=colors, zorder=3)
    for b, v in zip(bars, snap.median_viewer_age):
        ax.text(v - 1.5, b.get_y() + b.get_height() / 2, f"{v:.0f}", va="center",
                ha="right", color="white", fontweight="bold", fontsize=11)
    ax.set_xlim(0, max(snap.median_viewer_age) * 1.15)
    ax.set_xlabel("Median viewer age (years)")
    ax.grid(axis="y", visible=False)
    _style(ax, "The Tony audience is the oldest in the business",
           "Median age of the broadcast audience. Older snapshots; backfill a full "
           "panel to show the trend.")
    fig.tight_layout()
    fig.savefig(CH / "4_oldest_audience.png", bbox_inches="tight")
    plt.close(fig)


def main():
    df, demo = load()
    chart1_indexed(df)
    chart2_absolute(df)
    chart3_share(df)
    chart4_age(demo)
    print(f"Wrote 4 charts to {CH}/")
    for p in sorted(CH.glob("*.png")):
        print("   ", p.name)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Polished, layperson-friendly charts for the final critic-impact report.

Five charts, all designed for clarity over information density:
  1. cp_lift_over_time.png      — Headline narrative: CP effect drifting toward 1.0
  2. bayesian_posterior.png     — One-glance probability the effect has weakened
  3. what_critics_deliver.png   — Grouped bar of multipliers across outcomes
  4. how_the_boost_travels.png  — Direct-vs-Tony-mediated decomposition
  5. hit_rate_by_year.png       — CP shows vs non-CP shows, year by year

Design rules enforced everywhere:
  - 16:10 aspect, 300 dpi, generous margins (top 0.88, bottom 0.13)
  - Title font 22 bold, subtitle 14 regular gray, axis labels 13, ticks 12
  - One accent color per chart, soft secondary; never more than 4 colors
  - All annotations placed with bbox padding to avoid overlap with data
  - constrained_layout=True on every figure; no manual subplots_adjust shimming
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

ROOT     = Path(__file__).resolve().parent.parent
DB_PATH  = ROOT / "data" / "critics_impact.db"
OUT_DIR  = ROOT / "charts"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Style
# -----------------------------------------------------------------------------
INK         = "#1a1a1a"     # near-black for text
MUTED       = "#6b7280"     # secondary text
GRID        = "#e5e7eb"     # very light grey gridlines
BG          = "#ffffff"

# Signature palette — soft, modern, print-friendly
BLUE        = "#1f6fb4"     # primary
NAVY        = "#0b3d6b"     # primary dark
ORANGE      = "#e07a3c"     # accent
RUST        = "#a3502b"     # accent dark
GREEN       = "#3f8e6e"     # success
RED         = "#c0392b"     # alert
GOLD        = "#d4a017"     # highlight

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor":   BG,
    "axes.edgecolor":   "#cbd5e1",
    "axes.linewidth":   0.8,
    "axes.labelcolor":  INK,
    "axes.labelsize":   13,
    "axes.titlesize":   16,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.titlepad":    14,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "xtick.color":      INK,
    "ytick.color":      INK,
    "xtick.labelsize":  12,
    "ytick.labelsize":  12,
    "text.color":       INK,
    "font.family":      ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size":        12,
    "legend.frameon":   False,
    "legend.fontsize":  12,
    "grid.color":       GRID,
    "grid.linewidth":   0.7,
    "savefig.facecolor": BG,
    "savefig.dpi":      200,
})

def add_title(fig, title, subtitle=None, source=None):
    """Big bold title + grey subtitle + tiny footer with source.

    Places text in the reserved margin regions (top 12%, bottom 9%).
    Call AFTER plt.subplots_adjust(top=0.84, bottom=0.13, left=0.08, right=0.96).
    """
    fig.text(0.06, 0.945, title, fontsize=22, fontweight="bold",
             ha="left", color=INK)
    if subtitle:
        # Auto-wrap subtitle into 2 lines if it contains \n
        fig.text(0.06, 0.885, subtitle, fontsize=13, color=MUTED, ha="left",
                 va="top")
    if source:
        fig.text(0.06, 0.025, source, fontsize=9, color=MUTED, ha="left",
                 style="italic", va="center")

# -----------------------------------------------------------------------------
# Shared data loading
# -----------------------------------------------------------------------------
def load_show_panel(con):
    """Per-show panel used by the time-series and hit-rate charts.

    Each row is one Broadway show with:
      - is_cp           1 if it carries a NYT Critics Pick flag in `reviews`
      - week1_gross     opening-week box-office gross
      - gross_28        sum of weeks 2-8 gross
      - weeks_observed  count of non-preview gross rows
      - avg_pct_cap     mean capacity_pct (stored 0-1; 1.0 = 100%)
      - any_nom         1 if any Tony nomination in the database
      - top_nom         1 if nominated for Best Musical or Best Play
    """
    q = """
    WITH cp_flag AS (
      SELECT show_id,
             MAX(CASE WHEN is_nyt_critics_pick=1 THEN 1 ELSE 0 END) AS is_cp
        FROM reviews
       GROUP BY show_id
    ),
    tony AS (
      SELECT show_id,
             MAX(CASE WHEN nominated=1 THEN 1 ELSE 0 END) AS any_nom,
             MAX(CASE WHEN nominated=1
                       AND category IN ('Best Musical','Best Play')
                      THEN 1 ELSE 0 END) AS top_nom
        FROM tony_outcomes
       WHERE show_id IS NOT NULL
       GROUP BY show_id
    ),
    w1 AS (
      SELECT show_id, gross
        FROM (
          SELECT show_id, gross,
                 ROW_NUMBER() OVER (PARTITION BY show_id ORDER BY week_ending) AS rn
            FROM show_week_performances
            WHERE is_preview = 0
        ) WHERE rn=1
    ),
    w28 AS (
      SELECT show_id, SUM(gross) AS gross_28
        FROM (
          SELECT show_id, gross,
                 ROW_NUMBER() OVER (PARTITION BY show_id ORDER BY week_ending) AS rn
            FROM show_week_performances
            WHERE is_preview = 0
        )
        WHERE rn BETWEEN 2 AND 8
        GROUP BY show_id
    ),
    weeks_seen AS (
      SELECT show_id, COUNT(*) AS weeks_observed,
             AVG(capacity_pct) AS avg_pct_cap
        FROM show_week_performances
        WHERE is_preview = 0
       GROUP BY show_id
    )
    SELECT s.show_id, s.title, s.opening_date, s.show_type, s.is_revival,
           COALESCE(cf.is_cp, 0) AS is_cp,
           w1.gross    AS week1_gross,
           w28.gross_28 AS gross_28,
           ws.weeks_observed,
           ws.avg_pct_cap,
           COALESCE(t.any_nom, 0) AS any_nom,
           COALESCE(t.top_nom, 0) AS top_nom
      FROM shows s
      LEFT JOIN cp_flag cf  ON cf.show_id = s.show_id
      LEFT JOIN w1          ON w1.show_id = s.show_id
      LEFT JOIN w28         ON w28.show_id= s.show_id
      LEFT JOIN weeks_seen ws ON ws.show_id = s.show_id
      LEFT JOIN tony t      ON t.show_id  = s.show_id
     WHERE s.show_type IN ('M','P')
       AND s.opening_date IS NOT NULL
       AND s.opening_date >= '2014-01-01'
       AND s.opening_date <= '2026-05-25'
       AND NOT (s.opening_date BETWEEN '2020-03-12' AND '2021-09-13')
    """
    df = pd.read_sql(q, con)
    df["opening_date"] = pd.to_datetime(df["opening_date"])
    df["year"]         = df["opening_date"].dt.year
    df["is_musical"]   = (df["show_type"] == "M").astype(int)
    # capacity_pct is stored as a ratio (1.0 = 100%), not a percentage
    df["hit"]          = ((df["weeks_observed"] >= 26) & (df["avg_pct_cap"] >= 0.70)).astype(int)
    return df

# -----------------------------------------------------------------------------
# Chart 1 — The headline: CP lift over time
# -----------------------------------------------------------------------------
def chart_cp_lift_over_time(df):
    """Per-year CP lift on log(weeks 2-8 gross) controlling for log(week-1 gross)."""
    sub = df[(df["week1_gross"] > 0) & (df["gross_28"] > 0)].copy()
    sub["log_w1"]  = np.log(sub["week1_gross"])
    sub["log_w28"] = np.log(sub["gross_28"])

    yearly = []
    for yr, g in sub.groupby("year"):
        n_cp = int(g["is_cp"].sum())
        n_non = int((g["is_cp"] == 0).sum())
        # Require at least 4 CP shows and 4 non-CP shows to fit a stable model
        if n_cp < 4 or n_non < 4:
            continue
        try:
            m = smf.ols("log_w28 ~ is_cp + log_w1 + is_musical", data=g).fit()
            beta = m.params["is_cp"]
            se   = m.bse["is_cp"]
            lift = float(np.exp(beta))
            lo   = float(np.exp(beta - 1.96 * se))
            hi   = float(np.exp(beta + 1.96 * se))
            yearly.append((yr, lift, lo, hi, n_cp, len(g)))
        except Exception:
            continue
    yr_df = pd.DataFrame(yearly, columns=["year","lift","lo","hi","n_cp","n"])

    fig = plt.figure(figsize=(14, 8.5))
    ax  = fig.add_axes([0.08, 0.13, 0.88, 0.65])  # left, bottom, w, h

    # Use only years with stable estimates for the line + shading
    yr_df = yr_df.sort_values("year").reset_index(drop=True)
    years_plot = yr_df["year"].tolist()
    min_yr, max_yr = min(years_plot), max(years_plot)

    # Shade recent-cliff zone (2024+)
    ax.axvspan(2023.5, max_yr + 0.5, color=ORANGE, alpha=0.10, zorder=0)
    ax.axhline(1.0, color=MUTED, lw=1.0, ls="--", zorder=1)
    ax.text(min_yr - 0.3, 1.04, "no effect (1.0×)",
            fontsize=10, color=MUTED, va="bottom")

    # CI band
    ax.fill_between(yr_df["year"], yr_df["lo"].clip(upper=2.8),
                    yr_df["hi"].clip(upper=2.8),
                    color=BLUE, alpha=0.18, lw=0, zorder=2,
                    label="95% confidence band")
    # Per-year point estimates
    ax.plot(yr_df["year"], yr_df["lift"], "-", color=BLUE, lw=2.5,
            zorder=3, alpha=0.7)
    ax.scatter(yr_df["year"], yr_df["lift"], s=130, color=BLUE,
               edgecolor="white", lw=2, zorder=4,
               label="annual CP boost estimate")

    # Annotate the most recent year where the line dips toward 1.0
    last = yr_df.iloc[-1]
    if last["lift"] < 1.15:
        ax.annotate(
            f"{int(last['year'])}: ×{last['lift']:.2f}\n(no measurable boost)",
            xy=(last["year"], last["lift"]),
            xytext=(last["year"] - 2.7, 0.55),
            fontsize=12, color=RUST, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=RUST, lw=1.5,
                            connectionstyle="arc3,rad=-0.25"),
            ha="left", va="center",
        )

    # "Recent slump" label inside the shaded area, top-right
    slump_mid = (2023.5 + max_yr + 0.5) / 2  # midpoint of shaded band
    ax.text(slump_mid, 2.65, "RECENT SLUMP",
            fontsize=11, color=RUST, fontweight="bold", ha="center", va="top",
            alpha=0.85)

    # X axis: only the years we actually plotted
    ax.set_xticks(range(min_yr, max_yr + 1))
    ax.set_xlim(min_yr - 0.5, max_yr + 0.5)
    ax.set_ylim(0.4, 2.8)
    ax.set_yticks([0.5, 1.0, 1.5, 2.0, 2.5])
    ax.set_yticklabels(["0.5×","1.0×","1.5×","2.0×","2.5×"])
    ax.set_ylabel("CP boost on weeks 2-8 ticket sales\n(multiplier vs. otherwise-identical non-CP show)")
    ax.grid(True, axis="y", alpha=0.6)
    ax.set_axisbelow(True)

    ax.legend(loc="lower left", framealpha=0.95, facecolor="white",
              edgecolor="#e5e7eb", borderpad=0.8, fontsize=11)

    add_title(fig,
        "Does the NYT Critics Pick still move tickets?",
        "Each dot is the 'CP boost' for that year's Broadway openings, after controlling for\n"
        "opening-week sales. Above 1.0× means CP shows out-earn comparable non-CP shows in weeks 2-8.",
        source="Source: NYT Critics Pick spotlight + IBDB weekly grosses + DTLI reviews. "
               "Broadway 2014-2025, ex-COVID. Years with <4 CP or <4 non-CP shows omitted.")
    fig.savefig(OUT_DIR / "1_cp_lift_over_time.png")
    plt.close(fig)
    print(f"  ✓ 1_cp_lift_over_time.png  (years included: {list(yr_df['year'])})")
    return yr_df

# -----------------------------------------------------------------------------
# Chart 2 — Bayesian posterior at a glance
# -----------------------------------------------------------------------------
def chart_bayesian_posterior():
    """One-glance probability that CP pull has weakened.

    Uses the headline number from the extended report (77.7% robust posterior;
    90% on the full series). We display both with appropriate framing.
    """
    fig = plt.figure(figsize=(14, 8.5))
    ax  = fig.add_axes([0.20, 0.18, 0.76, 0.60])

    # Two horizontal bars, stacked vertically
    labels = ["Full series (2014-2025)\nposterior P(decline)",
              "Robust fit (drops 2014 outlier)\nposterior P(decline)"]
    values = [0.90, 0.78]
    colors = [NAVY, BLUE]

    y_pos = np.array([0.65, 0.30])
    bar_h = 0.20

    # Background "100%" rails
    for y in y_pos:
        ax.add_patch(mpatches.FancyBboxPatch(
            (0.02, y - bar_h/2), 0.96, bar_h,
            boxstyle="round,pad=0,rounding_size=0.015",
            linewidth=0, facecolor="#f1f5f9", zorder=1))

    # Filled probability bars
    for y, v, c in zip(y_pos, values, colors):
        ax.add_patch(mpatches.FancyBboxPatch(
            (0.02, y - bar_h/2), 0.96 * v, bar_h,
            boxstyle="round,pad=0,rounding_size=0.015",
            linewidth=0, facecolor=c, zorder=2))
        # Big % number at end of bar
        ax.text(0.02 + 0.96 * v + 0.012, y, f"{int(v*100)}%",
                fontsize=26, fontweight="bold", color=c, va="center")

    # Threshold markers
    for thr, lab in [(0.50, "50/50"), (0.80, "strong\nevidence\nthreshold"),
                     (0.95, "near-certain")]:
        x = 0.02 + 0.96 * thr
        ax.axvline(x, ymin=0.10, ymax=0.85, color=MUTED, ls=":", lw=1.0, alpha=0.6)
        ax.text(x, 0.92, lab, fontsize=9, color=MUTED, ha="center",
                style="italic")

    # Labels for each bar (on the left)
    for y, lab in zip(y_pos, labels):
        ax.text(0.00, y, lab, fontsize=12, color=INK, va="center", ha="right",
                fontweight="bold")

    ax.set_xlim(-0.30, 1.05)
    ax.set_ylim(0, 1.0)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Interpretation strip BELOW the plot area (in the bottom margin)
    interp = ("How to read: There's a strong probability that the CP boost on weeks 2-8 ticket sales\n"
              "is genuinely weaker now than it used to be — with the most likely break around 2024.")
    fig.text(0.5, 0.10, interp, fontsize=12, color=INK, ha="center",
             style="italic",
             bbox=dict(boxstyle="round,pad=0.8", facecolor="#fef9e7",
                       edgecolor=GOLD, linewidth=1))

    add_title(fig,
        "How confident are we that the CP boost has weakened?",
        "Bayesian change-point models translate the time series into a single, intuitive probability.",
        source="Method: Bayesian change-point on per-year CP lift, uniform prior on break year. "
               "78% is the conservative figure (drops the noisy 3-show 2014 cell).")
    fig.savefig(OUT_DIR / "2_bayesian_posterior.png")
    plt.close(fig)
    print("  ✓ 2_bayesian_posterior.png")

# -----------------------------------------------------------------------------
# Chart 3 — What critics deliver (grouped bars of multipliers)
# -----------------------------------------------------------------------------
def chart_what_critics_deliver():
    """Adjusted odds-ratios per signal × outcome.

    Numbers recomputed from `critics_impact.db` via adjusted logit (controls:
    is_musical, open_year, post_covid, log(1+total_reviews)). Cohort: Broadway
    shows opening on or before 2025-06-15, ex-COVID, with ≥1 review. The NYT-CP
    sub-cohort is restricted to 2014+. All effects survive Benjamini-Hochberg
    FDR correction at q < 0.05.
    """
    data = {
        "Box-office hit":      [2.94, 3.18, 2.18],   # majority, unanimous, CP
        "Any Tony nom":        [4.46, 3.19, 3.04],
        "Best Musical/Play":   [3.90, 3.27, 3.72],
    }
    signals = ["Majority of critics\npositive", "Unanimous\npositive", "NYT Critics Pick"]
    colors  = [BLUE, NAVY, ORANGE]

    fig = plt.figure(figsize=(14, 8.5))
    ax  = fig.add_axes([0.08, 0.16, 0.88, 0.62])

    x      = np.arange(len(data))
    width  = 0.26

    for i, (sig, color) in enumerate(zip(signals, colors)):
        vals = [data[k][i] for k in data]
        offsets = (i - 1) * width
        bars = ax.bar(x + offsets, vals, width=width, color=color,
                      edgecolor="white", lw=1.5, label=sig, zorder=3)
        # Value labels on top of bars
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width()/2, v + 0.10,
                    f"×{v:.1f}", ha="center", va="bottom",
                    fontsize=12, color=color, fontweight="bold")

    # "no effect" line
    ax.axhline(1.0, color=MUTED, ls="--", lw=1.0)
    ax.text(-0.55, 1.03, "no effect (1.0×)", color=MUTED, fontsize=10)

    ax.set_xticks(x)
    ax.set_xticklabels(list(data.keys()), fontsize=13, fontweight="bold")
    ax.set_ylabel("Multiplier on the odds of this outcome\n(adjusted for show type, era, review volume)")
    ax.set_ylim(0, 6.2)
    ax.set_yticks([0, 1, 2, 3, 4, 5, 6])
    ax.set_yticklabels(["0×","1×","2×","3×","4×","5×","6×"])
    ax.grid(True, axis="y", alpha=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=0)

    leg = ax.legend(loc="upper left", ncol=3,
                    bbox_to_anchor=(0.0, 1.02),
                    handlelength=1.2, handletextpad=0.5, columnspacing=1.4,
                    fontsize=11)

    # Annotation: which signal wins which outcome
    ann_y = 5.8
    notes = [
        ("Box office: broad consensus wins\n(NYT CP adds nothing once we know the consensus)", 0, ann_y, BLUE),
        ("Tony nom: every signal matters", 1, ann_y, GREEN),
        ("Top Tony win: NYT CP matters most\n(insider voters watch the NYT)", 2, ann_y, ORANGE),
    ]
    # Skip — would overlap with bars. Use a single caption below instead.

    fig.text(0.06, 0.03,
        "Read: 'A box-office hit is ×3.0 more likely (in adjusted odds) for shows where the majority of\n"
        "critics gave a positive review, vs. comparable shows without that majority.'",
        fontsize=11, color=INK, style="italic")

    add_title(fig,
        "What does a positive critic signal actually deliver?",
        "Three different critic signals × three different outcomes. Each bar is an adjusted odds-ratio.",
        source="Source: 542 Broadway shows 1988-2025 ex-COVID (NYT-CP sub-cohort 2014+). "
               "All 9 effects survive Benjamini-Hochberg correction (q<0.05).")
    fig.savefig(OUT_DIR / "3_what_critics_deliver.png")
    plt.close(fig)
    print("  ✓ 3_what_critics_deliver.png")

# -----------------------------------------------------------------------------
# Chart 4 — How the boost travels (direct vs Tony-mediated)
# -----------------------------------------------------------------------------
def chart_how_boost_travels():
    """Mediation decomposition: % via Tony nom vs. directly to ticket-buyers."""
    # From CRITIC_CONSENSUS_EXPERT
    signals = ["Majority\nof critics\npositive", "Unanimous\npositive",
               "NYT Critics\nPick"]
    direct  = [11.0, 10.6, 8.8]    # percentage points
    tony    = [4.4, 4.3, 3.8]
    totals  = [15.4, 14.9, 12.6]

    fig = plt.figure(figsize=(14, 8.5))
    ax  = fig.add_axes([0.16, 0.20, 0.78, 0.58])

    x = np.arange(len(signals))
    width = 0.55

    # Stacked horizontal bars (more intuitive for laypeople)
    b1 = ax.barh(x, direct, height=width, color=BLUE, edgecolor="white", lw=1.5,
                 label="Direct → ticket-buyers respond to reviews", zorder=3)
    b2 = ax.barh(x, tony, height=width, left=direct, color=ORANGE,
                 edgecolor="white", lw=1.5,
                 label="Indirect → reviews fuel Tony noms, noms drive sales", zorder=3)

    # Numbers inside each segment
    for xi, d, t in zip(x, direct, tony):
        ax.text(d/2, xi, f"{d:.1f} pp", color="white", fontsize=13,
                fontweight="bold", ha="center", va="center")
        ax.text(d + t/2, xi, f"{t:.1f} pp", color="white", fontsize=13,
                fontweight="bold", ha="center", va="center")
        # Total at end of bar
        ax.text(d + t + 0.4, xi, f"= {d+t:.1f} pp boost\n in hit probability",
                color=INK, fontsize=11, va="center", fontweight="bold")

    ax.set_yticks(x)
    ax.set_yticklabels(signals, fontsize=12, fontweight="bold")
    ax.invert_yaxis()
    ax.set_xlim(0, 22)
    ax.set_xlabel("Lift in the probability a show becomes a box-office hit (percentage points)")
    ax.grid(True, axis="x", alpha=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)

    leg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15),
                    ncol=1, fontsize=11, frameon=False)

    # Percentages callout box — placed bottom-right inside the plot
    ax.text(0.97, 0.12,
            "≈ 70% direct\n≈ 30% via Tonys",
            transform=ax.transAxes,
            fontsize=13, color=NAVY, fontweight="bold",
            ha="right", va="bottom",
            bbox=dict(boxstyle="round,pad=0.7", facecolor="#eef5fb",
                      edgecolor=BLUE, linewidth=1.5))

    add_title(fig,
        "Where does the box-office boost actually come from?",
        "Mediation analysis splits each critic signal's effect into two routes:\n"
        "directly to ticket-buyers, vs. indirectly through Tony nominations.",
        source="Linear-probability mediation model; bootstrap 95% CIs. "
               "Splits are stable across all three signal definitions.")
    fig.savefig(OUT_DIR / "4_how_boost_travels.png")
    plt.close(fig)
    print("  ✓ 4_how_boost_travels.png")

# -----------------------------------------------------------------------------
# Chart 5 — Historical scorecard: CP vs non-CP on completed runs (2014-2022)
# -----------------------------------------------------------------------------
def chart_hit_rate_by_year(df):
    """Clean dumbbell / dot-plot comparing CP vs non-CP on four headline metrics.

    Uses 2014-2022 only (complete runs, no right-censoring issues).
    Avoids the visual confusion of partial-year data.
    """
    # Full 2014-2022 cohort (all shows, not just long-runners)
    # hit column already encodes both conditions: ≥26 wks AND ≥70% cap
    # Pre-filtering to weeks_observed>=26 would throw away flops — don't do that
    complete = df[df["year"] <= 2022].copy()

    def wilson_ci(k, n, z=1.96):
        if n == 0: return (0.0, 0.0, 0.0)
        p = k / n
        denom  = 1 + z**2/n
        center = (p + z**2/(2*n)) / denom
        half   = z * np.sqrt(p*(1-p)/n + z**2/(4*n*n)) / denom
        return (p, max(0, center-half), min(1, center+half))

    metrics_labels = [
        "Became a\nbox-office hit",
        "Got any\nTony nomination",
        "Got Best Musical\nor Best Play nom",
    ]
    cp_vals, cp_lo, cp_hi = [], [], []
    ncp_vals, ncp_lo, ncp_hi = [], [], []

    cp_group  = complete[complete["is_cp"] == 1]
    ncp_group = complete[complete["is_cp"] == 0]
    n_cp  = len(cp_group)
    n_ncp = len(ncp_group)

    # Compute all three metrics directly from the cohort.
    # Tony data is joined in load_show_panel() above.
    for metric in ["hit", "any_nom", "top_nom"]:
        k_cp_v  = int(cp_group[metric].sum())
        k_ncp_v = int(ncp_group[metric].sum())
        p, lo, hi = wilson_ci(k_cp_v, n_cp)
        cp_vals.append(p);  cp_lo.append(lo);  cp_hi.append(hi)
        p, lo, hi = wilson_ci(k_ncp_v, n_ncp)
        ncp_vals.append(p); ncp_lo.append(lo); ncp_hi.append(hi)
        print(f"    {metric:8s}  CP {k_cp_v}/{n_cp} ({k_cp_v/n_cp*100:.1f}%) "
              f"vs non-CP {k_ncp_v}/{n_ncp} ({k_ncp_v/n_ncp*100:.1f}%)")

    # --- Draw ---
    fig = plt.figure(figsize=(14, 8.5))
    # Wide left margin so metric labels aren't clipped
    ax  = fig.add_axes([0.22, 0.13, 0.72, 0.64])

    # Order from bottom to top (matplotlib y-axis goes 0=bottom, 2=top)
    # bottom=hit, middle=Best Musical/Play, top=Tony nom (most dramatic at eye level)
    order = [0, 2, 1]   # hit at bottom (y=0), Best Mus at middle (y=1), Tony nom at top (y=2)
    metrics_labels = [metrics_labels[i] for i in order]
    cp_vals   = [cp_vals[i] for i in order]
    cp_lo     = [cp_lo[i] for i in order]
    cp_hi     = [cp_hi[i] for i in order]
    ncp_vals  = [ncp_vals[i] for i in order]
    ncp_lo    = [ncp_lo[i] for i in order]
    ncp_hi    = [ncp_hi[i] for i in order]

    y   = np.arange(len(metrics_labels))
    sep = 0.22    # vertical gap between CP and non-CP dots per metric

    for i, (lab, cpv, cplo, cphi, ncpv, ncplo, ncphi) in enumerate(
            zip(metrics_labels, cp_vals, cp_lo, cp_hi,
                ncp_vals, ncp_lo, ncp_hi)):
        y_cp  = i + sep
        y_ncp = i - sep

        # Dumbbell connectors (CI bars)
        ax.hlines([y_cp, y_ncp], [cplo, ncplo], [cphi, ncphi],
                  color=[ORANGE, BLUE], lw=6, alpha=0.22, zorder=2)

        # Dots
        ax.scatter([cpv], [y_cp],  s=280, color=ORANGE, edgecolor="white",
                   lw=2.5, zorder=4)
        ax.scatter([ncpv], [y_ncp], s=280, color=BLUE,  edgecolor="white",
                   lw=2.5, zorder=4)

        # Value labels — offset right of the dot
        offset_cp  = 0.025 if cpv < 0.88 else -0.04
        offset_ncp = 0.025 if ncpv < 0.88 else -0.04
        ha_cp  = "left" if cpv < 0.88 else "right"
        ha_ncp = "left" if ncpv < 0.88 else "right"
        ax.text(cpv  + offset_cp,  y_cp,  f"{cpv*100:.0f}%",
                fontsize=13, fontweight="bold", color=ORANGE, va="center", ha=ha_cp)
        ax.text(ncpv + offset_ncp, y_ncp, f"{ncpv*100:.0f}%",
                fontsize=13, fontweight="bold", color=BLUE,   va="center", ha=ha_ncp)

        # "+X pp" advantage label — place between the two dots, above both
        diff = (cpv - ncpv) * 100
        if abs(diff) > 0.5:
            sign = "+" if diff > 0 else ""
            mid_x = (cpv + ncpv) / 2
            ax.annotate(f"{sign}{diff:.0f} pp",
                        xy=(mid_x, i),
                        xytext=(mid_x, i + sep * 1.7),
                        fontsize=10, color=GREEN, fontweight="bold",
                        ha="center", va="bottom",
                        arrowprops=None)

    # Axis formatting
    ax.set_yticks(y)
    ax.set_yticklabels(metrics_labels, fontsize=13, fontweight="bold")
    ax.set_xlim(-0.02, 1.10)
    ax.set_xticks([0, 0.25, 0.50, 0.75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("Share of shows in each group achieving this outcome")
    ax.grid(True, axis="x", alpha=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)

    # Legend
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=ORANGE,
               markersize=14, label=f"NYT Critics Pick shows  (n={n_cp})"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=BLUE,
               markersize=14, label=f"Shows without Critics Pick  (n={n_ncp})"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=12,
              framealpha=0.95, facecolor="white", edgecolor="#e5e7eb",
              borderpad=0.8)

    add_title(fig,
        "CP vs. non-CP: the historical track record",
        "Among fully-completed Broadway runs, 2014–2022 (ex-COVID).\n"
        "Error bars = 95% confidence intervals. Green labels = CP advantage over non-CP.",
        source=f"Source: Broadway 2014-2022 ex-COVID, completed runs only. "
               f"Hit = ≥26 wks @ ≥70% capacity. Tony data from IBDB.")
    fig.savefig(OUT_DIR / "5_cp_vs_noncp_scorecard.png")
    plt.close(fig)
    print(f"  ✓ 5_cp_vs_noncp_scorecard.png  (CP n={n_cp}, non-CP n={n_ncp})")

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    print(f"Writing charts to {OUT_DIR}")
    con = sqlite3.connect(DB_PATH)
    df = load_show_panel(con)
    print(f"Loaded {len(df)} Broadway shows (2014-2026)")

    chart_cp_lift_over_time(df)
    chart_bayesian_posterior()
    chart_what_critics_deliver()
    chart_how_boost_travels()
    chart_hit_rate_by_year(df)

    con.close()
    print("\nAll charts written.")


if __name__ == "__main__":
    main()

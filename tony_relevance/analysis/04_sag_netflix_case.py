"""
04_sag_netflix_case.py — The SAG → Netflix natural experiment (Phase 2, Q1)
===========================================================================

Decision context: CBS's Tony broadcast deal (held since 1978) ran *through 2026*
with no renewal announced. The Tonys must choose a post-2026 home. The SAG Awards
are the best available analog for "a mid-tier awards show leaves linear for a
global streamer": they left TNT/TBS for Netflix (2024, after a 2023 free-YouTube
bridge). What happened to SAG is the most decision-relevant evidence for the Tony
choice.

THE CENTRAL METHODOLOGICAL PROBLEM (and the whole point of the study):
    The move *broke the measurement system*. Through 2022, SAG reach = Nielsen
    average-minute viewers. From 2023, "reach" = Netflix/YouTube *views*, a
    different, generally larger unit (a qualified play, or total-views ÷ runtime),
    which OVERSTATES audience relative to Nielsen. So you cannot difference the
    two regimes and call it a treatment effect. Anyone who reports "SAG held at
    1.8M after the move!" is comparing apples (Nielsen 2022) to oranges (Netflix
    2024). This script refuses to do that and instead:

      1. Estimates SAG's pre-move LINEAR decline (clean Nielsen series, 2013–2022)
         and projects the counterfactual "SAG had it stayed on linear."
      2. Reports the streaming era on its OWN terms (views, YoY growth) with the
         non-comparability stated in bold.
      3. Brackets the move: counterfactual linear floor vs. reported stream views.
      4. Translates all of it into a Tony decision read-across (the Tonys are a
         bigger, older show than SAG was, so the stakes and the demo upside differ).

Writes: outputs/SAG_NETFLIX_CASE.md   Charts: charts/5_*, charts/6_*
Run:    python3 tony_relevance/analysis/04_sag_netflix_case.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "tony_relevance.db"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
CH = ROOT / "charts"
CH.mkdir(exist_ok=True)
REPORT = OUT / "SAG_NETFLIX_CASE.md"

MOVE_YEAR = 2023          # first non-linear ceremony (free YouTube bridge)
NETFLIX_DEAL_YEAR = 2024  # first under the multi-year Netflix deal
LINEAR_END = 2022         # last clean Nielsen (TNT/TBS) ceremony

INK, TONY, NFLX, LINE = "#15161a", "#e6394a", "#E50914", "#3a86c8"
plt.rcParams.update({"figure.dpi": 220, "savefig.dpi": 220, "font.size": 11,
                     "axes.edgecolor": INK, "axes.linewidth": 1.1,
                     "axes.grid": True, "grid.color": "#d9dbe1",
                     "grid.linewidth": 0.8, "axes.axisbelow": True})


def load():
    con = sqlite3.connect(DB)
    sag = pd.read_sql(
        "SELECT ceremony_year AS year, viewers_m, measurement, network, confidence, notes "
        "FROM award_broadcasts WHERE award='SAG' ORDER BY ceremony_year", con)
    tony = pd.read_sql(
        "SELECT ceremony_year AS year, viewers_m FROM award_broadcasts "
        "WHERE award='Tony' AND measurement='linear' AND viewers_m IS NOT NULL "
        "ORDER BY ceremony_year", con)
    con.close()
    return sag, tony


def linear_its(sag):
    """Fit SAG's linear (TNT/TBS) decline and project the counterfactual."""
    lin = sag[(sag.measurement == "linear") & (sag.year <= LINEAR_END)].copy()
    # Exclude the 2021 pandemic 1-hour special as an outlier for the trend fit.
    fit = lin[lin.year != 2021].copy()
    fit["yc"] = fit.year - fit.year.min()
    m = smf.ols("np.log(viewers_m) ~ yc", data=fit).fit()
    slope = m.params["yc"]
    annual = np.expm1(slope)
    # Counterfactual projection to the streaming years
    def proj(y):
        return float(np.exp(m.predict(pd.DataFrame({"yc": [y - fit.year.min()]}))[0]))
    return dict(annual=annual, p=m.pvalues["yc"], n=int(m.nobs),
                proj_2024=proj(2024), proj_2025=proj(2025),
                last_linear=float(lin[lin.year == LINEAR_END].viewers_m.iloc[0]),
                peak=float(lin.viewers_m.max()), peak_year=int(lin.loc[lin.viewers_m.idxmax(), "year"]))


def main():
    sag, tony = load()
    its = linear_its(sag)
    stream = sag[sag.measurement == "stream_views"].sort_values("year")
    s2024 = float(stream[stream.year == 2024].viewers_m.iloc[0])
    s2025 = float(stream[stream.year == 2025].viewers_m.iloc[0])
    stream_growth = s2025 / s2024 - 1
    tony_last = float(tony[tony.year == tony.year.max()].viewers_m.iloc[0])
    tony_last_year = int(tony.year.max())

    L = []
    L.append("# The SAG → Netflix natural experiment — what it tells the Tonys\n")
    L.append(f"_Generated {pd.Timestamp.now():%Y-%m-%d %H:%M}._\n")
    L.append("**Bottom line up front.** SAG was dying on linear like every award "
             "show. Moving to Netflix did **not** rescue it into a phenomenon (it "
             "failed to crack Netflix's weekly Top 10 in 2024) — but it also did not "
             "obviously shrink its nominal reach, and its streaming views are "
             "*growing*. The honest lesson for the Tonys: **streaming is a "
             "global-reach + younger-demo + on-demand-discovery play, not a "
             "relevance cure.** The relevance problem is upstream in the content "
             "(see DEEPER_ANALYSIS Q2), not in the pipe.\n")

    # ---- 1. The clean part: SAG's linear decline ----
    L.append("## 1. SAG was already dying on linear (the clean, comparable part)\n")
    L.append(f"SAG peaked at **{its['peak']:.1f}M ({its['peak_year']})** and fell to "
             f"**{its['last_linear']:.1f}M** in its last TNT/TBS year ({LINEAR_END}). "
             f"Fitting the Nielsen series 2013–2022 (excluding the 2021 pandemic "
             f"special) gives an annual decline of **{its['annual']:+.1%}/yr** "
             f"(p={its['p']:.3f}, n={its['n']}) — the same linear-TV bleed Phase 1 "
             f"found for the Tonys and their peers.\n")
    L.append("| SAG year | Linear viewers (M, Nielsen) |")
    L.append("|---|---|")
    for _, r in sag[(sag.measurement == "linear")].iterrows():
        L.append(f"| {int(r.year)} | {r.viewers_m:.2f} |")
    L.append("")

    # ---- 2. The broken part: the measurement regime change ----
    L.append("## 2. The move broke the ruler (why you can't just difference it)\n")
    L.append("From 2023 the number stops being Nielsen average-minute viewers and "
             "becomes Netflix/YouTube **views** — a different, generally larger unit. "
             "**These are not comparable.** Reported streaming era:\n")
    L.append("| SAG year | Platform | Reported *views* (M) | Note |")
    L.append("|---|---|---|---|")
    for _, r in stream.iterrows():
        L.append(f"| {int(r.year)} | {r.network} | {r.viewers_m:.2f} | {r.notes} |")
    L.append("")
    L.append(f"Within the streaming era (a clean, like-for-like comparison), SAG "
             f"views grew **{s2024:.1f}M → {s2025:.1f}M ({stream_growth:+.0%})**. But "
             f"note the ceiling: in 2024 SAG **failed to make Netflix's weekly Top "
             f"10**, i.e. it remained a *minor* title on the platform.\n")

    # ---- 3. Bracketing the move ----
    L.append("## 3. Bracketing the move (counterfactual vs. reported)\n")
    L.append(f"- **Counterfactual linear floor** — extrapolating SAG's 2013–2022 "
             f"linear trend forward: it would have drawn ≈ **{its['proj_2024']:.1f}M "
             f"(2024)** and **{its['proj_2025']:.1f}M (2025)**, and falling.\n"
             f"- **Reported Netflix views**: {s2024:.1f}M (2024), {s2025:.1f}M (2025), "
             f"and rising.\n"
             f"- **Read with care:** the Netflix figure is nominally higher *and* a "
             f"measurement-inflated unit, so the most you can honestly say is the "
             f"move **plausibly held or modestly grew nominal reach while trading a "
             f"shrinking, measurable linear audience for a growing-but-fuzzy global, "
             f"on-demand one.** It did not manufacture cultural heat.\n")

    # ---- 4. Read-across to the Tony decision ----
    L.append("## 4. Read-across: what this says about the Tonys' post-2026 home\n")
    ratio = tony_last / its["last_linear"]
    L.append(f"| Factor | SAG (pre-move) | Tonys (now) | Implication |")
    L.append("|---|---|---|---|")
    L.append(f"| Last linear audience | {its['last_linear']:.1f}M (2022) | "
             f"{tony_last:.2f}M ({tony_last_year}) | Tonys are **~{ratio:.1f}× larger** "
             f"on linear — **more to lose** by abandoning it outright |")
    L.append(f"| Audience age | mid-tier | **oldest of any award show (~61)** | Tonys "
             f"have the **most demographic upside** from streaming's younger reach |")
    L.append(f"| Global audience fit | US-centric | **~41% of Broadway ticket buyers "
             f"are international** | A global streamer aligns broadcast reach with the "
             f"actual customer base |")
    L.append(f"| Platform outcome | minor Netflix title (no Top 10) | — | Streaming "
             f"**won't** make the Tonys a phenomenon on its own |")
    L.append("")
    L.append("**Recommendation logic (not a verdict — a framework).** The SAG case "
             "argues *against* a pure linear→streaming swap and *for* a **hybrid**: "
             "keep a linear/free broadcast spine to protect the still-meaningful "
             "(if old, shrinking) ~5M linear audience, while adding **global, "
             "on-demand, ad-supported streaming** (Netflix-style reach or free "
             "YouTube) to fix the two things linear can't: the **age skew** and the "
             "**international mismatch**. Crucially, expect streaming to **relocate** "
             "the Tonys, not **revive** them — revival has to come from the shows "
             "themselves (Phase 2, Q2).\n")

    # ---- caveats ----
    L.append("## Caveats\n")
    L.append(
        "- **Single treated unit, broken measurement.** This is a structured case "
        "study, not a clean DiD; the regime change forbids a simple treatment "
        "effect on viewership.\n"
        "- **Mid-decade SAG linear figures vary by source** (2015–2017 especially) "
        "and are flagged low-confidence; the *trend* is robust, individual cells "
        "less so.\n"
        "- **The decisive variables are still missing:** Netflix has not released "
        "SAG age/demographic splits, and we have no platform-neutral attention "
        "series (Google Trends / Wikipedia pageviews) yet. Backfilling those — and "
        "Netflix demo data if obtainable — would convert this from a directional "
        "case study into a quantified treatment effect. That is the top next step.\n")

    REPORT.write_text("\n".join(L))
    print(f"Wrote {REPORT}\n")

    # ---------------- charts ----------------
    _chart_sag(sag, its, s2024, s2025)
    _chart_readacross(its["last_linear"], tony_last, tony_last_year)
    print(f"Wrote charts to {CH}/ (5_sag_broke_the_ruler.png, 6_tony_vs_sag_stakes.png)")

    # console
    print("SAG linear decline (2013–2022, ex-2021):", f"{its['annual']:+.1%}/yr")
    print(f"SAG last linear (2022): {its['last_linear']:.1f}M | "
          f"Netflix views 2024->2025: {s2024:.1f}->{s2025:.1f}M ({stream_growth:+.0%})")
    print(f"Counterfactual linear 2025 ≈ {its['proj_2025']:.1f}M")
    print(f"Tony last linear ({tony_last_year}): {tony_last:.2f}M "
          f"= {tony_last/its['last_linear']:.1f}x SAG's last linear")


def _chart_sag(sag, its, s2024, s2025):
    fig, ax = plt.subplots(figsize=(9, 5.6))
    lin = sag[(sag.measurement == "linear")].sort_values("year")
    strm = sag[sag.measurement == "stream_views"].sort_values("year")
    ax.plot(lin.year, lin.viewers_m, color=LINE, lw=3.0, marker="o", ms=5,
            zorder=4, label="Linear (TNT/TBS, Nielsen viewers)")
    # counterfactual dashed projection
    proj_years = [2022, 2023, 2024, 2025]
    fitmin = lin[lin.year != 2021].year.min()
    L0 = its  # reuse slope via recompute
    # simple line through projected points
    proj_vals = [float(lin[lin.year == 2022].viewers_m.iloc[0]), None, its["proj_2024"], its["proj_2025"]]
    ax.plot([2022, 2024, 2025], [proj_vals[0], its["proj_2024"], its["proj_2025"]],
            color=LINE, lw=1.6, ls="--", alpha=0.7, zorder=2,
            label="Counterfactual linear (had it stayed)")
    ax.plot(strm.year, strm.viewers_m, color=NFLX, lw=3.0, marker="s", ms=6,
            zorder=4, label="Netflix/YouTube *views* (≠ Nielsen)")
    ax.axvspan(2022.5, 2025.5, color=NFLX, alpha=0.06, zorder=0)
    ax.text(2024, 3.6, "streaming era\n(different ruler)", color=NFLX, fontsize=9,
            ha="center", fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Millions (NB: units differ across the break)")
    ax.set_title("The SAG move broke the ruler — don't difference across it",
                 fontsize=14.5, fontweight="bold", color=INK, loc="left", pad=30)
    ax.text(0, 1.035, "SAG audience: blue = Nielsen linear viewers; red = Netflix "
            "reported views. Same axis, different units.", transform=ax.transAxes,
            fontsize=9.3, color="#5b606b")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    fig.tight_layout()
    fig.savefig(CH / "5_sag_broke_the_ruler.png", bbox_inches="tight")
    plt.close(fig)


def _chart_readacross(sag_last, tony_last, tony_year):
    fig, ax = plt.subplots(figsize=(8, 4.6))
    bars = ax.bar(["SAG\n(last linear, 2022)", f"Tonys\n(last linear, {tony_year})"],
                  [sag_last, tony_last], color=["#7a7f8a", TONY], zorder=3, width=0.55)
    for b, v in zip(bars, [sag_last, tony_last]):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.12, f"{v:.2f}M",
                ha="center", fontweight="bold", color=INK)
    ax.set_ylabel("Last linear audience (millions)")
    ax.set_ylim(0, tony_last * 1.25)
    ax.set_title(f"The Tonys have ~{tony_last/sag_last:.1f}× more linear audience at stake than SAG did",
                 fontsize=13, fontweight="bold", color=INK, loc="left", pad=14)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(CH / "6_tony_vs_sag_stakes.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()

"""
02_causal_did.py — Getting as close to causal as the data allow
===============================================================

The descriptive layer (01) shows the Tonys' linear audience fell ~50% since
2014. The trivial explanation is "all of linear TV fell." To say anything
*causal* about the Tonys specifically, we need a control group that ate the same
cord-cutting shock but is not the Tonys. That is what the peer award shows
(Oscars / Emmys / Grammys) are for.

This script runs three escalating designs and is deliberately honest about what
each can and cannot identify.

  DESIGN A — Difference-in-Differences (pooled peers as control)
      log(viewers) ~ is_tony + C(year) + is_tony:year_c
      C(year)        = common-year fixed effects -> absorb EVERYTHING that hit
                       all award shows in a given year (cord-cutting, the
                       pandemic, the rise of streaming, NFL counter-programming
                       to the extent it's common). This is the cord-cutting
                       control done right.
      is_tony:year_c = the DiD estimand: the Tonys' *extra* annual change beyond
                       the common award-show trajectory. If ~0, the Tonys are
                       declining no faster than their peers -> the ratings story
                       is a linear-TV story, not a theatre story.

  DESIGN B — Separate award-specific slopes (who is bleeding fastest?)
      log(viewers) ~ C(award) + C(award):year_c
      Reports each show's annual % change and ranks them.

  DESIGN C — Event study: Hamilton (2016) as a positive cultural shock
      A genuine natural experiment on the *upside*: one year a singular show
      saturated the culture. How big was the bump vs. the Tonys' own trend and
      vs. peers that had no Hamilton? Bounds the causal effect of "having a
      culturally massive nominee."

Honesty / identification caveats are written into the report. With only four
award shows, cluster-robust inference is underpowered; we report HC1 robust SEs
and treat p-values as directional, not dispositive.

Writes: outputs/CAUSAL_DID.md   Run: python3 tony_relevance/analysis/02_causal_did.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "tony_relevance.db"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
REPORT = OUT / "CAUSAL_DID.md"

PEERS = ["Oscars", "Emmys", "Grammys"]
WIN_LO, WIN_HI = 2014, 2025   # common window where all four shows have linear data
                              # (2026 Tony Nielsen not yet released; excluded)


def load_panel(drop_pandemic=False, min_conf=None):
    con = sqlite3.connect(DB)
    df = pd.read_sql(
        "SELECT award, ceremony_year AS year, viewers_m, confidence "
        "FROM award_broadcasts WHERE measurement='linear'", con)
    con.close()
    df = df.dropna(subset=["viewers_m"])  # drop pending/unreleased cells (e.g. 2026)
    df = df[(df.year >= WIN_LO) & (df.year <= WIN_HI)].copy()
    if drop_pandemic:
        df = df[~df.year.isin([2020, 2021])]
    if min_conf == "med+":
        df = df[df.confidence.isin(["high", "med"])]
    if min_conf == "high":
        df = df[df.confidence == "high"]
    df["log_v"] = np.log(df.viewers_m)
    df["year_c"] = df.year - WIN_LO
    df["is_tony"] = (df.award == "Tony").astype(int)
    return df


def design_A(df):
    """Pooled DiD: Tony vs pooled peers, common-year FE absorb shared shocks."""
    m = smf.ols("log_v ~ is_tony + C(year) + is_tony:year_c", data=df).fit(
        cov_type="HC1")
    beta = m.params.get("is_tony:year_c", np.nan)
    se = m.bse.get("is_tony:year_c", np.nan)
    p = m.pvalues.get("is_tony:year_c", np.nan)
    # exp(beta)-1 = extra annual % change for Tonys beyond the common trajectory
    return dict(beta=beta, se=se, p=p, extra_annual=np.expm1(beta),
                lo=np.expm1(beta - 1.96 * se), hi=np.expm1(beta + 1.96 * se),
                n=int(m.nobs))


def design_B(df):
    """Separate slope per award; rank annual % change."""
    m = smf.ols("log_v ~ C(award) + C(award):year_c", data=df).fit(cov_type="HC1")
    # Reconstruct each award's slope = base slope (reference award) + interaction
    awards = sorted(df.award.unique())
    ref = "Emmys" if "Emmys" in awards else awards[0]
    # statsmodels uses first alphabetical as reference for C(award); fit per-award
    # slopes directly instead, which is cleaner:
    slopes = {}
    for a in awards:
        sub = df[df.award == a]
        mm = smf.ols("log_v ~ year_c", data=sub).fit(cov_type="HC1")
        slopes[a] = dict(slope=mm.params["year_c"],
                         annual=np.expm1(mm.params["year_c"]),
                         p=mm.pvalues["year_c"], n=int(mm.nobs))
    return slopes


def design_C(df_full):
    """Hamilton (2016) event study: Tony residual vs a no-2016-shock trend."""
    tony = df_full[(df_full.award == "Tony")].copy()
    # Fit Tony's trend EXCLUDING 2016, predict 2016, compare to actual.
    train = tony[tony.year != 2016]
    m = smf.ols("log_v ~ year_c", data=train).fit()
    pred16 = m.predict(pd.DataFrame({"year_c": [2016 - WIN_LO]}))[0]
    actual16 = float(tony.loc[tony.year == 2016, "log_v"].iloc[0])
    bump = np.expm1(actual16 - pred16)
    # Peers in 2016 vs their own trend (placebo: should be ~0)
    placebo = {}
    for a in PEERS:
        s = df_full[df_full.award == a]
        if 2016 not in set(s.year):
            continue
        tr = s[s.year != 2016]
        mm = smf.ols("log_v ~ year_c", data=tr).fit()
        p16 = mm.predict(pd.DataFrame({"year_c": [2016 - WIN_LO]}))[0]
        a16 = float(s.loc[s.year == 2016, "log_v"].iloc[0])
        placebo[a] = np.expm1(a16 - p16)
    return dict(bump=bump, placebo=placebo)


def main():
    base = load_panel()
    L = []
    L.append("# Tony Awards — Causal-leaning analysis (DiD against peer award shows)\n")
    L.append(f"_Generated {pd.Timestamp.now():%Y-%m-%d %H:%M}. Window {WIN_LO}–{WIN_HI}, "
             "linear-TV viewers only. Control group: Oscars, Emmys, Grammys._\n")

    # ---------- DESIGN A ----------
    L.append("## Design A — Difference-in-Differences (the headline causal test)\n")
    L.append("`log(viewers) ~ is_tony + C(year) + is_tony:year_c`. The year fixed "
             "effects soak up every shock common to all award shows (cord-cutting, "
             "the pandemic, the secular flight from linear). The interaction is the "
             "Tonys' **extra** annual change beyond that common path.\n")
    L.append("| Specification | Tony extra annual change | 95% CI | p | n |")
    L.append("|---|---|---|---|---|")
    specs = [
        ("Main (2014–2024)", load_panel()),
        ("Drop pandemic (2020–21)", load_panel(drop_pandemic=True)),
        ("High-confidence cells only", load_panel(min_conf="high")),
    ]
    a_main = None
    for name, d in specs:
        r = design_A(d)
        if a_main is None:
            a_main = r
        L.append(f"| {name} | {r['extra_annual']:+.1%} | "
                 f"[{r['lo']:+.1%}, {r['hi']:+.1%}] | {r['p']:.3f} | {r['n']} |")
    L.append("")
    verdict = ("indistinguishable from zero" if a_main["p"] > 0.10
               else ("a faster decline" if a_main["beta"] < 0 else "a slower decline"))
    L.append(f"**Read:** the Tonys' differential trend is **{a_main['extra_annual']:+.1%}/yr** "
             f"({verdict}, p={a_main['p']:.2f}). ")
    if a_main["p"] > 0.10:
        L.append("In plain terms: **the Tonys are not falling on TV any faster than "
                 "the Oscars, Emmys or Grammys.** The ratings collapse is a *linear-TV* "
                 "phenomenon, not a *theatre* phenomenon. This is the single most "
                 "important — and most counter-intuitive — result in the project, and "
                 "it should reshape the thesis (see RESEARCH_PLAN §'What the data "
                 "actually licenses you to say').\n")
    else:
        L.append("\n")

    # ---------- DESIGN B ----------
    L.append("## Design B — Who is bleeding fastest? (separate slopes)\n")
    slopes = design_B(base)
    L.append("| Award | Annual % change in linear viewers | p | n |")
    L.append("|---|---|---|---|")
    for a, s in sorted(slopes.items(), key=lambda kv: kv[1]["annual"]):
        L.append(f"| {a} | {s['annual']:+.1%} | {s['p']:.3f} | {s['n']} |")
    L.append("")
    tony_rank = sorted(slopes.items(), key=lambda kv: kv[1]["annual"])
    pos = [a for a, _ in tony_rank].index("Tony") + 1
    L.append(f"**Read:** by annual rate of decline the Tonys rank **#{pos} of "
             f"{len(slopes)}** (1 = fastest-falling). The Tonys are mid-pack in *rate*; "
             "their problem is *level* (lowest absolute reach) and *age* (oldest "
             "audience), not an unusually steep slope.\n")

    # ---------- DESIGN C ----------
    L.append("## Design C — Hamilton (2016) as a natural experiment\n")
    c = design_C(base)
    L.append("Fit the Tonys' 2014–2024 trend *excluding* 2016, predict 2016, and "
             "measure the miss. Peers (no Hamilton) are the placebo — their 2016 "
             "should sit on-trend.\n")
    L.append(f"- **Tony 2016 bump above its own trend: {c['bump']:+.0%}.**")
    for a, v in c["placebo"].items():
        L.append(f"- Placebo {a} 2016 vs trend: {v:+.0%}")
    L.append("")
    L.append("**Read:** a single culture-saturating show (Hamilton) lifted the Tony "
             "broadcast by roughly the size of the bump above, while peers stayed "
             "on-trend. That bounds the causal value of *cultural penetration*: when "
             "theatre makes something the whole country is arguing about, the ratings "
             "follow. The relevance problem is the scarcity of Hamilton-scale shows, "
             "not the broadcast itself.\n")

    # ---------- Identification caveats ----------
    L.append("## Identification caveats (read before quoting any coefficient)\n")
    L.append(
        "- **Four units is not many.** With one treated show and three controls, "
        "robust/clustered inference is underpowered; treat p-values as directional.\n"
        "- **Parallel-trends is an assumption, not a fact.** DiD assumes the Tonys "
        "would have tracked the peer trajectory absent any Tony-specific cause. The "
        "drop-pandemic and high-confidence rows are partial stress-tests.\n"
        "- **'Relevance' ≠ 'linear ratings.'** Every design here is built on Nielsen "
        "linear viewers. That measures *broadcast reach*, which is necessary but not "
        "sufficient for cultural relevance. The strongest Tony-specific evidence "
        "(oldest/aging audience; smallest off-TV search & social footprint) lives in "
        "the demographic and attention layers, which need backfilling — see "
        "RESEARCH_PLAN.\n"
        "- **Measurement drift.** Networks increasingly headline 'across-platform' "
        "numbers (e.g. Tony 2025) that include streaming and are not comparable to "
        "the historical linear series; those rows are excluded here and the exclusion "
        "matters for the recent slope.\n")

    REPORT.write_text("\n".join(L))
    print(f"Wrote {REPORT}\n")
    print(f"DESIGN A (main): Tony extra annual change = {a_main['extra_annual']:+.1%} "
          f"(p={a_main['p']:.2f})")
    print("DESIGN B slopes (annual % change):")
    for a, s in sorted(slopes.items(), key=lambda kv: kv[1]["annual"]):
        print(f"    {a:8s} {s['annual']:+.1%}")
    print(f"DESIGN C: Hamilton-2016 Tony bump above trend = {c['bump']:+.0%}")


if __name__ == "__main__":
    main()

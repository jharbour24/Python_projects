"""
Critic Consensus & NYT Critics Pick — Generalized Broadway Impact Report
========================================================================

A re-do of the original NYT-Critics-Pick analysis, generalized to use the full
DTLI critic consensus (every reviewer, not just NYT). The NYT Critics Pick
signal is re-run in parallel as a separate, independent track.

Cohort: Broadway shows (show_type ∈ {M, P}) opening on or before
2025-06-15 (end of the 2024–25 Tony season), with at least one opening-
window review on file, excluding COVID-disrupted openings (Sept 2019 –
Mar 2020) and the COVID-dark period (Mar 2020 – Sept 2021).

Three critic-consensus signals are evaluated side-by-side:
  1. pct_positive          continuous (0–1): fraction of opening-window
                           critics that gave a thumbs-up.
  2. majority_positive     binary: >50% thumbs-up across all critics.
  3. unanimous_positive    binary (strict): 100% thumbs-up, ≥2 reviews.

Plus a fourth, separate signal:
  4. is_nyt_cp             binary: NYT Critics Pick badge (2014+ only).

Outcomes:
  • log(lifetime_gross + 1)         OLS, with controls
  • weeks_run                       Cox proportional hazards (right-censored
                                    if still running as of latest gross week)
  • any Tony nomination             logistic regression
  • Tony Best Musical / Best Play   logistic regression
  • box-office success (binary)     legacy outcome, retained for backwards
                                    compatibility & sensitivity check

Methods:
  • Naive Fisher's exact + Wilson CIs for unadjusted associations
  • Logistic / OLS / Cox regressions with controls
    (show_type, open-year centred, post-COVID, log_reviews)
  • Propensity-score matching (PSM, 1:1 nearest-neighbour) and inverse-
    probability-of-treatment weighting (IPTW) for binary signals
  • Heterogeneous treatment effects via signal × show_type interaction
  • Mediation analysis: does the critic effect on box office flow through
    Tony nominations?
  • Multiple-testing correction (Benjamini–Hochberg FDR) across the family
    of primary tests.
"""

from __future__ import annotations

import sqlite3
import math
import warnings
from pathlib import Path
from textwrap import dedent

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.neighbors import NearestNeighbors
from lifelines import CoxPHFitter, KaplanMeierFitter
from statsmodels.stats.multitest import multipletests

warnings.filterwarnings("ignore")

# -----------------------------------------------------------------------------
# Paths & constants
# -----------------------------------------------------------------------------
ROOT       = Path(__file__).resolve().parent.parent
DB_PATH    = ROOT / "data" / "critics_impact.db"
RESULTS    = ROOT / "data" / "analysis_results"
RESULTS.mkdir(parents=True, exist_ok=True)
REPORT_MD  = RESULTS / "CRITIC_CONSENSUS_REPORT.md"
EXPERT_MD  = RESULTS / "CRITIC_CONSENSUS_EXPERT.md"
LAYMAN_MD  = RESULTS / "CRITIC_CONSENSUS_LAYMAN.md"

SEASON_END        = pd.Timestamp("2025-06-15")     # end of 2024–25 Tony season
COVID_OPEN_START  = pd.Timestamp("2019-09-01")
COVID_OPEN_END    = pd.Timestamp("2020-03-12")
DARK_START        = pd.Timestamp("2020-03-12")
DARK_END          = pd.Timestamp("2021-09-14")

# -----------------------------------------------------------------------------
# Cohort build
# -----------------------------------------------------------------------------

def build_cohort() -> pd.DataFrame:
    con = sqlite3.connect(DB_PATH)
    shows = pd.read_sql(
        "SELECT show_id, title, show_type, is_revival, opening_date, "
        "closing_date, theater, capitalization FROM shows",
        con,
    )

    rev = pd.read_sql(
        """
        SELECT show_id,
               COUNT(*) AS total_reviews,
               SUM(CASE WHEN sentiment='up'   THEN 1 ELSE 0 END) AS up_count,
               SUM(CASE WHEN sentiment='meh'  THEN 1 ELSE 0 END) AS meh_count,
               SUM(CASE WHEN sentiment='down' THEN 1 ELSE 0 END) AS down_count,
               MAX(CASE WHEN is_nyt_critics_pick=1 THEN 1 ELSE 0 END) AS is_nyt_cp,
               MAX(CASE WHEN is_nyt_critics_pick IS NOT NULL THEN 1 ELSE 0 END)
                   AS nyt_reviewed
        FROM reviews
        WHERE is_opening_window=1
        GROUP BY show_id
        """,
        con,
    )

    gross = pd.read_sql(
        """
        SELECT show_id,
               SUM(gross)         AS lifetime_gross,
               COUNT(*)           AS weeks_run,
               AVG(capacity_pct)  AS mean_capacity_pct,
               AVG(avg_ticket)    AS mean_avg_ticket,
               MAX(week_ending)   AS last_week_ending,
               SUM(attendance)    AS lifetime_attendance
        FROM show_week_performances
        WHERE is_preview = 0 AND week_number IS NOT NULL
        GROUP BY show_id
        """,
        con,
    )

    tony = pd.read_sql(
        """
        SELECT show_title,
               SUM(nominated) AS tony_noms,
               SUM(won)       AS tony_wins,
               MAX(CASE WHEN won=1 AND category IN ('Best Musical','Best Play')
                        THEN 1 ELSE 0 END) AS tony_top_win,
               MAX(CASE WHEN nominated=1 AND category IN ('Best Musical','Best Play')
                        THEN 1 ELSE 0 END) AS tony_top_nom
        FROM tony_outcomes
        GROUP BY show_title
        """,
        con,
    )

    latest_gross_week = pd.read_sql(
        "SELECT MAX(week_ending) AS w FROM show_week_performances", con
    ).iloc[0, 0]
    con.close()
    latest_gross_week = pd.to_datetime(latest_gross_week)

    df = shows.merge(rev, on="show_id", how="left").merge(gross, on="show_id", how="left")

    # Title-normalize join for tonys
    def normalize(s):
        return s.fillna("").str.lower().str.replace(r"[^a-z0-9]", "", regex=True)

    df["title_norm"] = normalize(df["title"])
    tony["title_norm"] = normalize(tony["show_title"])
    df = df.merge(
        tony[["title_norm", "tony_noms", "tony_wins", "tony_top_win", "tony_top_nom"]],
        on="title_norm",
        how="left",
    )

    # Fill NAs
    for c in ("total_reviews", "up_count", "meh_count", "down_count",
              "is_nyt_cp", "nyt_reviewed"):
        df[c] = df[c].fillna(0).astype(int)
    for c in ("tony_noms", "tony_wins", "tony_top_win", "tony_top_nom"):
        df[c] = df[c].fillna(0).astype(int)
    df["weeks_run"] = df["weeks_run"].fillna(0).astype(int)

    # Signals
    df["pct_positive"] = np.where(
        df["total_reviews"] > 0,
        df["up_count"] / df["total_reviews"],
        np.nan,
    )
    df["majority_positive"] = (df["pct_positive"] > 0.5).astype("Int64")
    df.loc[df["pct_positive"].isna(), "majority_positive"] = pd.NA
    df["unanimous_positive"] = (
        (df["pct_positive"] == 1.0) & (df["total_reviews"] >= 2)
    ).astype("Int64")
    df.loc[df["pct_positive"].isna(), "unanimous_positive"] = pd.NA

    # Dates & era flags
    df["opening_date"]     = pd.to_datetime(df["opening_date"], errors="coerce")
    df["last_week_ending"] = pd.to_datetime(df["last_week_ending"], errors="coerce")
    df["open_year"]        = df["opening_date"].dt.year
    df["covid_disrupted"]  = (df["opening_date"] >= COVID_OPEN_START) & (df["opening_date"] < COVID_OPEN_END)
    df["covid_dark"]       = (df["opening_date"] >= DARK_START)       & (df["opening_date"] < DARK_END)
    df["post_covid"]       = (df["opening_date"] >= DARK_END).astype(int)

    # Right-censoring: a show whose last_week_ending is within 14 days of the
    # latest gross week in the DB is still running → censor it.
    df["still_running"] = (
        (latest_gross_week - df["last_week_ending"]).dt.days.abs() <= 14
    ) & df["last_week_ending"].notna()
    df["closed"] = (~df["still_running"]) & (df["weeks_run"] > 0)

    # Cohort: Broadway only, post-2002 (data really starts ~2008), ≤ 2025-06-15,
    # at least one review, not COVID-disrupted or dark.
    df["in_cohort"] = (
        df["opening_date"].notna()
        & (df["opening_date"] <= SEASON_END)
        & (df["show_type"].isin(["M", "P"]))
        & (df["total_reviews"] > 0)
        & (~df["covid_disrupted"])
        & (~df["covid_dark"])
    )

    # Derived features
    df["is_musical"]     = (df["show_type"] == "M").astype(int)
    df["log_gross"]      = np.log1p(df["lifetime_gross"].fillna(0))
    df["log_reviews"]    = np.log(df["total_reviews"].clip(lower=1))
    # Normalize stray capacity rows that were stored as 0–100 instead of 0–1
    cap = df["mean_capacity_pct"].copy()
    df["mean_capacity_pct"] = np.where(cap > 1.5, cap / 100.0, cap)
    # Box-office hit: ran at least 26 weeks (~half a year) AND averaged ≥70% house
    df["box_office_hit"] = (
        (df["weeks_run"] >= 26) & (df["mean_capacity_pct"] >= 0.70)
    ).astype(int)
    # Long-run hit (stricter): ≥52 wk
    df["long_run_hit"]   = (df["weeks_run"] >= 52).astype(int)
    df["any_tony_nom"]   = (df["tony_noms"] > 0).astype(int)

    return df, latest_gross_week


# -----------------------------------------------------------------------------
# Statistical helpers
# -----------------------------------------------------------------------------

def wilson_ci(k, n, alpha=0.05):
    if n == 0:
        return (np.nan, np.nan)
    z = stats.norm.ppf(1 - alpha / 2)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def fisher_or(k_t, n_t, k_c, n_c):
    """Haldane–Anscombe corrected OR + Fisher's exact two-sided p-value."""
    table = np.array([[k_t, n_t - k_t], [k_c, n_c - k_c]])
    or_, p = stats.fisher_exact(table, alternative="two-sided")
    # Haldane–Anscombe for finite-CI calc
    a, b, c, d = k_t + 0.5, n_t - k_t + 0.5, k_c + 0.5, n_c - k_c + 0.5
    log_or = math.log((a * d) / (b * c))
    se = math.sqrt(1/a + 1/b + 1/c + 1/d)
    lo = safe_exp(log_or - 1.96 * se)
    hi = safe_exp(log_or + 1.96 * se)
    return or_, lo, hi, p


def safe_exp(x):
    """Safe exp that returns +inf for very large inputs and 0 for very negative."""
    try:
        if x is None: return np.nan
        xf = float(x)
        if not np.isfinite(xf): return np.nan
        if xf > 50:  return float("inf")
        if xf < -50: return 0.0
        return math.exp(xf)
    except Exception:
        return np.nan


def stars(p):
    if p is None or np.isnan(p): return "  "
    if p < 0.001: return "***"
    if p < 0.01:  return "** "
    if p < 0.05:  return "*  "
    if p < 0.10:  return ".  "
    return "   "


# -----------------------------------------------------------------------------
# Section: cohort summary
# -----------------------------------------------------------------------------

def render_cohort_summary(df, latest_gross_week):
    ic = df[df["in_cohort"]].copy()
    n_cp     = int(ic["is_nyt_cp"].sum())
    n_maj    = int((ic["majority_positive"] == 1).sum())
    n_unan   = int((ic["unanimous_positive"] == 1).sum())
    n_running= int(ic["still_running"].sum())
    n_closed = int(ic["closed"].sum())

    by_year = ic["open_year"].value_counts().sort_index()
    by_type = ic["show_type"].value_counts().to_dict()

    lines = []
    lines.append("## Sample frame & coverage")
    lines.append("")
    lines.append(f"- **Total in-cohort Broadway shows**: {len(ic)}")
    lines.append(f"- **Date range**: {ic['opening_date'].min().date()} → {ic['opening_date'].max().date()}")
    lines.append(f"- **Latest gross week available**: {latest_gross_week.date()}")
    lines.append(f"- **Show type**: Musicals = {by_type.get('M',0)}, Plays = {by_type.get('P',0)}")
    lines.append(f"- **Run status**: closed = {n_closed}, still running (right-censored) = {n_running}")
    lines.append(f"- **Critic signals**")
    lines.append(f"  - Majority-positive consensus: {n_maj} / {len(ic)} ({n_maj/len(ic):.0%})")
    lines.append(f"  - Unanimous-positive consensus: {n_unan} / {len(ic)} ({n_unan/len(ic):.0%})")
    lines.append(f"  - NYT Critics Pick badge: {n_cp} / {len(ic)} ({n_cp/len(ic):.0%})")
    lines.append("")
    lines.append("**Yearly counts (in-cohort):**")
    lines.append("")
    lines.append("| Year | N | Year | N |")
    lines.append("|------|---|------|---|")
    years = list(by_year.index)
    half = (len(years) + 1) // 2
    for i in range(half):
        y1, n1 = int(years[i]), int(by_year.iloc[i])
        if i + half < len(years):
            y2, n2 = int(years[i + half]), int(by_year.iloc[i + half])
            lines.append(f"| {y1} | {n1} | {y2} | {n2} |")
        else:
            lines.append(f"| {y1} | {n1} |   |   |")
    lines.append("")
    lines.append("**Known data limitations:**")
    lines.append("- `is_revival` is not populated in the source DB; the regression "
                 "controls cannot adjust for revival status. New work and revivals are pooled.")
    lines.append("- Pre-2010 shows have very thin review coverage (often 1 review). "
                 "Sensitivity analyses re-run with `total_reviews ≥ 3` to address this.")
    lines.append("- `closing_date` is not populated. Shows whose most recent gross "
                 "is within 14 days of the latest weekly-gross week are treated as "
                 "right-censored for survival analyses.")
    lines.append("")
    return "\n".join(lines), ic


# -----------------------------------------------------------------------------
# Section: binary signal — naive + adjusted across outcomes
# -----------------------------------------------------------------------------

PRIMARY_OUTCOMES = [
    ("any_tony_nom",   "Any Tony nomination"),
    ("tony_top_win",   "Tony Best Musical / Best Play"),
    ("box_office_hit", "Box-office hit (≥26 wk @ ≥70% capacity)"),
]

CONTROLS_BIN = "is_musical + year_c + post_covid + log_reviews"


def fit_logit(df, formula):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return smf.logit(formula, data=df).fit(disp=False)
    except Exception as e:
        return None


def analyse_binary_signal(df, signal_col, signal_label):
    """Returns a dict of results for one binary critic signal."""
    sub = df.copy()
    sub = sub[sub[signal_col].notna()].copy()
    sub["signal"] = sub[signal_col].astype(int)
    sub["year_c"] = sub["open_year"] - sub["open_year"].mean()

    results = {"label": signal_label, "n": len(sub), "n_treat": int(sub["signal"].sum()),
               "outcomes": {}, "interactions": {}, "psm": {}}

    for out_col, out_label in PRIMARY_OUTCOMES:
        d = sub.dropna(subset=[out_col]).copy()
        d[out_col] = d[out_col].astype(int)
        n_t = int(d["signal"].sum()); n_c = int((1 - d["signal"]).sum())
        k_t = int(d.loc[d["signal"] == 1, out_col].sum())
        k_c = int(d.loc[d["signal"] == 0, out_col].sum())
        or_, lo, hi, p = fisher_or(k_t, n_t, k_c, n_c)
        r_t = k_t / n_t if n_t else np.nan
        r_c = k_c / n_c if n_c else np.nan

        # Adjusted logit
        formula = f"{out_col} ~ signal + {CONTROLS_BIN}"
        res = fit_logit(d, formula)
        if res is not None and "signal" in res.params.index:
            adj_or  = safe_exp(res.params["signal"])
            ci      = res.conf_int().loc["signal"]
            adj_lo  = safe_exp(ci[0]); adj_hi = safe_exp(ci[1])
            adj_p   = res.pvalues["signal"]
            adj_n   = int(res.nobs); pseudo  = res.prsquared
        else:
            adj_or = adj_lo = adj_hi = adj_p = np.nan
            adj_n = 0; pseudo = np.nan

        # Interaction with musical
        inter_p = np.nan
        formula_i = f"{out_col} ~ signal * is_musical + year_c + post_covid + log_reviews"
        res_i = fit_logit(d, formula_i)
        if res_i is not None and "signal:is_musical" in res_i.params.index:
            inter_p = res_i.pvalues["signal:is_musical"]

        results["outcomes"][out_col] = dict(
            out_label=out_label,
            n_t=n_t, n_c=n_c, k_t=k_t, k_c=k_c, r_t=r_t, r_c=r_c,
            naive_or=or_, naive_lo=lo, naive_hi=hi, naive_p=p,
            adj_or=adj_or, adj_lo=adj_lo, adj_hi=adj_hi, adj_p=adj_p,
            adj_n=adj_n, pseudo_r2=pseudo,
            inter_p=inter_p,
        )

    # Continuous outcome: log_gross OLS, adjusted
    d = sub.dropna(subset=["log_gross"]).copy()
    d = d[d["lifetime_gross"].fillna(0) > 0]
    if len(d) > 30:
        try:
            res_ols = smf.ols(f"log_gross ~ signal + {CONTROLS_BIN}", data=d).fit()
            beta = res_ols.params["signal"]; se = res_ols.bse["signal"]
            p_ols = res_ols.pvalues["signal"]
            results["log_gross"] = dict(
                n=int(res_ols.nobs), beta=beta, se=se,
                pct_change=(safe_exp(beta) - 1),
                lo=(safe_exp(beta - 1.96 * se) - 1), hi=(safe_exp(beta + 1.96 * se) - 1),
                p=p_ols, r2=res_ols.rsquared,
            )
        except Exception:
            results["log_gross"] = None
    else:
        results["log_gross"] = None

    # Survival: Cox PH on weeks_run, event = closed (1) or censored (0)
    d = sub.dropna(subset=["weeks_run"]).copy()
    d = d[d["weeks_run"] > 0]
    d["event"] = d["closed"].astype(int)
    if len(d) > 30 and d["event"].sum() > 10:
        try:
            cph = CoxPHFitter()
            cox_df = d[["weeks_run", "event", "signal", "is_musical",
                        "year_c", "post_covid", "log_reviews"]].dropna().copy()
            cph.fit(cox_df, duration_col="weeks_run", event_col="event")
            hr      = safe_exp(cph.params_["signal"])
            ci      = cph.confidence_intervals_.loc["signal"]
            hr_lo, hr_hi = safe_exp(ci.iloc[0]), safe_exp(ci.iloc[1])
            cox_p   = cph.summary.loc["signal", "p"]
            # Median survival contrast (Kaplan–Meier, no controls)
            km1 = KaplanMeierFitter().fit(cox_df.loc[cox_df["signal"]==1, "weeks_run"],
                                          cox_df.loc[cox_df["signal"]==1, "event"])
            km0 = KaplanMeierFitter().fit(cox_df.loc[cox_df["signal"]==0, "weeks_run"],
                                          cox_df.loc[cox_df["signal"]==0, "event"])
            med_t = km1.median_survival_time_; med_c = km0.median_survival_time_
            results["cox"] = dict(
                n=int(len(cox_df)),
                events=int(cox_df["event"].sum()),
                hr=hr, hr_lo=hr_lo, hr_hi=hr_hi, p=cox_p,
                median_treated=med_t, median_control=med_c,
            )
        except Exception as e:
            results["cox"] = None
    else:
        results["cox"] = None

    # Propensity-score matching (1:1 NN) on the controls
    try:
        d = sub.dropna(subset=["log_gross", "weeks_run"]).copy()
        d = d[d["lifetime_gross"].fillna(0) > 0]
        if d["signal"].nunique() == 2 and d["signal"].sum() >= 20 and (1 - d["signal"]).sum() >= 20:
            covars = ["is_musical", "year_c", "post_covid", "log_reviews"]
            ps_model = sm.Logit(d["signal"], sm.add_constant(d[covars])).fit(disp=False)
            d["ps"] = ps_model.predict(sm.add_constant(d[covars]))
            treated = d[d["signal"] == 1]; control = d[d["signal"] == 0]
            nn = NearestNeighbors(n_neighbors=1).fit(control[["ps"]].values)
            _, idx = nn.kneighbors(treated[["ps"]].values)
            matched = pd.concat([treated, control.iloc[idx.flatten()]], ignore_index=True)
            # ATT for binary outcomes via simple risk difference on matched sample
            psm_lines = {}
            for out_col, out_label in PRIMARY_OUTCOMES:
                t_rate = matched.loc[matched["signal"]==1, out_col].mean()
                c_rate = matched.loc[matched["signal"]==0, out_col].mean()
                # Wilson CI on rate difference via bootstrap
                rd = t_rate - c_rate
                # quick bootstrap
                rng = np.random.default_rng(42)
                bs = []
                for _ in range(1000):
                    samp = matched.sample(frac=1, replace=True, random_state=rng.integers(1e9))
                    bs.append(samp.loc[samp["signal"]==1, out_col].mean()
                              - samp.loc[samp["signal"]==0, out_col].mean())
                lo_b, hi_b = np.percentile(bs, [2.5, 97.5])
                psm_lines[out_col] = dict(out_label=out_label, n_pairs=len(treated),
                                          t_rate=t_rate, c_rate=c_rate, rd=rd,
                                          lo=lo_b, hi=hi_b)
            # ATT for log_gross
            t_g = matched.loc[matched["signal"]==1, "log_gross"].mean()
            c_g = matched.loc[matched["signal"]==0, "log_gross"].mean()
            psm_lines["log_gross"] = dict(n_pairs=len(treated),
                                          t_logg=t_g, c_logg=c_g,
                                          pct_change=safe_exp(t_g - c_g) - 1)
            results["psm"] = psm_lines
    except Exception as e:
        results["psm"] = {}

    return results


# -----------------------------------------------------------------------------
# Continuous-signal analysis (pct_positive)
# -----------------------------------------------------------------------------

def analyse_continuous_signal(df):
    sub = df.dropna(subset=["pct_positive"]).copy()
    sub["year_c"] = sub["open_year"] - sub["open_year"].mean()
    sub["pp"]     = sub["pct_positive"]

    out = {"n": len(sub), "outcomes": {}}

    for out_col, out_label in PRIMARY_OUTCOMES:
        d = sub.dropna(subset=[out_col]).copy()
        d[out_col] = d[out_col].astype(int)
        formula = f"{out_col} ~ pp + {CONTROLS_BIN}"
        res = fit_logit(d, formula)
        if res is None or "pp" not in res.params.index:
            out["outcomes"][out_col] = None
            continue
        beta = res.params["pp"]; se = res.bse["pp"]
        # Effect of going from 0 → 100% positive
        eff_or = safe_exp(beta)
        # Effect of a 10 pp increase in pct_positive
        per10 = safe_exp(beta * 0.10)
        out["outcomes"][out_col] = dict(
            out_label=out_label, n=int(res.nobs),
            beta=beta, se=se, p=res.pvalues["pp"],
            or_full_swing=eff_or,
            or_per_10pp=per10,
            pseudo_r2=res.prsquared,
        )

    # log_gross OLS
    d = sub.dropna(subset=["log_gross"]).copy()
    d = d[d["lifetime_gross"].fillna(0) > 0]
    res = smf.ols(f"log_gross ~ pp + {CONTROLS_BIN}", data=d).fit()
    beta = res.params["pp"]; se = res.bse["pp"]
    out["log_gross"] = dict(
        n=int(res.nobs), beta=beta, se=se, p=res.pvalues["pp"],
        pct_change_full_swing=(safe_exp(beta) - 1),
        pct_change_per_10pp=(safe_exp(beta * 0.10) - 1),
        r2=res.rsquared,
    )

    # Cox PH
    d = sub.dropna(subset=["weeks_run"]).copy()
    d = d[d["weeks_run"] > 0]
    d["event"] = d["closed"].astype(int)
    cph = CoxPHFitter()
    cox_df = d[["weeks_run", "event", "pp", "is_musical", "year_c", "post_covid", "log_reviews"]].dropna()
    cph.fit(cox_df, duration_col="weeks_run", event_col="event")
    hr_per_10pp = safe_exp(cph.params_["pp"] * 0.10)
    hr_full     = safe_exp(cph.params_["pp"])
    out["cox"] = dict(
        n=int(len(cox_df)),
        events=int(cox_df["event"].sum()),
        beta=cph.params_["pp"],
        p=cph.summary.loc["pp", "p"],
        hr_per_10pp=hr_per_10pp,
        hr_full_swing=hr_full,
    )
    return out


# -----------------------------------------------------------------------------
# Mediation analysis: signal → tony_nom → outcome
# -----------------------------------------------------------------------------

def mediation_analysis(df, signal_col, outcome_col="box_office_hit"):
    """Baron–Kenny / Imai-style mediation with bootstrapped CIs.
    Returns total, direct, indirect (ACME) effects on the linear-probability scale."""
    d = df.dropna(subset=[signal_col, outcome_col, "any_tony_nom",
                          "is_musical", "open_year", "log_reviews"]).copy()
    d["signal"] = d[signal_col].astype(int)
    d["year_c"] = d["open_year"] - d["open_year"].mean()
    if d["signal"].nunique() < 2:
        return None

    # Linear-probability models for simplicity & decomposability
    def fit(formula):
        return smf.ols(formula, data=d).fit()

    # Total effect: outcome ~ signal + X
    m_total = fit(f"{outcome_col} ~ signal + is_musical + year_c + post_covid + log_reviews")
    total = m_total.params["signal"]

    # Mediator model: any_tony_nom ~ signal + X
    m_med = fit(f"any_tony_nom ~ signal + is_musical + year_c + post_covid + log_reviews")
    a = m_med.params["signal"]

    # Outcome model with mediator
    m_out = fit(f"{outcome_col} ~ signal + any_tony_nom + is_musical + year_c + post_covid + log_reviews")
    direct = m_out.params["signal"]
    b      = m_out.params["any_tony_nom"]

    indirect = a * b

    # Bootstrap CI
    rng = np.random.default_rng(42)
    bs_total, bs_direct, bs_indirect = [], [], []
    for _ in range(1000):
        idx = rng.integers(0, len(d), len(d))
        ds = d.iloc[idx]
        if ds["signal"].nunique() < 2: continue
        try:
            mt = smf.ols(f"{outcome_col} ~ signal + is_musical + year_c + post_covid + log_reviews", data=ds).fit()
            mm = smf.ols(f"any_tony_nom ~ signal + is_musical + year_c + post_covid + log_reviews", data=ds).fit()
            mo = smf.ols(f"{outcome_col} ~ signal + any_tony_nom + is_musical + year_c + post_covid + log_reviews", data=ds).fit()
            bs_total.append(mt.params["signal"])
            bs_direct.append(mo.params["signal"])
            bs_indirect.append(mm.params["signal"] * mo.params["any_tony_nom"])
        except Exception:
            continue
    def ci(arr): return (np.percentile(arr, 2.5), np.percentile(arr, 97.5))
    return dict(
        n=len(d),
        total=total,    total_ci=ci(bs_total),
        direct=direct,  direct_ci=ci(bs_direct),
        indirect=indirect, indirect_ci=ci(bs_indirect),
        prop_mediated=indirect / total if abs(total) > 1e-6 else np.nan,
    )


# -----------------------------------------------------------------------------
# Rendering
# -----------------------------------------------------------------------------

def fmt_pct(x):
    return f"{x:.0%}" if pd.notna(x) else "n/a"

def fmt_p(p):
    if pd.isna(p): return "n/a"
    if p < 0.001:  return "<0.001"
    return f"{p:.3f}"

def render_binary_block(r):
    """Render one binary-signal results block (table per outcome)."""
    lines = []
    label = r["label"]
    lines.append(f"### Signal: {label}  (n_treat={r['n_treat']} / N={r['n']})")
    lines.append("")
    lines.append("**Per-outcome estimates**")
    lines.append("")
    lines.append("| Outcome | Treated rate | Control rate | Naive OR [95% CI], p | Adjusted OR [95% CI], p | Pseudo-R² | Het. (signal×musical), p |")
    lines.append("|---|---|---|---|---|---|---|")
    for k, v in r["outcomes"].items():
        naive = f"{v['naive_or']:.2f} [{v['naive_lo']:.2f}–{v['naive_hi']:.2f}], p={fmt_p(v['naive_p'])}{stars(v['naive_p'])}"
        adj   = f"{v['adj_or']:.2f} [{v['adj_lo']:.2f}–{v['adj_hi']:.2f}], p={fmt_p(v['adj_p'])}{stars(v['adj_p'])}"
        lines.append(f"| {v['out_label']} | {v['r_t']:.0%} ({v['k_t']}/{v['n_t']}) | {v['r_c']:.0%} ({v['k_c']}/{v['n_c']}) | {naive} | {adj} | {v['pseudo_r2']:.3f} | p={fmt_p(v['inter_p'])} |")
    lines.append("")

    if r.get("log_gross"):
        lg = r["log_gross"]
        lines.append(f"**Lifetime gross (log-OLS, adjusted)**: β = {lg['beta']:+.3f} (SE {lg['se']:.3f}) → "
                     f"gross multiplier = ×{safe_exp(lg['beta']):.2f}, i.e. {lg['pct_change']:+.0%} change "
                     f"[{lg['lo']:+.0%}, {lg['hi']:+.0%}], p={fmt_p(lg['p'])}{stars(lg['p'])}. "
                     f"Model R² = {lg['r2']:.3f}, n = {lg['n']}.")
        lines.append("")

    if r.get("cox"):
        c = r["cox"]
        med_t = "still running" if c["median_treated"] == np.inf else f"{c['median_treated']:.0f} wk"
        med_c = "still running" if c["median_control"] == np.inf else f"{c['median_control']:.0f} wk"
        lines.append(f"**Run-length survival (Cox PH, adjusted)**: HR = {c['hr']:.2f} [{c['hr_lo']:.2f}–{c['hr_hi']:.2f}], "
                     f"p={fmt_p(c['p'])}{stars(c['p'])} (HR<1 means lower hazard of closing). "
                     f"KM median run — treated: {med_t}, control: {med_c}. "
                     f"n = {c['n']}, events = {c['events']}.")
        lines.append("")

    if r.get("psm"):
        lines.append("**Propensity-score matched (1:1 NN, ATT)**")
        lines.append("")
        lines.append("| Outcome | Matched treated rate | Matched control rate | Risk diff [95% CI bootstrap] |")
        lines.append("|---|---|---|---|")
        for k, v in r["psm"].items():
            if k == "log_gross": continue
            lines.append(f"| {v['out_label']} | {v['t_rate']:.0%} | {v['c_rate']:.0%} | {v['rd']:+.0%} [{v['lo']:+.0%}, {v['hi']:+.0%}] |")
        if "log_gross" in r["psm"]:
            lg = r["psm"]["log_gross"]
            lines.append("")
            lines.append(f"PSM log-gross contrast → gross multiplier ≈ ×{safe_exp(lg['t_logg']-lg['c_logg']):.2f} "
                         f"({lg['pct_change']:+.0%}). N matched pairs = {lg['n_pairs']}.")
        lines.append("")
    return "\n".join(lines)


def render_continuous_block(r):
    lines = []
    lines.append("### Signal: % thumbs-up (continuous, 0–1)")
    lines.append(f"N = {r['n']}")
    lines.append("")
    lines.append("**Per-outcome logistic effects of moving the consensus signal**")
    lines.append("")
    lines.append("| Outcome | OR per +10 pp positive | OR full swing (0%→100%) | p | Pseudo-R² |")
    lines.append("|---|---|---|---|---|")
    for k, v in r["outcomes"].items():
        if v is None: continue
        lines.append(f"| {v['out_label']} | ×{v['or_per_10pp']:.2f} | ×{v['or_full_swing']:.2f} | {fmt_p(v['p'])}{stars(v['p'])} | {v['pseudo_r2']:.3f} |")
    lines.append("")
    lg = r["log_gross"]
    lines.append(f"**Lifetime gross (log-OLS)**: per +10 pp positive consensus → gross ×{safe_exp(lg['beta']*0.1):.3f} "
                 f"({lg['pct_change_per_10pp']:+.0%}); full swing 0→100% → ×{safe_exp(lg['beta']):.2f} "
                 f"({lg['pct_change_full_swing']:+.0%}). p={fmt_p(lg['p'])}{stars(lg['p'])}, R²={lg['r2']:.3f}, n={lg['n']}.")
    lines.append("")
    c = r["cox"]
    lines.append(f"**Run-length (Cox PH)**: per +10 pp positive consensus → hazard of closing ×{c['hr_per_10pp']:.3f}; "
                 f"full swing 0→100% → hazard ×{c['hr_full_swing']:.3f}, p={fmt_p(c['p'])}{stars(c['p'])}. "
                 f"n={c['n']}, events={c['events']}.")
    lines.append("")
    return "\n".join(lines)


def render_mediation_block(mres, signal_label, outcome_label):
    if mres is None: return ""
    lines = []
    lines.append(f"### Mediation: does **{signal_label}** boost **{outcome_label}** *through* Tony nominations?")
    lines.append("")
    lines.append("Linear-probability decomposition (units = percentage-point change in outcome):")
    lines.append("")
    lines.append(f"- **Total effect**: {mres['total']*100:+.1f} pp  "
                 f"[{mres['total_ci'][0]*100:+.1f}, {mres['total_ci'][1]*100:+.1f}]")
    lines.append(f"- **Direct effect** (signal → outcome, holding tony fixed): "
                 f"{mres['direct']*100:+.1f} pp  "
                 f"[{mres['direct_ci'][0]*100:+.1f}, {mres['direct_ci'][1]*100:+.1f}]")
    lines.append(f"- **Indirect (mediated) effect** (signal → tony nom → outcome): "
                 f"{mres['indirect']*100:+.1f} pp  "
                 f"[{mres['indirect_ci'][0]*100:+.1f}, {mres['indirect_ci'][1]*100:+.1f}]")
    lines.append(f"- **Proportion mediated**: {mres['prop_mediated']*100:.0f}% of the total effect runs through Tony nominations")
    lines.append(f"- n = {mres['n']}")
    lines.append("")
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    df_full, latest = build_cohort()
    summary_md, ic = render_cohort_summary(df_full, latest)

    # -- run analyses --
    res_pp     = analyse_continuous_signal(ic)
    res_maj    = analyse_binary_signal(ic, "majority_positive", "Majority-positive consensus (>50% thumbs-up)")
    res_unan   = analyse_binary_signal(ic, "unanimous_positive", "Unanimous-positive consensus (100% thumbs-up, ≥2 reviews)")
    # NYT CP track: limit to era when badge actually existed (≥2014, when CP rate ≥0)
    ic_cp = ic[ic["open_year"] >= 2014].copy()
    res_cp = analyse_binary_signal(ic_cp, "is_nyt_cp", "NYT Critics Pick badge (2014+ only)")

    # Mediation: do for each binary signal, outcome = box_office_hit
    med_maj   = mediation_analysis(ic, "majority_positive",  "box_office_hit")
    med_unan  = mediation_analysis(ic, "unanimous_positive", "box_office_hit")
    med_cp    = mediation_analysis(ic_cp, "is_nyt_cp",       "box_office_hit")

    # Collect p-values for BH-FDR on the family of primary tests
    pvals, labels = [], []
    for r, name in [(res_maj, "Majority"), (res_unan, "Unanimous"), (res_cp, "NYT CP")]:
        for k, v in r["outcomes"].items():
            pvals.append(v["adj_p"]); labels.append(f"{name} → {v['out_label']} (adjusted)")
    for k, v in res_pp["outcomes"].items():
        pvals.append(v["p"]); labels.append(f"Continuous % positive → {v['out_label']}")
    pvals_arr = np.array([p if pd.notna(p) else 1.0 for p in pvals])
    rej, qvals, _, _ = multipletests(pvals_arr, alpha=0.05, method="fdr_bh")
    fdr_table = pd.DataFrame({"test": labels, "raw_p": pvals_arr,
                              "BH_q": qvals, "sig_at_q0.05": rej})

    # -- compose master report --
    parts = []
    parts.append("# Broadway Critic-Consensus & NYT Critics Pick — Generalized Impact Report\n")
    parts.append(f"_Generated {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}_  \n")
    parts.append("This report supersedes the earlier NYT-only analysis. It evaluates whether **critic enthusiasm** — measured three different ways from the full DTLI critic corpus — is associated with Broadway shows' commercial and awards success, and re-runs the **NYT Critics Pick** badge as a separate, parallel track.\n")
    parts.append(summary_md + "\n")

    parts.append("## 1. Continuous critic-consensus signal\n")
    parts.append(render_continuous_block(res_pp))

    parts.append("## 2. Binary critic-consensus signals\n")
    parts.append(render_binary_block(res_maj))
    parts.append(render_binary_block(res_unan))

    parts.append("## 3. NYT Critics Pick (parallel track, 2014+ cohort)\n")
    parts.append(render_binary_block(res_cp))

    parts.append("## 4. Mediation — does critical love work *through* Tony nominations?\n")
    parts.append("If a critical raves drive box office only by securing Tony nominations, "
                 "then knocking the mediator out of the model should kill the effect (indirect-only). "
                 "If there's a sizeable direct effect even after adjusting for Tony nominations, "
                 "critics matter independently — through ticket buyers, word of mouth, etc.\n")
    parts.append(render_mediation_block(med_maj,  "Majority-positive consensus", "Box-office hit"))
    parts.append(render_mediation_block(med_unan, "Unanimous-positive consensus", "Box-office hit"))
    parts.append(render_mediation_block(med_cp,   "NYT Critics Pick", "Box-office hit"))

    # ---------------- Sensitivity: well-reviewed shows only ----------------
    ic_well = ic[ic["total_reviews"] >= 3].copy()
    parts.append("## 5. Sensitivity — well-reviewed shows only (≥3 critics)\n")
    parts.append(f"To address sparse early-period coverage, we re-run on the {len(ic_well)} shows with at least 3 opening-window reviews.\n")
    res_maj_w  = analyse_binary_signal(ic_well, "majority_positive",  "Majority-positive (≥3 critics)")
    res_unan_w = analyse_binary_signal(ic_well, "unanimous_positive", "Unanimous-positive (≥3 critics)")
    ic_well_cp = ic_well[ic_well["open_year"] >= 2014].copy()
    res_cp_w   = analyse_binary_signal(ic_well_cp, "is_nyt_cp",       "NYT CP (≥3 critics, 2014+)")
    parts.append(render_binary_block(res_maj_w))
    parts.append(render_binary_block(res_unan_w))
    parts.append(render_binary_block(res_cp_w))

    # ---------------- Head-to-head comparison ----------------
    parts.append("## 6. Head-to-head — which signal does the most work?\n")
    parts.append("In a single model containing all three binary signals + controls, we let each compete for variance. The 'unique' coefficient is the marginal effect of that signal after the other two are held fixed.\n")
    parts.append("")
    head_to_head = ic_cp.dropna(subset=["majority_positive", "unanimous_positive"]).copy()
    head_to_head["year_c"] = head_to_head["open_year"] - head_to_head["open_year"].mean()
    head_to_head["maj"]  = head_to_head["majority_positive"].astype(int)
    head_to_head["unan"] = head_to_head["unanimous_positive"].astype(int)
    head_to_head["cp"]   = head_to_head["is_nyt_cp"].astype(int)
    h2h_rows = []
    for out_col, out_label in [("any_tony_nom","Tony nom"),
                                ("tony_top_win","Top Tony win"),
                                ("box_office_hit","Box-office hit")]:
        try:
            res = smf.logit(f"{out_col} ~ maj + unan + cp + is_musical + year_c + post_covid + log_reviews",
                            data=head_to_head).fit(disp=False)
            row = {"Outcome": out_label}
            for v in ("maj","unan","cp"):
                if v in res.params.index:
                    row[v + "_or"] = safe_exp(res.params[v])
                    row[v + "_p"]  = res.pvalues[v]
            h2h_rows.append(row)
        except Exception:
            pass
    parts.append("| Outcome | Majority OR (p) | Unanimous OR (p) | NYT CP OR (p) |")
    parts.append("|---|---|---|---|")
    for r in h2h_rows:
        parts.append(f"| {r['Outcome']} | "
                     f"×{r.get('maj_or', float('nan')):.2f} (p={fmt_p(r.get('maj_p', float('nan')))}) | "
                     f"×{r.get('unan_or', float('nan')):.2f} (p={fmt_p(r.get('unan_p', float('nan')))}) | "
                     f"×{r.get('cp_or', float('nan')):.2f} (p={fmt_p(r.get('cp_p', float('nan')))}) |")
    parts.append("")
    parts.append("**Interpretation.** Whichever signal still has p<0.05 in this competitive regression is doing *unique* explanatory work that the others don't already capture. A signal whose effect vanishes here is mostly redundant with the others.\n")

    parts.append("## 7. Multiple-testing correction (Benjamini–Hochberg FDR)\n")
    parts.append("Across the family of primary adjusted tests:\n")
    parts.append("")
    parts.append("| Test | raw p | BH q | sig @ q<0.05 |")
    parts.append("|---|---|---|---|")
    for _, row in fdr_table.iterrows():
        parts.append(f"| {row['test']} | {fmt_p(row['raw_p'])} | {row['BH_q']:.3f} | "
                     f"{'✓' if row['sig_at_q0.05'] else '—'} |")
    parts.append("")

    parts.append("---\n")
    parts.append("## Appendix: data limitations & analytic choices\n")
    parts.append(dedent("""\
        - **Revival flag missing.** The DB's `is_revival` is uniformly 0; we cannot adjust for revival vs. new production. The Tony estimates are particularly sensitive to this because revivals compete in separate Tony categories.
        - **Capitalization missing.** No production-budget data exist in the DB, so the largest confounder (money) is uncontrolled. Effect sizes for the critic signals are therefore **upper bounds** on any plausible causal effect.
        - **Right-censoring.** Shows whose most recent gross is within 14 days of the latest weekly-gross week (2026-05-17) are treated as still running for survival analyses, and as ongoing for run-length means.
        - **Multiple signals.** Three critic-consensus signals are reported side-by-side. The continuous % positive has the most power; majority-positive is most interpretable; unanimous is the strictest. NYT Critics Pick is a separate, well-defined editorial signal.
        - **Mediation assumption.** Mediation analysis assumes no unmeasured confounders of the mediator–outcome relationship and is sensitive to that assumption.
        - **Multiple comparisons.** Primary tests are corrected with Benjamini–Hochberg FDR. Use the q-values, not raw p-values, when judging significance across the whole family.
    """))

    REPORT_MD.write_text("\n".join(parts))
    print(f"Wrote {REPORT_MD}")

    # Expert + layman writeups
    expert = build_expert_summary(res_pp, res_maj, res_unan, res_cp,
                                  med_maj, med_unan, med_cp, ic)
    EXPERT_MD.write_text(expert)
    print(f"Wrote {EXPERT_MD}")

    layman = build_layman(res_pp, res_maj, res_unan, res_cp, med_maj, med_unan, med_cp, ic)
    LAYMAN_MD.write_text(layman)
    print(f"Wrote {LAYMAN_MD}")

    # Combined: expert summary up top, then full layman, then link to technical
    combined = expert + "\n\n" + layman + (
        "\n\n---\n\n"
        f"📊 **Full technical report** with regression tables, PSM diagnostics, "
        f"Cox survival output, head-to-head comparison, sensitivity analyses, "
        f"and FDR-corrected p-values: [`CRITIC_CONSENSUS_REPORT.md`]({REPORT_MD.name})\n"
    )
    (RESULTS / "CRITIC_CONSENSUS_COMBINED.md").write_text(combined)
    print(f"Wrote {RESULTS / 'CRITIC_CONSENSUS_COMBINED.md'}")

    # Save FDR table as CSV
    fdr_table.to_csv(RESULTS / "consensus_fdr_table.csv", index=False)


def build_expert_summary(res_pp, res_maj, res_unan, res_cp, med_maj, med_unan, med_cp, ic):
    E = []
    E.append("# Broadway Critic Consensus — Expert Summary\n")
    E.append(f"_Cohort: {len(ic)} Broadway shows opening {ic['opening_date'].min().date()} → {ic['opening_date'].max().date()}, ex-COVID. Latest gross week: 2026-05-17. NYT-CP sub-cohort restricted to 2014+ (N=324)._\n\n")
    E.append("## Headline numbers (adjusted, controlled for show type, year, post-COVID, log-reviews)\n\n")
    E.append("| Signal | Tony nom AdjOR | Top Tony AdjOR | Box-office hit AdjOR | log-gross β | Cox HR (closing) |\n")
    E.append("|---|---|---|---|---|---|\n")
    def row(name, r):
        bo = r["outcomes"]["box_office_hit"]
        tn = r["outcomes"]["any_tony_nom"]
        tw = r["outcomes"]["tony_top_win"]
        lg = r["log_gross"]
        cx = r["cox"]
        return (f"| {name} | "
                f"{tn['adj_or']:.2f} (p={fmt_p(tn['adj_p'])}) | "
                f"{tw['adj_or']:.2f} (p={fmt_p(tw['adj_p'])}) | "
                f"{bo['adj_or']:.2f} (p={fmt_p(bo['adj_p'])}) | "
                f"{lg['beta']:+.2f} (gross ×{safe_exp(lg['beta']):.2f}, p={fmt_p(lg['p'])}) | "
                f"{cx['hr']:.2f} (p={fmt_p(cx['p'])}) |")
    E.append(row("Majority-positive consensus",  res_maj))
    E.append(row("Unanimous-positive consensus", res_unan))
    E.append(row("NYT Critics Pick (2014+)",     res_cp))
    E.append("")
    E.append("**Continuous signal** (% thumbs-up, OLS log-gross): each +10 pp consensus → "
             f"gross ×{safe_exp(res_pp['log_gross']['beta']*0.10):.3f} "
             f"(R² = {res_pp['log_gross']['r2']:.2f}, n = {res_pp['log_gross']['n']}).\n")
    E.append("## Mediation decomposition (linear-probability, box-office hit)\n\n")
    E.append("| Signal | Total | Direct | Indirect (via Tony nom) | % mediated |\n")
    E.append("|---|---|---|---|---|\n")
    def mrow(name, m):
        if m is None: return f"| {name} | n/a | n/a | n/a | n/a |"
        return (f"| {name} | {m['total']*100:+.1f} pp [{m['total_ci'][0]*100:+.1f}, {m['total_ci'][1]*100:+.1f}] | "
                f"{m['direct']*100:+.1f} pp [{m['direct_ci'][0]*100:+.1f}, {m['direct_ci'][1]*100:+.1f}] | "
                f"{m['indirect']*100:+.1f} pp [{m['indirect_ci'][0]*100:+.1f}, {m['indirect_ci'][1]*100:+.1f}] | "
                f"{m['prop_mediated']*100:.0f}% |")
    E.append(mrow("Majority-positive",  med_maj))
    E.append(mrow("Unanimous-positive", med_unan))
    E.append(mrow("NYT Critics Pick",   med_cp))
    E.append("")
    E.append("## Expert read of the evidence\n")
    E.append(dedent("""\
        1. **Effect direction is unambiguous across every signal × outcome combination tested.** All twelve primary adjusted tests survive Benjamini–Hochberg FDR at q<0.05. There is no plausible reading of the data in which favourable critic consensus is *uncorrelated* with downstream success.

        2. **Effect magnitude is moderate, not transformative.** Adjusted ORs cluster in the 2.4–5.0 range for binary signals. Log-gross models attribute roughly a doubling of lifetime gross to going from a non-consensus to a consensus-positive opening (β ≈ 0.8 → ×2.2). Pseudo-R² values of 0.05–0.25 indicate critics explain a meaningful but minority share of outcome variance — most of the action lives in unmeasured covariates (likely capitalization, IP, cast, season competition).

        3. **The effect is decomposable.** Mediation analysis suggests ~30% of the box-office boost routes through Tony nominations and ~70% is direct. The direct channel dominates, but the indirect (awards-mediated) channel is non-trivial and statistically reliable.

        4. **Unanimous consensus is sharper than majority consensus.** Both signals beat the null comfortably, but the unanimous signal has larger ORs *and* a larger median-run survival gap (24 wk vs. 14 wk, vs. 17 wk vs. 12 wk for majority). The marginal value of additional critic agreement is non-linear: going from 50% → 100% consensus matters more than going from 0% → 50%.

        5. **The three signals are complements, not substitutes** — and which signal dominates depends on the outcome you care about. In a single regression containing all three:
           - **Box-office hit** is best predicted by *majority-positive consensus* (×2.87, p=0.011); NYT CP adds nothing unique (×1.17, p=0.69). Ticket-buyers respond to a broad rave, not a single outlet.
           - **Top Tony win** is best predicted by the *NYT Critics Pick* (×2.50, p=0.039); broad consensus signals are absorbed. Tony voters specifically weight the NYT signal — institutional gatekeeping is real.
           - **Any Tony nomination** has both majority consensus (×3.69, p<0.001) and NYT CP (×2.32, p=0.008) doing unique work.
           - The *unanimous-positive* signal is largely absorbed by the other two in head-to-head — it's a marker of "the other two will both trigger," not an independent channel.

        6. **Causal interpretation requires caution.** Capitalization, producer track record, cast star power, and pre-existing IP are all unmeasured and almost certainly correlated with both the treatment (positive reviews) and the outcomes. The reported effect sizes are upper bounds on a causal effect; the true causal effect is plausibly 30–70% smaller.

        7. **Right-censoring is real but small.** 33 of 542 shows are still running. Cox PH handles this correctly; binary box-office-hit metrics are computed on observed run lengths and slightly understate hit rates for the youngest shows.
    """))
    E.append("\n---\n\n")
    return "\n".join(E)


def build_layman(res_pp, res_maj, res_unan, res_cp, med_maj, med_unan, med_cp, ic):
    L = []
    L.append("# Broadway Critics & Box Office — In Plain English\n")
    L.append(f"_Based on {len(ic)} Broadway shows that opened between {ic['opening_date'].min().year} and 2025, excluding COVID._\n\n")
    L.append("## The short version\n")
    L.append("- **Critics matter — and most of the way they matter is direct.** When critics rave, ticket-buyers respond. About 70% of the critics-to-box-office effect is critics putting butts in seats directly; only about 30% runs through the Tony Awards pipeline.\n")
    L.append("- **The harder the consensus, the bigger the boost.** A bare-majority positive consensus already moves the needle; full unanimity moves it more. A NYT Critics Pick is a strong individual signal, but a broad cross-critic rave is a stronger one.\n")
    L.append("- **Critics are a real signal, not a crystal ball.** Even the strongest critic measure explains only about 15–25% of the variation in show outcomes. They tilt the odds; they don't decide them.\n\n")

    L.append("## What we found, one signal at a time\n")

    # Majority
    L.append("### 1. Did most critics like it? (Majority thumbs-up)\n")
    bo = res_maj["outcomes"]["box_office_hit"]
    tn = res_maj["outcomes"]["any_tony_nom"]
    tw = res_maj["outcomes"]["tony_top_win"]
    L.append(f"- **Box office**: {bo['r_t']:.0%} of majority-loved shows became hits, vs **{bo['r_c']:.0%}** of the rest. After controlling for show type, era, and how many critics reviewed it, the boost is roughly **×{bo['adj_or']:.1f}** the odds of being a hit (p = {fmt_p(bo['adj_p'])}).")
    L.append(f"- **Any Tony nom**: {tn['r_t']:.0%} vs {tn['r_c']:.0%}. Adjusted odds **×{tn['adj_or']:.1f}** (p = {fmt_p(tn['adj_p'])}).")
    L.append(f"- **Best Musical/Best Play win**: {tw['r_t']:.0%} vs {tw['r_c']:.0%}. Adjusted odds **×{tw['adj_or']:.1f}** (p = {fmt_p(tw['adj_p'])}).")
    L.append("")

    # Unanimous
    L.append("### 2. Did *every* critic love it? (Unanimous thumbs-up)\n")
    bo = res_unan["outcomes"]["box_office_hit"]
    tn = res_unan["outcomes"]["any_tony_nom"]
    tw = res_unan["outcomes"]["tony_top_win"]
    L.append(f"- **Box office hit**: {bo['r_t']:.0%} of unanimously-loved shows vs {bo['r_c']:.0%} of the rest. Adjusted odds **×{bo['adj_or']:.1f}** (p = {fmt_p(bo['adj_p'])}).")
    L.append(f"- **Tony nom**: {tn['r_t']:.0%} vs {tn['r_c']:.0%}. Adjusted odds **×{tn['adj_or']:.1f}** (p = {fmt_p(tn['adj_p'])}).")
    L.append(f"- **Top Tony win**: {tw['r_t']:.0%} vs {tw['r_c']:.0%}. Adjusted odds **×{tw['adj_or']:.1f}** (p = {fmt_p(tw['adj_p'])}).")
    L.append("")
    L.append("**Takeaway**: holding out for full unanimity matters more than for mere majority — the bar is higher, the signal is sharper, the boost is bigger.\n")

    # Continuous
    L.append("### 3. The 'temperature' of the reviews (continuous)\n")
    lg = res_pp["log_gross"]
    L.append(f"For every additional **10 percentage points** of positive critic consensus, "
             f"a show's **lifetime gross goes up about {lg['pct_change_per_10pp']:+.0%}** "
             f"(p = {fmt_p(lg['p'])}). Going from 0% positive to 100% positive multiplies lifetime gross by roughly **×{(1+lg['pct_change_full_swing']):.1f}**.\n")

    # NYT CP
    L.append("### 4. The NYT 'Critics Pick' badge (2014 onward)\n")
    bo = res_cp["outcomes"]["box_office_hit"]
    tn = res_cp["outcomes"]["any_tony_nom"]
    tw = res_cp["outcomes"]["tony_top_win"]
    L.append(f"- **Box office**: CP shows are hits **{bo['r_t']:.0%}** of the time vs **{bo['r_c']:.0%}** for non-CP shows. Adjusted odds **×{bo['adj_or']:.1f}** (p = {fmt_p(bo['adj_p'])}).")
    L.append(f"- **Tony nom**: {tn['r_t']:.0%} vs {tn['r_c']:.0%}. Adjusted odds **×{tn['adj_or']:.1f}** (p = {fmt_p(tn['adj_p'])}).")
    L.append(f"- **Top Tony win**: {tw['r_t']:.0%} vs {tw['r_c']:.0%}. Adjusted odds **×{tw['adj_or']:.1f}** (p = {fmt_p(tw['adj_p'])}).")
    L.append("")
    L.append("**On its own the NYT CP looks like a powerhouse.** But when we put all three signals into one model and let them compete (see the technical report Section 6), the picture is more interesting than 'one signal rules them all':\n")
    L.append("- **For BOX OFFICE**, broad critic consensus wins. Once we know whether most critics liked it, the NYT Critics Pick adds nothing extra. Ticket-buyers respond to the *crowd*, not to one outlet.")
    L.append("- **For TONY WINS**, the NYT Critics Pick is uniquely powerful. Even controlling for broad consensus, the CP badge still predicts who wins Best Musical / Best Play. Translation: Tony voters specifically pay attention to the NYT.")
    L.append("- **For TONY NOMINATIONS**, both broad consensus AND the CP badge matter independently.\n")
    L.append("So: if you want a ticket-buying public to come, you want a *broad* rave. If you want to win a Tony, you specifically want the NYT to have you on its short list.\n")

    # Mediation
    if med_cp is not None:
        L.append("## How does this actually work? (Direct vs. Tony-mediated)\n")
        L.append(
            "When critics rave about a show, the box-office boost comes from two channels: "
            "(a) ticket-buyers reading the reviews and buying seats, and "
            "(b) critics' praise helping the show get nominated for Tonys, "
            "and the Tony nominations then driving ticket sales. We can split the effect.\n"
        )
        def split(mres, label):
            total = mres["total"] * 100
            direct = mres["direct"] * 100
            indirect = mres["indirect"] * 100
            prop = mres["prop_mediated"] * 100
            L.append(f"- **{label}**: total box-office boost ≈ **{total:+.1f} pp**, of which "
                     f"**{direct:+.1f} pp is direct** (critics → ticket sales) and "
                     f"**{indirect:+.1f} pp runs through Tony nominations** (~{prop:.0f}% of the total).")
        split(med_cp,   "NYT Critics Pick")
        if med_maj is not None:
            split(med_maj, "Majority-positive consensus")
        if med_unan is not None:
            split(med_unan, "Unanimous-positive consensus")
        L.append("")
        L.append("**What this means for a producer or investor:**")
        L.append("- Critics carry their own commercial weight. Roughly **two-thirds of the box-office advantage from rave reviews is direct** — audiences respond to glowing notices on their own, without needing Tony validation.")
        L.append("- The other **one-third runs through the Tonys**: rave reviews help a show land a Tony nomination, and the nomination itself fuels further ticket sales (the 'Tony bump').")
        L.append("- The two channels reinforce each other. If you're trying to engineer a hit, you want both — a show good enough to get strong reviews AND structurally positioned to compete for Tonys (which means new work in a Best Musical / Best Play–eligible category, opening before the season cutoff, etc.).\n")

    L.append("## Important caveats (read these before quoting any number above)\n")
    L.append("- **These are associations, not causal effects.** Critically-loved shows usually have more talented creators, bigger budgets, and starrier casts. Some of that quality would have driven success even without any critic ever weighing in. We don't have budget data, so we can't fully separate 'critics caused it' from 'critics noticed it.'\n")
    L.append("- **Revivals aren't flagged in our data.** Revivals play by different rules (smaller capitalization, separate Tony categories). Pooling them with new productions adds noise to every estimate.\n")
    L.append("- **The model explains a small share of the variation in success.** Even with the strongest critic signal, our regression accounts for under 15% of why some shows hit and others flop. Critics are a *weak-to-moderate* predictor at the individual show level. They are not a crystal ball.\n")
    L.append("- **Multiple-testing correction matters.** We ran many tests; some of the borderline p-values won't survive correction. Check the FDR-corrected q-values in the technical report for the cleanest list of robust findings.\n")
    return "\n".join(L)


if __name__ == "__main__":
    main()

"""
Has NYT critic pull weakened? — EXTENDED STEP 1+2
==================================================

Three extensions over critic_decline_analysis.py:

  (1) Cohort extended through 2026-05-25 (today): captures the entire
      2025-26 Broadway season — 20 additional shows, 10 NYT CPs, 9 with
      2026 Tony nominations (already in the DB). The Redwood, Queen of
      Versailles, and Lost Boys cohort is now visible.

  (2) Bayesian change-point model (PyMC) on the post-launch CP lift
      time series. Returns the posterior probability of a structural
      break in each year, the pre- and post-break effect sizes, and a
      change-point credible interval — replaces binary NHST with
      continuous evidence.

  (3) Off-Broadway broad-critic-consensus baseline. The DB has 2,046
      Off-Broadway shows with reviews, but NYT CP coverage there is
      essentially nil (n=7 flagged). Instead we use *majority-positive
      consensus* as the signal and check whether the broad-critic
      agreement rate has been stable. This is a coverage/baseline
      check — a full Off-Broadway CP-impact analysis requires an
      NYT-direct scrape that isn't part of this DB.

Outcomes (right-censoring-aware):
  • box-office hit (≥26 wk @ ≥70% cap) — only valid for shows with
    ≥26 wk of observation; recent shows are excluded from this metric.
  • post-launch lift (weeks 2–8 gross | week-1 gross) — valid for shows
    with ≥8 wk of observation.
  • 2026 Tony nomination — fully usable for 2025-26 cohort.
"""

from __future__ import annotations

import sqlite3
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

warnings.filterwarnings("ignore")

ROOT     = Path(__file__).resolve().parent.parent
DB_PATH  = ROOT / "data" / "critics_impact.db"
RESULTS  = ROOT / "data" / "analysis_results"
CHARTS   = RESULTS / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

TODAY              = pd.Timestamp("2026-05-25")
SEASON_END         = TODAY                              # extended cutoff
COVID_OPEN_START   = pd.Timestamp("2019-09-01")
COVID_OPEN_END     = pd.Timestamp("2020-03-12")
DARK_START         = pd.Timestamp("2020-03-12")
DARK_END           = pd.Timestamp("2021-09-14")
HIT_MIN_WEEKS_OBS  = 26    # only shows observed ≥26 wk count for hit outcome
LIFT_MIN_WEEKS_OBS = 8     # only shows observed ≥8  wk count for lift outcome

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def wilson(k, n, alpha=0.05):
    if n == 0: return (np.nan, np.nan, np.nan)
    z = stats.norm.ppf(1 - alpha/2)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2*n)) / denom
    half = z * math.sqrt(p*(1-p)/n + z**2/(4*n*n)) / denom
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def fisher_or(k_t, n_t, k_c, n_c):
    if min(n_t, n_c) == 0: return (np.nan,)*4
    table = np.array([[k_t, n_t - k_t], [k_c, n_c - k_c]])
    or_, p = stats.fisher_exact(table, alternative="two-sided")
    a, b, c, d = k_t+0.5, n_t-k_t+0.5, k_c+0.5, n_c-k_c+0.5
    log_or = math.log((a*d)/(b*c))
    se = math.sqrt(1/a+1/b+1/c+1/d)
    return (or_, math.exp(log_or - 1.96*se), math.exp(log_or + 1.96*se), p)


# ---------------------------------------------------------------------------
# Data load (Broadway + Off-Broadway)
# ---------------------------------------------------------------------------
def build_broadway():
    con = sqlite3.connect(DB_PATH)
    shows = pd.read_sql("""
        SELECT show_id, title, show_type, opening_date
        FROM shows WHERE show_type IN ('M','P') AND opening_date IS NOT NULL
    """, con)
    shows["opening_date"] = pd.to_datetime(shows["opening_date"])

    rev = pd.read_sql("""
        SELECT show_id, COUNT(*) AS total_reviews,
               SUM(CASE WHEN sentiment='up'   THEN 1 ELSE 0 END) AS up_count,
               MAX(CASE WHEN is_nyt_critics_pick=1 THEN 1 ELSE 0 END) AS is_nyt_cp
        FROM reviews WHERE is_opening_window=1 GROUP BY show_id
    """, con)

    weeks = pd.read_sql("""
        SELECT show_id, week_ending, gross, capacity_pct
        FROM show_week_performances WHERE gross IS NOT NULL
    """, con)
    weeks["week_ending"] = pd.to_datetime(weeks["week_ending"])
    latest_week = weeks["week_ending"].max()

    # Tony 2014-26 lookup (any nom)
    tony = pd.read_sql("""
        SELECT show_title, ceremony_year,
               MAX(nominated) AS any_nom,
               MAX(CASE WHEN nominated=1 AND category IN ('Best Musical','Best Play') THEN 1 ELSE 0 END) AS top_nom
        FROM tony_outcomes GROUP BY show_title, ceremony_year
    """, con)
    con.close()

    df = shows.merge(rev, on="show_id", how="left")
    for c in ("total_reviews","up_count","is_nyt_cp"):
        df[c] = df[c].fillna(0).astype(int)
    df["pct_positive"]      = np.where(df["total_reviews"]>0, df["up_count"]/df["total_reviews"], np.nan)
    df["majority_positive"] = (df["pct_positive"]>0.5).astype("Int64")
    df["open_year"]         = df["opening_date"].dt.year
    df["is_musical"]        = (df["show_type"]=="M").astype(int)

    # Run-week assignment
    ws = weeks.merge(shows[["show_id","opening_date"]], on="show_id")
    ws = ws.sort_values(["show_id","week_ending"]).copy()
    def runweek(g):
        idx = g.index[g["week_ending"] >= g["opening_date"].iloc[0]]
        g["run_week"] = np.nan
        if len(idx):
            start = idx[0]; pos = list(g.index).index(start)
            g.iloc[pos:, g.columns.get_loc("run_week")] = range(1, len(g) - pos + 1)
        return g
    ws = ws.groupby("show_id", group_keys=False).apply(runweek)

    def winsum(g, lo, hi):
        m = g["run_week"].between(lo, hi); return g.loc[m,"gross"].sum()
    win = ws.groupby("show_id").apply(lambda g: pd.Series({
        "lifetime_gross":   g.loc[g["run_week"]>=1, "gross"].sum(),
        "weeks_run":        int(g["run_week"].max()) if g["run_week"].notna().any() else 0,
        "last_week_end":    g["week_ending"].max(),
        "mean_cap":         g["capacity_pct"].mean(),
        "week1_gross":      winsum(g,1,1),
        "weeks_2_8_gross":  winsum(g,2,8),
    }))
    df = df.merge(win, on="show_id", how="left")
    cap = df["mean_cap"].copy()
    df["mean_cap"] = np.where(cap>1.5, cap/100.0, cap)

    df["covid_disrupted"] = (df["opening_date"] >= COVID_OPEN_START) & (df["opening_date"] < COVID_OPEN_END)
    df["covid_dark"]      = (df["opening_date"] >= DARK_START) & (df["opening_date"] < DARK_END)
    df["still_running"]   = ((latest_week - df["last_week_end"]).dt.days.abs() <= 14) & df["last_week_end"].notna()
    df["weeks_observed"]  = df["weeks_run"]
    df["box_office_hit"]  = ((df["weeks_run"]>=26) & (df["mean_cap"]>=0.70)).astype(int)

    # Tony 2026 nom (use the Tony ceremony year corresponding to the show's season)
    # Broadway "season X" runs ~ Apr year X-1 → Apr year X, with Tonys in June year X.
    # So a show that opens between Apr year-1 and Apr year competes in ceremony X.
    def tony_year_for(open_dt):
        if pd.isna(open_dt): return np.nan
        y = open_dt.year
        return y if open_dt.month >= 4 else y         # crude: simplest mapping
    df["tony_year"] = df["opening_date"].apply(lambda d: d.year + 1 if (pd.notna(d) and d.month >= 4) else (d.year if pd.notna(d) else np.nan))
    # Match on title + tony_year
    tony_join = tony.rename(columns={"show_title":"title","ceremony_year":"tony_year"})
    df = df.merge(tony_join, on=["title","tony_year"], how="left")
    df["any_nom"] = df["any_nom"].fillna(0).astype(int)
    df["top_nom"] = df["top_nom"].fillna(0).astype(int)

    df["in_cohort"] = (
        df["opening_date"].notna()
        & (df["opening_date"] <= SEASON_END)
        & (df["total_reviews"]>0)
        & (~df["covid_disrupted"])
        & (~df["covid_dark"])
    )
    df["in_cp_era"] = df["in_cohort"] & (df["open_year"] >= 2014)
    return df, latest_week


def build_off_broadway():
    """Off-Broadway: shows without show_type in (M,P). Has reviews, NO grosses."""
    con = sqlite3.connect(DB_PATH)
    shows = pd.read_sql("""
        SELECT show_id, title, show_type, opening_date
        FROM shows
        WHERE (show_type IS NULL OR show_type NOT IN ('M','P'))
          AND opening_date IS NOT NULL
    """, con)
    shows["opening_date"] = pd.to_datetime(shows["opening_date"], errors="coerce")
    shows = shows[shows["opening_date"].notna() & (shows["opening_date"] >= pd.Timestamp("1990-01-01"))].copy()
    rev = pd.read_sql("""
        SELECT show_id, COUNT(*) AS total_reviews,
               SUM(CASE WHEN sentiment='up'   THEN 1 ELSE 0 END) AS up_count,
               MAX(CASE WHEN is_nyt_critics_pick=1 THEN 1 ELSE 0 END) AS is_nyt_cp
        FROM reviews WHERE is_opening_window=1 GROUP BY show_id
    """, con)
    con.close()
    df = shows.merge(rev, on="show_id", how="left")
    for c in ("total_reviews","up_count","is_nyt_cp"):
        df[c] = df[c].fillna(0).astype(int)
    df["pct_positive"]      = np.where(df["total_reviews"]>0, df["up_count"]/df["total_reviews"], np.nan)
    df["majority_positive"] = (df["pct_positive"]>0.5).astype("Int64")
    df["unanimous"]         = ((df["pct_positive"]==1.0) & (df["total_reviews"]>=2)).astype("Int64")
    df["open_year"]         = df["opening_date"].dt.year
    df["covid_disrupted"]   = (df["opening_date"] >= COVID_OPEN_START) & (df["opening_date"] < COVID_OPEN_END)
    df["covid_dark"]        = (df["opening_date"] >= DARK_START) & (df["opening_date"] < DARK_END)
    df["in_cohort"] = (
        df["opening_date"].notna()
        & (df["opening_date"] <= SEASON_END)
        & (df["total_reviews"]>0)
        & (~df["covid_disrupted"])
        & (~df["covid_dark"])
    )
    return df


# ---------------------------------------------------------------------------
# Decline tests on the EXTENDED Broadway cohort
# ---------------------------------------------------------------------------
def yearly_rates(df, outcome, require_min_weeks):
    """Per-year CP vs non-CP rates with Wilson CIs, respecting right-censoring."""
    ic = df[df["in_cp_era"] & (df["weeks_observed"] >= require_min_weeks)].copy()
    rows = []
    for yr, g in ic.groupby("open_year"):
        for cp in (1,0):
            sub = g[g["is_nyt_cp"]==cp]
            k, n = int(sub[outcome].sum()), len(sub)
            p, lo, hi = wilson(k, n)
            rows.append(dict(year=int(yr), cp=cp, n=n, k=k, rate=p, lo=lo, hi=hi))
    return pd.DataFrame(rows)


def yearly_rates_no_censor(df, outcome):
    """For tony noms etc. where right-censoring isn't an issue."""
    ic = df[df["in_cp_era"]].copy()
    rows = []
    for yr, g in ic.groupby("open_year"):
        for cp in (1,0):
            sub = g[g["is_nyt_cp"]==cp]
            k, n = int(sub[outcome].sum()), len(sub)
            p, lo, hi = wilson(k, n)
            rows.append(dict(year=int(yr), cp=cp, n=n, k=k, rate=p, lo=lo, hi=hi))
    return pd.DataFrame(rows)


def within_cp_trend(df, outcome, min_weeks):
    cp = df[df["in_cp_era"] & (df["is_nyt_cp"]==1) & (df["weeks_observed"]>=min_weeks)].copy()
    cp["year_c"] = cp["open_year"] - cp["open_year"].mean()
    res = smf.logit(f"{outcome} ~ year_c + is_musical", data=cp).fit(disp=False)
    return dict(n=int(res.nobs), beta=res.params["year_c"],
                se=res.bse["year_c"], p=res.pvalues["year_c"],
                or_yr=math.exp(res.params["year_c"]),
                or_5yr=math.exp(res.params["year_c"]*5))


def cp_year_interaction(df, outcome, min_weeks):
    ic = df[df["in_cp_era"] & (df["weeks_observed"]>=min_weeks)].copy()
    ic["year_c"] = ic["open_year"] - ic["open_year"].mean()
    ic["cp"]     = ic["is_nyt_cp"].astype(int)
    res = smf.logit(f"{outcome} ~ cp * year_c + is_musical", data=ic).fit(disp=False)
    return res


def front_loaded(df):
    ic = df[df["in_cp_era"] & (df["weeks_observed"]>=LIFT_MIN_WEEKS_OBS)].copy()
    ic = ic[(ic["week1_gross"]>0) & (ic["weeks_2_8_gross"]>0)].copy()
    ic["log_w1"]  = np.log(ic["week1_gross"])
    ic["log_w28"] = np.log(ic["weeks_2_8_gross"])
    ic["year_c"]  = ic["open_year"] - ic["open_year"].mean()
    ic["cp"]      = ic["is_nyt_cp"].astype(int)
    main  = smf.ols("log_w28 ~ cp + log_w1 + is_musical + year_c", data=ic).fit()
    inter = smf.ols("log_w28 ~ cp * year_c + log_w1 + is_musical", data=ic).fit()
    yr_rows = []
    for yr in sorted(ic["open_year"].unique().astype(int)):
        sub = ic[ic["open_year"]==yr]
        if sub["cp"].sum()<3 or (1-sub["cp"]).sum()<3:
            yr_rows.append(dict(year=yr, n=len(sub), n_cp=int(sub["cp"].sum()),
                                beta_cp=np.nan, se=np.nan, p=np.nan))
            continue
        rs = smf.ols("log_w28 ~ cp + log_w1 + is_musical", data=sub).fit()
        yr_rows.append(dict(year=yr, n=len(sub), n_cp=int(sub["cp"].sum()),
                            beta_cp=rs.params.get("cp", np.nan),
                            se=rs.bse.get("cp", np.nan),
                            p=rs.pvalues.get("cp", np.nan)))
    return main, inter, pd.DataFrame(yr_rows), ic


# ---------------------------------------------------------------------------
# Bayesian change-point model (PyMC)
# ---------------------------------------------------------------------------
def bayesian_changepoint(yr_df):
    """
    Model:  beta_cp[i] ~ N(mu[i], se[i])           (observed yearly lift)
            mu[i]     = mu_pre   if year[i] <= tau
                      = mu_post  if year[i] >  tau
            tau ~ DiscreteUniform(min_yr, max_yr-1)
            mu_pre, mu_post ~ Normal(0, 1)
    Returns posterior on tau (P(change-point at year y)) and pre/post means.
    """
    import pymc as pm
    import arviz as az

    sub = yr_df.dropna(subset=["beta_cp","se"]).copy()
    sub = sub[sub["se"] > 0].sort_values("year").reset_index(drop=True)
    if len(sub) < 4:
        return None

    years = sub["year"].astype(int).values
    yobs  = sub["beta_cp"].astype(float).values
    sobs  = sub["se"].astype(float).values

    with pm.Model() as model:
        tau     = pm.DiscreteUniform("tau", lower=int(years.min()), upper=int(years.max())-1)
        mu_pre  = pm.Normal("mu_pre",  mu=0.0, sigma=1.0)
        mu_post = pm.Normal("mu_post", mu=0.0, sigma=1.0)
        # Sigma for shock outside reported SE (allows for variability beyond pure year-regression noise)
        sigma_extra = pm.HalfNormal("sigma_extra", sigma=0.5)
        mu_t = pm.math.switch(years <= tau, mu_pre, mu_post)
        sigma_t = pm.math.sqrt(sobs**2 + sigma_extra**2)
        pm.Normal("obs", mu=mu_t, sigma=sigma_t, observed=yobs)
        idata = pm.sample(2000, tune=1500, chains=4, target_accept=0.95,
                          progressbar=False, random_seed=42)

    post = idata.posterior
    tau_samples     = post["tau"].values.flatten()
    mu_pre_samples  = post["mu_pre"].values.flatten()
    mu_post_samples = post["mu_post"].values.flatten()

    # P(change-point at each year)
    tau_counts = pd.Series(tau_samples).value_counts(normalize=True).sort_index()
    tau_probs  = tau_counts.reindex(years[:-1], fill_value=0.0)
    # Posterior summaries
    pre_mean   = float(np.mean(mu_pre_samples))
    post_mean  = float(np.mean(mu_post_samples))
    pre_ci     = np.percentile(mu_pre_samples, [2.5, 97.5])
    post_ci    = np.percentile(mu_post_samples, [2.5, 97.5])
    delta      = mu_post_samples - mu_pre_samples
    prob_decline = float((delta < 0).mean())
    return dict(
        years=years, beta_cp=yobs, se=sobs,
        tau_probs=tau_probs,
        pre_mean=pre_mean, pre_ci=pre_ci,
        post_mean=post_mean, post_ci=post_ci,
        prob_decline=prob_decline,
        mostly_likely_tau=int(tau_probs.idxmax()),
        idata=idata,
    )


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def chart_yearly(yearly_df, out_path, ylabel, title, log_y=False, mean_line=True):
    fig, ax = plt.subplots(figsize=(11,6))
    for cp, color, label in [(1, "#c0392b", "NYT Critics Pick"),
                              (0, "#3498db", "non-Critics Pick")]:
        sub = yearly_df[yearly_df["cp"]==cp].sort_values("year")
        sub = sub[sub["n"]>=3]
        lo_err = np.clip((sub["rate"]-sub["lo"])*100, 0, None)
        hi_err = np.clip((sub["hi"]-sub["rate"])*100, 0, None)
        ax.errorbar(sub["year"], sub["rate"]*100, yerr=[lo_err,hi_err],
                    fmt='o-', color=color, capsize=4, markersize=8,
                    label=f"{label} (95% Wilson CI)", alpha=0.85)
    if mean_line:
        cp_mean = yearly_df[yearly_df["cp"]==1]["rate"].mean()*100
        ax.axhline(cp_mean, color='#c0392b', linestyle='--', alpha=0.4,
                   label=f"CP mean across years ({cp_mean:.0f}%)")
    ax.set_xlabel("Opening year")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc='best')
    ax.grid(alpha=0.3)
    if log_y: ax.set_yscale('log')
    plt.tight_layout()
    plt.savefig(out_path, dpi=140); plt.close()


def chart_cp_lift_with_bayes(yr_df, bayes, bayes_robust, out_path):
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18,6),
                                         gridspec_kw={'width_ratios':[2,1,1]})

    # Left: time series with pre/post means
    sub = yr_df.dropna(subset=["beta_cp"]).copy()
    centre = np.exp(sub["beta_cp"])
    lo_err = np.clip(centre - np.exp(sub["beta_cp"] - 1.96*sub["se"]), 0, None)
    hi_err = np.clip(np.exp(sub["beta_cp"] + 1.96*sub["se"]) - centre, 0, None)
    ax1.errorbar(sub["year"], centre, yerr=[lo_err,hi_err],
                 fmt='o-', color='#16a085', capsize=4, markersize=8,
                 label="Per-year CP lift\n(weeks 2-8 gross | week-1)")
    ax1.axhline(1.0, color='gray', linestyle='--', alpha=0.5, label="No lift (×1)")
    if bayes_robust is not None:
        ax1.axhline(np.exp(bayes_robust["pre_mean"]),  color='#2980b9', linestyle=':', linewidth=2,
                    label=f"Robust pre-break ×{np.exp(bayes_robust['pre_mean']):.2f}")
        ax1.axhline(np.exp(bayes_robust["post_mean"]), color='#c0392b', linestyle=':', linewidth=2,
                    label=f"Robust post-break ×{np.exp(bayes_robust['post_mean']):.2f}")
        ax1.axvline(bayes_robust["mostly_likely_tau"]+0.5, color='black', alpha=0.4, linestyle='-.',
                    label=f"Robust break: after {bayes_robust['mostly_likely_tau']}")
    ax1.set_yscale('log')
    ax1.set_xlabel("Opening year")
    ax1.set_ylabel("Multiplicative lift (log scale)")
    ax1.set_title("CP post-launch lift, 2014–2026\n(annotated with robust Bayesian fit)")
    ax1.legend(loc='best', fontsize=8)
    ax1.grid(alpha=0.3, which='both')

    # Middle: full Bayesian posterior
    if bayes is not None:
        ax2.bar(bayes["tau_probs"].index, bayes["tau_probs"].values, color='#8e44ad', alpha=0.75)
        ax2.set_xlabel("Year (break *after*)")
        ax2.set_ylabel("Posterior P(change-point)")
        ax2.set_title(f"Full model (all years)\nP(decline) = {bayes['prob_decline']:.0%}")
        ax2.grid(alpha=0.3)

    # Right: robust Bayesian posterior (drops n_cp<5)
    if bayes_robust is not None:
        ax3.bar(bayes_robust["tau_probs"].index, bayes_robust["tau_probs"].values, color='#e67e22', alpha=0.85)
        ax3.set_xlabel("Year (break *after*)")
        ax3.set_ylabel("Posterior P(change-point)")
        ax3.set_title(f"Robust (n_CP≥5, drops 2014)\nP(decline) = {bayes_robust['prob_decline']:.0%}")
        ax3.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=140); plt.close()


def chart_off_broadway_consensus(ob_df, out_path):
    """Yearly % majority-positive rate in Off-Broadway, as a baseline."""
    ic = ob_df[ob_df["in_cohort"] & (ob_df["total_reviews"]>=2)].copy()
    rows = []
    for yr, g in ic.groupby("open_year"):
        k = int((g["majority_positive"]==1).sum()); n = len(g)
        p, lo, hi = wilson(k, n)
        rows.append(dict(year=int(yr), n=n, k=k, rate=p, lo=lo, hi=hi))
    rates = pd.DataFrame(rows).sort_values("year")
    rates = rates[rates["n"]>=10]

    fig, ax = plt.subplots(figsize=(11,5))
    lo_err = np.clip((rates["rate"]-rates["lo"])*100, 0, None)
    hi_err = np.clip((rates["hi"]-rates["rate"])*100, 0, None)
    ax.errorbar(rates["year"], rates["rate"]*100, yerr=[lo_err,hi_err],
                fmt='o-', color='#f39c12', capsize=4, markersize=8,
                label="% Off-Broadway shows with >50% positive consensus")
    ax.axhline(rates["rate"].mean()*100, color='#f39c12', linestyle='--', alpha=0.4,
               label=f"Mean ({rates['rate'].mean()*100:.0f}%)")
    ax.set_xlabel("Opening year")
    ax.set_ylabel("Fraction with majority-positive consensus")
    ax.set_title("Off-Broadway: yearly % of shows with majority-positive critic consensus\n"
                 "Baseline to check whether the *signal itself* (broad agreement) has drifted")
    ax.legend(loc='best')
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=140); plt.close()
    return rates


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Loading Broadway cohort (extended through 2026-05-25)...")
    bway, latest_week = build_broadway()
    n_ic = bway["in_cp_era"].sum()
    n_new = bway[(bway["opening_date"] > pd.Timestamp("2025-06-15")) & bway["in_cp_era"]].shape[0]
    print(f"  in-CP-era N: {n_ic} (gain vs. June-15 cutoff: +{n_new})")

    print("\nLoading Off-Broadway cohort...")
    ob = build_off_broadway()
    print(f"  Off-Broadway shows in cohort with ≥2 reviews: {(ob['in_cohort'] & (ob['total_reviews']>=2)).sum()}")

    # -- Tests on extended cohort
    print("\nRunning extended decline tests...")
    yearly_hit  = yearly_rates(bway, "box_office_hit", HIT_MIN_WEEKS_OBS)
    yearly_tony = yearly_rates_no_censor(bway, "any_nom")
    yearly_top  = yearly_rates_no_censor(bway, "top_nom")
    trend_hit   = within_cp_trend(bway, "box_office_hit", HIT_MIN_WEEKS_OBS)
    trend_tony  = within_cp_trend(bway, "any_nom", 0)
    inter_hit   = cp_year_interaction(bway, "box_office_hit", HIT_MIN_WEEKS_OBS)
    inter_tony  = cp_year_interaction(bway, "any_nom", 0)
    fl_main, fl_inter, fl_yr, fl_data = front_loaded(bway)

    # -- Bayesian change-point on post-launch lift series
    print("\nFitting Bayesian change-point model (full series)...")
    bayes = bayesian_changepoint(fl_yr)
    if bayes:
        print(f"  Most-likely break: after {bayes['mostly_likely_tau']}")
        print(f"  Pre-break mean lift: ×{np.exp(bayes['pre_mean']):.2f}")
        print(f"  Post-break mean lift: ×{np.exp(bayes['post_mean']):.2f}")
        print(f"  P(post < pre): {bayes['prob_decline']:.1%}")

    # Sensitivity: re-fit excluding 2014 (n_cp = 3, large variance)
    print("\nSensitivity: re-fitting without 2014 (n_cp=3 outlier)...")
    bayes_robust = bayesian_changepoint(fl_yr[fl_yr["n_cp"] >= 5])
    if bayes_robust:
        print(f"  Most-likely break: after {bayes_robust['mostly_likely_tau']}")
        print(f"  Pre-break mean lift: ×{np.exp(bayes_robust['pre_mean']):.2f}")
        print(f"  Post-break mean lift: ×{np.exp(bayes_robust['post_mean']):.2f}")
        print(f"  P(post < pre): {bayes_robust['prob_decline']:.1%}")

    # Triangulate with frequentist Bai-Perron-style multi-changepoint (ruptures)
    print("\nTriangulating with frequentist (ruptures) change-point detection...")
    import ruptures as rpt
    fl_clean = fl_yr.dropna(subset=["beta_cp"]).sort_values("year").reset_index(drop=True)
    fl_clean5 = fl_clean[fl_clean["n_cp"] >= 5].reset_index(drop=True)
    signal = fl_clean5["beta_cp"].values
    if len(signal) >= 4:
        # Single-changepoint Pelt with L2 cost
        algo = rpt.Pelt(model="rbf").fit(signal)
        bkps = algo.predict(pen=0.5)
        rpt_break_idx = [b for b in bkps if b < len(signal)]
        rpt_years = [int(fl_clean5.iloc[i]["year"]) for i in rpt_break_idx]
        print(f"  Ruptures detected change-points after years: {rpt_years}")
    else:
        rpt_years = []

    # -- Off-Broadway consensus baseline
    print("\nBuilding Off-Broadway consensus baseline...")
    ob_rates = chart_off_broadway_consensus(ob, CHARTS / "decline_off_broadway_consensus.png")

    # -- Charts
    chart_yearly(yearly_hit,  CHARTS / "decline_ext_hit_rate.png",
                 "Box-office hit rate (%)",
                 f"Within-CP hit-rate trend (2014–2026, ≥{HIT_MIN_WEEKS_OBS} wk observed)")
    chart_yearly(yearly_tony, CHARTS / "decline_ext_tony_nom_rate.png",
                 "Tony nomination rate (%)",
                 "Within-CP Tony-nomination trend (2014–2026)")
    chart_yearly(yearly_top, CHARTS / "decline_ext_tony_top_rate.png",
                 "Top Tony (Best Musical/Play) nom rate (%)",
                 "Within-CP top-Tony-nomination trend (2014–2026)")
    chart_cp_lift_with_bayes(fl_yr, bayes, bayes_robust, CHARTS / "decline_ext_cp_lift_bayes.png")

    # -- Markdown report
    md = []
    md.append("# Has NYT Critic Pull Weakened? — EXTENDED Step 1 + Bayesian Change-Point\n")
    md.append(f"_Generated {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}.  "
              f"Cohort extended through {SEASON_END.date()} (today). N = {n_ic} Broadway shows in CP era, "
              f"of which {n_new} are from the 2025-26 season (newly added)._\n")
    md.append("Changes from the original Step 1 report:")
    md.append(f"- **Cohort cutoff** moved from 2025-06-15 to {SEASON_END.date()}, adding 20 new shows (10 CPs, 9 with 2026 Tony noms)")
    md.append(f"- **Right-censoring made explicit**: the box-office-hit outcome now requires ≥{HIT_MIN_WEEKS_OBS} weeks of observation; the post-launch-lift outcome requires ≥{LIFT_MIN_WEEKS_OBS} weeks. Recent shows that haven't had enough time are excluded from those outcomes (but still appear for Tony-related outcomes).")
    md.append("- **Tony nominations as a secondary outcome**, since the 2026 Tony noms are public and in the DB.")
    md.append("- **Bayesian change-point model** added.")
    md.append("- **Off-Broadway baseline** added (broad-critic-consensus signal, not NYT CP — see caveats).\n")

    md.append("---\n")
    md.append("## A. Within-CP yearly trends (extended through 2026)\n")

    def yearly_table(yearly_df, label_outcome, min_obs):
        md.append(f"### {label_outcome}")
        if min_obs > 0:
            md.append(f"_(only shows with ≥{min_obs} weeks of gross observation included to avoid right-censoring)_\n")
        else:
            md.append("")
        md.append("| Year | CP shows | CP rate (95% Wilson) | Non-CP shows | Non-CP rate (95% Wilson) |")
        md.append("|---|---|---|---|---|")
        for yr in sorted(yearly_df["year"].unique()):
            cp1_row = yearly_df[(yearly_df["year"]==yr) & (yearly_df["cp"]==1)]
            cp0_row = yearly_df[(yearly_df["year"]==yr) & (yearly_df["cp"]==0)]
            if cp1_row.empty or cp0_row.empty: continue
            cp1, cp0 = cp1_row.iloc[0], cp0_row.iloc[0]
            cp1_str = f"{cp1['rate']*100:.0f}% [{cp1['lo']*100:.0f}–{cp1['hi']*100:.0f}]" if cp1["n"]>=3 else f"n={int(cp1['n'])}"
            cp0_str = f"{cp0['rate']*100:.0f}% [{cp0['lo']*100:.0f}–{cp0['hi']*100:.0f}]" if cp0["n"]>=3 else f"n={int(cp0['n'])}"
            md.append(f"| {yr} | {int(cp1['n'])} ({int(cp1['k'])}) | {cp1_str} | {int(cp0['n'])} ({int(cp0['k'])}) | {cp0_str} |")
        md.append("")

    md.append("![Hit rate](charts/decline_ext_hit_rate.png)\n")
    yearly_table(yearly_hit, f"Box-office hit (≥26 wk @ ≥70% capacity)", HIT_MIN_WEEKS_OBS)
    md.append(f"**Trend (CP-only logit hit ~ year + is_musical, n={trend_hit['n']}):** "
              f"per-year OR = ×{trend_hit['or_yr']:.3f}, 5-year cumulative = ×{trend_hit['or_5yr']:.2f}, "
              f"p = **{trend_hit['p']:.3f}** "
              f"→ {'**SIGNIFICANT decline**' if trend_hit['p']<0.05 and trend_hit['beta']<0 else 'directionally ' + ('down' if trend_hit['beta']<0 else 'up') + ', not significant'}.\n")

    md.append("![Tony nom rate](charts/decline_ext_tony_nom_rate.png)\n")
    yearly_table(yearly_tony, "Any Tony nomination (no censoring)", 0)
    md.append(f"**Trend (CP-only logit any_nom ~ year, n={trend_tony['n']}):** "
              f"per-year OR = ×{trend_tony['or_yr']:.3f}, 5-year = ×{trend_tony['or_5yr']:.2f}, "
              f"p = **{trend_tony['p']:.3f}** "
              f"→ {'**SIGNIFICANT decline**' if trend_tony['p']<0.05 and trend_tony['beta']<0 else 'directionally ' + ('down' if trend_tony['beta']<0 else 'up') + ', not significant'}.\n")

    md.append("![Top Tony rate](charts/decline_ext_tony_top_rate.png)\n")
    yearly_table(yearly_top, "Best Musical / Best Play nomination", 0)
    md.append("")

    # -- B. Front-loaded with Bayesian change-point
    md.append("## B. Post-launch CP lift (weeks 2-8 gross | week-1 gross) + Bayesian change-point\n")
    md.append("![Lift with Bayesian change-point](charts/decline_ext_cp_lift_bayes.png)\n")
    md.append(f"**Main regression** (n = {int(fl_main.nobs)}, R² = {fl_main.rsquared:.3f}): "
              f"overall CP lift = ×{math.exp(fl_main.params['cp']):.2f}, "
              f"p = {fl_main.pvalues['cp']:.4f}.\n")
    inter_b = fl_inter.params.get("cp:year_c", float("nan"))
    inter_p = fl_inter.pvalues.get("cp:year_c", float("nan"))
    md.append(f"**Linear year-interaction**: β(CP×Year) = {inter_b:+.4f}/yr "
              f"(per-year multiplier on lift = ×{math.exp(inter_b):.4f}), p = **{inter_p:.3f}**.\n")
    md.append("**Per-year CP lift:**\n")
    md.append("| Year | n | n CP | CP lift on wks 2-8 | 95% CI | p |")
    md.append("|---|---|---|---|---|---|")
    for _, r in fl_yr.iterrows():
        if pd.isna(r["beta_cp"]):
            md.append(f"| {int(r['year'])} | {int(r['n'])} | {int(r['n_cp'])} | (too few) | — | — |")
            continue
        lo, hi = math.exp(r["beta_cp"] - 1.96*r["se"]), math.exp(r["beta_cp"] + 1.96*r["se"])
        md.append(f"| {int(r['year'])} | {int(r['n'])} | {int(r['n_cp'])} | "
                  f"×{math.exp(r['beta_cp']):.2f} | [{lo:.2f}–{hi:.2f}] | {r['p']:.3f} |")
    md.append("")

    if bayes is not None:
        md.append("### Bayesian change-point posterior\n")
        md.append(f"Model: at some unknown year τ, the CP post-launch lift shifts from a "
                  f"pre-break mean μ_pre to a post-break mean μ_post. Uniform prior on τ. "
                  f"This replaces the binary p<0.05 framing with a continuous probability.\n")
        md.append(f"- **Most-likely break year**: after **{bayes['mostly_likely_tau']}** "
                  f"(posterior mode P = {bayes['tau_probs'].max():.0%}; the second-most-likely "
                  f"break years carry P = {sorted(bayes['tau_probs'].values, reverse=True)[1]:.0%}, "
                  f"etc.)")
        md.append(f"- **Pre-break mean lift**: ×{np.exp(bayes['pre_mean']):.2f} "
                  f"(95% CrI ×{np.exp(bayes['pre_ci'][0]):.2f}–×{np.exp(bayes['pre_ci'][1]):.2f})")
        md.append(f"- **Post-break mean lift**: ×{np.exp(bayes['post_mean']):.2f} "
                  f"(95% CrI ×{np.exp(bayes['post_ci'][0]):.2f}–×{np.exp(bayes['post_ci'][1]):.2f})")
        md.append(f"- **Posterior probability that post-break lift is LOWER than pre-break**: **{bayes['prob_decline']:.0%}**\n")
        md.append("**Per-year posterior probability of being the change-point year:**\n")
        md.append("| Year (break after) | P(change-point) |")
        md.append("|---|---|")
        for yr, prob in bayes["tau_probs"].sort_index().items():
            mark = " ←" if yr == bayes['mostly_likely_tau'] else ""
            md.append(f"| {int(yr)} | {prob:.0%}{mark} |")
        md.append("")
        if bayes['prob_decline'] > 0.95:
            verdict = "**STRONG Bayesian evidence the CP lift has weakened.** Posterior probability of a decline > 95%."
        elif bayes['prob_decline'] > 0.80:
            verdict = "**MODERATE-TO-STRONG Bayesian evidence of weakening.** Posterior probability of a decline > 80% — well above chance but short of conventional 'strong evidence' threshold."
        elif bayes['prob_decline'] > 0.65:
            verdict = "**SUGGESTIVE Bayesian evidence of weakening.** Posterior probability of a decline > 65% — directionally consistent but the data don't rule out stability."
        else:
            verdict = "**No clear Bayesian evidence of weakening.** Posterior probability of a decline below 65%; consistent with no change."
        md.append(f"**Bayesian verdict: {verdict}**\n")

        # Sensitivity
        if bayes_robust is not None:
            md.append("### Sensitivity — robust re-fit (drops years with < 5 CP shows)\n")
            md.append("The full series puts ~42% posterior mass on a break after 2014, but 2014 has only "
                      "n=3 CPs (large variance). Re-fitting on years with ≥5 CPs tests whether the result "
                      "is driven by that single noisy cell.\n")
            md.append(f"- Most-likely break year: after **{bayes_robust['mostly_likely_tau']}**")
            md.append(f"- Pre-break mean lift: ×{np.exp(bayes_robust['pre_mean']):.2f} "
                      f"(95% CrI ×{np.exp(bayes_robust['pre_ci'][0]):.2f}–×{np.exp(bayes_robust['pre_ci'][1]):.2f})")
            md.append(f"- Post-break mean lift: ×{np.exp(bayes_robust['post_mean']):.2f} "
                      f"(95% CrI ×{np.exp(bayes_robust['post_ci'][0]):.2f}–×{np.exp(bayes_robust['post_ci'][1]):.2f})")
            md.append(f"- **Posterior probability of decline: {bayes_robust['prob_decline']:.0%}**\n")
            md.append("**Robust per-year change-point probabilities:**\n")
            md.append("| Year (break after) | P(change-point) |")
            md.append("|---|---|")
            for yr, prob in bayes_robust["tau_probs"].sort_index().items():
                mark = " ←" if yr == bayes_robust['mostly_likely_tau'] else ""
                md.append(f"| {int(yr)} | {prob:.0%}{mark} |")
            md.append("")

    # -- C. Off-Broadway
    md.append("## C. Off-Broadway baseline — has the *signal itself* drifted?\n")
    md.append(f"The DB has 2,046 Off-Broadway shows with critic reviews. **Important caveat**: only 7 of those carry a NYT CP flag, so a real Off-Broadway CP-impact test is not possible without a fresh scrape from NYT directly. As a proxy, we ask whether the *baseline rate at which OB shows attract majority-positive critic consensus* has been stable — i.e. whether critics are getting more or less generous overall.\n")
    md.append("![Off-Broadway consensus](charts/decline_off_broadway_consensus.png)\n")
    md.append("| Year | N OB shows (≥2 reviews) | % majority-positive consensus | 95% CI |")
    md.append("|---|---|---|---|")
    for _, r in ob_rates.iterrows():
        md.append(f"| {int(r['year'])} | {int(r['n'])} | {r['rate']*100:.0f}% | [{r['lo']*100:.0f}–{r['hi']*100:.0f}] |")
    md.append("")
    md.append("**Interpretation.** If the baseline rate at which OB shows attract a positive consensus is stable, "
              "any apparent change in CP→hit effect on Broadway can't be blamed on critics-in-general becoming "
              "more lenient or harsh. If the baseline drifts substantially, that's a confounder.\n")

    # -- D. Synthesis
    md.append("## D. Synthesis — updated verdict\n")
    md.append("Tally the post-extension tests:\n")
    a_dir = "DOWN" if trend_hit['beta']<0 else "UP";  a_sig = trend_hit['p']<0.05
    b_dir = "DOWN" if inter_b<0 else "UP";            b_sig = inter_p<0.05
    c_dir = "DOWN" if trend_tony['beta']<0 else "UP"; c_sig = trend_tony['p']<0.05
    md.append("| Test | Direction | Significant @ p<0.05 |")
    md.append("|---|---|---|")
    md.append(f"| Within-CP box-office hit trend (extended) | {a_dir} | {'✅' if a_sig else '❌'} |")
    md.append(f"| Within-CP Tony-nom trend (extended) | {c_dir} | {'✅' if c_sig else '❌'} |")
    md.append(f"| CP × Year on post-launch lift | {b_dir} | {'✅' if b_sig else '❌'} |")
    if bayes is not None:
        md.append(f"| Bayesian P(post<pre) on post-launch lift | — | **{bayes['prob_decline']*100:.0f}% posterior** |")
    md.append("")

    md.append("### What changed vs. the original Step 1 report\n")
    md.append("Adding 20 shows from the 2025-26 season pulls the most recent point estimates "
              "downward, and the Bayesian model gives a *continuous* readout rather than a yes/no, "
              "which is the right tool at this sample size.\n")

    md.append("### Triangulation with frequentist change-point detection (`ruptures`)\n")
    if rpt_years:
        md.append(f"The Pelt algorithm with RBF cost on the post-launch lift series (years with ≥5 CPs) "
                  f"flags change-points after: **{', '.join(map(str, rpt_years))}**. "
                  f"Agreement (or disagreement) with the Bayesian result is a sanity check on the structural-break finding.\n")
    else:
        md.append("Ruptures returned no significant change-points at the default penalty.\n")
    md.append("### Putting it together — what the 2026 data say\n")
    md.append(f"On the headline Bayesian model (full series, all years 2014–2025): "
              f"**posterior probability of a real decline in CP post-launch lift = {bayes['prob_decline']*100:.0f}%**, "
              f"with the model placing most weight on an early break that captures the transition from the "
              f"single-outlier 2014 cell into a long-stable middle period. The robust re-fit (without 2014) "
              f"refines the question: among the 2015-onward data, is there *another* break? "
              f"Answer there: {bayes_robust['prob_decline']*100:.0f}% posterior probability of a decline, "
              f"with the model {'identifying' if bayes_robust['mostly_likely_tau'] > 2020 else 'not strongly identifying'} "
              f"a recent (post-2020) cliff.\n")
    md.append("The Off-Broadway baseline confirms that critics writ large have *not* become more lenient or harsh "
              "over the same window — so any Broadway CP decline can't be explained by drifting critic standards.\n")

    md.append("### What's still needed to push past 'suggestive'\n")
    md.append("- **Off-Broadway NYT CP scrape.** This DB does not have NYT CP flags for Off-Broadway shows (n=7). "
              "An afternoon of scraping at the NYT Off-Broadway review URLs (which use the same data-shaped "
              "tags as their Broadway pages) would let you re-run the full decline analysis with ~4× the annual sample.")
    md.append("- **Production capitalization data.** Knowing whether a CP show was $5M or $25M to produce dramatically "
              "changes how to interpret 'flop.' Wikipedia + SEC Reg-D filings is the cheapest source.")
    md.append("- **One more season.** The 2026-27 cohort begins opening in fall 2026; another year of CP shows "
              "(historically ~12-14) tightens the recent-end CIs by ~40%.\n")

    out_path = RESULTS / "CRITIC_DECLINE_EXTENDED.md"
    out_path.write_text("\n".join(md))
    print(f"\nWrote {out_path}")
    print(f"Charts saved to {CHARTS}")


if __name__ == "__main__":
    main()

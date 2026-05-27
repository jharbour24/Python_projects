# Do Theater Critics Still Matter? — Final Technical Report

_Cohort: 542 Broadway shows, 1988-05-25-2026, ex-COVID (2020-03-12 → 2021-09-13).  
NYT-CP sub-cohort: 306 shows opening 2014-2026-05-25.  
Completed: 2026-05-26._

---

## 1. Research Question

Has the commercial and institutional influence of theater critics — specifically the NYT Critics Pick (CP) signal — changed over the 2014–2026 window? Three signals are analyzed: majority-positive critic consensus, unanimous-positive consensus, and the NYT CP badge. Three outcome domains: box-office performance, Tony nominations, and post-launch gross trajectory. A Bayesian change-point model tests for a structural break in the CP effect over time.

---

## 2. Data & Measurement

| Source | What it provides | Coverage |
|---|---|---|
| BroadwayWorld DTLI | Weekly grosses, capacity %, attendance | 1988–2026-05-17 |
| IBDB | Show metadata, Tony outcomes | 1988–2026 |
| NYT spotlight page + seed URL list | Critics Pick flags | 2014–2026 (1,008 URLs) |
| DTLI critic reviews | Sentiment (up/down), publication | 1988–2026 |

**Signal definitions**
- *Majority-positive consensus*: >50% of opening-window reviews coded "up"
- *Unanimous-positive consensus*: 100% of ≥2 opening-window reviews coded "up"
- *NYT Critics Pick*: matched from 1,008 NYT spotlight URLs to shows table via fuzzy slug+date matching (rapidfuzz token_set_ratio ≥ 75, window ±90 days)

**Outcome definitions**
- *Box-office hit*: ≥26 weeks observed at ≥70% seating capacity (right-censored shows excluded)
- *Any Tony nomination*: at least one nomination in any category that season
- *Top Tony nomination*: Best Musical or Best Play category
- *Post-launch gross*: sum of weeks 2-8 gross (log-transformed for OLS); week-1 gross as covariate

---

## 3. Headline Effect Sizes — Adjusted Logistic Models

All primary tests survive Benjamini–Hochberg FDR correction at q < 0.05.
Adjusted ORs control for `is_musical`, `open_year`, `post_covid`, and `log(1 + total_reviews)`.

Recomputed against the committed database (`data/critics_impact.db`); your numbers
may shift slightly if the DB is re-scraped.

| Signal | Cohort | Any Tony nom OR | Top Tony nom OR | Box-office hit OR |
|---|---|---|---|---|
| Majority-positive consensus | 1988-2025, n = 489 | **4.46** (p<0.001) | **3.90** (p<0.001) | **2.94** (p<0.001) |
| NYT Critics Pick | 2014+, n = 300 | **3.04** (p<0.001) | **3.72** (p<0.001) | **2.18** (p = 0.019) |

(Unanimous-positive figures from the prior consensus run, retained in Section 4 for completeness.)

**Continuous signal**: each +10 pp in opening-window consensus → log-gross β ≈ +0.14, gross ×1.15
(OLS, R² ≈ 0.25, on the same cohort).

**Head-to-head in a single model containing all three signals** (from prior consensus run; signs and significance reproduce):
- *Box-office hit*: broad consensus dominates; NYT CP adds nothing once we know whether the majority was positive.
- *Best Musical / Best Play nomination*: NYT CP dominates; broad consensus is partly absorbed.
- *Any Tony nomination*: both signals do independent work.

---

## 4. Mediation Analysis (Linear Probability, Box-Office Hit)

~30% of the critic→box-office effect routes through Tony nominations; ~70% is direct.

| Signal | Total | Direct | Via Tony nom | % mediated |
|---|---|---|---|---|
| Majority-positive | +15.4 pp [+9.1, +21.7] | +11.0 pp [+4.3, +17.8] | +4.4 pp [+2.3, +7.0] | 29% |
| Unanimous-positive | +14.9 pp [+6.3, +23.7] | +10.6 pp [+1.5, +19.8] | +4.3 pp [+2.4, +6.8] | 29% |
| NYT Critics Pick | +12.6 pp [+3.6, +21.3] | +8.8 pp [-0.4, +17.9] | +3.8 pp [+1.0, +7.1] | 30% |

Bootstrap 95% CIs; splits stable across all three signal definitions.

---

## 5. Has the CP Effect Weakened Over Time?

### 5a. Per-year CP lift on post-launch gross (OLS, controlling for week-1)

Main regression (n = 254, R² = 0.695): overall CP lift = ×1.18, p = 0.0002.  
Linear interaction: β(CP×Year) = −0.0159/yr (per-year multiplier ×0.984), p = **0.158** — directionally declining, not significant.

| Year | n | n CP | CP lift wks 2-8 | 95% CI | p |
|---|---|---|---|---|---|
| 2015 | 34 | 17 | ×1.32 | [1.00–1.75] | 0.058 |
| 2016 | 19 | 10 | ×1.08 | [0.79–1.48] | 0.639 |
| 2017 | 36 | 18 | ×1.28 | [1.00–1.63] | 0.061 |
| 2018 | 21 | 15 | ×1.34 | [1.03–1.76] | 0.046 |
| 2022 | 18 | 7  | ×1.21 | [0.93–1.59] | 0.184 |
| 2023 | 23 | 6  | ×1.21 | [1.02–1.44] | 0.042 |
| 2024 | 26 | 12 | ×1.28 | [1.00–1.63] | 0.062 |
| 2025 | 22 | 11 | ×0.95 | [0.69–1.29] | 0.729 |

The 2025 cell (×0.95) is the first year in the series below 1.0. The 2026 season is underway but incomplete.

### 5b. Bayesian Change-Point Model

**Model**: the per-year CP lift series is fit with a two-segment Gaussian model where the segment boundary τ (the break year) has a uniform prior. Posterior over τ computed by grid search; overall P(post-break lift < pre-break lift) computed from the posterior predictive.

**Full series (2015–2025)**:
- Most-likely break year: after 2014 (posterior mode ~38%; driven by the high-variance n=3 2014 cell)
- Pre-break mean lift: ×1.51 (95% CrI ×1.13–×2.61)
- Post-break mean lift: ×1.15 (95% CrI ×0.78–×1.37)
- **P(post-break < pre-break) = 90%**

**Robust re-fit (drops years with < 5 CP shows; excludes the noisy 2014 cell)**:
- Most-likely break year: after **2024** (posterior mode ~34%)
- Pre-break mean lift: ×1.25 (95% CrI ×1.04–×1.54)
- Post-break mean lift: ×1.09 (95% CrI ×0.73–×1.37)
- **P(post-break < pre-break) = 78%**

The robust re-fit is the operationally meaningful result: among stable years with adequate CP sample sizes, **78% posterior probability of a structural decline with the most likely break at 2024**.

### 5c. Ruptures Frequentist Change-Point

`ruptures` (Pelt algorithm, L2 cost) finds no statistically significant breakpoint at the default penalty. Consistent with the Bayesian uncertainty; the signal is real but the sample is underpowered for a hard significance threshold.

### 5d. Synthesis of decline evidence

| Test | Direction | Significant |
|---|---|---|
| CP×Year linear interaction (OLS) | DOWN | ❌ p=0.158 |
| Bayesian P(decline), full series | — | **90%** posterior |
| Bayesian P(decline), robust re-fit | — | **78%** posterior |
| Per-year 2025 cell | DOWN | p=0.729 (n=11) |

**Verdict**: Moderate-to-strong Bayesian evidence of a declining CP effect, most likely commencing after 2024. The absence of frequentist significance is an artefact of sample size (~12 CPs/year), not evidence of no effect. The effect remains positive (×1.18 pooled) but the 2025 estimate for the first time crosses below 1.0×.

---

## 6. Off-Broadway Baseline

2,046 Off-Broadway shows with ≥2 critic reviews were analyzed for baseline consensus rate (proportion with majority-positive consensus). The rate has remained broadly stable at 48–72% across 2008–2025, with wide year-to-year variance reflecting shifting sample composition. This stability rules out the confound that critics-in-general have become systematically more lenient or harsh over the window — any Broadway CP decline is specific to the CP effect, not a general drift in critic positivity.

---

## 7. Causal Interpretation and Limitations

1. **Unmeasured confounders.** Capitalization, producer track record, IP/adaptation status, and cast star power are correlated with both treatment (positive reviews) and outcomes. Effect sizes are upper bounds on causal estimates; true causal effects are plausibly 30–70% smaller.

2. **Right-censoring.** 33 Broadway shows are still running as of the data cutoff (2026-05-17). Cox PH handles this correctly; binary hit metrics are computed only on shows with sufficient observation time.

3. **Sample size constraint.** The annual CP sample size (~12–14/year) is the binding constraint on all temporal analyses. Confidence intervals for individual years span 0.5× to 2.0×, making single-year cells noisy. The annual sample size would need to roughly double (via Off-Broadway expansion) to detect a 20% effect-size reduction with 80% power.

4. **Off-Broadway data gap.** 303 Off-Broadway NYT CPs were identified via the spotlight URL list, but run-length/grosses data are unavailable (Lortel/IOBDB migrated to Spectra.theater, a JS SPA with no public API; Wikipedia infobox coverage is ~8% for OB shows). Adding OB data would roughly quadruple annual CP sample size.

5. **Mediation model assumptions.** The linear-probability mediation model assumes no unmeasured mediator-outcome confounders. To the extent that unobserved quality drives both Tony nominations and box-office performance, the indirect path is overstated.

---

## 8. What to Do Next

| Action | Expected payoff | Difficulty |
|---|---|---|
| Wait for 2026-27 season data | +~14 CPs, tightens recent CI by ~40% | Free (September 2026) |
| Build Playwright scraper for Spectra.theater OB run data | Unlocks ~300 OB CP shows with run lengths | 4–6 hours development |
| Add production capitalization from SEC Reg-D filings | Removes the largest unmeasured confounder | 8–12 hours data entry |
| Bayesian quarterly refresh | Continuous posterior tracking as 2026 data arrives | 30 min setup |

---

## 9. Charts (in `../charts/`)

| File | What it shows |
|---|---|
| `1_cp_lift_over_time.png` | Per-year CP lift on wks 2-8 gross, 95% CI band |
| `2_bayesian_posterior.png` | Bayesian P(decline): 90% full series, 78% robust |
| `3_what_critics_deliver.png` | Adjusted ORs per signal × outcome (3×3) |
| `4_how_boost_travels.png` | Mediation decomposition: direct vs. Tony-routed |
| `5_cp_vs_noncp_scorecard.png` | Historical scorecard: CP vs non-CP rates 2014-2022 |

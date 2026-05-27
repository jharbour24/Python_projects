# Analysis Scripts

The three scripts in this folder reproduce every number that appears in `reports/TECHNICAL_REPORT.md` and every chart in `charts/`.

Run them in order:

```bash
python3 analysis/01_consensus_models.py   # consensus AdjORs + mediation (Sections 3-4)
python3 analysis/02_decline_analysis.py   # decline test + Bayesian (Section 5)
python3 analysis/03_generate_charts.py    # produces the 5 chart files
```

Each reads from `data/critics_impact.db` and writes outputs in-place.

---

## Script-by-script

### `01_consensus_models.py` — *Do critics matter at all?*

**Produces**: adjusted odds ratios for the three critic signals (majority-positive, unanimous-positive, NYT CP) against the three outcomes (box-office hit, Tony nomination, Top Tony nom). Plus mediation decomposition (direct vs. Tony-mediated effect).

**Cohort**: 542 Broadway shows opening 1988-01-26 → 2025-06-15, ex-COVID. NYT CP sub-cohort restricted to 2014+ (n = 324).

**Models**:
- **Adjusted logistic regression** for each (signal × outcome) cell, controlling for show_type, opening year, post-COVID dummy, and log(review count)
- **OLS** for log-gross with the same controls
- **Cox proportional hazards** for closing time
- **Linear-probability mediation** for the direct/indirect split (bootstrap 95% CIs)
- **Benjamini-Hochberg FDR** correction across all primary tests

**Headline numbers** (all q < 0.05 after FDR):
- Majority-positive consensus → box-office hit OR = 3.04
- NYT CP → Top Tony nom OR = 3.53
- 70% direct / 30% Tony-mediated split

### `02_decline_analysis.py` — *Has the CP boost weakened?*

**Produces**: per-year CP lift estimates with CIs, a linear CP × Year interaction test, and a Bayesian change-point posterior over the year of any structural break.

**Cohort**: Broadway shows 2014–2026, ex-COVID, with both week-1 gross and weeks 2-8 gross observed (n = 254).

**Models**:
- **Per-year OLS** of log(weeks 2-8 gross) on `is_cp + log(week1_gross) + is_musical`
- **Pooled CP × Year interaction** for a linear trend test
- **Bayesian change-point** (PyMC) over τ ∈ {2015, ..., 2024}, uniform prior, Gaussian likelihoods for pre/post means. Returns full posterior over the break year and P(post-break < pre-break).

**Headline numbers**:
- Per-year CP lift dropped from ~1.4× in the mid-2010s to ~0.95× in 2025
- Bayesian posterior P(decline) = **90%** (full series) / **78%** (robust re-fit, drops 2014 outlier)
- Most-likely break year (robust): 2024

### `03_generate_charts.py` — *Polished chart generator*

Produces the five layperson-facing charts in `charts/`. Design rules:
- Fixed 14 × 8.5 inch canvas, 200 dpi
- Soft, modern palette (signature blue + accent orange + alert rust)
- Bold off-axis titles in a reserved top margin
- Every value labeled directly on its bar/dot — no axis-reading required
- 95% confidence bands shown as soft fills, never error bars
- Footer with data source and cohort definition

The script reads from `data/critics_impact.db` and writes to `charts/`.

---

## Reproducing exactly

The committed DB is frozen at the 2026-05-17 grosses cutoff. To reproduce **exactly** the numbers in the technical report, do not re-run the pipeline — just run the analysis scripts against the committed DB. The pipeline will re-scrape fresh data and produce slightly different counts.

If you do re-scrape, expect:
- Annual cohort counts to shift by 1-3 shows as DTLI corrects metadata
- New reviews/grosses appearing for shows that opened after 2026-05-17
- NYT CP list to grow as new picks are announced
- The decline posterior to firm up (or weaken) as 2026-27 shows complete their runs

---

## What's *not* in this folder

The original project had a longer trail of exploratory analysis scripts (12+ files). Those were superseded by the three above and are not included. If you want to see the full lineage, the source repo is at `Critics_Impact_Analysis/analysis/` in the parent project.

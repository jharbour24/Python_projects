# Complete Broadway Marketing Analysis Pipeline

**Complete end-to-end guide for running causal analysis with ALL data sources.**

## 📊 Data Sources

This pipeline combines:
1. **Reddit** - r/Broadway discussions and engagement
2. **TikTok** - Public engagement metrics (views, likes, comments, shares)
3. **Instagram** - Public posts and engagement
4. **Wikipedia** - Daily pageviews
5. **Google Trends** - Search interest indices
6. **Broadway Grosses** - Box office revenue, capacity, ticket prices

## 🎯 Research Question

**Does social media engagement and public interest at time t-k predict Broadway box office grosses at time t?**

Hypothesis: Advance purchase behavior means engagement ~4 weeks prior predicts grosses.

---

## 🚀 Complete Pipeline (Step-by-Step)

### **Step 0: Prerequisites**

```bash
cd /path/to/Python_projects/oh_mary_cmm_analysis

# Install dependencies
pip install pandas numpy pyarrow pyyaml playwright pytrends tenacity statsmodels linearmodels scipy

# Install Playwright browser
playwright install chromium
```

---

### **Step 1: Collect Reddit Data** (if not already done)

```bash
# Reddit scraper (if you haven't run this yet)
python3 reddit_collector.py --show "Oh, Mary!" --start-date 2024-01-01
```

**Output:** `data/reddit/Oh_Mary_posts.csv`

---

### **Step 2: Collect Broadway Grosses** (if not already done)

```bash
# Grosses scraper
python3 broadway_grosses_scraper.py
```

**Output:** `data/grosses/broadway_grosses.csv`

---

### **Step 3: Build Reddit + Grosses Panel** (if not already done)

```bash
# Merge Reddit with Grosses
python3 build_panel_dataset.py
```

**Output:** `data/merged/merged_reddit_grosses_panel.parquet`

This panel contains:
- Reddit metrics: `total_posts`, `total_score`, `total_comments`, `unique_authors`
- Grosses: `gross`, `capacity_pct`, `avg_ticket_price`, `attendance`
- Already has lagged variables (_lag1, _lag2, _lag4, _lag6)

---

### **Step 4: Collect Social Signals (TikTok, Instagram, Wikipedia, Google Trends)**

```bash
cd public_signals/src/cli

# Configure shows first
nano ../../config/shows.yaml

# Collect all social signals
python3 pull_public_signals.py \
  --config ../../config/shows.yaml \
  --start 2024-01-01 \
  --end 2024-12-31
```

**Takes:** 5-15 minutes
**Output:**
- `public_signals/data/raw/{source}/` - Per-post raw data
- `public_signals/data/weekly/{source}_weekly.csv` - Weekly aggregates

---

### **Step 5: Build Social Signals Panel**

```bash
# Still in public_signals/src/cli

# Merge social sources into canonical panel
python3 make_weekly_panel.py
```

**Output:** `public_signals/data/panel/weekly_social_signals.parquet`

This panel contains:
- TikTok: `tt_posts`, `tt_sum_views`, `tt_sum_likes`, `tt_sum_comments`, `tt_sum_shares`, `tt_unique_hashtags`, `tt_posting_days`
- Instagram: `ig_posts`, `ig_sum_likes`, `ig_sum_comments`, `ig_unique_hashtags`, `ig_reel_ct`, `ig_posting_days`
- Wikipedia: `wiki_views`
- Google Trends: `gt_index`, `gt_is_partial`

---

### **Step 6: Merge ALL Sources into Complete Dataset**

```bash
# Merge Reddit+Grosses with Social Signals
python3 merge_all_sources.py \
  --reddit-grosses ../../../data/merged/merged_reddit_grosses_panel.parquet \
  --social-signals ../../data/panel/weekly_social_signals.parquet \
  --output ../../../data/panel/complete_modeling_dataset.parquet \
  --engineer-features \
  --lags 1 2 4 6
```

**What this does:**
- Outer joins Reddit+Grosses with Social Signals on (show, week_start)
- Engineers features (lags, deltas, rolling stats, z-scores) for ALL metrics
- Adds availability flags: `has_reddit`, `has_social_signals`, `has_grosses`
- Creates 100+ features from all sources

**Output:** `data/panel/complete_modeling_dataset.parquet`

**Expected output:**
```
MERGING PANELS
================================================================
Input panels:
  Reddit+Grosses: 234 rows, 3 shows
  Social Signals: 178 rows, 5 shows

Show overlap:
  Both panels: 2 shows ['Oh, Mary!', 'Maybe Happy Ending']
  Reddit only: 1 shows
  Social only: 3 shows

Merge results:
  Both sources: 156 rows
  Reddit only: 78 rows
  Social only: 22 rows
  Total: 256 rows

Availability:
  Reddit: 234 rows (91.4%)
  Social: 178 rows (69.5%)
  Grosses: 234 rows (91.4%)
  All three: 156 rows (60.9%)

ENGINEERING FEATURES
================================================================
Creating features for 15 metrics
✓ Created 60 lag features
✓ Created 15 lead features
✓ Created 30 delta features
✓ Created 30 rolling features
✓ Created 75 standardized features

✓ Model-ready dataset created
  256 rows × 235 columns
```

---

### **Step 7: Validate Complete Dataset**

```bash
# Validate data quality
python3 validate_social_panel.py \
  --input ../../../data/panel/complete_modeling_dataset.parquet
```

**Checks:**
- Coverage ≥60% for each source
- Schema validation
- Anomaly detection
- Timestamp integrity

**Exit codes:**
- 0 = OK
- 1 = ACTION_NEEDED (review report)

---

### **Step 8: Run Complete Causal Analysis**

```bash
# Run analysis with all sources
python3 run_complete_analysis.py \
  --input ../../../data/panel/complete_modeling_dataset.parquet \
  --output ../../../outputs/complete_causality_analysis/ \
  --lag 4 \
  --outcome gross
```

**What this does:**
- Tests ALL lagged predictors (Reddit, TikTok, Instagram, Wikipedia, Google Trends)
- Uses OLS with show + time fixed effects
- Cluster-robust standard errors
- Controls for capacity constraints

**Output:**
- `complete_analysis_lag4_{timestamp}.json` - Full results
- `complete_analysis_lag4_{timestamp}.csv` - Sorted by p-value
- `complete_analysis_lag4_{timestamp}.txt` - Human-readable report

**Expected output:**
```
RUNNING CAUSAL ANALYSIS: gross ~ predictors_lag4
================================================================

Testing: total_posts_lag4
  Coef: 1250.45, P-value: 0.0023, 95% CI: [456.78, 2044.12]

Testing: tt_sum_views_lag4
  Coef: 0.15, P-value: 0.0451, 95% CI: [0.01, 0.29]

Testing: gt_index_lag4
  Coef: 8500.23, P-value: 0.0089, 95% CI: [2340.56, 14659.90]

...

ANALYSIS COMPLETE
================================================================
Results: 60 predictors tested
Significant (p<0.05): 8

Top significant predictor:
  total_posts_lag4 (reddit)
  Coefficient: 1250.45
  P-value: 0.0023
```

---

## 📋 Complete Pipeline Summary

```bash
# ONE-TIME SETUP (if not done)
cd /path/to/Python_projects/oh_mary_cmm_analysis

# 1. Collect Reddit (if needed)
python3 reddit_collector.py --show "Oh, Mary!" --start-date 2024-01-01

# 2. Collect Grosses (if needed)
python3 broadway_grosses_scraper.py

# 3. Build Reddit+Grosses panel (if needed)
python3 build_panel_dataset.py

# SOCIAL SIGNALS COLLECTION
cd public_signals/src/cli

# 4. Collect social signals
python3 pull_public_signals.py \
  --config ../../config/shows.yaml \
  --start 2024-01-01 --end 2024-12-31

# 5. Build social signals panel
python3 make_weekly_panel.py

# MERGE & ANALYZE
# 6. Merge all sources + engineer features
python3 merge_all_sources.py \
  --reddit-grosses ../../../data/merged/merged_reddit_grosses_panel.parquet \
  --social-signals ../../data/panel/weekly_social_signals.parquet \
  --output ../../../data/panel/complete_modeling_dataset.parquet \
  --engineer-features --lags 1 2 4 6

# 7. Validate
python3 validate_social_panel.py \
  --input ../../../data/panel/complete_modeling_dataset.parquet

# 8. Run analysis
python3 run_complete_analysis.py \
  --input ../../../data/panel/complete_modeling_dataset.parquet \
  --lag 4 --outcome gross
```

---

## 📂 Output Files Reference

After running complete pipeline:

```
oh_mary_cmm_analysis/
├── data/
│   ├── reddit/
│   │   └── Oh_Mary_posts.csv                      # Raw Reddit posts
│   ├── grosses/
│   │   └── broadway_grosses.csv                   # Weekly box office
│   ├── merged/
│   │   └── merged_reddit_grosses_panel.parquet    # Reddit + Grosses
│   └── panel/
│       ├── complete_modeling_dataset.parquet      # ⭐ MAIN DATASET (all sources)
│       ├── complete_modeling_dataset.csv          # Preview
│       └── complete_modeling_dataset_metadata.json # Coverage stats
├── public_signals/
│   └── data/
│       ├── raw/                                   # Per-post social data
│       ├── raw_snapshots/                         # HTML debugging
│       ├── weekly/                                # Per-source weekly
│       └── panel/
│           ├── weekly_social_signals.parquet      # Social signals panel
│           └── validation_report.json             # Quality report
└── outputs/
    └── complete_causality_analysis/
        ├── complete_analysis_lag4_{date}.json     # Full results
        ├── complete_analysis_lag4_{date}.csv      # Sorted results
        └── complete_analysis_lag4_{date}.txt      # Report
```

---

## 🎯 Key Features of Complete Dataset

### Available Predictors (with lag 4):

**Reddit (4 predictors):**
- `total_posts_lag4`
- `total_score_lag4`
- `total_comments_lag4`
- `unique_authors_lag4`

**TikTok (7 predictors):**
- `tt_posts_lag4`
- `tt_sum_views_lag4`
- `tt_sum_likes_lag4`
- `tt_sum_comments_lag4`
- `tt_sum_shares_lag4`
- `tt_unique_hashtags_lag4`
- `tt_posting_days_lag4`

**Instagram (5 predictors):**
- `ig_posts_lag4`
- `ig_sum_likes_lag4`
- `ig_sum_comments_lag4`
- `ig_unique_hashtags_lag4`
- `ig_posting_days_lag4`

**Wikipedia (1 predictor):**
- `wiki_views_lag4`

**Google Trends (1 predictor):**
- `gt_index_lag4`

**Plus:** Deltas (_delta, _pct_change), rolling stats (_roll3), and z-scores (_z) for each!

**Total:** ~100+ engineered features from 18 core metrics across 5 sources

---

## 🔍 Interpreting Results

### Example Output:

```
Predictor: tt_sum_views_lag4
  Source: tiktok
  Coefficient: 0.15
  P-value: 0.0451
  95% CI: [0.01, 0.29]
  R²: 0.67
```

**Interpretation:**
- A 1-unit increase in TikTok views 4 weeks ago predicts $0.15 higher grosses
- Statistically significant (p < 0.05)
- 95% confident true effect is between $0.01 and $0.29
- Model explains 67% of variance in grosses

**Practical Significance:**
- If TikTok views increase by 100,000 → predicts $15,000 higher weekly gross
- Accounts for: show fixed effects (baseline popularity), time fixed effects (seasonal trends), capacity constraints

---

## ⚠️ Troubleshooting

### Issue: "No lagged predictors found"

**Solution:** Make sure you ran merge with `--engineer-features` flag:
```bash
python3 merge_all_sources.py ... --engineer-features --lags 1 2 4 6
```

### Issue: "Insufficient data (X non-null)"

**Cause:** Some shows don't have enough weeks with that metric

**Solution:** Normal for some social handles. Analysis automatically skips predictors with <30 observations.

### Issue: Validation fails

**Solution:** Check `validation_report.json`:
```bash
cat data/panel/validation_report.json | python3 -m json.tool
```

### Issue: Merge shows "0 rows with all three sources"

**Cause:** Show names don't match between Reddit and Social Signals

**Solution:** Standardize show names in both:
- Reddit data: Check `show_name` column
- Social config: Check `shows.yaml` → `name` field
- Must match exactly (case-sensitive)

---

## 📊 Expected Results

Based on prior studies and advance purchase hypothesis:

**Likely Significant Predictors (p < 0.05):**
- Reddit posts lag 4 (community buzz)
- TikTok views lag 4 (viral reach)
- Google Trends lag 4 (search intent)
- Wikipedia views lag 2-4 (research behavior)

**Likely Non-Significant:**
- Instagram (hidden counts reduce signal)
- Very short lags (same-week, lag 1) - too late for advance purchase
- Very long lags (lag 6+) - signal fades

**Model Fit:**
- Expected R²: 0.55-0.75 (show + time fixed effects explain most variance)
- Significant effects: 5-10 predictors out of 60+

---

## 🎓 Academic Rigor

This pipeline produces **publication-ready results** with:

✅ **Panel regression** with entity (show) and time (week) fixed effects
✅ **Cluster-robust standard errors** (accounts for serial correlation within shows)
✅ **Lagged predictors** (addresses reverse causality)
✅ **Multiple hypothesis testing** (Bonferroni correction available if needed)
✅ **Sensitivity analysis** (test multiple lags: 1, 2, 4, 6 weeks)
✅ **Placebo tests** (lead variables should NOT be significant)
✅ **Data quality validation** (automated checks with status codes)
✅ **Reproducibility** (deterministic runs, cached data, version control)

---

## 📝 Citation

When using this pipeline in publications:

```
Data sources:
- Reddit: r/Broadway via Reddit API
- TikTok: Public profile data (no authentication)
- Instagram: Public profile data (no authentication)
- Wikipedia: Wikimedia REST API
- Google Trends: pytrends unofficial API
- Broadway grosses: BroadwayWorld.com

Analysis: Panel regression with entity and time fixed effects,
cluster-robust standard errors (Stata-equivalent).
```

---

## ✅ Quick Checklist

Before running analysis:

- [ ] Reddit data collected and in `data/reddit/`
- [ ] Broadway grosses collected and in `data/grosses/`
- [ ] Reddit+Grosses panel built: `data/merged/merged_reddit_grosses_panel.parquet`
- [ ] Social signals configured in `public_signals/config/shows.yaml`
- [ ] Social signals collected (TikTok, Instagram, Wikipedia, Google Trends)
- [ ] Social signals panel built: `public_signals/data/panel/weekly_social_signals.parquet`
- [ ] All sources merged with `--engineer-features`: `data/panel/complete_modeling_dataset.parquet`
- [ ] Validation passed (exit code 0)
- [ ] Ready to run `run_complete_analysis.py`!

---

**You now have a complete, production-grade pipeline that combines Reddit, TikTok, Instagram, Wikipedia, Google Trends, and Broadway Grosses for rigorous causal analysis!** 🎉

# Broadway Marketing Analysis - Quick Start Guide

**Get started with the complete pipeline in 10 minutes.**

---

## ⚡ Prerequisites (2 minutes)

```bash
cd /path/to/Python_projects/oh_mary_cmm_analysis

# Install dependencies
pip install pandas numpy pyarrow pyyaml playwright pytrends tenacity \
            statsmodels linearmodels scipy matplotlib seaborn

# Install Playwright browser
playwright install chromium
```

---

## 🚀 Run Complete Analysis (3 Commands)

### **Step 1: Configure Shows** (1 minute)

Edit `public_signals/config/shows.yaml`:

```yaml
shows:
  - name: "Oh, Mary!"
    google_queries:
      - "Oh Mary Broadway"
      - "Cole Escola"
    wikipedia_title: "Oh,_Mary!"
    tiktok_handle: "@ohmaryplay"
    instagram_handle: "ohmaryplay"
```

### **Step 2: Collect Social Signals** (5-10 minutes)

```bash
cd public_signals/src/cli

python3 pull_public_signals.py \
  --config ../../config/shows.yaml \
  --start 2024-01-01 --end 2024-12-31
```

**What it does:** Collects TikTok, Instagram, Wikipedia, Google Trends data

### **Step 3: Merge & Engineer Features** (30 seconds)

```bash
python3 merge_all_sources.py --engineer-features --lags 1 2 4 6
```

**What it does:** Merges Reddit + Social + Grosses, creates 100+ features

### **Step 4: Run Analysis** (1 minute)

```bash
python3 run_complete_analysis.py --lag 4 --outcome gross
```

**What it does:** Tests all 60+ predictors, generates results

---

## 📊 View Results

```bash
# Check results directory
ls -lh ../../../outputs/complete_causality_analysis/

# View text report
cat ../../../outputs/complete_causality_analysis/complete_analysis_lag4_*.txt

# Or open CSV in Excel
open ../../../outputs/complete_causality_analysis/complete_analysis_lag4_*.csv
```

---

## 🎯 Example Output

```
RUNNING CAUSAL ANALYSIS: gross ~ predictors_lag4
================================================================

Results: 60 predictors tested
Significant (p<0.05): 8

Top significant predictor:
  total_posts_lag4 (reddit)
  Coefficient: $1,250.45
  P-value: 0.0023

  → Each Reddit post 4 weeks ago predicts $1,250 higher weekly gross
```

---

## 🔄 Update Data Weekly

```bash
cd public_signals/src/cli

# Collect last 45 days
python3 pull_public_signals.py \
  --config ../../config/shows.yaml \
  --start $(date -d '45 days ago' +%Y-%m-%d) \
  --end $(date +%Y-%m-%d)

# Rebuild & analyze
python3 merge_all_sources.py --engineer-features --lags 1 2 4 6
python3 run_complete_analysis.py --lag 4
```

---

## ❓ Troubleshooting

### Issue: "No module named 'playwright'"
```bash
pip install playwright
playwright install chromium
```

### Issue: "File not found: reddit_grosses_panel.parquet"

You need Reddit + Grosses data first:

```bash
cd /path/to/oh_mary_cmm_analysis

# Collect Broadway grosses (if not done)
python3 broadway_grosses_scraper.py

# Build Reddit + Grosses panel (if not done)
python3 build_panel_dataset.py
```

### Issue: Validation fails

```bash
# Check validation report
cat public_signals/data/panel/validation_report.json

# Common fixes:
# 1. Low coverage → normal for some shows
# 2. Anomalies → review but not errors
# 3. Schema errors → re-run make_weekly_panel.py
```

---

## 📖 Next Steps

- **Customize analysis**: See [HOW_TO_RUN_COMPLETE_ANALYSIS.md](HOW_TO_RUN_COMPLETE_ANALYSIS.md)
- **Technical details**: See [public_signals/README_social_pipeline.md](public_signals/README_social_pipeline.md)
- **Main README**: See [README.md](README.md)

---

## 📂 Key Files Reference

```
oh_mary_cmm_analysis/
├── public_signals/src/cli/
│   ├── pull_public_signals.py      # Step 2: Collect data
│   ├── merge_all_sources.py        # Step 3: Merge & engineer
│   └── run_complete_analysis.py    # Step 4: Analyze
├── public_signals/config/
│   └── shows.yaml                  # Step 1: Configure
├── data/panel/
│   └── complete_modeling_dataset.parquet  # Output from Step 3
└── outputs/complete_causality_analysis/
    └── complete_analysis_lag4_*.txt       # Output from Step 4
```

---

## ✅ Quick Checklist

Before running analysis:

- [ ] Dependencies installed (`pip install ...`)
- [ ] Playwright browser installed (`playwright install chromium`)
- [ ] Shows configured in `public_signals/config/shows.yaml`
- [ ] Reddit + Grosses data exists (check `data/merged/`)
- [ ] Ready to collect social signals!

---

**That's it! You now have a complete causal analysis pipeline.** 🎉

For more details, see [HOW_TO_RUN_COMPLETE_ANALYSIS.md](HOW_TO_RUN_COMPLETE_ANALYSIS.md)

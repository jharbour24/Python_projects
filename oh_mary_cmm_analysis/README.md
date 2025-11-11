# Broadway Marketing Analysis: Complete Causal Inference Pipeline

**Publication-ready analysis of how social media engagement and public interest predict Broadway box office performance.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 Research Question

**Does social media engagement and public interest at time t-k predict Broadway box office grosses at time t?**

We test the **advance purchase hypothesis**: audiences engage with content ~4 weeks before attending shows, meaning early engagement should predict future box office performance.

---

## 📊 Data Sources

This pipeline integrates **6 comprehensive data sources**:

| Source | Metrics | Frequency | Coverage |
|--------|---------|-----------|----------|
| **Reddit** (r/Broadway) | Posts, comments, score, unique authors | Weekly | High |
| **TikTok** | Views, likes, comments, shares, hashtags | Weekly | Medium |
| **Instagram** | Posts, likes, comments, reels | Weekly | Medium |
| **Wikipedia** | Daily pageviews | Daily → Weekly | High |
| **Google Trends** | Search interest index (0-100) | Weekly | High |
| **Broadway Grosses** | Revenue, capacity, attendance, ticket price | Weekly | High |

**Total predictors:** 60+ lagged engagement metrics across 5 social sources

---

## 🏗️ Architecture

```
oh_mary_cmm_analysis/
├── broadway_grosses_scraper.py          # Collect weekly box office data
├── build_panel_dataset.py               # Build Reddit + Grosses panel
├── marketing_science_analysis.py        # Statistical comparison (successful vs unsuccessful)
├── reddit_grosses_correlation_analysis.py  # Reddit → Grosses correlation
├── run_lagged_causality_analysis.py     # Panel regression with fixed effects
├── why_campaigns_succeed_analysis.py    # Qualitative analysis
│
├── public_signals/                      # Social signals collection system
│   ├── src/
│   │   ├── common/                      # Utilities (net, snapshots, timebins)
│   │   ├── sources/                     # Data collectors
│   │   │   ├── google_trends.py
│   │   │   ├── wikipedia.py
│   │   │   ├── tiktok_public.py
│   │   │   └── instagram_public.py
│   │   ├── aggregation/                 # Weekly aggregation + schema
│   │   ├── features/                    # Feature engineering (lags, deltas, etc.)
│   │   ├── quality/                     # Data validation
│   │   └── cli/                         # Command-line tools
│   │       ├── pull_public_signals.py   # Collect all social data
│   │       ├── make_weekly_panel.py     # Build social panel
│   │       ├── merge_all_sources.py     # Merge Reddit + Social + Grosses
│   │       ├── build_model_ready_social.py  # Feature engineering
│   │       ├── validate_social_panel.py     # Data quality checks
│   │       └── run_complete_analysis.py     # Complete causal analysis
│   ├── config/
│   │   └── shows.yaml                   # Show configuration
│   └── README_social_pipeline.md        # Technical documentation
│
├── analysis/                            # Analysis utilities
├── models/                              # Statistical models
├── data/                                # Data storage
│   ├── reddit/                          # Reddit posts
│   ├── grosses/                         # Broadway grosses
│   ├── merged/                          # Reddit + Grosses panel
│   └── panel/                           # Complete merged dataset
├── outputs/                             # Analysis outputs
│
├── README.md                            # This file
├── QUICKSTART.md                        # Quick start guide
└── HOW_TO_RUN_COMPLETE_ANALYSIS.md      # Detailed step-by-step guide
```

---

## ⚡ Quick Start

### **Prerequisites**

```bash
# Clone repository
cd /path/to/Python_projects/oh_mary_cmm_analysis

# Install dependencies
pip install pandas numpy pyarrow pyyaml playwright pytrends tenacity \
            statsmodels linearmodels scipy matplotlib seaborn

# Install Playwright browser (for TikTok/Instagram)
playwright install chromium
```

### **Run Complete Pipeline (3 Commands)**

```bash
cd public_signals/src/cli

# 1. Collect all social signals (TikTok, Instagram, Wikipedia, Google Trends)
python3 pull_public_signals.py \
  --config ../../config/shows.yaml \
  --start 2024-01-01 --end 2024-12-31

# 2. Merge all sources (Reddit + Social + Grosses) + engineer features
python3 merge_all_sources.py --engineer-features --lags 1 2 4 6

# 3. Run complete causal analysis
python3 run_complete_analysis.py --lag 4 --outcome gross
```

**That's it!** Results will be in `outputs/complete_causality_analysis/`

See **[QUICKSTART.md](QUICKSTART.md)** for detailed instructions.

---

## 📖 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[HOW_TO_RUN_COMPLETE_ANALYSIS.md](HOW_TO_RUN_COMPLETE_ANALYSIS.md)** - Complete step-by-step guide
- **[public_signals/README_social_pipeline.md](public_signals/README_social_pipeline.md)** - Technical documentation for social signals system

---

## 🔬 Methodology

### **Statistical Approach**

- **Panel Regression** with entity (show) and time (week) fixed effects
- **Cluster-Robust Standard Errors** (accounts for serial correlation within shows)
- **Lagged Predictors** (temporal precedence for causal inference)
- **Control Variables** (capacity constraints, preview periods)

### **Model Specification**

```
gross_it = β₀ + β₁·engagement_i(t-k) + α_i + γ_t + ε_it

where:
  gross_it        = Weekly gross for show i at time t
  engagement_i(t-k) = Engagement metric k weeks prior
  α_i             = Show fixed effects (baseline popularity)
  γ_t             = Time fixed effects (seasonal trends)
  ε_it            = Error term (clustered by show)
```

### **Default Configuration**

- **Primary lag:** 4 weeks (advance purchase hypothesis)
- **Sensitivity analysis:** 1, 2, 4, 6 week lags
- **Placebo tests:** Lead variables (should NOT be significant)
- **Significance threshold:** p < 0.05
- **Minimum observations:** 30 per predictor

---

## 📊 Example Results

```
RUNNING CAUSAL ANALYSIS: gross ~ predictors_lag4
================================================================

Results: 60 predictors tested
Significant (p<0.05): 8

Top 3 Significant Predictors:

1. total_posts_lag4 (reddit)
   Coefficient: $1,250.45
   P-value: 0.0023
   95% CI: [$456.78, $2,044.12]
   Interpretation: Each additional Reddit post 4 weeks ago predicts
                   $1,250 higher weekly gross

2. tt_sum_views_lag4 (tiktok)
   Coefficient: $0.15
   P-value: 0.0451
   95% CI: [$0.01, $0.29]
   Interpretation: Each 1,000 additional TikTok views 4 weeks ago
                   predicts $150 higher weekly gross

3. gt_index_lag4 (google_trends)
   Coefficient: $8,500.23
   P-value: 0.0089
   95% CI: [$2,340.56, $14,659.90]
   Interpretation: 10-point increase in Google Trends 4 weeks ago
                   predicts $85,000 higher weekly gross
```

---

## 🎓 Academic Rigor

This pipeline produces **publication-ready results** suitable for marketing and entertainment journals:

✅ **Causal Inference Design**
- Lagged predictors establish temporal precedence
- Fixed effects control for unobserved heterogeneity
- Cluster-robust SEs account for autocorrelation

✅ **Data Quality**
- Automated validation with anomaly detection
- Deduplication by post ID
- Coverage metrics (must be ≥60%)
- Schema enforcement with type checking

✅ **Reproducibility**
- Deterministic runs with timestamps
- HTML snapshots for debugging
- Cached API requests
- Version-controlled code

✅ **Robustness**
- Multiple data sources (triangulation)
- Sensitivity analysis across lag specifications
- Placebo tests with lead variables
- Multiple hypothesis testing adjustments available

---

## 📂 Key Files

### **Data Collection**

- `broadway_grosses_scraper.py` - Scrape weekly Broadway box office data from BroadwayWorld
- `public_signals/src/cli/pull_public_signals.py` - Collect TikTok, Instagram, Wikipedia, Google Trends

### **Data Processing**

- `build_panel_dataset.py` - Merge Reddit with Broadway Grosses
- `public_signals/src/cli/make_weekly_panel.py` - Build social signals panel
- `public_signals/src/cli/merge_all_sources.py` - Merge all sources + feature engineering

### **Analysis**

- `run_lagged_causality_analysis.py` - Panel regression (Reddit + Grosses only)
- `public_signals/src/cli/run_complete_analysis.py` - Complete analysis (all sources)
- `marketing_science_analysis.py` - Statistical comparison (successful vs unsuccessful campaigns)
- `why_campaigns_succeed_analysis.py` - Qualitative analysis of success factors

### **Validation**

- `public_signals/src/cli/validate_social_panel.py` - Data quality checks with exit codes

---

## 🔧 Configuration

### **Add Shows**

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

  - name: "Your Show Name"
    google_queries:
      - "Your Show Broadway"
    tiktok_handle: "@yourshow"
    instagram_handle: "yourshow"
```

### **Customize Analysis**

```bash
# Different lag period
python3 run_complete_analysis.py --lag 2

# Different outcome variable
python3 run_complete_analysis.py --outcome capacity_pct

# Custom feature engineering
python3 merge_all_sources.py --engineer-features --lags 1 3 5 --no-deltas
```

---

## 📈 Output Files

After running the complete pipeline:

```
data/panel/
├── complete_modeling_dataset.parquet          # Main dataset (all sources)
├── complete_modeling_dataset_metadata.json    # Coverage statistics

outputs/complete_causality_analysis/
├── complete_analysis_lag4_{timestamp}.json    # Full results
├── complete_analysis_lag4_{timestamp}.csv     # Sorted by p-value
└── complete_analysis_lag4_{timestamp}.txt     # Human-readable report

public_signals/data/
├── raw/                                       # Per-post raw data
├── raw_snapshots/                             # HTML for debugging
├── weekly/                                    # Per-source weekly aggregates
└── panel/                                     # Social signals panel
```

---

## ⚠️ Known Limitations

1. **TikTok/Instagram** - Public data only (no authentication)
   - Instagram may hide exact counts
   - TikTok selectors may change (HTML snapshots enable quick fixes)

2. **Google Trends** - Low search volume returns zeros
   - Use multiple related queries per show
   - Aggregate as mean across queries

3. **Wikipedia** - Article title auto-detection may fail
   - Manually specify `wikipedia_title` in config if needed

4. **Sample Size** - Need sufficient weeks per show
   - Minimum 30 observations per predictor
   - More shows = more statistical power

See **[HOW_TO_RUN_COMPLETE_ANALYSIS.md](HOW_TO_RUN_COMPLETE_ANALYSIS.md)** for troubleshooting.

---

## 🤝 Contributing

This is a research project. If you use this pipeline:

1. **Cite data sources** appropriately in publications
2. **Respect rate limits** and robots.txt
3. **Share findings** (open science principles)
4. **Report issues** with HTML snapshots attached

---

## 📄 License

MIT License - See LICENSE file for details

When using in publications, please cite:
```
Broadway Marketing Analysis Pipeline
GitHub: https://github.com/yourusername/oh_mary_cmm_analysis
Year: 2025
```

---

## 📞 Support

- **Quick Start**: See [QUICKSTART.md](QUICKSTART.md)
- **Detailed Guide**: See [HOW_TO_RUN_COMPLETE_ANALYSIS.md](HOW_TO_RUN_COMPLETE_ANALYSIS.md)
- **Technical Docs**: See [public_signals/README_social_pipeline.md](public_signals/README_social_pipeline.md)
- **Issues**: Check validation reports and HTML snapshots

---

## 🎯 Summary

**This pipeline enables publication-ready causal analysis of how social media engagement predicts Broadway box office performance.**

Key features:
- ✅ 6 data sources (Reddit, TikTok, Instagram, Wikipedia, Google Trends, Broadway Grosses)
- ✅ 60+ lagged predictors with feature engineering
- ✅ Panel regression with fixed effects and cluster-robust SEs
- ✅ Automated data quality validation
- ✅ Production-grade error handling and retry logic
- ✅ Complete documentation and reproducibility

**Get started:** See [QUICKSTART.md](QUICKSTART.md)

---

*Built for rigorous causal inference in entertainment marketing research.*

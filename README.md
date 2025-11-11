# Broadway Digital Movement → Sales Pipeline

**Reproducible public-data analysis testing whether digital movement density predicts sales velocity for Broadway shows**

## Overview

This repository implements a fully reproducible pipeline to test the **Cultural Movement Marketing (CMM)** thesis: that higher digital movement density (engagement depth and persistence across social platforms) predicts faster and more durable sales velocity for Broadway shows.

### Hypothesis

Higher digital movement density → Stronger sales velocity

Where:
- **Movement Density Score (MDS)**: Composite metric of social engagement across Instagram, TikTok, Reddit, and Google Trends
- **Sales Velocity (SV)**: Composite metric of box office performance from public grosses, ticket prices, and discount availability

### Study Design

- **Cohorts:**
  - **CMM Depth**: Hamilton, Beetlejuice, Hadestown, Six, Maybe Happy Ending, Oh Mary!
  - **Broad Appeal**: Betty Boop, Smash, Bad Cinderella, Spamalot

- **Timeline**: Aligned by relative weeks (4 weeks before opening → 12 weeks after opening)

- **Statistical Tests**:
  1. Pearson and Spearman correlations
  2. OLS regression with show and week fixed effects
  3. Lead-lag analysis (does MDS predict future SV?)
  4. Robustness: exclude Tony weeks, cohort-specific, PCA-based MDS

## Repository Structure

```
.
├── config/
│   └── shows.yaml              # Show metadata, handles, opening dates
├── data/
│   ├── raw/                    # Cached HTML/JSON from scrapers
│   └── processed/              # Cleaned CSVs and scores
├── notebooks/
│   ├── 01_collect.ipynb        # Data collection from all sources
│   ├── 02_build_scores.ipynb  # Feature extraction and scoring
│   └── 03_analysis.ipynb       # Statistical analysis and plots
├── src/
│   ├── scrapers/               # Data collection modules
│   ├── processing/             # Feature extraction and scoring
│   └── analysis/               # Statistical models and plots
├── outputs/                    # Generated plots and reports
├── README.md                   # This file
├── METHODOLOGY.md              # Detailed methodology
└── requirements.txt            # Python dependencies
```

## Quick Start

### Prerequisites

- Python 3.9+
- pip

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Execution

Run notebooks in order:

```bash
# 1. Collect data (takes ~30-60 min with rate limiting)
jupyter notebook notebooks/01_collect.ipynb

# 2. Build scores (takes ~5 min)
jupyter notebook notebooks/02_build_scores.ipynb

# 3. Run analysis (takes ~2 min)
jupyter notebook notebooks/03_analysis.ipynb
```

## Data Sources & Compliance

All data sources are **public-only** and comply with ToS:

- Instagram (public profiles)
- TikTok (hashtag data)
- Reddit (r/Broadway via JSON API)
- Google Trends (pytrends)
- BroadwayWorld grosses
- SeatGeek/TodayTix prices
- BroadwayBox discounts

**Rate Limiting**: 0.5-2 sec between requests per source

**Caching**: 7-day local cache to minimize requests

## Key Metrics

### Movement Density Score (MDS)

Weighted sum of z-scored social engagement features:
- Instagram: comments/post, comment-to-like ratio
- TikTok: hashtag video count, UGC share
- Reddit: thread count, median comments
- Google Trends: 4-week slope, volatility

### Sales Velocity (SV)

Weighted sum of z-scored sales proxy slopes:
- BroadwayWorld: grosses slope, attendance slope
- Ticket prices: price slope
- Availability: listings slope (negative)
- Discounts: discount count slope (negative)

## Limitations

**Data Quality:**
- Instagram/TikTok: Limited public access
- Sales Proxies: Not actual ticket sales
- Missing Shows: Betty Boop/Smash may not have opened

**Statistical:**
- Correlation ≠ Causation
- Small sample (N=10 shows)
- Confounds: marketing, reviews, stars

See **METHODOLOGY.md** for detailed validity discussion.

## Configuration

Edit `config/shows.yaml` to update:
- Show metadata and handles
- Opening dates (marked TODO)
- Rate limits

## License

MIT License

---

**Last Updated:** 2025-01-11
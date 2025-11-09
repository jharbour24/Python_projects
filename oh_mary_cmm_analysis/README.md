# Oh Mary! Cultural Movement Marketing (CMM) Analysis

A computational sociology study analyzing audience discourse patterns around the Broadway show "Oh Mary!" to measure Cultural Movement Marketing effects.

## 🚀 Quick Start

**Collect real data and run analysis in ~1 hour:**

```bash
cd oh_mary_cmm_analysis
python collect_all_data.py
```

This interactive tool will guide you through:
1. ✅ Reddit API setup (10 min, automated)
2. ✅ TikTok manual collection (30 min, safe, no login)
3. ✅ Instagram manual collection (30 min, safe, no login)
4. ✅ Run analysis → get results!

**See [QUICKSTART.md](QUICKSTART.md) for detailed instructions**

---

## Research Question

Does the audience speak as if "Oh Mary!" is a movement, identity space, or necessity — rather than just entertainment?

## Methodology

- **Data Sources**: TikTok, Instagram, Reddit (public data only)
- **Date Range**: Last 12 months
- **Analysis Framework**: Cultural Movement Marketing (CMM)
- **Methods**: NLP, discourse analysis, network analysis, weak supervision

## Core Metrics

1. **Movement Sentiment Score (MSS)**: Engagement lift with collective language
2. **Identity Resonance Index (IRI)**: Frequency of "felt seen/represented" language
3. **Evangelism Ratio (ER)**: % urging others to attend
4. **Repeat Attendance Signal (RAS)**: % referencing 2+ viewings
5. **Belonging Intensity Score (BIS)**: NLP measure of belonging language
6. **Gatekeeping & Insider Markers (GIM)**: Inside jokes, ritual talk
7. **Community Formation Signals (CFS)**: Evidence of fan communities
8. **Mimetic Propagation Index (MPI)**: Meme/audio trend persistence

## Project Structure

```
oh_mary_cmm_analysis/
├── config/
│   └── config.yaml          # Analysis configuration
├── data/
│   ├── raw/                 # Raw scraped data
│   └── processed/           # Processed datasets
├── src/
│   ├── scrapers/            # Platform scrapers
│   ├── analysis/            # NLP and metrics
│   └── utils/               # Helper functions
└── outputs/
    ├── reports/             # Final reports
    └── visualizations/      # Charts and graphs
```

## Installation

```bash
pip install -r requirements.txt
```

## Data Collection

### Interactive Guide (Recommended)
```bash
python collect_all_data.py
```

### Individual Tools
```bash
# Reddit API setup (10 min)
python setup_reddit.py

# TikTok manual collection (30 min)
python collect_tiktok.py

# Instagram manual collection (30 min)
python collect_instagram.py
```

### Important: Safe & Compliant Methods
- ✅ Reddit: Official API (no password required)
- ✅ TikTok: Manual collection (no login required)
- ✅ Instagram: Public viewers like Picuki.com (no login required)
- ❌ Never share login credentials for automation

## Usage

Once data is collected:

```bash
python src/main.py
```

## Compliance

- Public data only; no login-required scraping
- All claims linked to URLs + timestamps
- Uncertainty documented via bootstrap CIs
- Counter-signals (negatives, critiques) included

## Output Files

- `report.md`: Main findings with evidence links
- `audience_discourse.csv`: Post-level labels + scores
- `memes_catalog.csv`: Memetic motifs + viral half-life
- `community_signals.csv`: Referral, repeat, ritual behaviors
- `assumption_log.md`: Methodological decisions and limitations

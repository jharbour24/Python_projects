# Oh Mary! Cultural Movement Marketing (CMM) Analysis

A computational sociology study analyzing audience discourse patterns around the Broadway show "Oh Mary!" to measure Cultural Movement Marketing effects.

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

## Usage

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

# Broadway Producer & Tony Awards Analysis - Usage Guide

## Overview
This project analyzes the relationship between Broadway producers and Tony Award success (2010-2025), including performance metrics and financial data.

## Project Components

### 1. Data Collection Scripts
- **`add_performances_to_tony_data.py`** - **NEW** Independently scrapes performance counts for all shows from IBDB
- **`browser_ibdb_scraper.py`** - Scrapes producer data from IBDB for all Broadway shows
- **`broadway_grosses_scraper.py`** - Scrapes weekly grosses data from BroadwayWorld (2010-present)

### 2. Reference Data
- **`REVIVALS_DICTIONARY.py`** - Comprehensive dictionary of 161 Broadway revivals with accurate years
- **`raw/all_broadway_shows_2010_2025.csv`** - Complete list of 536 Broadway shows to scrape
- **`raw/tony_winners_2010_2025.csv`** - List of 50 Tony Award Best Musical/Play winners

### 3. Analysis Scripts
- **`analysis/producer_tony_analysis.py`** - Comprehensive statistical analysis including:
  - Producer count vs Tony win correlation
  - Individual producer success rates
  - Performance metrics (longest-running shows)
  - Financial metrics (ticket prices, gross revenues)
  - Yearly trends and 5-year predictions
  - Visualizations and charts

## Step-by-Step Workflow

### **NEW RECOMMENDED WORKFLOW** (Independent Performance Scraping)

### Step 1: Add Performance Data to Tony Outcomes
```bash
python3 add_performances_to_tony_data.py
```

**What it does:**
- Independently scrapes number of performances and production year for all 535 shows
- Adds data directly to `data/tony_outcomes.csv`
- Creates `data/tony_outcomes_with_performances.csv`
- **IMPORTANT:** You must be present to solve CAPTCHAs manually
- Infinite retry loop - won't stop until 100% complete

**Features:**
- 4-second delay between shows for CAPTCHA solving
- Saves progress after each show (resumable)
- Automatically includes "revival" in IBDB searches

**Expected duration:** 30-60 minutes (with CAPTCHA solving)

**Why this first?**
- More reliable than extracting from producer scraper
- Can check if show counts are correct (e.g., Romeo + Juliet 2011 vs 2024)
- Provides performance data even if you don't need producer analysis yet

### Step 2 (Optional): Scrape Broadway Grosses Data
```bash
python3 broadway_grosses_scraper.py
```

**What it does:**
- Scrapes weekly grosses data from BroadwayWorld for 2010-present
- Collects: gross revenue, ticket prices, attendance, capacity %
- Output: `data/broadway_grosses_2010_present.xlsx`

**Expected duration:** 15-30 minutes

### Step 3 (Optional): Scrape IBDB Producer Data
```bash
python3 browser_ibdb_scraper.py
```

**What it does:**
- Opens Chrome browser (Safari also supported)
- Searches IBDB for each of the 536 Broadway shows
- Extracts producer names and counts
- **IMPORTANT:** You must be present to solve CAPTCHAs manually
- Output: `data/broadway_producer_data.xlsx`

**Features:**
- 4-second delay between shows for CAPTCHA solving
- Infinite retry loop - won't stop until all shows are successfully scraped
- Progress saved after each show (can resume if interrupted)

**Expected duration:** 30-60 minutes (with CAPTCHA solving)

**Note:** Only run this if you need producer-specific analysis

### Step 4: Run Complete Analysis
```bash
python3 analysis/producer_tony_analysis.py
```

**What it does:**
- Loads Tony outcomes (with performance data) and optionally producer/grosses data
- Runs analysis based on available data:
  - **Performance Analysis** (if you ran Step 1) - show lengths, production years
  - **Producer Analysis** (if you ran Step 3) - Tony win rates, producer success
  - **Financial Analysis** (if you ran Step 2) - ticket prices, gross revenues
- Generates visualizations and charts (when producer data available)
- Saves results to CSV files

**Flexible Workflow:**
- Works with any combination of data sources
- Gracefully skips analyses for missing data
- Warns you about what's missing and how to get it

**Outputs:**
- `data/producer_tony_analysis.csv` - Complete merged dataset
- `analysis/results/producer_success_analysis.csv` - Individual producer stats
- `analysis/results/producer_financial_analysis.csv` - Financial metrics
- `analysis/results/yearly_producer_trends.csv` - Yearly trends
- `analysis/results/producer_count_predictions.csv` - 5-year forecast
- `analysis/results/*.png` - 10+ visualization charts
- `analysis/results/analysis_summary.txt` - Executive summary
- `logs/analysis.log` - Detailed output log

**Expected duration:** 1-2 minutes

## Key Findings (Analysis Tests)

The analysis will answer these research questions:

### 1. Producer Count vs Tony Success
- Do shows with more producers have higher odds of winning a Tony?
- Statistical significance testing (logistic regression, t-tests)

### 2. Individual Producer Success
- **Top 5 by Tony Win Rate** - Which producers have the highest % of shows winning?
- **Top 5 by Average Performances** - Which producers have the longest-running shows?
- **Top 5 by Total Performances** - Which producers have the most Broadway impact?

### 3. Financial Performance
- **Top 5 by Average Ticket Price** - Which producers command premium pricing?
- **Top 5 by Average Gross Per Show** - Which producers have highest average revenues?
- **Top 5 by Total Gross** - Which producers have generated the most total revenue?

### 4. Temporal Trends
- How has the number of producers per show changed over time (2010-2025)?
- 5-year prediction: What will producer counts look like in 2025-2030?

## File Structure

```
/home/user/Python_projects/
├── browser_ibdb_scraper.py           # Main IBDB scraper
├── broadway_grosses_scraper.py       # Grosses scraper
├── REVIVALS_DICTIONARY.py            # 161 revivals with years
├── USAGE_GUIDE.md                    # This file
├── raw/
│   ├── all_broadway_shows_2010_2025.csv    # 536 shows to scrape
│   └── tony_winners_2010_2025.csv          # 50 Tony winners
├── data/
│   ├── broadway_producer_data.xlsx         # Scraped producer data
│   ├── broadway_grosses_2010_present.xlsx  # Scraped grosses data
│   └── producer_tony_analysis.csv          # Merged analysis dataset
├── analysis/
│   ├── producer_tony_analysis.py           # Main analysis script
│   └── results/
│       ├── producer_success_analysis.csv
│       ├── producer_financial_analysis.csv
│       ├── yearly_producer_trends.csv
│       ├── producer_count_predictions.csv
│       ├── analysis_summary.txt
│       └── *.png                           # Visualization charts
└── logs/
    └── analysis.log                        # Detailed analysis output
```

## Requirements

### Python Packages
```bash
pip install selenium pandas openpyxl xlsxwriter beautifulsoup4 lxml requests
pip install matplotlib seaborn scipy scikit-learn statsmodels
```

### Browsers
- Chrome or Safari (for Selenium automation)
- ChromeDriver or SafariDriver must be available in PATH

## Troubleshooting

### IBDB Scraper Issues

**Problem:** CAPTCHAs blocking Google search
- **Solution:** Wait for the 15-second pause and solve manually
- The script will retry automatically

**Problem:** Wrong production found (original instead of revival)
- **Solution:** Already handled - script adds "revival" to all searches
- If issues persist, check REVIVALS_DICTIONARY.py for accuracy

**Problem:** Co-producers not being captured
- **Solution:** Fixed in latest version - all producer categories included

### Grosses Scraper Issues

**Problem:** Network errors or timeouts
- **Solution:** Script will continue and skip failed weeks
- Check output for any error messages

### Analysis Issues

**Problem:** "File not found" error
- **Solution:** Make sure you've run the scrapers first
- Check that files exist in `data/` directory

**Problem:** Financial analysis not running
- **Solution:** Ensure `broadway_grosses_2010_present.xlsx` exists
- Financial analysis is optional - will skip gracefully if missing

## Notes

- **Data Currency:** Scraper uses date range 2010..2025 in Google search
- **Revival Accuracy:** REVIVALS_DICTIONARY has been manually curated for accuracy
- **CAPTCHA Solving:** You must be present during IBDB scraping
- **Retry Logic:** IBDB scraper will retry failed shows indefinitely until 100% complete
- **Data Quality:** Analysis filters out shows with unknown theaters/names

## Questions or Issues?

Check the logs:
- IBDB Scraper: Console output shows real-time progress
- Analysis: `logs/analysis.log` for detailed statistical output
- Summary: `analysis/results/analysis_summary.txt` for executive overview

## Next Steps

After running all scripts, you can:
1. Review `analysis/results/analysis_summary.txt` for key findings
2. Examine CSV files for detailed metrics
3. View PNG charts for visual insights
4. Check `logs/analysis.log` for full statistical output

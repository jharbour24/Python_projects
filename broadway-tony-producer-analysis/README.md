# Broadway Tony Producer Analysis

**Research Question:** What is the relationship between the number of producers on a Broadway show and:
1. Tony Award nominations and wins
2. Weekly Broadway grosses
3. Show run length (survival)

**Time Period:** 2010-2011 season through present

---

## Overview

This is a reproducible research pipeline that:
- Collects data on Broadway shows, Tony Awards, producer credits, and weekly grosses
- Builds cleaned analytical datasets
- Runs statistical models (logistic regression, count models, panel regression, survival analysis)
- Produces transparent, well-documented results

**Key Principle:** No fabricated data. When sources are unavailable, the code creates stubs with clear TODOs.

---

## Directory Structure

```
broadway-tony-producer-analysis/
├── README.md                   # This file
├── requirements.txt            # Python dependencies
├── data_sources.md            # Documentation of all data sources
├── config.py                  # Configuration and constants
│
├── data/
│   ├── raw/                   # Raw scraped/downloaded data
│   ├── processed/             # Cleaned master tables (shows.csv, etc.)
│   ├── scrape_tonys.py       # Tony Awards scraper
│   ├── scrape_producers.py   # Producer counts from IBDB/Playbill
│   ├── get_grosses.py        # Weekly grosses collector
│   └── build_master.py       # Merge all sources into master tables
│
├── utils/
│   ├── matching.py           # Title normalization & fuzzy matching
│   ├── date_helpers.py       # Date parsing & season computation
│   └── logging_config.py     # Structured logging
│
├── analysis/
│   └── tony_producers_analysis.ipynb  # Main analysis notebook
│
└── output/
    ├── tables/               # Model output tables (CSV)
    ├── figures/              # Plots & visualizations
    └── results_summary.md    # Narrative summary (generated)
```

---

## Installation

### Requirements
- Python 3.9 or higher
- Internet connection (for scraping)

### Setup

1. **Clone or download this repository**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation:**
   ```bash
   python -c "import pandas, statsmodels, lifelines; print('All dependencies installed!')"
   ```

---

## Usage

### Step 1: Scrape Tony Awards Data

```bash
cd data
python scrape_tonys.py
```

**What it does:**
- Scrapes Tony nominations and wins from Wikipedia (2011-present)
- Creates `data/raw/tony_nominations_raw.csv`
- Creates `data/raw/tony_outcomes_aggregated.csv`

**Expected output:** ~300-500 show records

**Note:** If Wikipedia structure changes, this may fail gracefully with warnings.

---

### Step 2: Scrape Producer Counts

```bash
python scrape_producers.py
```

**What it does:**
- For each Tony-nominated show, searches IBDB for producer credits
- Parses producer names and counts (total, lead, co-producers)
- Creates `data/raw/producers_raw.csv` and `data/raw/producers_clean.csv`

**Expected output:** Producer counts for most shows (some may fail if IBDB page unavailable)

**Important:** IBDB scraping may be slow due to rate limiting. Be patient.

**Known issues:**
- IBDB structure may vary; some shows may not match
- Producer name parsing is heuristic-based

---

### Step 3: Collect Weekly Grosses Data

```bash
python get_grosses.py
```

**What it does:**
- Scrapes weekly grosses from Broadway World (2010-present)
- Collects gross revenue, attendance, capacity%, ticket prices
- Includes comprehensive theater name normalization
- Computes week-over-week changes
- Creates `data/raw/broadway_world_grosses_full.csv`
- Creates `data/processed/weekly_grosses_preliminary.csv`

**Expected output:** 50,000+ weekly records covering hundreds of shows

**Data collected:**
- Weekly gross revenue
- Attendance and capacity percentage
- Average and top ticket prices
- Number of performances
- Theater name and seating capacity

**Expected runtime:** 15-30 minutes (scraping from 2010-present with rate limiting)

**Progress tracking:** The scraper logs progress every 10 weeks

**Note:** This is a long-running scraper. It will scrape ~780 weeks of data (15 years). Be patient!

---

### Step 4: Build Master Datasets

```bash
python build_master.py
```

**What it does:**
- Merges Tony data, producer data, and grosses data
- Builds three master tables:
  - `data/processed/shows.csv` (one row per show)
  - `data/processed/weekly_grosses.csv` (panel data)
  - `data/processed/survival_panel.csv` (for hazard models)

**Known limitations:**
- Opening/closing dates are placeholders (NaN) unless IBDB scraping is enhanced
- Review scores, theatre metadata, etc. are placeholders

---

### Step 5: Run Analysis

```bash
cd ../analysis
jupyter notebook tony_producers_analysis.ipynb
```

**What it does:**
- Loads master datasets
- Runs descriptive statistics
- Fits statistical models:
  - Logistic regression (Tony wins vs producer count)
  - Count model (Tony nominations vs producer count)
  - Panel regression (weekly grosses vs producer count) *[if data available]*
  - Cox proportional hazards (run length vs producer count) *[if data available]*
- Saves results to `output/tables/` and `output/figures/`

**Expected runtime:** 2-5 minutes (depending on data size)

---

## Data Sources

See `data_sources.md` for detailed documentation of all data sources.

**Summary:**
- **Tony Awards:** Wikipedia Tony Award year pages (e.g., "65th Tony Awards")
- **Producer Credits:** IBDB (Internet Broadway Database)
- **Weekly Grosses:** Manual CSV drop-in (see Step 3)
- **Show Metadata:** IBDB (partially implemented)

---

## Key Datasets

### `shows.csv` (Master Show Table)

One row per show. Key columns:
- `show_id`: Unique identifier (e.g., "Hadestown_2019")
- `title`: Show title
- `season`: Broadway season (e.g., "2018-2019")
- `tony_year`: Tony ceremony year
- `tony_nom_count`: Total Tony nominations
- `tony_win_count`: Total Tony wins
- `tony_win_any`: 1 if won at least one Tony
- `tony_major_win`: 1 if won Best Musical/Play/Revival
- `producer_count_total`: Total number of producers
- `lead_producer_count`: Number of lead producers
- `co_producer_count`: Number of co-producers
- `opening_date`, `closing_date`: (currently NaN, TODO)
- `weeks_running_total`: Run length in weeks (currently NaN, TODO)
- Other metadata fields (placeholders)

### `weekly_grosses.csv` (Panel Data)

One row per show-week. Key columns:
- `show_id`: Links to shows.csv
- `week_ending_date`: Week ending date
- `week_number_since_open`: Week number since opening
- `weekly_gross`: Gross revenue ($)
- `capacity_pct`: Capacity percentage (0-100)
- `post_tony_period`: 1 if after Tony ceremony

### `survival_panel.csv` (Survival Analysis)

One row per show (for hazard models). Key columns:
- `show_id`
- `duration`: Weeks running (or observation time)
- `event`: 1 if show closed, 0 if censored
- Producer counts and other covariates

---

## Optional Enhancements

The core pipeline is fully automated, but these optional enhancements can improve analysis quality:

### 1. **NYT Review Scores** (Improves quality controls)
   - **Why:** Requires sentiment analysis or manual coding
   - **Action:**
     - Scrape NYT theater reviews or use NYT API
     - Code as +1 (positive), 0 (mixed), -1 (negative)
     - Add to `shows.csv` as `nyt_review_score` and `critic_pick`
   - **Impact:** Better controls for show quality in models

### 2. **Opening/Closing Dates** (Enables survival analysis)
   - **Why:** IBDB scraping for dates not fully implemented
   - **Action:** Enhance `scrape_producers.py` or add separate IBDB metadata scraper
   - **Impact:** Enables proper survival analysis and run length calculations

### 3. **Theatre Metadata** (Better venue controls)
   - **Why:** Theatre names are captured, but size/location not fully linked
   - **Action:** Add IBDB scraper for complete theatre metadata
   - **Impact:** Allows controlling for venue characteristics

### 4. **Show Category Refinement** (Better subsample analysis)
   - **Why:** Musical vs Play is captured from grosses data, but not validated
   - **Action:** Cross-validate with Tony categories and IBDB
   - **Impact:** More accurate subsample analysis (musicals vs plays)

---

## Reproducibility Notes

- **No random seeds needed:** All models are deterministic
- **Scraping may vary:** Web scraping results depend on website structure at time of execution
- **Fuzzy matching:** Title matching uses threshold=85 (configurable in `config.py`)
- **Rate limiting:** Scraping includes 1.5-second delays (configurable)

To ensure full reproducibility:
1. Save raw scraped data with timestamps
2. Document any manual edits to data
3. Use version control (git) for code changes

---

## Limitations

1. **Incomplete data:** Not all shows may have complete producer, grosses, or metadata
2. **Scraping fragility:** Web scraping may break if source websites change structure
3. **Missing controls:** Review scores, capitalization, star power not yet implemented
4. **Causality:** All analyses are correlational; cannot infer causation
5. **Selection bias:** Only Tony-eligible shows are included (may miss Off-Broadway, etc.)

See analysis notebook for detailed discussion of limitations.

---

## Extending the Analysis

### Adding New Variables

To add a new variable to `shows.csv`:
1. Collect data (scraping or manual)
2. Save to `data/raw/your_variable.csv` with `show_id` column
3. Modify `data/build_master.py` to merge it
4. Re-run `python build_master.py`

### Adding New Models

To add a new statistical model:
1. Open `analysis/tony_producers_analysis.ipynb`
2. Add a new section with your model code
3. Document interpretation clearly

### Using Different Time Periods

To change the analysis period:
1. Edit `config.py`: change `START_TONY_YEAR` and `END_TONY_YEAR`
2. Re-run all data collection scripts

---

## Troubleshooting

### Problem: Tony scraper returns no data
- **Cause:** Wikipedia page structure changed
- **Solution:** Inspect the Wikipedia page manually, update `scrape_tonys.py` parsing logic

### Problem: Producer scraper fails for most shows
- **Cause:** IBDB blocking requests or structure changed
- **Solution:**
  - Check IBDB website manually
  - Increase rate limiting delay in `config.py`
  - Consider manual data entry for key shows

### Problem: Grosses scraper fails or returns no data
- **Cause:** Broadway World website structure changed or connection issues
- **Solution:**
  - Check internet connection
  - Verify Broadway World is accessible: https://www.broadwayworld.com/json_grosses.cfm
  - Check error messages in logs
  - If Broadway World is down, wait and retry later

### Problem: Analysis notebook cells fail
- **Cause:** Missing data or dependencies
- **Solution:**
  - Check that master CSVs exist in `data/processed/`
  - Verify all Python packages installed (`pip install -r requirements.txt`)
  - Check for NaN values in key columns

---

## Citation

If you use this pipeline or data in your research, please cite:

```
Broadway Tony Producer Analysis Pipeline (2025)
https://github.com/[your-repo]/broadway-tony-producer-analysis
```

---

## Contact & Contributions

This is a research pipeline built for transparency and reproducibility.

**Contributions welcome:**
- Improved scrapers (especially IBDB metadata)
- Additional data sources
- Enhanced statistical models
- Bug fixes

Please open an issue or pull request on GitHub.

---

## License

This code is provided for educational and research purposes.

**Data sources:**
- Tony Awards data: Wikipedia (CC BY-SA)
- IBDB data: Used for research purposes (check IBDB terms of service)
- Grosses data: Depends on source (cite appropriately)

**Code:** MIT License (or specify your preferred license)

---

## Changelog

**v1.0 (2025-01-XX)** - Initial release
- Tony Awards scraper (Wikipedia)
- Producer count scraper (IBDB)
- Weekly grosses importer (manual CSV)
- Master dataset builder
- Analysis notebook with 5 statistical models
- Documentation and README

**Future versions:**
- Enhanced IBDB metadata scraping
- NYT review sentiment analysis
- Automated grosses collection
- Interactive visualizations

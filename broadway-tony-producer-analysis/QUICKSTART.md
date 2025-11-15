# Quick Start Guide

Get started with the Broadway Tony Producer Analysis in 5 minutes.

## Prerequisites

- Python 3.9+
- Internet connection
- Terminal/command line

## Installation (2 minutes)

```bash
# 1. Navigate to project directory
cd broadway-tony-producer-analysis

# 2. Install dependencies
pip install -r requirements.txt
```

## Run the Pipeline (3 minutes)

### Option 1: Run Everything (Automated)

```bash
# Run the entire pipeline
./run_pipeline.sh
```

This will:
1. Scrape Tony Awards data (2011-present)
2. Scrape producer counts from IBDB
3. Process grosses data (if you provide it)
4. Build master datasets

### Option 2: Run Step-by-Step

```bash
# Step 1: Tony data
cd data
python scrape_tonys.py

# Step 2: Producer data
python scrape_producers.py

# Step 3: Grosses data (optional - see note below)
python get_grosses.py

# Step 4: Build master datasets
python build_master.py
cd ..
```

## View Results

```bash
# Open the analysis notebook
cd analysis
jupyter notebook tony_producers_analysis.ipynb
```

Then run all cells (Cell → Run All).

## Important Notes

### Weekly Grosses Data (Optional but Recommended)

The pipeline works without grosses data, but for complete analysis:

1. Obtain weekly grosses CSV from:
   - Broadway World (https://www.broadwayworld.com/grosses)
   - The Numbers (https://www.the-numbers.com/broadway)
   - Other public source

2. Format as CSV with columns:
   - `show_title`, `week_ending_date`, `weekly_gross`
   - (See `data/raw/grosses_raw_TEMPLATE.csv` for example)

3. Save to: `data/raw/grosses_raw.csv`

4. Re-run: `python data/get_grosses.py && python data/build_master.py`

### Expected Runtime

- Tony scraping: 30-60 seconds
- Producer scraping: 5-10 minutes (rate limited)
- Grosses processing: <10 seconds
- Master dataset building: <30 seconds
- **Total: ~10-15 minutes**

### What You'll Get

After running the pipeline:

**Data Files:**
- `data/processed/shows.csv` - Master show table (~300-500 shows)
- `data/processed/weekly_grosses.csv` - Weekly grosses panel (if data provided)
- `data/processed/survival_panel.csv` - Survival analysis data

**Analysis Outputs:**
- Statistical model results in `output/tables/`
- Visualizations in `output/figures/`
- Results summary in `output/results_summary.md`

## Troubleshooting

### "No Tony data scraped"
- Wikipedia structure may have changed
- Check your internet connection
- See README.md → Troubleshooting section

### "No IBDB page found for [show]"
- Some shows may not be in IBDB or have different titles
- Check `data/raw/producers_raw.csv` for which shows succeeded
- You can manually add producer counts if needed

### "Grosses data not available"
- This is expected if you haven't provided manual data
- Pipeline will skip grosses analysis
- See note above on obtaining grosses data

### Jupyter notebook won't open
```bash
# Install Jupyter if needed
pip install jupyter

# Try again
jupyter notebook
```

## Next Steps

1. **Review the data:** Check `data/processed/shows.csv` for completeness
2. **Run the analysis:** Open and run the Jupyter notebook
3. **Interpret results:** See analysis notebook for statistical findings
4. **Read full docs:** See README.md for detailed information

## Getting Help

- **Full documentation:** See README.md
- **Data sources:** See data_sources.md
- **Issues:** Check README.md → Troubleshooting

---

**That's it! You should now have a complete analysis of Broadway producers and Tony outcomes.**

Happy analyzing! 🎭

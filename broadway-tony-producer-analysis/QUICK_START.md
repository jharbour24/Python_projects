# Quick Start Guide - Broadway Producer Analysis

This guide gets you up and running with the Broadway show scraper in 5 minutes.

## Step 1: Get Latest Code

Your git pull is having issues, so download the key files directly:

```bash
cd ~/Python_projects/broadway-tony-producer-analysis/data

# Download latest scraper files
curl -o scrape_all_broadway_shows.py https://raw.githubusercontent.com/jharbour24/Python_projects/claude/broadway-tony-producer-analysis-01Cdc38t4zVhAxDDqRB17GLJ/broadway-tony-producer-analysis/data/scrape_all_broadway_shows.py

curl -o test_hadestown_scrape.py https://raw.githubusercontent.com/jharbour24/Python_projects/claude/broadway-tony-producer-analysis-01Cdc38t4zVhAxDDqRB17GLJ/broadway-tony-producer-analysis/data/test_hadestown_scrape.py

curl -o test_simple_scraper.py https://raw.githubusercontent.com/jharbour24/Python_projects/claude/broadway-tony-producer-analysis-01Cdc38t4zVhAxDDqRB17GLJ/broadway-tony-producer-analysis/data/test_simple_scraper.py
```

## Step 2: Install Dependencies

```bash
pip3 install undetected-chromedriver beautifulsoup4 selenium
```

## Step 3: Test Your Setup

Run this first to make sure everything works:

```bash
python3 test_simple_scraper.py
```

**Expected output:**
- "✓ Required packages installed"
- "✓ Chrome initialized successfully"
- "✓ Successfully accessed IBDB page!"
- "✓ No Cloudflare blocking detected"
- "✓✓✓ ALL TESTS PASSED ✓✓✓"

**If it fails:**
- Make sure Google Chrome browser is installed
- Try: `pip3 install --upgrade undetected-chromedriver`
- Close all Chrome windows and run again

## Step 4: Test Hadestown (Verify Producer Count)

Once the basic test passes:

```bash
python3 test_hadestown_scrape.py
```

**This will:**
- Open Chrome browser (visible)
- Go to Hadestown IBDB page
- Count all producers
- Show you if it finds 44 producers (correct count)

## Step 5: Run Full Scraper

If Hadestown test works:

```bash
python3 scrape_all_broadway_shows.py
```

**This will:**
1. Get list of ALL Broadway shows from 2010-2025
2. Scrape producer data for each show
3. Save results to `raw/broadway_shows_with_producers.csv`

**First run:** Only scrapes 10 shows (test mode)

**To scrape all ~500 shows:** Edit `scrape_all_broadway_shows.py` line ~430 and change:
```python
test_mode = True
```
to:
```python
test_mode = False
```

## Troubleshooting

### "ChromeOptions object has no attribute 'headless'"

This error is from old cached files. The new files use a simpler initialization. Make sure you:
1. Downloaded the latest files (Step 1)
2. Restarted your terminal

### "Cloudflare is blocking"

- Try again in 10-15 minutes (Cloudflare strictness varies)
- Try from a different network
- Make sure Chrome browser is fully updated

### "Chrome not found"

Install Google Chrome:
- Download from: https://www.google.com/chrome/

### Still having issues?

Run the simple test first:
```bash
python3 test_simple_scraper.py
```

This will show you exactly what's wrong.

## What You'll Get

After successful scraping:

**File:** `raw/broadway_shows_complete_list.csv`
- Complete list of all Broadway shows since 2010 (~500 shows)
- Includes show title, IBDB URL, season year

**File:** `raw/broadway_shows_with_producers.csv`
- All shows with producer data
- Accurate producer counts (e.g., Hadestown: 44 producers)
- Raw producer text for verification

## Next Steps

After collecting producer data:
1. Run the full analysis pipeline
2. Merge with Tony nominations and weekly grosses
3. Run statistical models

See main README.md for full pipeline documentation.

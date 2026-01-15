# Local Setup Guide - Run Scraper on Your Machine

## Quick Start (5 minutes)

```bash
# 1. Clone repository
git clone <your-repo-url>
cd Python_projects

# 2. Install dependencies
pip install -r requirements.txt

# 3. Test scraper (should find Hamilton=4, Hadestown=45)
python3 advanced_ibdb_scraper.py

# 4. If test passes, run full scrape (30-60 minutes)
python3 run_full_scrape.py

# 5. Run analysis
python3 analysis/producer_tony_analysis.py
```

**Expected result**: Complete dataset with producer counts for 535 shows!

---

## Detailed Instructions

### Prerequisites

- **Python 3.8+** (check: `python3 --version`)
- **pip** (Python package manager)
- **Internet connection** (unrestricted)

### Step 1: Download the Code

#### Option A: Git Clone (if you have git)
```bash
git clone https://github.com/jharbour24/Python_projects.git
cd Python_projects
```

#### Option B: Download ZIP
1. Go to your GitHub repository
2. Click "Code" → "Download ZIP"
3. Extract ZIP file
4. Open terminal/command prompt in extracted folder

### Step 2: Create Virtual Environment (Recommended)

**On Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

###  Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed cloudscraper-1.2.71 beautifulsoup4-4.12.0 pandas-2.0.0 ...
```

**If you get errors**, try:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Test the Scraper

**Run test with Hamilton and Hadestown:**
```bash
python3 advanced_ibdb_scraper.py
```

**Expected output:**
```
TEST: Hamilton (expecting ~4 producers)
✓ Successfully fetched IBDB page
Found 4 unique producer names
✓ MATCH (within ±2 of expected 4)

TEST: Hadestown (expecting ~45 producers)
✓ Successfully fetched IBDB page
Found 45 unique producer names
✓ MATCH (within ±2 of expected 45)
```

**If test passes:** ✓ Scraper works! Proceed to full scrape.

**If test fails:** See Troubleshooting section below.

### Step 5: Run Full Scrape (All 535 Shows)

```bash
python3 run_full_scrape.py
```

**What happens:**
- Scrapes all 535 shows from `raw/all_broadway_shows_2010_2025.csv`
- Takes 30-60 minutes (4-6 seconds per show)
- Shows progress every 10 shows
- Can be interrupted (Ctrl+C) and resumed
- Saves results to `data/show_producer_counts_ibdb.csv`

**Sample output:**
```
[1/535] (0.2%) Processing: A BEHANDING IN SPOKANE
✓ SUCCESS: Found 15 producers

[2/535] (0.4%) Processing: A FREE MAN OF COLOR
✓ SUCCESS: Found 12 producers

...

[10/535] (1.9%) Processing: BURN THE FLOOR
PROGRESS REPORT
  Completed: 10/535
  Successful: 9
  Not found: 1
  Rate: 0.15 shows/sec
  Elapsed: 1.1 minutes
  Est. remaining: 58.3 minutes
```

**To resume if interrupted:**
Just run `python3 run_full_scrape.py` again - it will automatically resume from checkpoint.

### Step 6: Review Results

```bash
# Check how many shows were scraped
wc -l data/show_producer_counts_ibdb.csv

# View first few rows
head -20 data/show_producer_counts_ibdb.csv

# Check for failed shows
cat data/failed_shows.csv
```

### Step 7: Run Analysis

```bash
python3 analysis/producer_tony_analysis.py
```

**Output:**
- Statistical analysis (t-tests, logistic regression)
- Visualizations in `analysis/results/`
- Summary in `analysis/results/analysis_summary.txt`

---

## Troubleshooting

### Issue: "Module not found" errors

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Mac/Linux
# OR
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Test shows 403 errors

**Possible causes:**
1. **Corporate/School network with firewall**
   - Try from home network or mobile hotspot
   - Or use VPN

2. **IP blocked by IBDB**
   - Wait 10-15 minutes and try again
   - Increase rate limit: Edit `advanced_ibdb_scraper.py`, change `rate_limit_delay=4.0` to `rate_limit_delay=8.0`

3. **Cloudflare challenge not solved**
   - Update cloudscraper: `pip install --upgrade cloudscraper`

### Issue: Some shows return "not_found"

**This is normal!** Not all shows may be on IBDB, or names might not match exactly.

**Solutions:**
- Check `data/failed_shows.csv` for list
- Manually look up these shows on IBDB
- Add their data to the CSV manually

### Issue: Scraper is too slow

**Speed it up:**
- Edit `run_full_scrape.py`
- Change `rate_limit_delay=4.0` to `rate_limit_delay=2.0`
- **Warning**: May increase chance of being blocked

### Issue: Computer goes to sleep during scrape

**Solutions:**
- Adjust power settings to prevent sleep
- Or run in screen/tmux session (advanced)
- Or just resume from checkpoint when you wake it up

---

## File Structure

```
Python_projects/
├── raw/
│   └── all_broadway_shows_2010_2025.csv    # 535 shows (input)
│
├── data/
│   ├── show_producer_counts_ibdb.csv       # Results (output)
│   ├── checkpoint_producer_scrape.csv      # Auto-saved progress
│   └── failed_shows.csv                    # Shows that failed
│
├── logs/
│   ├── full_scrape.log                     # Detailed scraping log
│   └── advanced_scraper.log                # Debug information
│
├── analysis/
│   ├── producer_tony_analysis.py           # Analysis script
│   └── results/
│       ├── producer_counts_comparison.png  # Visualization
│       ├── producer_tony_relationship.png  # Scatter plot
│       └── analysis_summary.txt            # Summary stats
│
├── advanced_ibdb_scraper.py                # Core scraper
├── run_full_scrape.py                      # Full scrape script
├── utils.py                                # Utilities
└── requirements.txt                        # Dependencies
```

---

## Performance Tips

### Speed vs. Politeness Trade-off

**Current settings**: 4 seconds between requests
- **Time**: ~40 minutes for 535 shows
- **Risk**: Very low chance of being blocked

**Faster (2 seconds)**:
- **Time**: ~20 minutes
- **Risk**: Low chance of being blocked

**Very fast (1 second)**:
- **Time**: ~10 minutes
- **Risk**: Higher chance of being blocked

**Recommendation**: Start with 4 seconds. If everything works smoothly, you can speed it up on future runs.

### Running Overnight

If you want to run this overnight:

**Mac/Linux:**
```bash
nohup python3 run_full_scrape.py > scrape_output.txt 2>&1 &
```

**Check progress:**
```bash
tail -f scrape_output.txt
# Press Ctrl+C to stop watching (scrape continues in background)
```

**Windows:**
- Use Task Scheduler to keep running
- Or just leave terminal open with "Prevent sleep" enabled

---

## Expected Results

### Successful Scrape

**Output file**: `data/show_producer_counts_ibdb.csv`

**Sample data:**
```csv
show_id,show_name,ibdb_url,num_total_producers,num_lead_producers,num_co_producers,scrape_status,scrape_notes
232,HAMILTON,https://www.ibdb.com/broadway-production/hamilton-499521,4,2,2,ok,Found 4 total producers
365,HADESTOWN,https://www.ibdb.com/broadway-production/hadestown-509022,45,3,42,ok,Found 45 total producers
```

### Success Metrics

**Good scrape:**
- 450-500 shows (85-95%) with producer data
- 35-85 shows with "not_found" status
- Average producer count: 10-20 per show

**Problem indicators:**
- <400 shows successful → Network issues or rate limiting
- >100 shows "not_found" → Search logic may need adjustment

---

## Alternative: Google Colab

If local setup is difficult, use Google Colab (free, online, requires no setup):

1. Go to https://colab.research.google.com
2. Click "File" → "Upload notebook"
3. Create new notebook
4. Upload project files to Colab session
5. Run in notebook cells:

```python
# Install dependencies
!pip install cloudscraper beautifulsoup4 lxml pandas

# Run scraper
!python3 run_full_scrape.py

# Download results
from google.colab import files
files.download('data/show_producer_counts_ibdb.csv')
```

---

## Next Steps After Scraping

1. **Validate data**: `python3 validate_manual_data.py`
2. **Run analysis**: `python3 analysis/producer_tony_analysis.py`
3. **Review results**: Check `analysis/results/`
4. **Commit to git**: `git add data/ && git commit -m "Add scraped producer data"`

---

## Support

If you encounter issues:
1. Check `logs/full_scrape.log` for detailed error messages
2. Review Troubleshooting section above
3. Check `data/failed_shows.csv` to see which shows failed
4. Refer to `ENVIRONMENT_LIMITATIONS_AND_SOLUTIONS.md` for technical details

**Common questions:**
- "Why 403 errors?" → Network firewall or IBDB blocking your IP
- "Why 'not_found'?" → Show not on IBDB or name doesn't match
- "How to speed up?" → Reduce `rate_limit_delay` (but risks blocking)

---

## Success Checklist

- [ ] Python 3.8+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Test scraper passes (Hamilton=4, Hadestown=45)
- [ ] Full scrape completes (30-60 minutes)
- [ ] Results file created (`data/show_producer_counts_ibdb.csv`)
- [ ] Analysis runs successfully
- [ ] Visualizations generated

**Once all checked:** ✅ You have complete producer dataset for 535 shows!

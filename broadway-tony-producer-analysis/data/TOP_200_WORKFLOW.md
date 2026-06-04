# Top 200 Broadway Shows Producer Data Collection

This guide explains how to collect producer data for the top 200 highest-grossing Broadway shows.

## Overview

You have two options:

1. **Automated scraping** (may be blocked by Cloudflare)
2. **Manual data entry** (100% reliable but time-consuming)

Both approaches start with the same template file.

---

## Step 1: Create the Top 200 Template

This analyzes your existing weekly grosses data and creates a prioritized list of the 200 highest-grossing shows.

```bash
cd ~/Python_projects/broadway-tony-producer-analysis/data
python3 create_top200_template.py
```

**Output**: Creates `raw/top_200_shows_producer_template.csv`

The template includes:
- Show title and ID
- Total gross revenue (for prioritization)
- Weeks tracked
- Average weekly gross
- Empty columns for producer data

---

## Step 2A: Try Automated Scraping (Recommended First)

This uses advanced anti-detection techniques to bypass Cloudflare.

### Install Dependencies

```bash
pip3 install undetected-chromedriver beautifulsoup4
```

### Run the Scraper

```bash
python3 scrape_producers_undetected.py
```

### What to Expect

1. **First run**: Takes 30-60 seconds to set up ChromeDriver
2. **Cloudflare test**: The scraper will test if it can bypass Cloudflare
3. **If bypass works**: ✓ Will scrape first 10 shows (test mode)
4. **If bypass fails**: ✗ You'll see a message to try manual collection

### Important Notes

- **Headless mode**: The scraper runs with browser visible (headless=False) because Cloudflare detects headless browsers more easily
- **Test mode**: By default, only scrapes 10 shows to test if it's working
- **Remove test limit**: In `scrape_producers_undetected.py`, change or remove `test_limit = 10`
- **Rate limiting**: Includes 3-second delay between requests to be respectful

### Expected Success Rate

- **If Cloudflare bypass works**: 70-90% success rate
- **If Cloudflare is strict**: 0% success rate (need manual collection)

---

## Step 2B: Manual Data Collection (100% Reliable)

If automated scraping fails or you want guaranteed accuracy:

### Open the Template

```bash
open raw/top_200_shows_producer_template.csv
```

Or open in Excel, Numbers, Google Sheets, etc.

### For Each Show

1. **Visit IBDB**: Go to https://www.ibdb.com/
2. **Search for show**: Use the `title` from the template
3. **Find "Produced by" section**: Usually near the top of the show page
4. **Count producers**:
   - Look for "Lead Producer" or main producers listed first
   - Look for "Co-Producer" or "Associate Producer"
   - Count total number of entities (partnerships count as 1)

5. **Fill in template**:
   - `ibdb_url`: Direct URL to the show page
   - `producer_count_total`: Total number of producers
   - `lead_producer_count`: Number of lead/primary producers
   - `co_producer_count`: Number of co-producers/associate producers
   - `notes`: Any relevant observations (e.g., "unclear distinction between lead/co")
   - `data_quality`: Change to `verified`

### Example Entry

```csv
title,ibdb_url,producer_count_total,lead_producer_count,co_producer_count,notes,data_quality
Hamilton,https://www.ibdb.com/broadway-production/Hamilton-499521,4,3,1,"Jeffrey Seller/Sander Jacobs/Jill Furman (lead), The Public Theater (co)",verified
```

### Time Estimate

- **Per show**: 2-3 minutes
- **Top 200 shows**: 6-10 hours total
- **Recommendation**: Do in batches (25-50 shows at a time)

---

## Step 3: Verify and Use Data

After collection (automated or manual):

### Check Data Quality

```bash
python3 -c "
import pandas as pd
df = pd.read_csv('raw/top_200_shows_producer_template.csv')
verified = df[df['data_quality'].isin(['verified', 'scraped'])]
print(f'Collected: {len(verified)}/{len(df)} shows ({len(verified)/len(df)*100:.1f}%)')
print(f'Average producers: {verified[\"producer_count_total\"].mean():.1f}')
print(f'Range: {verified[\"producer_count_total\"].min()}-{verified[\"producer_count_total\"].max()} producers')
"
```

### Integrate with Pipeline

The data will automatically be used by `build_master.py` when you run the full pipeline:

```bash
cd ..  # Go to project root
python3 -m data.build_master
```

This will:
1. Load your top 200 producer data
2. Merge with weekly grosses and Tony nominations
3. Create analysis-ready datasets in `data/processed/`

---

## Troubleshooting

### Automated Scraping

**Problem**: "Cloudflare is still blocking"
- **Solution**: Use manual data collection (Step 2B)
- **Why**: Cloudflare periodically updates detection; bypass may stop working

**Problem**: "undetected-chromedriver not found"
- **Solution**: `pip3 install undetected-chromedriver`

**Problem**: "Chrome binary not found"
- **Solution**: Install Google Chrome browser
- **Download**: https://www.google.com/chrome/

### Manual Data Entry

**Problem**: Can't find show on IBDB
- **Solution**: Try alternative title or check `show_id` from grosses data
- **Note**: Some shows may have different names on IBDB

**Problem**: Unclear lead vs co-producer distinction
- **Solution**: Put all in `producer_count_total`, note in `notes` column
- **Acceptable**: Just having total count is fine for initial analysis

**Problem**: Partnership entities (e.g., "Dede Harris & Linda B. Rubin")
- **Solution**: Count as single entity
- **Rationale**: They function as a single producing unit

---

## Next Steps

After collecting producer data:

1. **Run full pipeline**: `python3 -m data.build_master`
2. **Run analysis**: `jupyter notebook analysis/tony_producers_analysis.ipynb`
3. **View results**: Check `analysis/output/` for tables and plots

---

## Questions?

See main README.md or check the methodology document:
- `data/PRODUCER_DATA_METHODOLOGY.md`

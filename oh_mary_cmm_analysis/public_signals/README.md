# Public Signals Data Collection System

Collects public demand proxy signals for Broadway shows from various sources. All data collection is **public-only** (no authentication required), respects robots.txt, and uses ethical rate limiting.

## Overview

This system collects weekly aggregated data from:

1. **Google Trends** - Search interest indices (0-100 scale)
2. **Wikipedia** - Daily pageviews aggregated to weekly
3. **TikTok** - Public engagement metrics (views, likes, comments, shares)
4. **Instagram** - Public engagement metrics (likes, comments, posts)

## Architecture

```
public_signals/
├── src/
│   ├── common/          # Shared utilities
│   │   ├── net.py       # HTTP client with robots.txt checking, rate limiting, retries
│   │   └── timebins.py  # Weekly aggregation and time binning
│   ├── sources/         # Data source collectors
│   │   ├── google_trends.py
│   │   ├── wikipedia.py
│   │   ├── tiktok_public.py
│   │   └── instagram_public.py
│   └── cli/             # Command-line tools
│       ├── pull_public_signals.py   # Orchestrates all collectors
│       └── make_weekly_panel.py     # Merges sources into panel
├── config/
│   └── shows.yaml       # Show configuration (queries, handles)
└── data/
    ├── raw/             # Per-source raw CSVs
    ├── weekly/          # Per-source weekly aggregates
    └── panel/           # Combined panel dataset
```

## Installation

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers (for TikTok/Instagram)
playwright install chromium
```

### 2. Configure Shows

Edit `public_signals/config/shows.yaml` to add your Broadway shows:

```yaml
shows:
  - name: "Oh, Mary!"
    google_queries:
      - "Oh Mary Broadway"
      - "Cole Escola"
    wikipedia_title: "Oh,_Mary!"
    tiktok_handle: "@ohmaryplay"
    instagram_handle: "ohmaryplay"

  - name: "Hamilton"
    google_queries:
      - "Hamilton Broadway"
      - "Hamilton musical"
    wikipedia_title: "Hamilton_(musical)"
    tiktok_handle: "@hamiltonmusical"
    instagram_handle: "hamiltonmusical"
```

**Required:**
- `name`: Show name (used as identifier)

**Optional:**
- `google_queries`: List of search terms (recommended: 2-5 specific queries)
- `wikipedia_title`: Wikipedia article name (auto-detected if omitted)
- `tiktok_handle`: TikTok profile handle (with or without @)
- `instagram_handle`: Instagram profile handle (without @)

## Usage

### Step 1: Collect Public Signals

```bash
cd public_signals/src/cli

# Collect all sources for 2024 season
python3 pull_public_signals.py \
  --config ../../config/shows.yaml \
  --start 2024-01-01 \
  --end 2024-12-31

# Collect only specific sources
python3 pull_public_signals.py \
  --config ../../config/shows.yaml \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --sources google_trends wikipedia

# Adjust social media post limit
python3 pull_public_signals.py \
  --config ../../config/shows.yaml \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --max-posts 50
```

**Output:**
- `public_signals/data/raw/{source}/` - Raw data per show
- `public_signals/data/weekly/{source}_weekly.csv` - Weekly aggregates per source

### Step 2: Build Panel Dataset

```bash
# Merge all sources into combined panel
python3 make_weekly_panel.py

# Custom input/output locations
python3 make_weekly_panel.py \
  --input ../../data/weekly \
  --output ../../data/panel

# Create balanced panel (fill missing weeks)
python3 make_weekly_panel.py --fill-missing
```

**Output:**
- `public_signals/data/panel/weekly_signals_panel.parquet` - Combined panel (main format)
- `public_signals/data/panel/weekly_signals_panel_preview.csv` - Preview (first 1000 rows)
- `public_signals/data/panel/panel_metadata.json` - Summary statistics

## Output Schemas

### Google Trends
```
show          | week_start | gt_avg_index | is_partial
--------------|------------|--------------|------------
Oh, Mary!     | 2024-09-09 | 78.5         | False
Hamilton      | 2024-09-09 | 62.0         | False
```

- `gt_avg_index`: Average interest across queries (0-100 scale)
- `is_partial`: True if data is incomplete

### Wikipedia
```
show          | week_start | wiki_views
--------------|------------|------------
Oh, Mary!     | 2024-09-09 | 45302
Hamilton      | 2024-09-09 | 123456
```

- `wiki_views`: Total pageviews for the week

### TikTok
```
show          | week_start | tt_posts | tt_sum_views | tt_sum_likes | tt_sum_comments | tt_sum_shares | tt_unique_hashtags
--------------|------------|----------|--------------|--------------|-----------------|---------------|--------------------
Oh, Mary!     | 2024-09-09 | 5        | 1250000      | 45000        | 3200            | 890           | 18
```

### Instagram
```
show          | week_start | ig_posts | ig_sum_likes | ig_sum_comments | ig_unique_hashtags | ig_reel_ct
--------------|------------|----------|--------------|-----------------|--------------------|-----------
Oh, Mary!     | 2024-09-09 | 3        | 12500        | 450             | 12                 | 1
```

**Note:** Instagram metrics may be null if hidden by platform for non-authenticated users.

### Combined Panel
The panel dataset merges all sources on `(show, week_start)` using an **outer join**, preserving all observations. Missing values indicate that source had no data for that show-week.

Additional columns:
- `has_google_trends`: 1 if Google Trends data available, 0 otherwise
- `has_wikipedia`: 1 if Wikipedia data available, 0 otherwise
- `has_tiktok`: 1 if TikTok data available, 0 otherwise
- `has_instagram`: 1 if Instagram data available, 0 otherwise

## Ethical Considerations

This system is designed for **academic research** and follows ethical web scraping practices:

### 1. robots.txt Compliance
- Every URL is checked against `robots.txt` before fetching
- URLs blocked by `robots.txt` are skipped with warning

### 2. Rate Limiting
- Random delays between requests (2-5 seconds by default)
- Exponential backoff on errors (2s, 4s, 8s, 16s)
- Maximum 4 retry attempts per request

### 3. User-Agent Identification
- Custom user-agent identifying this as academic research:
  ```
  BroadwayMarketingResearch/1.0 (+https://github.com/research/broadway-analysis; academic research)
  ```

### 4. Public Data Only
- **No authentication or login** - only scrapes publicly visible data
- No personal information collection
- No bypassing of access controls

### 5. Responsible Resource Usage
- Limited number of posts per show (default: 30)
- Headless browser used efficiently for JavaScript-heavy sites
- Data cached locally to minimize repeated requests

## Technical Details

### Common Utilities

**`common/net.py`** - HTTP client with ethical safeguards:
- `respect_robots(url)` - Checks robots.txt compliance
- `fetch(url, ...)` - Makes HTTP request with rate limiting and retries
- Uses `tenacity` library for exponential backoff

**`common/timebins.py`** - Time binning for weekly aggregation:
- `to_week_start(timestamp)` - Floors date to Monday of week
- `week_agg(df, ...)` - Aggregates DataFrame to weekly level
- `fill_missing_weeks(df, ...)` - Creates balanced panel with NaN for missing weeks

### Data Collection Flow

1. **Load Config** - Parse `shows.yaml` to get show list and handles
2. **Collect Per-Show** - For each show, call source-specific collector
3. **Weekly Aggregation** - Convert daily/post-level data to weekly bins
4. **Save Raw Data** - Store per-show CSVs in `data/raw/{source}/`
5. **Combine Shows** - Concatenate all shows into single weekly CSV per source
6. **Merge Sources** - Outer join all sources on `(show, week_start)`
7. **Add Metadata** - Generate summary stats and coverage metrics

### Error Handling

- **Source failures are isolated** - If Google Trends fails, other sources continue
- **Missing data is explicit** - NaN values indicate no data (not zero)
- **Logging is comprehensive** - All HTTP requests, parse failures, and merge stats logged
- **Exit codes** - CLI returns non-zero if any source encountered errors

## Troubleshooting

### Issue: TikTok/Instagram scraping fails with "No posts found"

**Possible causes:**
1. Profile is private or doesn't exist
2. Handle in config is incorrect
3. Page layout changed (selectors outdated)
4. Rate limited by platform

**Solutions:**
- Verify handle exists and is public
- Check `data/raw/{source}/` for error logs
- Try with `--max-posts 10` (fewer requests)
- Wait 24 hours and retry if rate limited

### Issue: Google Trends returns all zeros

**Possible causes:**
1. Query has insufficient search volume
2. Time period too short
3. Geographic restriction (default: US-NY)

**Solutions:**
- Use broader queries (e.g., "Hamilton musical" vs "Hamilton Broadway tickets")
- Try multiple related queries per show
- Check `is_partial` flag in output

### Issue: Wikipedia article not found

**Possible causes:**
1. Auto-detection failed (article has unusual name)
2. Article doesn't exist or is redirect

**Solutions:**
- Manually specify `wikipedia_title` in config
- Check Wikipedia URL: `https://en.wikipedia.org/wiki/{title}`
- Try disambiguation suffixes: `_(musical)`, `_(play)`, `_(2024_musical)`

### Issue: robots.txt blocks all requests

**Symptoms:** Logs show "URL blocked by robots.txt"

**Solution:**
- Respect the block - it's intentional
- Use alternative data sources
- For Wikipedia/Trends, this should never happen (APIs are allowed)

## Integration with Causal Analysis

To integrate public signals with Broadway grosses for causal analysis:

1. **Collect public signals** (this system)
2. **Load Broadway grosses** (from `broadway_grosses_scraper.py`)
3. **Merge on (show, week_start)**
4. **Create lagged predictors** (using `analysis/feature_engineering.py`)
5. **Run panel regression** (using `models/lagged_causality.py`)

See main repository `README.md` for full causal analysis workflow.

## Future Enhancements

Potential additions (not implemented):
- **News mentions** - Scrape Playbill, Broadway World articles
- **Ticketing signals** - TodayTix availability, SeatGeek pricing
- **YouTube** - Video engagement metrics
- **Spotify** - Cast recording streams (if API access available)

## License and Attribution

This system is for **academic research purposes**. When using:
1. Cite data sources appropriately in publications
2. Respect rate limits and robots.txt
3. Do not use for commercial purposes without permission
4. Share findings publicly (open science principles)

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review logs in `data/raw/{source}/` directories
3. Verify config in `shows.yaml`
4. Ensure dependencies installed: `pip install -r requirements.txt`
5. Check Playwright browsers: `playwright install chromium`

---

**Built for:** Oh, Mary! CMM Analysis Project
**Date:** 2025-01-10
**Status:** Production-ready

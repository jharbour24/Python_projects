# Social Signals Pipeline: Production-Grade Data Collection & Feature Engineering

**Status:** Production-ready
**Version:** 2.0
**Date:** 2025-01-10

## Overview

This pipeline collects, aggregates, validates, and engineers features from public social media signals for Broadway shows. Designed for **publication-ready causal analysis** with robust error handling, data quality checks, and reproducibility.

### Objectives

1. **Stability & Resilience**: Robust scraping with retries, error taxonomy, and HTML snapshotting for audit
2. **Data Quality**: Weekly canonical panel with strict schemas, deduplication, and anomaly detection
3. **Analytics-Ready Features**: Computed lags/leads (e.g., +4 weeks), deltas, rolling stats, and standardization
4. **Reproducibility**: Deterministic runs, caching, tests, and clear logs
5. **Documentation**: Clear operational procedures with known limitations

## Architecture

```
public_signals/
├── src/
│   ├── common/          # Core utilities
│   │   ├── net.py       # HTTP client with robots.txt, retries, error taxonomy
│   │   ├── timebins.py  # Weekly aggregation utilities
│   │   └── snapshots.py # HTML archiving for debugging
│   ├── sources/         # Data collectors
│   │   ├── google_trends.py
│   │   ├── wikipedia.py
│   │   ├── tiktok_public.py      # With TikTokPost dataclass
│   │   └── instagram_public.py
│   ├── aggregation/     # Weekly aggregation & schema
│   │   └── weekly.py    # Canonical schema enforcement, deduplication
│   ├── features/        # Feature engineering
│   │   └── panel_features.py  # Lags, leads, deltas, rolling, z-scores
│   ├── quality/         # Data quality
│   │   └── checks.py    # Coverage, anomalies, validation
│   └── cli/             # Command-line tools
│       ├── pull_public_signals.py  # Data collection orchestrator
│       ├── make_weekly_panel.py    # Build canonical panel
│       ├── validate_social_panel.py    # Validation CLI
│       └── build_model_ready_social.py # Feature engineering CLI
├── config/
│   └── shows.yaml       # Show configuration
└── data/
    ├── raw/             # Per-source raw CSVs (per-post)
    ├── raw_snapshots/   # HTML snapshots (last 50 per handle)
    ├── weekly/          # Per-source weekly aggregates
    └── panel/           # Combined panel datasets
```

## Key Features

### 1. Stability & Resilience

**Error Taxonomy** (`net.py`):
- `ROBOTS_BLOCKED`: URL disallowed by robots.txt
- `RATE_LIMITED`: 429 response
- `SERVER_ERROR`: 5xx errors
- `CLIENT_ERROR`: 4xx errors (not retried)
- `TIMEOUT`: Request timeout
- `NETWORK`: Network failures
- `PARSE_ERROR`: HTML parsing issues

**Retry Logic**:
```python
fetch_with_metadata(url, max_retries=4)
# Returns FetchResult with attempts, error_category, total_wait_time
```

**HTML Snapshots** (`snapshots.py`):
- Saves last 50 HTML snapshots per handle
- Enables post-mortem debugging
- Automatic rolling window cleanup

### 2. Data Quality

**Canonical Weekly Schema** (`aggregation/weekly.py`):
```python
CANONICAL_SCHEMA = {
    "columns": [
        {"name": "show", "dtype": "object"},
        {"name": "week_start", "dtype": "object"},  # YYYY-MM-DD
        {"name": "tt_posts", "dtype": "Int64", "nullable": True},
        {"name": "tt_sum_views", "dtype": "Int64", "nullable": True},
        # ... all 18 columns ...
        {"name": "scrape_run_at", "dtype": "object"}
    ]
}
```

**Deduplication**:
- By `post_id` within each run
- Keeps most recent scrape if multiple runs

**Anomaly Detection** (`quality/checks.py`):
- Flags weeks where metric jumps >5× median of prior 8 weeks
- Detects both spikes and drops
- Likely parse changes or data issues

**Coverage Metrics**:
- % non-null by source
- Shows and weeks covered
- Minimum 60% coverage threshold for "OK" status

### 3. Analytics-Ready Features

**Lag Features** (`features/panel_features.py`):
```python
# Advance purchase hypothesis: engagement at t-4 predicts grosses at t
make_lags(df, ['tt_sum_views', 'ig_sum_likes'], lags=[1, 2, 4, 6])
# Creates: tt_sum_views_lag1, tt_sum_views_lag2, tt_sum_views_lag4, ...
```

**Lead Features** (placebo tests):
```python
make_leads(df, ['tt_sum_views'], leads=[4])
# Creates: tt_sum_views_lead4 (should NOT predict past outcomes)
```

**Delta Features** (week-over-week changes):
```python
make_deltas(df, ['tt_sum_views'])
# Creates: tt_sum_views_delta, tt_sum_views_pct_change
```

**Rolling Statistics** (3-week windows):
```python
make_rolling_stats(df, ['tt_sum_views'], window=3)
# Creates: tt_sum_views_roll3_sum, tt_sum_views_roll3_mean
```

**Standardization** (z-scores):
```python
standardize(df, ['tt_sum_views', 'ig_sum_likes'])
# Creates: tt_sum_views_z, ig_sum_likes_z
```

### 4. Reproducibility

**Deterministic Runs**:
- Scrape timestamp recorded in `scrape_run_at` column
- Per-post CSVs saved with date: `{show}_posts_{YYYYMMDD}.csv`
- HTML snapshots archived with timestamp

**Caching** (Google Trends):
- Filesystem cache keyed by query + date range
- Avoids rate limits on repeated runs
- Cache location: `data/cache/google_trends/`

**Idempotent Merges**:
- Duplicate posts dropped by `post_id`
- Schema enforcement ensures consistent dtypes
- Validation checks prevent silent errors

## Usage

### 1. Data Collection

#### Configure Shows
Edit `public_signals/config/shows.yaml`:
```yaml
shows:
  - name: "Oh, Mary!"
    google_queries:
      - "Oh Mary Broadway"
      - "Cole Escola"
    tiktok_handle: "@ohmaryplay"
    instagram_handle: "ohmaryplay"
```

#### Collect Data
```bash
cd public_signals/src/cli

# Collect all sources for 2024 season
python -m public_signals.cli.pull_public_signals \
  --config ../../config/shows.yaml \
  --start 2024-01-01 \
  --end 2024-12-31

# Collect only specific sources
python -m public_signals.cli.pull_public_signals \
  --config ../../config/shows.yaml \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --sources google_trends wikipedia
```

**Output**:
- `data/raw/{source}/{show}_posts_{date}.csv` - Per-post data
- `data/raw_snapshots/{source}/{handle}/{timestamp}.html` - HTML snapshots
- `data/weekly/{source}_weekly.csv` - Weekly aggregates

### 2. Build Canonical Panel

```bash
# Merge all sources into canonical panel
python -m public_signals.cli.make_weekly_panel

# Custom input/output
python -m public_signals.cli.make_weekly_panel \
  --input ../../data/weekly \
  --output ../../data/panel
```

**Output**:
- `data/panel/weekly_social_signals.parquet` - Canonical panel (main)
- `data/panel/weekly_social_signals.csv` - Preview (first 1000 rows)
- `data/panel/weekly_panel_schema.json` - Schema definition

### 3. Validate Data Quality

```bash
# Validate panel
python -m public_signals.cli.validate_social_panel

# Custom thresholds
python -m public_signals.cli.validate_social_panel \
  --anomaly-threshold 3.0

# Suppress console output (JSON only)
python -m public_signals.cli.validate_social_panel --no-print
```

**Checks**:
- ✓ Coverage ≥60% for at least one metric per source
- ✓ Schema matches canonical definition
- ✓ Timestamps are monotonic (no duplicates, sorted)
- ✓ Week binning correct (all Mondays)
- ✓ Anomalies flagged (not failed, but logged)

**Exit Codes**:
- `0`: Validation passed (status OK)
- `1`: Validation failed (status ACTION_NEEDED)
- `2`: Error loading data or running validation

**Output**:
- `data/panel/validation_report.json` - Full report
- Console summary (unless `--no-print`)

### 4. Build Model-Ready Dataset

```bash
# Build with defaults (lags 1,2,4,6 + lead 4)
python -m public_signals.cli.build_model_ready_social

# Custom lags and leads
python -m public_signals.cli.build_model_ready_social \
  --lags 1 2 4 --leads 2 4

# Skip deltas and rolling
python -m public_signals.cli.build_model_ready_social \
  --no-deltas --no-rolling
```

**Output**:
- `data/panel/weekly_social_signals_model_ready.parquet` - Model-ready dataset
- `data/panel/weekly_social_signals_model_ready_preview.csv` - Preview
- `data/panel/weekly_social_signals_model_ready_metadata.json` - Feature summary

### 5. Integration with Causal Analysis

```python
import pandas as pd

# Load model-ready social signals
social_df = pd.read_parquet('public_signals/data/panel/weekly_social_signals_model_ready.parquet')

# Load Broadway grosses (from main pipeline)
grosses_df = pd.read_parquet('data/merged/merged_reddit_grosses_panel.parquet')

# Merge on (show, week_start)
merged = grosses_df.merge(
    social_df,
    on=['show', 'week_start'],
    how='inner'
)

# Run lagged causality analysis
from models.lagged_causality import LaggedCausalityModels

models = LaggedCausalityModels()

# Test: Does TikTok views at t-4 predict grosses at t?
result = models.fit_ols_fe(
    merged,
    outcome='gross',
    predictor='tt_sum_views_lag4',
    controls=['capacity_constraint', 'is_preview', 'week_index']
)

print(f"Coefficient: {result['coefficient']:.2f}")
print(f"P-value: {result['pvalue']:.4f}")
print(f"95% CI: [{result['ci_lower']:.2f}, {result['ci_upper']:.2f}]")
```

## Data Schemas

### TikTok (per-post)
```python
@dataclass
class TikTokPost:
    post_id: str          # Extracted from URL
    post_url: str         # Full URL
    post_datetime: str    # ISO date (YYYY-MM-DD)
    views: int            # View count
    likes: int            # Like count
    comments: int         # Comment count
    shares: int           # Share count
    caption: str          # Post caption
    hashtags: List[str]   # Extracted hashtags
    is_video: bool        # Always True for TikTok
```

### TikTok (weekly aggregate)
```
show | week_start | tt_posts | tt_sum_views | tt_sum_likes | tt_sum_comments |
tt_sum_shares | tt_unique_hashtags | tt_posting_days
```

### Instagram (weekly aggregate)
```
show | week_start | ig_posts | ig_sum_likes | ig_sum_comments |
ig_unique_hashtags | ig_reel_ct | ig_posting_days
```
**Note:** Instagram `ig_sum_likes` and `ig_sum_comments` may be null if hidden.

### Google Trends (weekly aggregate)
```
show | week_start | gt_index | gt_is_partial
```
- `gt_index`: 0-100 interest index (average across queries)
- `gt_is_partial`: True if any query had incomplete data

### Canonical Panel Schema
All sources merged on `(show, week_start)` with outer join.

18 columns total:
- Identifiers: `show`, `week_start`, `scrape_run_at`
- TikTok: 7 metrics + 1 posting days
- Instagram: 5 metrics + 1 posting days
- Google Trends: 2 metrics

## Known Limitations

### 1. TikTok & Instagram Scraping

**Platform Changes**:
- Selectors (`data-e2e="video-views"`) may change
- HTML snapshots enable quick fixes

**Public-Only Data**:
- No authentication means limited data
- Instagram often hides exact counts for non-logged-in users
- Solution: Metrics are nullable; validation flags low coverage

**Rate Limiting**:
- Random delays (2-5s) + exponential backoff usually sufficient
- If blocked: Wait 24 hours and retry
- HTML snapshots preserve data from successful fetches

### 2. Google Trends

**Search Volume Threshold**:
- Queries with low search volume return zeros
- Solution: Use multiple related queries per show
- Aggregate as mean across queries

**Partial Data**:
- Last week often marked as partial (incomplete)
- Flagged in `gt_is_partial` column
- Solution: Exclude partial weeks or re-scrape after week completes

**Geographic Restriction**:
- Currently hardcoded to `US-NY` for Broadway relevance
- Can be changed in `google_trends.py`

### 3. Wikipedia Pageviews

**Article Title Detection**:
- Auto-detects with common suffixes (`_(musical)`, `_(play)`)
- May fail for shows with unusual titles
- Solution: Manually specify `wikipedia_title` in `shows.yaml`

**Bot Traffic**:
- Wikipedia API excludes known bots
- Some automated traffic may remain
- Generally reliable for weekly trends

### 4. Data Quality

**Missing Weeks**:
- Shows may have no posts in some weeks (legitimate zeros vs missing data)
- Solution: Distinguish by checking `scrape_run_at` timestamp

**Anomalies**:
- Threshold of 5× median flags extreme changes
- May be legitimate (viral moment) or parser change
- Solution: Review flagged anomalies manually; HTML snapshots aid debugging

**Coverage**:
- Minimum 60% threshold for "OK" status
- Some sources (Instagram) inherently have lower coverage
- Solution: Use multiple sources; primary analysis on TikTok + Google Trends

### 5. Reproducibility

**Non-Determinism**:
- Playwright may render slightly different content on different runs
- Solution: HTML snapshots allow audit; re-run validation after changes

**Caching**:
- Google Trends cache may become stale
- Solution: Clear cache (`data/cache/`) to force fresh fetches

## Troubleshooting

### Issue: TikTok scraping returns no posts

**Symptoms**: `fetch_profile_posts()` returns empty list

**Possible Causes**:
1. Profile is private or doesn't exist
2. Selector changed (TikTok updated layout)
3. Rate limited

**Solutions**:
1. Verify profile is public at `https://www.tiktok.com/@{handle}`
2. Check HTML snapshot in `data/raw_snapshots/tiktok/{handle}/`
3. Wait 24 hours and retry
4. Update selectors in `tiktok_public.py` if layout changed

### Issue: Validation fails with "ACTION_NEEDED"

**Symptoms**: `validate_social_panel.py` exits with code 1

**Possible Causes**:
1. Coverage below 60% threshold
2. Schema mismatch (e.g., wrong dtypes)
3. Timestamp issues (duplicates, non-monotonic)
4. High anomaly count

**Solutions**:
1. Review `validation_report.json` for specific errors
2. Check `coverage` section - which sources have low coverage?
3. Check `timestamp_issues` - re-run aggregation if issues found
4. Check `anomalies` - review HTML snapshots for flagged weeks

### Issue: Anomalies flagged for legitimate spikes

**Symptoms**: Viral post triggers anomaly flag

**Solution**:
- Anomalies are warnings, not errors
- Review context: Did show go viral? Award win? News coverage?
- Adjust `--anomaly-threshold` if too sensitive (default: 5.0)
- Include anomaly flag as control variable in regression

### Issue: Google Trends returns all zeros

**Symptoms**: `gt_index` is 0 for all weeks

**Possible Causes**:
1. Query has insufficient search volume
2. Time period too narrow
3. Geographic restriction too specific

**Solutions**:
1. Use broader queries (e.g., "Hamilton musical" vs "Hamilton Broadway tickets")
2. Try multiple related queries per show (averages reduce noise)
3. Check `is_partial` flag - if True, re-scrape after week completes

## Testing

Unit tests in `tests/`:

```bash
# Run all tests
pytest tests/

# Specific test modules
pytest tests/test_aggregation.py
pytest tests/test_features.py
pytest tests/test_quality.py
```

**Test Coverage**:
- `test_aggregation.py`: Week binning, deduplication, schema enforcement
- `test_features.py`: Lags, leads, deltas, rolling stats, z-scores
- `test_quality.py`: Coverage calculation, anomaly detection, validation

## Maintenance

### Weekly Refresh
```bash
# 1. Pull latest data (incremental update)
python -m public_signals.cli.pull_public_signals \
  --config config/shows.yaml \
  --start $(date -d '45 days ago' +%Y-%m-%d) \
  --end $(date +%Y-%m-%d)

# 2. Rebuild panel
python -m public_signals.cli.make_weekly_panel

# 3. Validate
python -m public_signals.cli.validate_social_panel

# 4. Build model-ready
python -m public_signals.cli.build_model_ready_social
```

### Selector Updates (TikTok/Instagram)

When platform changes selectors:

1. Check HTML snapshot: `data/raw_snapshots/{source}/{handle}/latest.html`
2. Identify new selector in browser DevTools
3. Update `{source}_public.py`:
   ```python
   # Old
   views_elem = await page.query_selector('[data-e2e="video-views"]')

   # New
   views_elem = await page.query_selector('[data-testid="video-view-count"]')
   ```
4. Re-run scraper and validate

### Cache Maintenance

Clear caches periodically:

```bash
# Clear Google Trends cache (force fresh fetches)
rm -rf public_signals/data/cache/google_trends/

# Clear old HTML snapshots (manual cleanup if needed)
find public_signals/data/raw_snapshots/ -type f -mtime +30 -delete
```

## License

This system is for **academic research purposes**. When using:
1. Cite data sources appropriately
2. Respect rate limits and robots.txt
3. Do not use for commercial purposes without permission
4. Share findings publicly (open science principles)

## Support

For issues:
1. Check `validation_report.json` for specific errors
2. Review HTML snapshots in `data/raw_snapshots/`
3. Check logs in console output
4. Verify `shows.yaml` configuration
5. Clear caches and retry

---

**Built for:** Oh, Mary! CMM Analysis Project
**Pipeline Version:** 2.0 (Production-Grade)
**Status:** ✓ Production-ready

# Broadway Marketing Analysis - 2024-2025 Season

Comprehensive analysis of Broadway marketing effectiveness combining Reddit fan engagement with box office performance data.

## Overview

This project analyzes **40+ Broadway shows** from the 2024-2025 Tony season to understand:

1. **WHAT** metrics differentiate successful vs unsuccessful campaigns (statistical analysis)
2. **WHY** certain campaigns succeed - themes, content, messaging (qualitative analysis)
3. **HOW** fan engagement correlates with financial success (correlation analysis)

## Shows Analyzed

### Original Plays (14)
- All In: Comedy About Love
- Cult of Love
- English
- Good Night, and Good Luck
- The Hills of California
- Job
- John Proctor is the Villain ⭐
- Left on Tenth
- McNeal
- Oh Mary! ⭐
- The Picture of Dorian Gray
- The Purpose
- The Roommate
- Stranger Things: The First Shadow

### Original Musicals (14)
- A Wonderful World
- Boop!
- Buena Vista Social Club
- The Dead Outlaw
- Death Becomes Her
- Just in Time
- Maybe Happy Ending ⭐
- Operation Mincemeat
- Real Women Have Curves
- Redwood
- Smash
- The Old Friends
- Swept Away
- Tammy Faye

### Play Revivals (7)
- Eureka Day
- Glengarry Glen Ross
- Home
- Othello
- Our Town
- Romeo + Juliet
- Yellow Face

### Musical Revivals (7)
- Elf The Musical
- Floyd Collins
- Gypsy
- The Last Five Years
- Once Upon a Mattress
- The Pirates of Penzance
- Sunset Boulevard

⭐ = Initially identified as successful campaigns

## What This Analysis Does

### 1. Reddit Data Collection
- Scrapes Reddit posts and comments for all shows
- Searches 11 curated subreddits (Broadway, musicals, theatre, NYC, LGBTQ+, entertainment)
- Collects: upvotes, comments, sentiment, engagement metrics
- Time period: Last 12 months

### 2. Broadway Box Office Data Collection
- Scrapes weekly grosses from BroadwayWorld.com JSON API
- Uses `json_grosses.cfm` endpoint (more reliable than HTML scraping)
- Covers full 2024-2025 Tony season (April 2024 - present)
- Collects: weekly gross revenue, capacity %, average ticket price, attendance, performances

### 3. Statistical Analysis (WHAT)
- Extracts 30+ metrics per show from Reddit data
- Performs t-tests comparing successful vs unsuccessful campaigns
- Calculates effect sizes (Cohen's d) and confidence intervals
- Identifies which metrics significantly differentiate success/failure

### 4. Qualitative Analysis (WHY)
- Analyzes conversation themes (performance, creative, emotional, identity, etc.)
- Identifies viral content characteristics
- Examines audience language patterns and tone
- Discovers what messaging resonates with communities

### 5. Correlation Analysis (Reddit vs Grosses)
- Merges Reddit engagement data with box office performance
- Calculates correlations between social metrics and financial success
- Identifies over/underperformers (shows that defy the buzz-to-revenue pattern)
- Analyzes patterns by show type (original vs revival, play vs musical)

## Installation

### Requirements
- Python 3.8+
- Mac or Linux (Windows with WSL)

### Setup

1. Clone the repository:
```bash
cd /path/to/oh_mary_cmm_analysis
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Verify configuration:
```bash
cat config/config.yaml
```

## Running the Complete Analysis

### Option 1: Run Everything (Recommended)

```bash
python3 run_success_failure_analysis.py
```

This runs all 5 steps sequentially:
1. Reddit data collection (2-3 hours)
2. Broadway grosses scraping (10-15 minutes)
3. Statistical analysis (5-10 minutes)
4. Qualitative analysis (5-10 minutes)
5. Correlation analysis (2-3 minutes)

**Total time: ~2.5-3.5 hours**

### Option 2: Run Individual Scripts

If you want to run steps separately:

```bash
# Step 1: Collect Reddit data
python3 multi_show_reddit_scraper.py

# Step 2: Scrape Broadway grosses
python3 broadway_grosses_scraper.py

# Step 3: Statistical analysis
python3 marketing_science_analysis.py

# Step 4: Qualitative analysis
python3 why_campaigns_succeed_analysis.py

# Step 5: Correlation analysis
python3 reddit_grosses_correlation_analysis.py
```

### Option 3: Simple Marketing Effectiveness (Alternative)

For a simpler analysis without complex statistics:

```bash
python3 marketing_effectiveness_analysis.py
```

This provides straightforward engagement, reach, sentiment, and word-of-mouth scores.

## Output Files

### Reddit Data
```
data/raw/
├── reddit_oh_mary.csv
├── reddit_john_proctor.csv
├── reddit_maybe_happy_ending.csv
└── ... (40+ files)
```

### Box Office Data
```
data/grosses/
├── broadway_grosses_2024_2025.csv    # Weekly data
└── grosses_summary.csv                # Summary by show
```

### Analysis Reports
```
outputs/
├── marketing_science_all_metrics.csv          # All metrics for all shows
├── statistical_comparison.csv                 # T-test results
├── marketing_science_report.json              # Statistical analysis JSON
├── why_campaigns_succeed_report.md            # Qualitative insights
├── why_analysis_raw_data.json                 # Theme and pattern data
├── reddit_grosses_correlation_report.md       # Correlation analysis
├── merged_reddit_grosses.csv                  # Combined dataset
├── reddit_grosses_correlation.png             # Visualizations
└── correlation_analysis_data.json             # Raw correlation data
```

## Key Questions Answered

### 1. WHAT differs between successful and unsuccessful campaigns?

**See:** `outputs/statistical_comparison.csv`

Find out:
- Which Reddit metrics are statistically different
- Effect sizes (how big the differences are)
- Statistical significance (p-values)
- Confidence intervals

### 2. WHY do some campaigns succeed?

**See:** `outputs/why_campaigns_succeed_report.md`

Discover:
- What themes dominate conversations (performance quality, emotional impact, identity resonance)
- What language patterns indicate success (personal vs collective voice)
- What content characteristics make posts go viral
- What types of conversations generate buzz

### 3. How does fan engagement correlate with financial success?

**See:** `outputs/reddit_grosses_correlation_report.md`

Learn:
- Which Reddit metrics predict box office performance
- Correlation coefficients and significance levels
- Over/underperformers (shows defying expectations)
- Patterns by show type (original plays vs musicals vs revivals)

## Configuration

### Adding/Removing Shows

Edit `config/config.yaml`:

```yaml
shows:
  show_id:
    name: "Show Name"
    show_type: "original_play|original_musical|play_revival|musical_revival"
    category: "successful|unsuccessful|unknown"
    keywords:
      - "Keyword 1"
      - "Keyword 2"
```

### Adjusting Search Parameters

```yaml
reddit:
  subreddits:
    - broadway
    - musicals
    # Add more subreddits

limits:
  reddit_posts_per_subreddit: 100  # Adjust for faster/slower scraping
```

## Technical Details

### Reddit API
- Uses PRAW (Python Reddit API Wrapper)
- Credentials hardcoded in `multi_show_reddit_scraper.py`
- Rate limited to avoid API restrictions
- Searches 11 verified subreddits
- Only uses first keyword per show to reduce API calls

### BroadwayWorld Scraping
- Uses JSON API endpoint (`json_grosses.cfm`) instead of HTML page scraping
- BeautifulSoup parses HTML fragments from API responses
- Respectful rate limiting (0.5 second delays between weeks)
- Fetches both musicals and plays for each week
- Matches show names to config via exact and keyword matching

### Statistical Methods
- T-tests for comparing group means
- Cohen's d for effect size
- 95% confidence intervals
- Pearson and Spearman correlations

### Qualitative Methods
- Theme extraction via keyword matching
- Sentiment analysis using word lists
- Viral content pattern identification
- Language tone analysis (personal vs collective voice)

## Troubleshooting

### Reddit Scraper Hangs
- Reduced to 25 posts per subreddit to prevent hanging
- If still hanging, reduce `reddit_posts_per_subreddit` in config.yaml

### No Grosses Data / Missing Shows
- **Script now uses BroadwayWorld JSON API** (much more reliable than HTML scraping)
- If no data is found:
  1. Check network connectivity
  2. Verify the API endpoint is still available: https://www.broadwayworld.com/json_grosses.cfm
  3. Try running `broadway_grosses_scraper.py` directly to see detailed error messages
- If some shows are missing:
  - Show names in config.yaml may not match BroadwayWorld's naming
  - Check `match_show_to_config()` function in `broadway_grosses_scraper.py`
  - Add alternative keywords to config.yaml for better matching
  - Check BroadwayWorld website to see exact show names used

### Correlation Analysis Shows "No Data"
- Ensure both Reddit and grosses data exist
- Run `multi_show_reddit_scraper.py` first
- Then run `broadway_grosses_scraper.py`
- Then run correlation analysis

### Import Errors (scipy, etc.)
- scipy is optional - code will work without it
- If issues persist, check `requirements.txt` compatibility
- Mac M1/M2: Use simplified requirements (no Fortran dependencies)

## Project Structure

```
oh_mary_cmm_analysis/
├── config/
│   └── config.yaml                              # Show configuration
├── data/
│   ├── raw/                                     # Reddit data (CSV)
│   └── grosses/                                 # Box office data (CSV)
├── outputs/                                     # Analysis reports
├── multi_show_reddit_scraper.py                # Reddit data collection
├── broadway_grosses_scraper.py                 # Box office scraper
├── marketing_science_analysis.py               # Statistical analysis
├── why_campaigns_succeed_analysis.py           # Qualitative analysis
├── reddit_grosses_correlation_analysis.py      # Correlation analysis
├── marketing_effectiveness_analysis.py         # Simple alternative
├── run_success_failure_analysis.py             # Master orchestrator
├── requirements.txt                             # Python dependencies
└── README.md                                    # This file
```

## Future Enhancements

Potential additions:
- TikTok and Instagram data collection
- Sentiment analysis using ML models (BERT, etc.)
- Time series analysis (how buzz changes over run)
- Predictive modeling (predict grosses from early Reddit activity)
- Topic modeling (LDA, BERTopic)
- Network analysis (community detection, influencer identification)

## Credits

**Data Sources:**
- Reddit (via PRAW API)
- BroadwayWorld.com (public box office data)

**Analysis Framework:**
- Statistical methods: scipy, scikit-learn
- Visualization: matplotlib, seaborn
- Data processing: pandas, numpy

**2024-2025 Broadway Season Coverage**
- Original research analyzing 40+ shows
- Combining social media analytics with financial performance
- PhD-level comparative analysis methodology

---

**Last Updated:** November 2025
**Season:** 2024-2025 Tony Awards Season

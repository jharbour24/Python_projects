# Oh Mary! CMM Analysis — Usage Guide

Complete guide for running Cultural Movement Marketing (CMM) analysis on "Oh Mary!" Broadway show.

## Quick Start

```bash
# 1. Navigate to project directory
cd oh_mary_cmm_analysis

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run analysis
python src/main.py
```

## Data Collection Options

The analysis pipeline supports three data collection methods:

### Option 1: Automated Collection (Recommended if APIs are available)

**Reddit (PRAW):**
```bash
# Install PRAW
pip install praw

# Configure in src/scrapers/reddit_scraper.py
client_id='YOUR_CLIENT_ID'
client_secret='YOUR_CLIENT_SECRET'
user_agent='oh_mary_cmm_analysis:v1.0 (by /u/YOUR_USERNAME)'

# Get credentials at: https://www.reddit.com/prefs/apps
```

### Option 2: Manual Data Collection (Most Reliable)

The pipeline creates CSV templates for manual entry:

**Reddit Template:** `data/raw/reddit_manual_template.csv`
```csv
id,title,text,author,subreddit,score,num_comments,url,created_utc,comments_json
```

**TikTok Template:** `data/raw/tiktok_manual_template.csv`
```csv
video_id,url,author,caption,hashtags,likes,comments,shares,views,created_at,top_comments
```

**Instagram Template:** `data/raw/instagram_manual_template.csv`
```csv
post_id,url,author,caption,hashtags,likes,comments_count,created_at,post_type,top_comments
```

**How to manually collect:**
1. Search platforms for keywords: "#OhMary", "Oh Mary Broadway", etc.
2. Document top 50-100 posts/videos
3. Fill in template CSV files
4. Save as `reddit_manual.csv`, `tiktok_manual.csv`, `instagram_manual.csv` in `data/raw/`
5. Run analysis

### Option 3: Third-Party APIs

**TikTok:**
- Apify: https://apify.com/clockworks/tiktok-scraper
- RapidAPI: https://rapidapi.com/ti-services/api/tiktok-scraper7

**Instagram:**
- Apify: https://apify.com/apify/instagram-scraper
- Instagram Basic Display API (requires Facebook App)

## Understanding the Outputs

### 1. Main Report (`outputs/reports/report.md`)

Comprehensive markdown report including:
- **Overall CMM Score** (0-100): Movement marketing strength
- **Movement Behaviors Detected**: At least 3 identified patterns
- **Detailed Metrics**: All 8 CMM metrics with interpretations
- **Evidence Examples**: Real quotes with URLs and timestamps
- **Counter-Signals**: Negative/mixed sentiment documentation
- **Strategic Implications**: Actionable recommendations for producers

**Score Interpretation:**
- **70-100**: DEFINITIVE MOVEMENT — Audiences speak as if this is a movement
- **50-69**: STRONG MOVEMENT — Clear CMM patterns detected
- **30-49**: MODERATE MOVEMENT — Some movement characteristics
- **0-29**: LIMITED MOVEMENT — Functions primarily as entertainment

### 2. Metrics JSON (`outputs/reports/metrics.json`)

Machine-readable metrics including:
- All 8 CMM scores
- Statistical significance tests
- Confidence intervals (95%)
- Sample sizes

### 3. Visualizations (`outputs/visualizations/`)

8 publication-quality charts:
- **CMM Dashboard**: All metrics at a glance
- **Discourse Distribution**: Breakdown by discourse type
- **Movement Score Distribution**: Audience movement behavior histogram
- **Platform Comparison**: Cross-platform analysis
- **Temporal Trends**: Movement signal over time
- **Engagement Analysis**: Movement score vs engagement
- **Pronoun Analysis**: We/I ratio (collective vs individual voice)
- **Discourse Clusters**: NLP clustering visualization

### 4. Data Files (`data/processed/`)

**`audience_discourse.csv`**: Post-level analysis
- All extracted features
- Discourse labels (movement_framing, identity_resonance, etc.)
- Movement scores
- Sentiment analysis
- Engagement metrics

**`memes_catalog.csv`**: Mimetic motifs
- Repeated phrases/patterns
- Frequency counts
- Viral half-life estimates

**`community_signals.csv`**: Community formation evidence
- Rush line mentions
- Lottery references
- Meetup organization
- Fan community indicators

### 5. Assumption Log (`outputs/reports/assumption_log.md`)

Documents:
- Data collection limitations
- Methodological decisions
- Known biases
- Uncertainty sources

## The 8 CMM Metrics Explained

### 1. Movement Sentiment Score (MSS)
**What it measures:** Engagement lift when audiences use collective ("we/us") vs individual ("I/me") language.

**Interpretation:**
- High MSS = Collective framing drives more engagement
- Indicates audiences identify as part of a movement

### 2. Identity Resonance Index (IRI)
**What it measures:** Frequency + engagement of "felt seen/represented" language.

**Interpretation:**
- High IRI = Show functions as identity/representation space
- Key CMM signal: Show meets identity needs, not just entertainment needs

### 3. Evangelism Ratio (ER)
**What it measures:** Percentage of posts urging others to attend.

**Interpretation:**
- High ER = Audiences act as unpaid marketers
- Movement behavior: Spreading the word becomes part of fan identity

### 4. Repeat Attendance Signal (RAS)
**What it measures:** Percentage mentioning 2+ viewings or future intent.

**Interpretation:**
- High RAS = Show functions as ritual/pilgrimage
- Repeat viewing signals necessity framing

### 5. Belonging Intensity Score (BIS)
**What it measures:** NLP measure of belonging/emotional significance words.

**Interpretation:**
- High BIS = Audiences speak in belonging/community language
- Shows create "found family" or "safe space" dynamics

### 6. Gatekeeping & Insider Markers (GIM)
**What it measures:** "If you know you know," inside jokes, insider culture.

**Interpretation:**
- High GIM = Distinct in-group/out-group boundaries
- Cultural insiderism typical of movements

### 7. Community Formation Signals (CFS)
**What it measures:** Evidence of rush line communities, meetups, organized fandom.

**Interpretation:**
- High CFS = Formal/informal fan infrastructure emerging
- Shows spawning self-organizing communities

### 8. Mimetic Propagation Index (MPI)
**What it measures:** Persistence and spread of audience-generated memes/motifs.

**Interpretation:**
- High MPI = Memetic/viral spread patterns
- Audiences creating shared cultural artifacts

## Configuration

Edit `config/config.yaml` to customize:

```yaml
# Keywords to search
keywords:
  - "Oh Mary!"
  - "#OhMary"
  - "Cole Escola"
  # Add more...

# Subreddits to search
reddit:
  subreddits:
    - broadway
    - musicals
    - LGBT
    # Add more...

# Movement language lexicon
movement_lexicon:
  collective_pronouns: ["we", "us", "our"]
  belonging_terms: ["community", "family", "felt seen"]
  necessity_terms: ["must see", "need to", "essential"]
  # Customize lexicon...
```

## Advanced Usage

### Running with Real Data

```bash
# 1. Collect data (manually or via APIs)
# 2. Save to data/raw/ with correct filenames
# 3. Run analysis
python src/main.py

# Analysis will automatically:
# - Detect available data sources
# - Process all platforms
# - Generate comprehensive outputs
```

### Analyzing Other Shows

```bash
# 1. Copy project directory
cp -r oh_mary_cmm_analysis new_show_analysis

# 2. Edit config/config.yaml
show: "Show Name"
keywords:
  - "Show Name"
  - "#ShowNameHashtag"

# 3. Run analysis
python src/main.py
```

### Installing Optional NLP Models

For advanced NLP features (embeddings, sentiment):

```bash
pip install sentence-transformers transformers torch textblob
```

These enable:
- Semantic clustering of discourse
- Deep sentiment analysis
- More accurate movement detection

## Interpreting Results for Strategy

### If CMM Score ≥ 70 (Definitive Movement)

**Strategic Implications:**
1. **Amplify fan voices** — User-generated content is your best marketing
2. **Build community infrastructure** — Formalize rush lines, create fan spaces
3. **Enable identity expression** — Merch/content for fans to signal belonging
4. **Facilitate evangelism** — Referral programs, group discounts
5. **Extend the ritual** — Tours, revivals, extensions

**Example Shows:** Hamilton, Dear Evan Hansen (peak), Rent

### If CMM Score 50-69 (Strong Movement)

**Strategic Implications:**
1. **Strengthen identity connections** — Emphasize representation in marketing
2. **Support repeat attendance** — Lottery, membership programs
3. **Encourage word-of-mouth** — Social campaigns amplifying fan content
4. **Test community features** — Pilot meetups, fan events

**Example Shows:** Hadestown, Six, Be More Chill

### If CMM Score 30-49 (Moderate Movement)

**Strategic Implications:**
1. **Identify core constituencies** — Who shows movement behaviors?
2. **Lower repeat barriers** — Affordable return options
3. **Test movement messaging** — Does community framing resonate?

### If CMM Score < 30 (Limited Movement)

**Strategic Implications:**
1. **Traditional PR** — Focus on reviews, quality, star power
2. **Demographic targeting** — Niche movement may exist
3. **Monitor emergence** — CMM can develop over time

## Troubleshooting

### "No data collected" Error
**Solution:** The analysis will run in DEMO MODE with synthetic data to demonstrate the pipeline. To analyze real data, manually collect and add CSV files to `data/raw/`.

### "NLP models not available" Warning
**Solution:** This is optional. Analysis runs with lexicon-based methods. For advanced NLP, install: `pip install sentence-transformers textblob`

### "PRAW not installed" Warning
**Solution:** This is expected. Install `pip install praw` and configure API credentials, or use manual collection.

### Small Sample Size Warnings
**Solution:** Collect more data. CMM analysis is most reliable with 100+ posts per platform.

## Citation

If using this analysis in research or publications:

```
Oh Mary! Cultural Movement Marketing Analysis
Framework: Cultural Movement Marketing (CMM)
Method: Multi-platform discourse analysis with NLP
Date: 2024-2025
```

## Support

For questions or issues:
- Review `assumption_log.md` for documented limitations
- Check data collection templates in `data/raw/`
- Verify config.yaml settings
- Ensure sufficient sample size (100+ posts recommended)

## Next Steps

After running analysis:
1. Review `outputs/reports/report.md` for key findings
2. Examine visualizations in `outputs/visualizations/`
3. Share metrics JSON with stakeholders
4. Implement strategic recommendations
5. Monitor trends over time (re-run monthly)

---

**Remember:** You are analyzing audience effects, not marketing intentions. The question is whether fans *speak and behave* as if this is a movement, regardless of what the marketing team intended.

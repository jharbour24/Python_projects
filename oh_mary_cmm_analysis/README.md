# Broadway Campaign Effectiveness Analysis

A computational sociology study comparing Cultural Movement Marketing (CMM) effects across multiple Broadway shows using Reddit discourse analysis.

## 🎭 Shows Analyzed

1. **Oh Mary!**
2. **John Proctor is the Villain**
3. **Maybe Happy Ending**

## 🚀 Quick Start (Complete Pipeline)

**One command to run everything:**

```bash
cd oh_mary_cmm_analysis
python run_full_analysis.py
```

This will:
1. ✅ Collect Reddit data for all three shows (20-40 min)
2. ✅ Analyze discourse and calculate CMM metrics (5 min)
3. ✅ Generate comparative visualizations (2 min)
4. ✅ Create comprehensive report (1 min)

**Total time:** ~30-60 minutes (mostly waiting for Reddit API)

---

## Research Question

**Which Broadway show generated the most effective Cultural Movement Marketing campaign?**

We measure whether audiences discuss shows as movements, identity spaces, or cultural necessities — rather than just entertainment.

---

## Manual Workflow (Step by Step)

If you prefer to run each step manually:

### Step 1: Collect Reddit Data

```bash
python multi_show_reddit_scraper.py
```

This searches 30+ subreddits for all three shows and saves data to `data/raw/`.

**Time:** 20-40 minutes (Reddit API rate limits)

### Step 2: Run Analysis

```bash
python run_comparative_analysis.py
```

This processes discourse, calculates CMM metrics, and creates comparative summary.

**Time:** 5 minutes

### Step 3: Generate Visualizations

```bash
python generate_comparative_visualizations.py
```

This creates charts comparing all three shows across metrics.

**Time:** 2 minutes

### Step 4: Generate Report

```bash
python generate_comparative_report.py
```

This creates a comprehensive markdown report with findings and recommendations.

**Time:** 1 minute

---

## 📊 Outputs

After running the analysis, you'll find:

### Reports
- **`outputs/reports/comparative_analysis_report.md`** — Full analysis with rankings and insights
- **`outputs/comparative_summary.csv`** — Quick comparison table

### Visualizations
- **`outputs/visualizations/overall_comparison.png`** — Overall CMM scores
- **`outputs/visualizations/metrics_heatmap.png`** — All metrics heatmap
- **`outputs/visualizations/radar_comparison.png`** — Radar chart
- **`outputs/visualizations/metric_*.png`** — 8 individual metric charts

### Data
- **`data/raw/reddit_*.csv`** — Raw Reddit data per show
- **`data/processed/*_processed.csv`** — Processed data with discourse features
- **`outputs/detailed_results.json`** — Complete metrics in JSON format

---

## 📋 Requirements

### Python Dependencies

Install all requirements:

```bash
pip install -r requirements.txt
```

Core dependencies:
- `praw` — Reddit API
- `pandas` — Data processing
- `pyyaml` — Configuration
- `matplotlib` — Visualizations
- `seaborn` — Charts
- `nltk` — Natural language processing
- `scikit-learn` — Machine learning

### Reddit API

✅ **Already configured!** The script uses pre-configured Reddit credentials.

If you need to use your own:
1. Create app at https://www.reddit.com/prefs/apps
2. Update credentials in `multi_show_reddit_scraper.py`

---

## 🎯 Cultural Movement Marketing (CMM) Framework

### What is CMM?

CMM measures whether audiences treat entertainment as a **movement** vs. just a product.

### 8 Core Metrics

| Metric | Abbreviation | Measures |
|--------|--------------|----------|
| Movement Sentiment Score | MSS | Collective voice engagement lift |
| Identity Resonance Index | IRI | Personal identity connection |
| Evangelism Ratio | ER | Sharing & recommendation behavior |
| Repeat Attendance Signal | RAS | Multiple viewing indicators |
| Belonging Intensity Score | BIS | Community & belonging language |
| Gatekeeping Markers | GIM | Insider culture signals |
| Community Formation Signals | CFS | Social bonding patterns |
| Mimetic Propagation Index | MPI | Viral quote/meme spread |

**Overall CMM Score:** Average of all 8 metrics (0-100 scale)

### Score Interpretation

- **70-100:** Strong movement characteristics
- **50-69:** Moderate movement signals
- **30-49:** Weak movement formation
- **0-29:** Minimal movement discourse

---

## 📁 Project Structure

```
oh_mary_cmm_analysis/
├── config/
│   └── config.yaml                      # Show configs & subreddit list
├── src/
│   └── analysis/
│       ├── discourse_extractor.py       # Extract movement language
│       ├── cmm_metrics.py               # Calculate 8 metrics
│       └── nlp_engine.py                # NLP analysis
├── data/
│   ├── raw/                             # Collected Reddit data
│   └── processed/                       # Processed data with features
├── outputs/
│   ├── reports/                         # Markdown reports
│   ├── visualizations/                  # Charts and graphs
│   ├── comparative_summary.csv          # Quick comparison table
│   └── detailed_results.json            # Complete metrics
├── multi_show_reddit_scraper.py         # Data collection script
├── run_comparative_analysis.py          # Analysis pipeline
├── generate_comparative_visualizations.py  # Visualization generator
├── generate_comparative_report.py       # Report generator
└── run_full_analysis.py                 # Complete pipeline orchestrator
```

---

## 🔧 Configuration

Edit `config/config.yaml` to:

- Add/remove shows
- Change keywords for each show
- Modify subreddit list
- Adjust search parameters

Example:

```yaml
shows:
  oh_mary:
    name: "Oh Mary!"
    keywords:
      - "Oh Mary!"
      - "Cole Escola"
      # ... more keywords

reddit:
  subreddits:
    - broadway
    - musicals
    # ... 30+ subreddits
```

---

## 📊 Data Collection Details

### Subreddits Searched

**30+ communities including:**

- **Theater:** broadway, musicals, theatre, theater, OffBroadway
- **NYC:** nyc, AskNYC, newyork, manhattan
- **LGBTQ+:** lgbt, gaybros, askgaybros, gay, rupaulsdragrace
- **Arts:** entertainment, acting, comedy, arts, culture
- **General:** AskReddit, movies, CasualConversation

### Data Points Collected

For each Reddit post:
- Post title and text
- Author, subreddit, score
- Comments (top 25 per post)
- Timestamps, URLs
- Upvote ratio, comment count

### Privacy & Ethics

- ✅ Public data only (no private subreddits)
- ✅ Reddit API compliant
- ✅ No personal information stored
- ✅ Respects platform ToS

---

## 💡 Example Results

After analysis, you might see:

```
COMPARATIVE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Show                           CMM Score   Posts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Oh Mary!                         68.5      247
John Proctor is the Villain      52.3      89
Maybe Happy Ending               61.2      134

🏆 Most Effective Campaign: Oh Mary!
```

---

## 🛠️ Troubleshooting

### "PRAW not installed"

```bash
pip install praw
```

### "No data found for show"

The scraper may not have found Reddit posts. Try:
1. Run scraper again (different API limits)
2. Add more keywords in `config/config.yaml`
3. Expand date range in config

### "Rate limit exceeded"

Reddit API has rate limits. The scraper includes delays, but you may need to:
- Wait 10 minutes
- Run again (it will continue)

### Missing visualizations

```bash
pip install matplotlib seaborn
```

### Old data interfering with new analysis

If you want to start completely fresh:

```bash
python clean_data.py
```

Type `DELETE` when prompted. This removes all previous data, outputs, and reports.

**Note:** The `run_full_analysis.py` script will automatically prompt you to clean old data before starting.

---

## 📚 Documentation

- **This README** — Overview and quick start
- **`outputs/reports/comparative_analysis_report.md`** — Full analysis findings
- **`AUTOMATION_SUMMARY.md`** — Previous automation work (legacy)
- **`AUTOMATED_COLLECTION_GUIDE.md`** — TikTok/Instagram guides (legacy)

---

## 🎓 Methodology

### Discourse Analysis

Uses lexicon-based extraction to identify:
- Collective pronouns (we, us, our)
- Belonging terms (community, family, home)
- Necessity language (must see, essential)
- Identity markers (queer, theater kid)
- Evangelism phrases (you have to see)
- Repeat signals (second time, going back)

### Statistical Analysis

- Bootstrap confidence intervals (95%)
- T-tests for significance
- Effect size calculations
- Comparative ranking

### NLP Features

- Transformer embeddings (sentence-transformers)
- Topic clustering
- Sentiment analysis
- Pronoun shift detection (I→we)

---

## 📈 Use Cases

### For Producers
- Benchmark campaign effectiveness
- Identify successful marketing tactics
- Understand audience engagement patterns

### For Marketers
- Learn what drives movement behavior
- Optimize community-building strategies
- Measure cultural impact beyond tickets

### For Researchers
- Study cultural movement formation
- Analyze social media discourse
- Measure entertainment as identity space

---

## ⚠️ Limitations

1. **Reddit-only analysis** — Doesn't include TikTok/Instagram
2. **English language only** — Non-English posts excluded
3. **Public data only** — Private communities not accessible
4. **Past 12 months** — Limited historical context
5. **Correlation not causation** — High CMM doesn't prove campaign caused it

---

## 🚀 Quick Reference

**Run everything:**
```bash
python run_full_analysis.py
```

**Just collect data:**
```bash
python multi_show_reddit_scraper.py
```

**Just analyze (if data exists):**
```bash
python run_comparative_analysis.py
python generate_comparative_visualizations.py
python generate_comparative_report.py
```

**View results:**
```bash
cat outputs/reports/comparative_analysis_report.md
open outputs/visualizations/
```

**Clean all old data (start fresh):**
```bash
python clean_data.py
```
This removes all previous data, outputs, and reports to ensure a clean slate.

---

## 📞 Support

If you encounter issues:

1. Check `data/raw/collection_summary.json` for collection stats
2. Review `outputs/detailed_results.json` for metric details
3. Verify all dependencies: `pip install -r requirements.txt`

---

## 📄 License

Research and educational use.

---

**Created:** 2024
**Analysis Platform:** Reddit API via PRAW
**Framework:** Cultural Movement Marketing (CMM)
**Shows:** Oh Mary! | John Proctor is the Villain | Maybe Happy Ending

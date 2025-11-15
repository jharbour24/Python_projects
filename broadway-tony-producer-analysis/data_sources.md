# Data Sources Documentation

This document provides detailed information about all data sources used in the Broadway Tony Producer Analysis.

---

## 1. Tony Awards Nominations and Wins

### Source
**Wikipedia - Tony Awards Year Pages**

Example URLs:
- 65th Tony Awards (2011): https://en.wikipedia.org/wiki/65th_Tony_Awards
- 75th Tony Awards (2022): https://en.wikipedia.org/wiki/75th_Tony_Awards

### Coverage
- Years: 2011 (65th) through present
- Updates: Annual (after each Tony ceremony, typically in June)

### Data Collected
For each nominated show:
- Show title
- Tony year (year of ceremony)
- Season (e.g., "2010-2011")
- Category (Best Musical, Best Play, Best Revival, acting/technical categories)
- Nomination status (all nominees)
- Win status (winners marked)

### Methodology
- **Scraper:** `data/scrape_tonys.py`
- **Strategy:**
  - Iterate through Tony years 2011-present
  - For each year, construct Wikipedia URL based on ordinal (65th, 66th, etc.)
  - Parse HTML for category headings (h2, h3 tags)
  - Extract nominee lists (typically in `<ul>` or `<table>` elements)
  - Identify winners by text patterns: "(winner)", "WINNER", etc.

### Aggregation
Raw nominations are aggregated to show level:
- `tony_nom_count`: Count of nominations per show
- `tony_win_count`: Count of wins per show
- `tony_win_any`: Binary indicator (1 if any wins)
- `tony_major_win`: Binary indicator (1 if won Best Musical/Play/Revival)

### Data Quality Notes
- **Accuracy:** Wikipedia is community-maintained; generally accurate for major awards
- **Verification:** Cross-reference with official TonyAwards.com when possible
- **Title Variations:** Show titles normalized for matching (see `utils/matching.py`)
- **Limitations:**
  - Does not capture nominations in all technical categories (focus on major categories)
  - Some years may have structural differences in Wikipedia pages

### Alternative Sources (for future enhancement)
- Official Tony Awards website (TonyAwards.com)
  - May require more complex scraping or API access
  - More authoritative but potentially less structured
- Internet Broadway Database (IBDB) Tony section
  - Provides show-level Tony history
  - Could serve as validation

### Update Frequency
- Annual update required after each Tony ceremony (typically June)
- Historical data stable (unlikely to change)

---

## 2. Producer Credits

### Source
**Internet Broadway Database (IBDB)**

Website: https://www.ibdb.com/

### Coverage
- Comprehensive Broadway production data
- Historical coverage back to 1900s
- Updated regularly

### Data Collected
For each show:
- Producer names (full list)
- Lead producers (when distinguished)
- Co-producers (when distinguished)
- Associate producers (when applicable)
- Source URL (IBDB show page)

### Methodology
- **Scraper:** `data/scrape_producers.py`
- **Strategy:**
  1. For each show from Tony outcomes, search IBDB
  2. Construct search URL or direct show URL
  3. Parse show page for "Produced by" section
  4. Extract producer names from HTML
  5. Parse and clean producer names:
     - Split by delimiters (comma, semicolon, "and")
     - Remove duplicate entries
     - Distinguish lead vs co-producers based on section headings
  6. Count: total, lead, co-producer counts

### Parsing Rules
- **Producer name cleaning:**
  - Remove suffixes (Jr., Sr., III, II, etc.)
  - Normalize whitespace
  - Handle LLCs and corporate entities as single producers
- **Lead vs Co-producer distinction:**
  - Look for explicit section headings: "Lead Producer(s)", "Co-Producer(s)"
  - If no distinction, classify all as lead producers (conservative)

### Data Quality Notes
- **Completeness:** Not all shows may have producer data on IBDB
- **Scraping success rate:** Logged in `scrape_success` column
- **Name variations:** Same producer may appear with slight name variations
- **Entity types:** Mix of individuals and production companies
- **Limitations:**
  - Producer role definitions may vary across shows
  - Some shows may list dozens of producers (mega-productions like musicals)
  - Limited information on producer hierarchy or financial contribution

### Known Issues
- IBDB website structure may change, breaking scraper
- Some shows may have redirect URLs or non-standard pages
- Rate limiting required (1.5 second delay between requests)

### Alternative Sources (for future enhancement)
- **Playbill Vault** (https://www.playbillvault.com/)
  - Similar data to IBDB
  - Could serve as validation or backup
- **Official show programs/websites**
  - Most authoritative but not centralized
- **The Broadway League**
  - Industry organization; data not publicly available

### Update Frequency
- Producer credits are historical; rarely change after opening
- Re-scrape if data quality issues identified

---

## 3. Weekly Broadway Grosses

### Source
**Manual CSV Drop-in** (primary method)

User obtains data from:
- Broadway World grosses archives (https://www.broadwayworld.com/grosses)
- Playbill grosses pages
- The Numbers (https://www.the-numbers.com/broadway)
- Other public aggregators

### Coverage
- Desired: Weekly grosses for all shows, 2010-present
- Actual: Depends on user's data source

### Data Collected
For each show-week:
- Show title
- Week ending date (Sunday)
- Weekly gross revenue (dollars)
- Capacity percentage (optional)
- Average ticket price (optional)
- Number of performances (optional)

### Methodology
- **Collector:** `data/get_grosses.py`
- **Strategy:**
  - **Option A (automatic):** Scrape from public grosses aggregators
    - **Status:** Not fully implemented (many sites block scraping)
  - **Option B (manual):** User provides CSV
    - **Status:** Primary method
    - **Format:** See `data/raw/grosses_raw_TEMPLATE.csv`

### Expected CSV Format
```csv
show_title,week_ending_date,weekly_gross,capacity_pct,avg_ticket_price,performances
Hamilton,2015-08-16,587135.00,99.8,123.45,8
Hamilton,2015-08-23,622875.00,100.0,125.50,8
```

Columns:
- `show_title` (str): Show name (will be matched to `shows.csv` via fuzzy matching)
- `week_ending_date` (date): ISO format YYYY-MM-DD
- `weekly_gross` (float): Dollar amount
- `capacity_pct` (float, optional): 0-100
- `avg_ticket_price` (float, optional): Dollar amount
- `performances` (int, optional): Number of performances that week

### Processing
1. Load manual CSV
2. Parse dates
3. Normalize show titles for matching
4. Fuzzy match to shows from Tony outcomes
5. Compute derived fields:
   - `week_number_since_open` (requires opening date)
   - `post_tony_period` (1 if after Tony ceremony)
   - `season`

### Data Quality Notes
- **Title matching:** Uses fuzzy matching (threshold=85) to handle title variations
- **Unmatched shows:** Weekly data for non-Tony-nominated shows will be dropped
- **Completeness:** Depends entirely on user's data source
- **Validation:** Check for outliers, missing weeks, duplicate entries

### Limitations
- **No automated collection:** Requires manual data acquisition
- **Source variability:** Different sources may have different coverage/accuracy
- **Historical data:** Some sources may not have complete historical records
- **Long-running shows:** Need continuous data collection

### Alternative Sources (for future enhancement)
- **Broadway League official data**
  - Most authoritative source
  - Requires membership access (not publicly available)
- **Scraping Playbill grosses**
  - Technically feasible but may violate terms of service
  - Would require robust scraper
- **APIs:**
  - No known public API for Broadway grosses data

### Update Frequency
- Weekly (for current shows)
- Historical data is static

---

## 4. Show Metadata (Opening/Closing Dates, Theatre Info)

### Source
**Internet Broadway Database (IBDB)**

### Coverage
- Opening dates
- Closing dates (or "still running")
- Theatre name
- Theatre size (seat count)
- Show category (musical, play, revival)

### Methodology
- **Status:** Partially implemented placeholder
- **Planned scraper:** Enhancement to `data/scrape_producers.py` or separate module
- **Strategy:**
  1. Use IBDB show pages (same as producer scraping)
  2. Parse production details section
  3. Extract:
     - Opening date
     - Closing date (if closed)
     - Theatre name
     - Number of performances

### Current Implementation
- **Opening date, closing date:** Placeholder (NaN in `shows.csv`)
- **Theatre name, size:** Placeholder (NaN in `shows.csv`)
- **Category:** Placeholder (could be inferred from Tony categories)

### Data Quality Notes
- **Accuracy:** IBDB is highly accurate for Broadway productions
- **Limitations:**
  - Some shows may have multiple production runs (need to match correct one)
  - Preview performances vs official opening distinction

### TO DO
- Implement IBDB metadata scraper
- Add date parsing for various date formats
- Handle "still running" shows
- Map theatre names to seat counts (may require separate theatre database)

---

## 5. NYT Review Scores (Future Enhancement)

### Source
**The New York Times Theatre Reviews**

### Coverage
- Professional theatre reviews for most Broadway shows
- Includes "Critic's Pick" designation

### Data to Collect
- Review sentiment: +1 (positive), 0 (mixed), -1 (negative)
- Critic's Pick: 1/0 binary

### Methodology (Planned)
- **Option A:** Manual coding
  - Read reviews and assign sentiment score
  - Labor-intensive but accurate
- **Option B:** Automated sentiment analysis
  - Scrape review text
  - Use NLP sentiment analysis (VADER, TextBlob, or LLM)
  - Validate on sample
- **Option C:** Use existing datasets
  - Check if anyone has compiled this data

### Current Implementation
- Placeholder columns in `shows.csv`: `nyt_review_score`, `critic_pick`
- All values currently NaN

### Data Quality Notes
- **Subjectivity:** Sentiment coding involves judgment
- **Reliability:** Inter-coder reliability check recommended if manual
- **Timing:** Reviews typically published around opening night

### TO DO
- Implement review scraper or manual coding workflow
- Validate sentiment analysis approach
- Add to master dataset builder

---

## 6. Additional Metadata (Future Enhancements)

### IP Familiarity
- **Definition:** 1 if show based on well-known IP (film, novel, etc.), else 0
- **Source:** Manual coding or Wikipedia/IBDB show descriptions
- **Current status:** Placeholder (NaN)

### Capitalization Bracket
- **Definition:** Production budget category (small/medium/large)
- **Source:** Not publicly available (Broadway League member data)
- **Current status:** Placeholder (NaN)
- **Proxy:** Could use theatre size, cast size, or producer count as rough proxies

### Star Power
- **Definition:** 1 if show features major film/TV star, else 0
- **Source:** IBDB cast listings + manual coding
- **Current status:** Placeholder (NaN)
- **Method:** Would require cross-referencing cast with IMDB or similar

---

## Data Integration and Matching

### Title Normalization
All show titles normalized using `utils/matching.py`:
- Lowercase
- Remove leading articles (the, a, an)
- Remove punctuation (except apostrophes)
- Remove parentheticals (e.g., "(Revival)")
- Normalize whitespace

### Fuzzy Matching
- Used to match shows across data sources (Tony, IBDB, grosses)
- Algorithm: fuzzywuzzy `token_sort_ratio`
- Threshold: 85 (configurable in `config.py`)
- Handles minor title variations (e.g., "Dear Evan Hansen" vs "Dear Evan Hansen")

### Show ID Generation
- Format: `{Title}_{Year}`
- Example: `Hadestown_2019`
- Ensures uniqueness for shows with same title in different years

### Season Assignment
- Broadway season runs May-April
- Shows opening May-December: in `year-(year+1)` season
- Shows opening January-April: in `(year-1)-year` season
- Example: Show opening March 2019 is in "2018-2019" season

---

## Data Validation and Quality Checks

### Automated Checks (in `build_master.py`)
1. **Missing data:** Log shows with missing producer counts, Tony data, etc.
2. **Outliers:** Flag unusually high producer counts (>100)
3. **Date validity:** Check that opening_date < closing_date
4. **Match rates:** Report fuzzy matching success rates

### Manual Validation (Recommended)
1. **Spot check:** Manually verify data for 10-20 random shows
2. **Known shows:** Check data for well-known shows (Hamilton, Wicked, etc.)
3. **Edge cases:** Verify handling of:
   - Shows with same name in different years
   - Limited runs vs open-ended runs
   - Shows that transferred from Off-Broadway

---

## Data Retention and Versioning

### Raw Data
- All raw scraped data saved in `data/raw/` with timestamps
- Never delete raw data; allows re-processing if errors found

### Processed Data
- Master tables in `data/processed/`
- Include data processing date in filename or metadata
- Keep previous versions for comparison

### Git Tracking
- Use `.gitignore` for large raw data files
- Track code and documentation in git
- Consider using Git LFS for data files

---

## Ethical and Legal Considerations

### Web Scraping
- **Respect robots.txt:** Check each website's robots.txt
- **Rate limiting:** Use delays to avoid overloading servers (1.5 sec default)
- **Terms of Service:** Review ToS for each website
- **Fair use:** Scraping for research purposes generally considered fair use

### Data Usage
- **Attribution:** Cite all data sources appropriately
- **Non-commercial:** This pipeline intended for research/educational use
- **Privacy:** No personal data collected (only public production data)

### Data Redistribution
- **Wikipedia data:** CC BY-SA license (redistribution allowed with attribution)
- **IBDB data:** Check terms of service before redistributing
- **Grosses data:** Depends on source; cite appropriately

---

## Contact for Data Issues

If you encounter data quality issues or source changes:
1. Check the relevant scraper log output
2. Manually inspect the source website
3. File an issue on GitHub with:
   - Data source affected
   - Error message or unexpected output
   - Example show(s) demonstrating the issue

---

## References

- The Tony Awards: https://www.tonyawards.com/
- Internet Broadway Database: https://www.ibdb.com/
- Wikipedia Tony Awards pages: https://en.wikipedia.org/wiki/Tony_Awards
- Playbill Vault: https://www.playbillvault.com/
- Broadway World: https://www.broadwayworld.com/
- The Numbers (Broadway): https://www.the-numbers.com/broadway

---

**Last Updated:** January 2025

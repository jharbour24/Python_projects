# Google-Based IBDB Search Approach

## What Changed

Instead of trying to construct IBDB URLs directly or using IBDB's internal search, the scraper now uses **Google search** to find IBDB pages.

### Why This Works Better

1. **More Reliable**: Google is excellent at finding the right page even with complex titles
2. **Handles Special Characters**: No issues with commas, ampersands, etc.
3. **Finds Correct Show**: Google's ranking usually puts the right show first
4. **Less Browser Navigation**: Fewer page loads mean less chance of browser crashes

## How It Works

For each show (e.g., "Hadestown"):
1. Search Google for: `"Hadestown IBDB"`
2. Parse the Google results page
3. Find the first link that contains `ibdb.com/broadway-production/`
4. Use that URL to scrape producer data

## Testing the New Approach

### Step 1: Test Google Search Only

Run this to verify Google search works for finding IBDB pages:

```bash
cd /home/user/Python_projects/broadway-tony-producer-analysis/data
python3 test_google_search.py
```

This will test 6 shows with various title complexities:
- Simple titles: "Hadestown", "Hamilton"
- Complex titles: "The Book of Mormon", "& Juliet"
- Punctuation: "Hello, Dolly!"
- Long titles: "Natasha, Pierre & The Great Comet of 1812"

**Expected**: All 6 should be found successfully.

### Step 2: Test Full Scraper on One Show

Once Google search works, test the full producer scraping on Hadestown:

```bash
cd /home/user/Python_projects/broadway-tony-producer-analysis/data
python3 test_hadestown_scrape.py
```

**Expected**: Should find 45 producers (user confirmed this is correct count).

### Step 3: Run Full Producer Scraper

If both tests pass, run the full scraper:

```bash
cd /home/user/Python_projects/broadway-tony-producer-analysis/data
python3 scrape_producers_from_grosses.py
```

This will:
1. Load **535 shows** from `all_broadway_shows_2010_2025.csv` (comprehensive list - EVERY Broadway show since 2010)
2. Use Google to find each show's IBDB page
3. Scrape producer data
4. Save to `raw/producers_all_shows_2010_2025.csv`

**Note**: Currently in TEST MODE (first 10 shows only). Edit the script to set `test_mode = False` to scrape all 535 shows.

**Important**: With 535 shows and ~5-6 seconds per show, the full scrape will take approximately 45-55 minutes.

## What to Watch For

### Good Signs:
- ✓ Browser opens and stays open
- ✓ "Found via Google" messages for each show
- ✓ Producer counts seem reasonable (usually 5-45 producers per show)
- ✓ Success rate > 90%

### Warning Signs:
- ✗ "No IBDB page found in Google results" - Google didn't return IBDB links
- ✗ Browser crashes during navigation
- ✗ Many shows showing 0 producers

## Troubleshooting

### If Google search fails:
- Google may be showing a CAPTCHA challenge
- Try waiting a few seconds between searches
- Google may rate-limit automated searches

### If browser still crashes:
- Close all other Chrome windows before starting
- Ensure you have enough RAM available
- Try running in smaller batches (e.g., 5-10 shows at a time)

### If producer counts seem wrong:
- Check the debug output for one show
- Look at the "Raw producer text" to see what was parsed
- The parser stops at production history text ("received its Premiere", etc.)

## Files Modified

- `scrape_all_broadway_shows.py` - Updated `search_ibdb()` method to use Google
- `scrape_producers_from_grosses.py` - Already uses the updated method (imports from above)
- `test_google_search.py` - New test script for Google search approach

## Next Steps

1. Run Step 1 test (Google search only)
2. If successful, run Step 2 (Hadestown full scrape)
3. If both pass, run Step 3 (all shows)
4. Review the results and adjust as needed

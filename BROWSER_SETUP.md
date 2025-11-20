# Browser Automation Setup Guide

This guide will help you set up Selenium for browser-based scraping.

---

## Quick Setup (Mac)

### Step 1: Install Selenium

```bash
pip3 install selenium
```

### Step 2: Install Chrome Driver (if using Chrome)

**Option A: Using Homebrew (Easiest)**

```bash
brew install chromedriver
```

If you don't have Homebrew:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Option B: Manual Download**

1. Check your Chrome version: Chrome menu → About Google Chrome
2. Download matching chromedriver from: https://chromedriver.chromium.org/downloads
3. Unzip and move to /usr/local/bin:
   ```bash
   sudo mv chromedriver /usr/local/bin/
   sudo chmod +x /usr/local/bin/chromedriver
   ```

### Step 3: Or Use Safari (No Setup Needed!)

Safari works out of the box on Mac! Just:
1. Enable automation: Safari → Preferences → Advanced → Show Develop menu
2. Develop menu → Allow Remote Automation

---

## Running the Browser Scraper

### Using Chrome:

```bash
python3 browser_ibdb_scraper.py
```

### Using Safari:

Edit `browser_ibdb_scraper.py` at the bottom, change:
```python
browser='chrome',  # Change this to 'safari'
```

Then run:
```bash
python3 browser_ibdb_scraper.py
```

---

## What You'll See

A browser window will open and you'll see it:
1. Search Google for each show
2. Click the first IBDB link
3. Count the producers
4. Move to the next show

**This is normal!** The browser is being controlled by the script.

---

## Headless Mode (No Browser Window)

If you don't want to see the browser window, edit the script:

```python
headless=False,  # Change to True
```

**Note:** Safari doesn't support headless mode, only Chrome.

---

## Troubleshooting

### "chromedriver cannot be opened because the developer cannot be verified"

**Mac Security Fix:**
```bash
xattr -d com.apple.quarantine /usr/local/bin/chromedriver
```

### "Safari could not connect to Web Driver"

Enable remote automation:
1. Safari → Preferences → Advanced → Show Develop menu
2. Develop → Allow Remote Automation

### Browser opens but nothing happens

- Make sure you have internet connection
- Try increasing wait times in the script
- Check if Google is accessible

---

## Performance

- **Speed:** About 5-10 seconds per show (with pauses to be polite)
- **Total time:** 45-90 minutes for 535 shows
- **Checkpoint:** Saves progress after each show, can resume if interrupted

---

## Estimated Timeline

```
535 shows × 8 seconds/show = ~71 minutes
```

You can walk away and let it run! ☕

---

## Watching Progress

The terminal will show:

```
[1/535] (0.2%) Processing: HAMILTON
✓ Found IBDB link: https://www.ibdb.com/broadway-production/hamilton-499521
✓ SUCCESS: Found 4 producers

[2/535] (0.4%) Processing: HADESTOWN
✓ Found IBDB link: https://www.ibdb.com/broadway-production/hadestown-534103
✓ SUCCESS: Found 45 producers
```

---

## Next Steps After Scraping

Once complete, you'll have:
- `data/show_producer_counts_ibdb.csv` - All producer counts
- `data/tony_outcomes.csv` - Tony winners (already done)

Then you can run the analysis:
```bash
python3 analysis/producer_tony_analysis.py
```

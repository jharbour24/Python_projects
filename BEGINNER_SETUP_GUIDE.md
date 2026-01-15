# Complete Beginner's Guide: Scraping Broadway Producer Data

**No coding experience needed!** This guide will walk you through everything step-by-step.

---

## What You'll Do

You're going to:
1. Download the research code from GitHub
2. Install Python (the programming language)
3. Run a script that automatically collects Broadway producer data
4. Get your final dataset ready for analysis

**Time needed:** About 30-60 minutes (most of it is the computer doing the work)

---

## Step 1: Download the Code from GitHub

### Option A: Download as ZIP (Easiest - No Account Needed)

1. **Go to the GitHub page:**
   - Open your web browser
   - Go to: `https://github.com/jharbour24/Python_projects`

2. **Download the code:**
   - Look for a green button that says `<> Code`
   - Click on it
   - Click `Download ZIP`
   - Save it somewhere you'll remember (like your Desktop or Downloads folder)

3. **Unzip the file:**
   - **Windows:** Right-click the ZIP file → Select "Extract All" → Click "Extract"
   - **Mac:** Double-click the ZIP file (it will automatically unzip)

4. **Remember where you saved it!**
   - You should now have a folder called `Python_projects-claude-broadway-tony-dataset...` (or similar)
   - We'll need this folder in the next steps

### Option B: Using Git (If You're Comfortable with Terminal/Command Prompt)

**Windows Users:**
```
1. Press Windows Key + R
2. Type: cmd
3. Press Enter
4. Type: cd Desktop
5. Type: git clone https://github.com/jharbour24/Python_projects.git
6. Press Enter
```

**Mac Users:**
```
1. Open Spotlight (Cmd + Space)
2. Type: Terminal
3. Press Enter
4. Type: cd Desktop
5. Type: git clone https://github.com/jharbour24/Python_projects.git
6. Press Enter
```

---

## Step 2: Install Python

Python is the programming language that will run the scraper. Don't worry - you won't need to write any code!

### For Windows:

1. **Download Python:**
   - Go to: https://www.python.org/downloads/
   - Click the big yellow "Download Python 3.x.x" button
   - Save the file

2. **Install Python:**
   - Double-click the downloaded file
   - **IMPORTANT:** Check the box that says "Add Python to PATH" ✓
   - Click "Install Now"
   - Wait for installation to complete
   - Click "Close"

3. **Verify it worked:**
   - Press Windows Key + R
   - Type: `cmd`
   - Press Enter
   - Type: `python --version`
   - Press Enter
   - You should see something like "Python 3.12.0" (or similar)

### For Mac:

1. **Check if you have Python:**
   - Open Spotlight (Cmd + Space)
   - Type: `Terminal`
   - Press Enter
   - Type: `python3 --version`
   - Press Enter

2. **If you see "Python 3.x.x" - you're done!**
   - Skip to Step 3

3. **If you don't have Python, install it:**
   - Go to: https://www.python.org/downloads/
   - Click "Download Python 3.x.x"
   - Open the downloaded file
   - Follow the installation steps
   - When done, close and reopen Terminal

---

## Step 3: Install Required Libraries

Python needs some extra tools to scrape websites. We'll install them now.

### Windows:

1. **Open Command Prompt:**
   - Press Windows Key + R
   - Type: `cmd`
   - Press Enter

2. **Navigate to your downloaded folder:**
   ```
   cd Desktop\Python_projects-claude-broadway-tony-dataset-01Q2qbxaKfYdfo4zsXzTTrtt
   ```
   (Your folder name might be slightly different - adjust as needed)

3. **Install the libraries:**
   ```
   pip install -r requirements.txt
   ```
   - Press Enter
   - Wait 1-2 minutes while it installs everything
   - You'll see lots of text scrolling - this is normal!

### Mac:

1. **Open Terminal:**
   - Cmd + Space
   - Type: `Terminal`
   - Press Enter

2. **Navigate to your downloaded folder:**
   ```
   cd Desktop/Python_projects-claude-broadway-tony-dataset-01Q2qbxaKfYdfo4zsXzTTrtt
   ```
   (Your folder name might be slightly different - adjust as needed)

3. **Install the libraries:**
   ```
   pip3 install -r requirements.txt
   ```
   - Press Enter
   - Wait 1-2 minutes while it installs everything

---

## Step 4: Run the Scraper

This is where the magic happens! The scraper will automatically visit IBDB.com and count producers for all 535 Broadway shows.

### Windows:

In the same Command Prompt window from Step 3:

```
python run_full_scrape.py
```

Press Enter and watch it work!

### Mac:

In the same Terminal window from Step 3:

```
python3 run_full_scrape.py
```

Press Enter and watch it work!

---

## What You'll See While It's Running

The scraper will show you progress updates like:

```
======================================================================
BROADWAY PRODUCER DATA SCRAPER - FULL RUN
======================================================================

Starting full scrape of 535 shows from IBDB.com

Progress: [█████░░░░░] 50/535 shows (9.3%)
Current: Scraping "HAMILTON"
Status: Found 4 producers
Rate: 12.5 shows/minute
Estimated time remaining: 38 minutes
```

**Important Notes:**
- This will take **30-60 minutes** to complete
- Don't close the window while it's running!
- You'll see it pause between each show (this is normal - we're being polite to IBDB's servers)
- If it stops with an error, see the "Troubleshooting" section below

---

## Step 5: Get Your Results

When the scraper finishes, you'll see:

```
======================================================================
SCRAPING COMPLETE!
======================================================================

Total shows processed: 535
Successfully scraped: 520
Failed: 15
Success rate: 97.2%

Results saved to: data/show_producer_counts_ibdb.csv
```

### Your Data Files

All your data is in the `data` folder:

1. **show_producer_counts_ibdb.csv** - Producer counts from IBDB
   - Columns: show_id, show_name, ibdb_url, num_total_producers, scrape_status, scrape_notes

2. **tony_outcomes.csv** - Tony Award winners (already complete!)
   - Columns: show_id, show_name, tony_win, tony_category, tony_year

### How to Open CSV Files:

**Option 1: Excel**
- Right-click the CSV file
- Choose "Open with Microsoft Excel"

**Option 2: Google Sheets**
- Go to sheets.google.com
- Click "File" → "Import"
- Upload the CSV file

**Option 3: Any text editor**
- Notepad (Windows) or TextEdit (Mac) will work too

---

## Step 6: Run the Analysis (Optional)

Want to see the statistical analysis right away?

### Windows:
```
python analysis\producer_tony_analysis.py
```

### Mac:
```
python3 analysis/producer_tony_analysis.py
```

This will create:
- Statistical analysis results
- Charts showing the relationship between producer counts and Tony wins
- Output saved in the `analysis/output` folder

---

## Troubleshooting

### Problem: "Python is not recognized" or "command not found"

**Windows Fix:**
1. Reinstall Python
2. Make sure to check "Add Python to PATH" during installation

**Mac Fix:**
- Use `python3` instead of `python` in all commands

### Problem: "pip is not recognized"

**Windows Fix:**
```
python -m pip install -r requirements.txt
```

**Mac Fix:**
```
python3 -m pip install -r requirements.txt
```

### Problem: The scraper gets 403 Forbidden errors

This means IBDB is blocking automated requests. Try:

1. **Wait 30 minutes and try again** (you may have been temporarily blocked)

2. **Use Google Colab instead** (free cloud environment):
   - Go to: https://colab.research.google.com/
   - Click "New Notebook"
   - Upload your code files
   - Run the scraper in the cloud

3. **Check your internet connection**

### Problem: Scraper stops in the middle

**Don't panic!** The scraper has checkpoint recovery:

- Just run the same command again
- It will resume from where it left off
- It won't re-scrape shows you've already completed

### Problem: "ModuleNotFoundError: No module named 'cloudscraper'"

You need to install the required libraries:

**Windows:**
```
pip install cloudscraper beautifulsoup4 pandas
```

**Mac:**
```
pip3 install cloudscraper beautifulsoup4 pandas
```

---

## Getting Help

If you get stuck:

1. **Check the error message** - Copy the exact error text
2. **Look in the documentation:**
   - `README.md` - Project overview
   - `LOCAL_SETUP_GUIDE.md` - Technical setup details
3. **Check the scraper logs** in `data/show_producer_counts_ibdb.csv` - the "scrape_notes" column shows what went wrong

---

## What Each File Does (Optional Reading)

You don't need to understand this, but in case you're curious:

- `run_full_scrape.py` - Main script that runs the scraper
- `advanced_ibdb_scraper.py` - The actual scraping logic
- `populate_tony_winners.py` - Script that identified Tony winners
- `requirements.txt` - List of Python libraries needed
- `raw/all_broadway_shows_2010_2025.csv` - List of 535 shows to scrape
- `data/tony_outcomes.csv` - Tony Award results (already done!)
- `data/show_producer_counts_ibdb.csv` - Producer counts (created by scraper)

---

## Summary: Quick Command Reference

**Windows Users:**
```bash
# Step 1: Navigate to folder
cd Desktop\Python_projects-claude-broadway-tony-dataset-01Q2qbxaKfYdfo4zsXzTTrtt

# Step 2: Install libraries
pip install -r requirements.txt

# Step 3: Run scraper
python run_full_scrape.py

# Step 4 (Optional): Run analysis
python analysis\producer_tony_analysis.py
```

**Mac Users:**
```bash
# Step 1: Navigate to folder
cd Desktop/Python_projects-claude-broadway-tony-dataset-01Q2qbxaKfYdfo4zsXzTTrtt

# Step 2: Install libraries
pip3 install -r requirements.txt

# Step 3: Run scraper
python3 run_full_scrape.py

# Step 4 (Optional): Run analysis
python3 analysis/producer_tony_analysis.py
```

---

## You're All Set!

That's it! You now have:
- ✓ The code downloaded
- ✓ Python installed
- ✓ Instructions to run everything

The scraper will do all the work for you. Just follow the steps above and you'll have your complete research dataset ready for analysis.

**Good luck with your research!**

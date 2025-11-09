# Quick Start Guide for Complete Beginners

This guide assumes you have **zero coding experience** and walks you through every step.

---

## What This Analysis Does

This program:
1. Collects Reddit discussions about three Broadway shows
2. Analyzes how people talk about them
3. Determines which show has the most effective marketing campaign
4. Creates charts and a report

**Shows analyzed:**
- Oh Mary!
- John Proctor is the Villain
- Maybe Happy Ending

**Time:** About 1 hour total (mostly waiting for Reddit)

---

## Step-by-Step Instructions

### Step 1: Open Your Terminal

**On Mac:**
1. Press `Command + Space` (opens Spotlight)
2. Type: `terminal`
3. Press Enter

**On Windows:**
1. Press `Windows key`
2. Type: `cmd`
3. Press Enter

**On Linux:**
1. Press `Ctrl + Alt + T`

You should see a black or white window with text. This is your terminal.

---

### Step 2: Navigate to the Project Folder

Type or copy-paste this command and press Enter:

```bash
cd ~/Python_projects/oh_mary_cmm_analysis
```

**On Windows, use this instead:**
```bash
cd C:\Users\YourUsername\Python_projects\oh_mary_cmm_analysis
```
*(Replace `YourUsername` with your actual Windows username)*

**What this does:** Changes directory (cd) to the project folder.

If you get an error like "no such file or directory", the folder might be elsewhere. Try:
```bash
cd /home/user/Python_projects/oh_mary_cmm_analysis
```

---

### Step 3: Install Required Packages

Type this command and press Enter:

```bash
pip install -r requirements.txt
```

**What this does:** Installs all the Python libraries needed for the analysis.

**What you'll see:** Lots of text scrolling by as packages install. This takes 2-5 minutes.

**If you get an error about "pip not found":**
Try this instead:
```bash
python -m pip install -r requirements.txt
```

---

### Step 4: Run the Complete Analysis

Type this command and press Enter:

```bash
python run_full_analysis.py
```

**What happens next:**

1. You'll see a menu asking if you want to proceed
2. Type: `yes` and press Enter
3. The program will start collecting Reddit data
4. **This takes 30-60 minutes** (mostly waiting for Reddit's API)
5. You'll see progress updates as it works
6. When done, you'll see "✅ ANALYSIS COMPLETE!"

**During the wait:**
- ☕ You can make coffee
- 📱 The program will show progress messages
- ⏸️ You can minimize the terminal, but don't close it

---

## What You'll Get

After the analysis finishes, you'll have:

### 📄 Main Report
Located at: `outputs/reports/comparative_analysis_report.md`

This is a detailed report showing:
- Which show had the most effective campaign
- Detailed metrics for each show
- Strategic recommendations

**How to open it:**
- **Mac:** Type `open outputs/reports/comparative_analysis_report.md`
- **Windows:** Type `start outputs\reports\comparative_analysis_report.md`
- Or just navigate to the folder and double-click the file

### 📊 Charts
Located in: `outputs/visualizations/`

You'll find:
- `overall_comparison.png` — Bar chart comparing all shows
- `metrics_heatmap.png` — Heatmap of all metrics
- `radar_comparison.png` — Radar chart
- 8 individual metric charts

**How to view:** Navigate to the folder and open the PNG files

### 📈 Quick Summary Table
Located at: `outputs/comparative_summary.csv`

Open with Excel, Google Sheets, or any spreadsheet program.

Shows all the scores in an easy-to-read table.

---

## Understanding the Results

### Overall CMM Score (0-100)

This is the main number showing campaign effectiveness.

- **70-100** = Strong movement (very effective campaign)
- **50-69** = Moderate movement (good campaign)
- **30-49** = Weak movement (campaign had limited impact)
- **0-29** = Minimal movement (campaign didn't create buzz)

### The 8 Metrics

Each measures a different aspect of how people talk about the show:

1. **MSS** — Do people use "we" and "us" when discussing it?
2. **IRI** — Do people say it represents their identity?
3. **ER** — Do people tell others they must see it?
4. **RAS** — Are people seeing it multiple times?
5. **BIS** — Do people talk about belonging to a community?
6. **GIM** — Are there inside jokes and insider language?
7. **CFS** — Are fans forming communities around it?
8. **MPI** — Are quotes and memes spreading?

---

## Example: Reading the Report

You might see something like:

```
🏆 Most Effective Campaign: Oh Mary!
Overall CMM Score: 68.5/100

Campaign Effectiveness Ranking:
1. 🥇 Oh Mary! — 68.5/100 (247 Reddit posts)
2. 🥈 Maybe Happy Ending — 61.2/100 (134 posts)
3. 🥉 John Proctor is the Villain — 52.3/100 (89 posts)
```

**What this means:**
- Oh Mary! had the most effective campaign
- It scored 68.5 out of 100 (moderate-to-strong movement)
- The analysis used 247 Reddit posts about Oh Mary!
- Maybe Happy Ending came in second
- John Proctor is the Villain came in third

---

## Troubleshooting

### "Command not found: python"

Try using `python3` instead:
```bash
python3 run_full_analysis.py
```

### "ModuleNotFoundError: No module named 'praw'"

The requirements didn't install properly. Try:
```bash
pip install praw pandas pyyaml matplotlib seaborn
```

### "Rate limit exceeded"

Reddit has limits on how fast you can collect data.

**Solution:** Wait 10 minutes, then run the script again. It will continue where it left off.

### No data collected for a show

Some shows might not have many Reddit posts. This is normal and part of the findings!

The report will note which shows had limited data.

---

## Manual Step-by-Step (If Full Script Fails)

If `run_full_analysis.py` doesn't work, run each step individually:

### 1. Collect Data
```bash
python multi_show_reddit_scraper.py
```
Wait 30-60 minutes for this to finish.

### 2. Analyze Data
```bash
python run_comparative_analysis.py
```
Takes about 5 minutes.

### 3. Create Charts
```bash
python generate_comparative_visualizations.py
```
Takes about 2 minutes.

### 4. Generate Report
```bash
python generate_comparative_report.py
```
Takes about 1 minute.

---

## FAQ

### How long does this take?
- **Setup:** 5 minutes (installing packages)
- **Data collection:** 30-60 minutes (waiting for Reddit)
- **Analysis:** 5-10 minutes
- **Total:** About 1 hour

### Can I stop it and come back later?
Yes! The data collection saves progress. You can close the terminal and run it again later.

### Do I need a Reddit account?
No! The script uses pre-configured credentials. You don't need to log in.

### Will this cost money?
No! This uses Reddit's free API. There are no costs.

### Can I analyze different shows?
Yes! Edit the file `config/config.yaml` to add different show names and keywords.

### What if I get stuck?
1. Read the error message carefully
2. Check the Troubleshooting section above
3. Try running each step manually
4. Make sure all packages are installed

---

## What to Do With Your Results

### For Academic Use
- Use the report and visualizations in your research
- Cite the methodology section
- Include the CSV data as supporting material

### For Business Use
- Share the comparative summary with stakeholders
- Use visualizations in presentations
- Reference specific metrics in marketing discussions

### For Personal Interest
- Read the detailed report to understand the findings
- Look at the visualizations to see patterns
- Compare the three shows across metrics

---

## Quick Commands Reference

**Navigate to project:**
```bash
cd ~/Python_projects/oh_mary_cmm_analysis
```

**Install everything:**
```bash
pip install -r requirements.txt
```

**Run complete analysis:**
```bash
python run_full_analysis.py
```

**View report (Mac):**
```bash
open outputs/reports/comparative_analysis_report.md
```

**View report (Windows):**
```bash
start outputs\reports\comparative_analysis_report.md
```

**List all outputs:**
```bash
ls outputs/
```

---

## You're Done! 🎉

After running the analysis, you'll have:
- ✅ A comprehensive report comparing all three shows
- ✅ Professional visualizations
- ✅ Statistical data in CSV format
- ✅ Evidence-based rankings of campaign effectiveness

**Next steps:**
1. Open and read the report
2. Look at the visualizations
3. Review the comparative summary table
4. Use the insights for your research/business needs

---

**Need help?** Check the main README.md file for more details.

**Want to customize?** Edit config/config.yaml to change shows or search parameters.

**Questions about results?** Read the Methodology section in the main report

# Quick Start Guide - Broadway Form D Analysis

## 🚀 First Time Setup (Required!)

### Step 1: Configure SEC EDGAR Credentials

SEC requires you to identify yourself when accessing their data. Run this **ONE TIME**:

```bash
cd broadway_form_d_analysis

# Configure your credentials
python3 scripts/sec_config.py
```

You'll be prompted for:
- **Your name or organization**: `John Doe` or `Broadway Research`
- **Your email**: `jdoe@university.edu`

**Example:**
```
Enter your name or organization: Jared Harbour
Enter your email address: jared@example.com

✓ Configuration saved!
User-Agent: Jared Harbour jared@example.com
```

This creates a `.config/sec_credentials.json` file (ignored by git for privacy).

---

## 📊 Collect Real Broadway Data

### Step 2: Run Bulk Collection

```bash
# Collect real Form D data from SEC EDGAR
python3 scripts/run_full_analysis.py --bulk
```

**What happens:**
1. Queries SEC EDGAR API for all Form D filings (2010-2025)
2. Filters for Broadway/theatrical productions only
3. Downloads ~100-300 Broadway filings
4. Parses all financial data
5. Runs quantitative analysis
6. Generates visualizations
7. **Complete in 5-15 minutes!**

---

## 🎯 Alternative Options

### Test with Sample Data First

```bash
# Generate 200 sample filings to test
python3 scripts/run_full_analysis.py --sample

# Generate 500 samples
python3 scripts/run_full_analysis.py --sample --num-samples 500
```

### Daily Scraping (Old Method - Slower)

```bash
# Scrape daily indices (may encounter rate limits)
python3 scripts/run_full_analysis.py --live
```

---

## 📁 Output Files

After running, you'll find:

```
data/processed/broadway_form_d_2010_2025.csv  # Master dataset (200 fields)
analysis/analysis_results.json                 # Quantitative analysis
visuals/*.png                                  # 7 chart sets (2.4 MB)
```

Open visualizations:
```bash
# macOS
open visuals/

# Linux
xdg-open visuals/

# Windows
explorer visuals\
```

---

## ⚠️ Troubleshooting

### Still Getting 403 Errors?

1. **Check you ran sec_config.py:**
   ```bash
   python3 scripts/sec_config.py
   ```

2. **Verify config was created:**
   ```bash
   cat .config/sec_credentials.json
   ```

3. **Test SEC access manually:**
   ```bash
   curl -A "Your Name your@email.com" https://www.sec.gov/cgi-bin/browse-edgar
   ```

   Should return HTML (not 403).

### Invalid Email Format

SEC may reject generic emails. Use a real email address you control.

### Network Issues

```bash
# Test general internet
ping sec.gov

# Test SEC access
curl -I https://www.sec.gov/
```

---

## 📊 Expected Results

### Collection Stats

- **Years covered**: 2010-2025 (15 years)
- **Expected filings**: 50-300 Broadway productions
- **Collection time**: 5-15 minutes
- **Success rate**: 95%+

### What Gets Filtered

✅ **Included:**
- "Hadestown Productions LLC"
- "Hamilton Broadway Production LLC"
- "Chicago The Musical Productions"
- "Wicked National Tour LLC"

❌ **Excluded (False Positives Fixed!):**
- "Hamilton Lane Private Markets" (financial firm)
- "Chicago Ventures Fund" (VC fund)
- "Convey Health Parent" (healthcare)
- "Prana Current Yield Fund" (investment fund)

---

## 🎭 Full Analysis Pipeline

The `--bulk` option runs all steps:

1. **Data Collection** (5-10 min)
   - Query SEC EDGAR API
   - Filter Broadway productions
   - Download Form D XML files
   - Parse all fields

2. **Quantitative Analysis** (30 sec)
   - Capitalization trends
   - Investor base evolution
   - Post-COVID analysis
   - Geographic patterns
   - Outlier detection

3. **Visualizations** (30 sec)
   - 7 comprehensive chart sets
   - High-resolution PNG (300 DPI)
   - Ready for presentations

---

## 💡 Pro Tips

### Resume Interrupted Collection

The script automatically skips already-downloaded files. If interrupted:

```bash
# Just run again - it will resume
python3 scripts/run_full_analysis.py --bulk
```

### Clean Start

```bash
# Remove all downloaded data
rm -rf data/raw/*
rm -f data/processed/*.csv

# Start fresh
python3 scripts/run_full_analysis.py --bulk
```

### View Logs

```bash
# Save logs to file
python3 scripts/run_full_analysis.py --bulk 2>&1 | tee collection.log

# Then review
less collection.log
```

---

## 📚 Documentation

- **This guide**: `QUICKSTART.md`
- **Bulk download details**: `BULK_DOWNLOAD_GUIDE.md`
- **False positive fixes**: `FIXES_SUMMARY.md`
- **Complete README**: `README.md`

---

## ✅ Summary

**Complete setup in 3 commands:**

```bash
# 1. Configure SEC credentials (one time)
python3 scripts/sec_config.py

# 2. Collect real Broadway data
python3 scripts/run_full_analysis.py --bulk

# 3. View results
open visuals/
```

**That's it!** You'll have complete Broadway Form D financing data from 2010-2025. 🎭

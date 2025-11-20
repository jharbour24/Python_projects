# Python Projects

## Broadway Tony Awards Dataset

Research infrastructure to analyze the relationship between producer counts and Tony Award wins.

### Quick Start

**Current Status**: Infrastructure complete, awaiting manual data collection.

#### 3-Step Process

1. **Collect Data** (2-4 hours)
   - Follow: `MANUAL_DATA_COLLECTION_GUIDE.md`
   - Use templates in `data/templates/`

2. **Validate Data** (<1 minute)
   ```bash
   python3 validate_manual_data.py
   ```

3. **Run Analysis** (<1 minute)
   ```bash
   python3 analysis/producer_tony_analysis.py
   ```

### Documentation

- **📘 START HERE**: `PROJECT_SUMMARY.md` - Complete project overview
- **📝 Data Collection**: `MANUAL_DATA_COLLECTION_GUIDE.md` - Detailed instructions
- **⚠️ Technical Details**: `SCRAPING_STATUS_REPORT.md` - Why scraping didn't work

### What's Included

- ✅ 173 Broadway shows (2010-2025)
- ✅ Complete analysis pipeline (logistic regression, visualizations)
- ✅ Data validation scripts
- ✅ Manual collection templates & guides
- ⏳ Producer counts (awaiting manual collection)
- ⏳ Tony outcomes (awaiting manual collection)

### Demo with Sample Data

```bash
# Create synthetic data for testing
python3 create_sample_data.py

# Run analysis
python3 analysis/producer_tony_analysis.py

# View results
ls analysis/results/
```

**Note**: Sample data is synthetic. Replace with real data for actual research.

---

## Other Projects

This repository also contains other Broadway-related analysis projects. See subdirectories for details.
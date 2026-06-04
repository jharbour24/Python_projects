# How to Run the Broadway Producer-Tony Analysis

## Simple 3-Step Process

### Step 1: Get the Code

```bash
cd ~/Documents/Python_projects/broadway-clean
git checkout claude/broadway-tony-producer-analysis-01Cdc38t4zVhAxDDqRB17GLJ
```

### Step 2: Install Requirements

```bash
cd broadway-tony-producer-analysis
pip3 install pandas numpy scipy requests beautifulsoup4 scikit-learn
```

### Step 3: Run the Analysis

```bash
python3 complete_analysis.py
```

That's it! The script will:
- ✅ Scrape producer data for all 535 Broadway shows (2010-2025)
- ✅ Get Tony Award data
- ✅ Run statistical analysis
- ✅ Tell you if more producers = more likely to win Tonys

## What to Expect

- **Time**: About 30-45 minutes (due to respectful delays between web requests)
- **Output**: You'll see progress updates as it scrapes each show
- **Results**: Statistical analysis will print at the end

## Output Files

All results saved to `output/` folder:
- `output/complete_dataset.csv` - Full merged dataset
- `data/raw/producers_complete.csv` - All producer data
- `data/raw/tony_awards.csv` - Tony award data

## Troubleshooting

### If you get "command not found: python3"
Try `python` instead:
```bash
python complete_analysis.py
```

### If you get import errors
Make sure you installed all requirements:
```bash
pip3 install --user pandas numpy scipy requests beautifulsoup4 scikit-learn
```

### If scraping fails
- Check your internet connection
- The script automatically retries failed requests
- You can re-run it - it won't re-scrape shows that already succeeded

## Understanding the Results

The analysis will tell you:

1. **T-Test**: Do Tony-winning shows have more/fewer producers than non-winners?
2. **Correlation**: Is there a relationship between producer count and Tony nominations?
3. **Logistic Regression**: How much does each additional producer increase odds of winning?

Look for:
- **P-value < 0.05** = Statistically significant result
- **Positive correlation** = More producers → Better Tony outcomes
- **Negative correlation** = More producers → Worse Tony outcomes

## Questions?

The script is fully commented. Open `complete_analysis.py` to see exactly what each section does.

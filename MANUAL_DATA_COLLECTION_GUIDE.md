# Manual Data Collection Guide
## Broadway Producer & Tony Awards Research

**Purpose**: Collect producer counts and Tony Award outcomes for 173 Broadway shows (2010-2025)

**Estimated Time**: 2-4 hours (depending on familiarity with sources)

---

## Data Collection Strategy

### Two-Phase Approach (Recommended)

**Phase 1: Tony Awards Data** (Easier - ~30-45 minutes)
- Use official Tony Awards website or Wikipedia
- Binary outcome: won major award (Yes/No)
- Template: `data/templates/tony_outcomes_template.csv`

**Phase 2: Producer Counts** (More time-intensive - ~2-3 hours)
- Use IBDB.com (manual browsing)
- Count producers by role
- Template: `data/templates/producer_counts_template.csv`

**Or use**: `data/templates/combined_data_template.csv` (all fields in one file)

---

## Phase 1: Tony Awards Data

### Data Source Options

1. **Official Tony Awards Website**: https://www.tonyawards.com/nominees/
   - Search by year
   - Look for Best Musical, Best Play, Best Revival categories

2. **Wikipedia Tony Awards Pages**:
   - Example: "2019 Tony Awards" → Winners section
   - Faster for bulk lookups

3. **Playbill Tony Awards Database**: https://www.playbill.com/tonys
   - Good search functionality

### Fields to Fill

| Field | Values | Instructions |
|-------|--------|--------------|
| `tony_win` | 0 or 1 | 1 = Won Best Musical, Best Play, Best Revival of Musical, or Best Revival of Play<br>0 = Did not win any of these categories<br>Leave blank if unsure |
| `tony_category` | Text | e.g., "Best Musical", "Best Play", "Best Revival of a Musical" (optional) |
| `tony_year` | YYYY | Year the award was won (optional) |

### Quick Method (Recommended)

1. Open Wikipedia: "List of Tony Award ceremonies"
2. For each year (2010-2025):
   - Open that year's Tony Awards page
   - Note winners in 4 categories:
     - Best Musical
     - Best Play
     - Best Revival of a Musical
     - Best Revival of a Play
3. Match winners to your show list
4. Mark `tony_win = 1` for winners, `tony_win = 0` for all others

### Example

```csv
show_id,show_name,tony_win,tony_category,tony_year
1,& Juliet,0,,
2,A Behanding in Spokane,0,,
...
56,Hamilton,1,Best Musical,2016
57,Hadestown,1,Best Musical,2019
```

---

## Phase 2: Producer Counts

### Data Source

**IBDB.com** - Internet Broadway Database
- **Access Method**: Manual web browsing (automated scraping is blocked)
- **URL Pattern**: Search for show → Click production page

### Step-by-Step Process

#### Setup (5 minutes)
1. Open template: `data/templates/producer_counts_template.csv`
2. Open IBDB.com in your browser
3. Have a text editor or Excel/Google Sheets ready

#### For Each Show (60-90 seconds per show)

1. **Search for the show**
   - Go to https://www.ibdb.com
   - Use search bar (top right)
   - Type exact show name
   - Click correct production (check opening year/theater)

2. **Find producer information**
   - Scroll to "Production Staff" or "Credits" section
   - Look for these roles:
     - "Produced by" → Lead producers
     - "Co-Producer" → Co-producers
     - "Associate Producer" → Often grouped with co-producers
     - "Executive Producer" → May be separate

3. **Count producers**
   - `num_lead_producers`: Count names under "Produced by"
   - `num_co_producers`: Count "Co-Producer" + "Associate Producer" names
   - `num_total_producers`: Sum of all producer-related roles
   - If a person has multiple roles, count them once

4. **Record data**
   - Copy IBDB URL to `ibdb_url`
   - Enter counts in appropriate columns
   - `scrape_status`: "manual_ok" or "not_found"
   - `scrape_notes`: Note any issues (e.g., "ambiguous roles", "multiple productions")

5. **Save every 10-20 shows** (prevent data loss)

### Example Entry

```csv
show_id,show_name,ibdb_url,num_lead_producers,num_co_producers,num_total_producers,scrape_status,scrape_notes
56,Hamilton,https://www.ibdb.com/broadway-production/hamilton-499521,5,12,17,manual_ok,Clear producer hierarchy
```

### Handling Edge Cases

| Situation | What to Do |
|-----------|------------|
| **Multiple productions** | Choose the one from 2010-2025 period (check opening date) |
| **Show not found** | Leave producer counts blank, set `scrape_status = "not_found"` |
| **Unclear producer roles** | Count all producer-titled roles in `num_total_producers`, note in `scrape_notes` |
| **Producer is an organization** | Count as 1 producer (e.g., "Lincoln Center Theater" = 1) |
| **Same person, multiple roles** | Count once in total |

---

## Time-Saving Tips

### Batch Processing
- **Group by year**: Process all 2010 shows, then 2011, etc.
- **Use keyboard shortcuts**: Ctrl+C/Ctrl+V for URLs
- **Multiple tabs**: Open 5-10 IBDB tabs at once, fill in parallel

### Prioritize High-Impact Shows
If time is limited, focus on:
1. Tony-nominated/winning shows first (higher research value)
2. Well-known shows (Hamilton, Wicked, Book of Mormon, etc.)
3. Skip obscure shows with very short runs

### Sampling Strategy (If needed)
- **Random sample**: Every 3rd show (gives ~60 shows)
- **Stratified sample**: Equal numbers from each year
- Analysis can still work with partial data

---

## Data Validation

### Before Submitting

Run validation script (after collection):
```bash
python3 validate_manual_data.py
```

This will check:
- ✅ All required fields filled
- ✅ Numeric fields contain numbers
- ✅ `tony_win` is 0 or 1
- ✅ Counts are reasonable (e.g., not 500 producers for one show)
- ✅ URLs are valid IBDB links

---

## Need Help?

### Common Issues

**Q: I can't find the show on IBDB**
- Try alternate titles (e.g., "Book of Mormon" vs "The Book of Mormon")
- Check if it was actually a Broadway production (not Off-Broadway)
- Mark as `scrape_status = "not_found"` and continue

**Q: Producer roles are confusing**
- When in doubt, count everyone with "Producer" in their title
- Note ambiguity in `scrape_notes`

**Q: This is taking too long**
- Consider sampling (see above)
- Focus on Tony nominees/winners
- Skip shows you can't find quickly

---

## After Data Collection

1. **Save your completed file** to: `data/show_producer_counts_manual.csv` (or `data/tony_outcomes_manual.csv`)

2. **Run validation**: `python3 validate_manual_data.py`

3. **Run analysis**: `python3 analysis/producer_tony_analysis.py`

4. **Review results**: Output will be in `analysis/results/`

---

## Alternative: Recruit Help

- **Research assistants**: Split the show list among 2-3 people
- **Crowdsourcing**: Use Amazon Mechanical Turk or similar
- **Student project**: Could be a good undergraduate research assistant task

---

**Good luck with data collection!**
If you have questions or encounter issues, check the validation script output or review the analysis pipeline documentation.

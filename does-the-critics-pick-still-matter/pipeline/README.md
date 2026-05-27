# Pipeline

The pipeline builds `data/critics_impact.db` from scratch by scraping public sources. The committed DB is the result of running the pipeline end-to-end with data current to **2026-05-25**.

You only need to run the pipeline if you want **fresher data** than what's committed. To just reproduce the analysis, see `analysis/README.md`.

---

## Order of execution

Each script is numbered. Run them in order:

```bash
python3 pipeline/01_discover_shows.py            # ≈ 2 min
python3 pipeline/02_scrape_dtli_reviews.py       # ≈ 90 min (rate-limited)
python3 pipeline/03_match_nyt_critics_picks.py   # ≈ 5 min  (requires NYT_API_KEY)
python3 pipeline/04_match_off_broadway_cp.py     # ≈ 10 min
python3 pipeline/05_refresh_grosses.py           # ≈ 30 min (incremental: ≈ 2 min)
python3 pipeline/06_import_tony_outcomes.py      # < 30 sec (needs CIA_TONY_CSV)
python3 pipeline/07_build_exports.py             # ≈ 30 sec
```

Total: ≈ 2.5 hours cold from scratch; ≈ 5 minutes for a daily refresh.

---

## What each step does

### `01_discover_shows.py`

Reads the DTLI Broadway archive (`didtheylikeit.com/broadway/`) and populates the `shows` table with title, slug, opening date, and show type. Resolves revivals by year. Idempotent — re-running adds new shows without disturbing existing rows.

### `02_scrape_dtli_reviews.py`

For each show in `shows`, fetches its DTLI show page and extracts every critic review: critic name, publication, sentiment (`up`/`meh`/`down`), and date. Rate-limited at 1.5–3.5 s between requests; uses HTML cache in `data/raw_html/dtli_show/`. The `is_opening_window` flag is set for reviews dated within 21 days of opening night.

### `03_match_nyt_critics_picks.py`

Queries the NYT Article Search API for theater reviews. Each review URL is matched to a show by fuzzy title + date window. CP-flagged reviews have `is_nyt_critics_pick = 1` set on the corresponding `reviews` row.

**Requires** `NYT_API_KEY` environment variable. Get one free at [developer.nytimes.com](https://developer.nytimes.com/). Without the key, you'll get only ~3 years of recent coverage via web scraping.

### `04_match_off_broadway_cp.py`

The default NYT scraper is Broadway-only. This step lifts that restriction and matches the NYT spotlight URL list (`data/nyt_critics_pick_urls.txt`) against the full `shows` table — Off-Broadway included. Adds 303 Off-Broadway CP flags as of last run.

### `05_refresh_grosses.py`

Scrapes BroadwayWorld's JSON grosses API. Two modes:
- **Cold start**: loads from a seed xlsx if `CIA_GROSSES_XLSX` is set, otherwise scrapes from 2010-01-03
- **Incremental**: fetches only new weeks since the last `week_ending` in the DB

After loading, recomputes `week_number` for every row based on each show's opening date (week 0 = the week containing official opening).

### `06_import_tony_outcomes.py`

Loads `tony_outcomes` from a CSV at `CIA_TONY_CSV` if set. Title-normalizes and fuzzy-matches each Tony record to a `show_id`. Skips if the env var is unset (in which case run `06b_import_wikipedia_tony.py` instead).

### `07_build_exports.py`

Writes the flat-file exports to `data/exports/`:
- One CSV per core table
- One Parquet (`master.parquet`) with everything joined for ML/regression use

Idempotent.

---

## Configuration

Most settings live in `config.py`. Override via environment variables:

| Env var | Default | What |
|---|---|---|
| `NYT_API_KEY` | — | Required for step 3 if you want full CP history (2000+) |
| `CIA_GROSSES_XLSX` | unset | If set, step 5 seeds from this xlsx before scraping |
| `CIA_TONY_CSV` | unset | If set, step 6 loads Tony outcomes from this CSV |
| `CIA_SHOWS_CSV` | unset | Optional supplemental show list |

---

## Caching / checkpointing

- HTML cache: `data/raw_html/{dtli_show,grosses,nyt}/` — re-fetched only if older than 7 days (365 days for closed shows)
- Checkpoint state: `data/checkpoints/` — tracks per-source scrape progress so interruptions can resume
- Scrape run observability: `scrape_runs` table in the DB

Both are gitignored. Restart safely — every step is idempotent.

---

## Troubleshooting

**"DTLI rate-limited me"** — Increase `RATE_LIMIT_MIN`/`RATE_LIMIT_MAX` in `config.py` to 3.0/6.0.

**"NYT API key isn't working"** — The free key has a 4,000-request daily limit and ~10 req/min throttle. Run step 3 across multiple days if needed.

**"BroadwayWorld JSON is empty"** — Their JSON endpoint occasionally returns a placeholder. Wait an hour and retry.

**"My DB doesn't match the committed one"** — DTLI corrects metadata regularly. Show counts will drift by a few rows. Run `python3 -c "import sqlite3; ...stats..."` to check; nothing should be off by more than ~5%.

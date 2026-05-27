# Data

All data used in the analysis is contained in this folder.

## Files

| File | Size | What it is |
|---|---|---|
| `critics_impact.db` | 11 MB | SQLite database — the canonical source for everything |
| `schema.sql` | 9 KB | Full database schema (tables, indexes, views) |
| `nyt_critics_pick_urls.txt` | 87 KB | 1,008 NYT Critics Pick URLs from the spotlight page + Wayback |
| `exports/` | ~21 MB | Flat-file CSV / Parquet exports for users who prefer pandas over SQL |

## Database schema

`critics_impact.db` is a normalized SQLite database. Inspect with:

```bash
sqlite3 data/critics_impact.db ".schema"
sqlite3 data/critics_impact.db ".tables"
```

### Core tables

| Table | Rows | What it stores |
|---|---|---|
| `shows` | 2,837 | One row per production. PK = `show_id`. |
| `reviews` | 9,789 | Critic reviews. FK to shows, critics, publications. |
| `publications` | 162 | Deduped publication directory. |
| `critics` | 451 | Deduped critic directory with primary publication. |
| `show_week_performances` | 21,397 | Weekly grosses by show. Week 0 = opening week. |
| `tony_outcomes` | 1,113 | Tony nominations and wins by show, year, category. |
| `lortel_data` | 25 | Off-Broadway run lengths (Wikipedia-harvested, sparse). |
| `scrape_runs` | — | Observability for scraper checkpointing. |

### Views

| View | What it joins |
|---|---|
| `v_opening_consensus` | Reviews filtered to opening window (±21 days from opening night) |
| `v_weekly_gross_with_reviews` | Weekly grosses joined to show metadata + opening-window aggregates |

### Key columns explained

**`shows`**
- `show_type` — `M` (Musical), `P` (Play), `S` (Specialty), `O` (Other), `U` (Unknown)
- `is_revival` — 0/1 flag
- `opening_date` / `closing_date` — official opening, NOT first preview
- `dtli_slug` — the show's slug on didtheylikeit.com
- `source_bww` — 1 if the show appears in BroadwayWorld grosses (proxy for "is Broadway")

**`reviews`**
- `is_opening_window` — 1 if review published within 21 days of opening
- `is_nyt_critics_pick` — 1 if this is the NYT review and it received the CP badge
- `sentiment` — `up` / `meh` / `down` (DTLI's three-class label)
- `days_from_opening` — signed integer; -3 = published 3 days before opening

**`show_week_performances`**
- `week_number` — 0 = BroadwayWorld week containing official opening; negative = previews
- `is_preview` — 1 if the week is before official opening
- `gross` — weekly box-office gross in dollars
- `capacity_pct` — stored as a **ratio** (1.0 = 100% capacity), max possible ≈ 1.04
- `attendance` — total tickets sold that week
- `performances` — number of performances that week (typically 8)

**`tony_outcomes`**
- One row per show × ceremony × category combination
- `nominated` and `won` are 0/1 flags
- `ceremony_year` is the year of the ceremony, not the season

## Exports (`data/exports/`)

For analyses that prefer pandas over SQL, the exports folder contains CSV/Parquet versions of the key tables.

| File | What it is | Best for |
|---|---|---|
| `shows.csv` | Show metadata, one row per production | Building cohorts |
| `reviews.csv` | One row per critic review | Sentiment analysis |
| `weekly_grosses.csv` | One row per show × week | Time-series analysis |
| `tony_outcomes.csv` | Tony noms/wins | Award outcomes |
| `publications.csv` | Publication directory | Lookup |
| `critics.csv` | Critic directory | Lookup |
| `opening_consensus.csv` | Per-show opening-window review aggregates | Quick consensus features |
| `master.parquet` | Pre-joined show × week panel | Drop-in for ML / regression |

`master.parquet` is the recommended starting point if you want one analysis-ready table.

## How this data was collected

See `pipeline/README.md` for the step-by-step. In brief:

1. **Show titles** scraped from `didtheylikeit.com/broadway/` archive pages (XML sitemap)
2. **Critic reviews** scraped from per-show pages on the same site
3. **NYT Critics Picks** matched from the spotlight page (`nytimes.com/spotlight/theater-critics-picks`) and Wayback Machine snapshots, then fuzzy-matched to shows by title + date
4. **Weekly grosses** pulled from BroadwayWorld's JSON API (`broadwayworld.com/json_grosses.cfm`)
5. **Tony outcomes** imported from a CSV originally derived from IBDB; supplemented with Wikipedia infobox scraping

## Data freshness

| Stream | Cutoff | Notes |
|---|---|---|
| Reviews | 2026-05-25 | DTLI updates daily |
| Grosses | 2026-05-17 | BroadwayWorld publishes Monday for prior Sunday-ending week |
| Tony outcomes | 2026 season noms public; winners not yet announced | Wikipedia is fastest for noms |
| NYT Critics Picks | 2026-05-25 | 1,008 URLs in seed file |

## Privacy / ethics

All data is from public sources. No personal information beyond publicly-listed critic names. The reviews are aggregated; full review text is not redistributed.

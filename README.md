# Does the *Critics' Pick* Still Matter?

A data-driven look at whether the New York Times' "Critics Pick" badge still moves Broadway ticket sales — and what theater critics in general are worth to the box office in 2026.

> **TL;DR.** Critics still matter. Across 1988–2025, a Broadway show with majority-positive reviews was 3× more likely to become a box-office hit and 4.5× more likely to land a Tony nomination than one without. But the *specific* NYT Critics Pick boost on post-launch ticket sales has been weakening: a Bayesian change-point model puts the probability of a real decline starting around 2024 at **78%–90%**. The 2025 season is the first in the dataset where CP shows showed *no* measurable post-launch advantage over comparable non-CP shows.

📄 **[Executive Summary (plain English)](reports/EXECUTIVE_SUMMARY.md)**  •  **[Technical Report (full methods)](reports/TECHNICAL_REPORT.md)**

---

## The Five Charts

### 1. Has the CP boost weakened over time?

![CP lift over time](charts/1_cp_lift_over_time.png)

Each dot is one year of openings. The dot's height shows how much more money CP shows earned in their first two months *vs. otherwise-identical non-CP shows that opened the same year*. Above 1.0× means CP shows out-earned. The boost stayed between 1.2× and 1.5× for nearly a decade; the 2025 season is the first year it sat below 1.0×.

### 2. How confident are we?

![Bayesian posterior](charts/2_bayesian_posterior.png)

The full series gives 90% posterior probability of a real decline; a robust re-fit (dropping the noisy 3-show 2014 cell) gives 78%. Both well above 50/50, but short of the conventional 95% "near-certain" threshold. The most likely break-point year, in the robust fit, is **2024**.

### 3. What do critics actually deliver, across all eras?

![What critics deliver](charts/3_what_critics_deliver.png)

Pooled across 542 Broadway shows (1988–2025), critics matter for both audiences and award voters — but the *which-signal-wins-which-outcome* split is interesting. Broad critical consensus dominates the box-office. The NYT Critics Pick specifically dominates *Best Musical / Best Play* — Tony voters watch the NYT.

### 4. Where does the box-office boost come from?

![How the boost travels](charts/4_how_boost_travels.png)

About 70% of the box-office advantage from good reviews is direct (audiences buy tickets after reading the rave). About 30% runs through the Tony pipeline (good reviews drive Tony nominations, nominations drive ticket sales). Producers who want a commercial hit need both, but the direct critic-to-audience channel is by far the larger of the two.

### 5. CP vs. non-CP shows: the historical scorecard

![Scorecard](charts/5_cp_vs_noncp_scorecard.png)

Across fully-completed Broadway runs 2014–2022, the CP badge is most powerful as a Tony predictor (+30 pp on any Tony nomination, +14 pp on Best Musical/Play). The box-office advantage (+7 pp) is real but smaller — consistent with the finding that audiences respond more to a crowd of positive reviews than to one outlet on its own.

---

## What's in this repo

```
does-the-critics-pick-still-matter/
├── README.md                       ← you are here
├── reports/
│   ├── EXECUTIVE_SUMMARY.md        Plain-English findings (≈ 1500 words)
│   └── TECHNICAL_REPORT.md         Full methods, tables, model specs
├── charts/                         The five final charts (PNG, 300 dpi)
├── data/
│   ├── critics_impact.db           SQLite database (11 MB, committed)
│   ├── schema.sql                  Database schema
│   ├── nyt_critics_pick_urls.txt   NYT spotlight seed URLs (1,008)
│   └── exports/                    Flat-file CSV/Parquet exports
│       ├── shows.csv               2,837 productions
│       ├── reviews.csv             9,789 critic reviews
│       ├── weekly_grosses.csv      21,397 show-week rows
│       ├── tony_outcomes.csv       Tony nominations + wins
│       ├── publications.csv        Publication directory
│       ├── critics.csv             Critic directory
│       ├── opening_consensus.csv   Opening-window review aggregates
│       └── master.parquet          One-row-per-show-week joined view
├── analysis/                       Code that produced the findings
│   ├── 01_consensus_models.py      Adjusted ORs + mediation
│   ├── 02_decline_analysis.py      Decline test + Bayesian change-point
│   └── 03_generate_charts.py       Polished chart generator
├── pipeline/                       Build the DB from raw sources
│   ├── 01_discover_shows.py        DTLI Broadway archive → shows table
│   ├── 02_scrape_dtli_reviews.py   Per-show review pages
│   ├── 03_match_nyt_critics_picks.py  NYT API → CP flags
│   ├── 04_match_off_broadway_cp.py    OB-aware CP matcher
│   ├── 05_refresh_grosses.py       BroadwayWorld weekly grosses
│   ├── 06_import_tony_outcomes.py  Tony noms + wins
│   └── 07_build_exports.py         Generate CSV/Parquet exports
├── scrapers/                       Low-level scraping library
├── normalize/                      Title / critic / publication normalization
├── config.py                       Project paths + scrape settings
├── db.py                           SQLite connection + upsert helpers
├── utils.py                        Logging / shared utilities
└── requirements.txt
```

---

## Reproducing the findings

### Just want to read the analysis?

The committed SQLite DB (`data/critics_impact.db`) already contains every show, review, weekly gross, and Tony outcome used in the report. To reproduce the five charts:

```bash
python3 -m pip install -r requirements.txt
python3 analysis/03_generate_charts.py
```

Charts will be written to `charts/`. To reproduce the full statistical tables:

```bash
python3 analysis/01_consensus_models.py   # produces consensus AdjORs + mediation
python3 analysis/02_decline_analysis.py   # produces decline test + Bayesian posterior
```

### Rebuilding the database from scratch

This is only necessary if you want to re-scrape with newer data. The full pipeline:

```bash
# Optional: set CIA_GROSSES_XLSX and CIA_TONY_CSV env vars to seed from existing files
# Otherwise the pipeline will scrape from scratch (takes ~6 hours)

python3 pipeline/01_discover_shows.py
python3 pipeline/02_scrape_dtli_reviews.py
python3 pipeline/03_match_nyt_critics_picks.py   # requires NYT_API_KEY (free)
python3 pipeline/04_match_off_broadway_cp.py
python3 pipeline/05_refresh_grosses.py
python3 pipeline/06_import_tony_outcomes.py
python3 pipeline/07_build_exports.py
```

See `pipeline/README.md` for details on what each step does.

---

## Data sources

| Source | What it provides | Method |
|---|---|---|
| [Did They Like It?](https://didtheylikeit.com) | Critic reviews, sentiment, publication | XML sitemap + per-show page scrape |
| BroadwayWorld | Weekly grosses, capacity %, attendance | JSON API |
| [NYT spotlight page](https://www.nytimes.com/spotlight/theater-critics-picks) | Critics Pick flags | spotlight + Wayback URL list |
| Internet Broadway Database | Show metadata, Tony outcomes | CSV import |
| Wikipedia | Tony nominees, run lengths | API + infobox parsing |

---

## Methodology in 60 seconds

We build a per-show dataset combining three streams:

1. **Critic reviews** (DTLI + NYT) — sentiment (up/meh/down), publication, date relative to opening night
2. **Weekly grosses** (BroadwayWorld) — capacity %, attendance, ticket prices, week by week
3. **Tony outcomes** (IBDB + Wikipedia) — nominations and wins by category and year

Three critic signals are tested side-by-side:
- **Majority positive** — more than half of opening-window reviews are positive
- **Unanimous positive** — every opening-window review is positive (≥ 2 reviews)
- **NYT Critics Pick** — the show carries the official NYT CP badge

Against three outcomes:
- **Box-office hit** — ran ≥ 26 weeks at ≥ 70% capacity (right-censored shows excluded)
- **Tony nomination** — any nomination in any category
- **Top Tony** — Best Musical or Best Play nomination

Effect sizes are estimated with adjusted logistic regression (controlling for show type, year, post-COVID dummy, and review volume), Cox proportional hazards for closing time, and Benjamini-Hochberg FDR correction for multiple testing. All twelve primary tests survive at q < 0.05. The decline analysis uses a Bayesian change-point model with a uniform prior on break year.

Full specifications in [`reports/TECHNICAL_REPORT.md`](reports/TECHNICAL_REPORT.md).

---

## Important caveats

- **Associations, not causal effects.** Critically acclaimed shows tend to have bigger budgets, stronger casts, and better creative teams. We don't have capitalization data, so some of what looks like a "critic effect" is actually "underlying quality" that critics noticed at the same time audiences did. Treat effect sizes as upper bounds.
- **Right-censoring on recent shows.** 33 of 542 shows in the consensus cohort were still running at the data cutoff. Cox models handle this correctly; binary hit metrics use only fully-observed shows.
- **Annual CP sample size is the binding constraint.** ~12-14 NYT Critics Picks per year on Broadway. The Bayesian posterior is *roughly* the right tool given that sample size; a binary frequentist NHST framework will not have power.
- **Off-Broadway data is partial.** 303 OB Critics Picks were identified but Off-Broadway grosses and run lengths are not available through public sources after Lortel/IOBDB migrated to Spectra.theater. Adding OB data would roughly quadruple the annual CP sample.

---

## License

[MIT](LICENSE). Use the code freely; cite the analysis if you use the findings.

## Acknowledgements

- DTLI for being the only structured archive of NYC theater reviews that exists
- BroadwayWorld for publishing weekly grosses every Monday going back to 2010
- The NYT theater desk, whose Critics Pick decisions made this analysis possible (and necessary)

---

_Last data refresh: 2026-05-17 (grosses). Analysis cutoff: 2026-05-25._

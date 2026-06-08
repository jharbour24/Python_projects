"""
build_db.py — Build `tony_relevance.db` from curated, source-tagged seed data.
==============================================================================

This script is the single source of truth for the Tony-relevance dataset. Every
number below carries a provenance tag (see `sources/SOURCES.md` for the full URL
list) and a `confidence` flag so the analysis can run sensitivity checks that
drop low-confidence cells.

Design note (why this DB exists):
    The thesis is "the Tony Awards are losing cultural *relevance*." Relevance is
    a latent construct — there is no single column for it. So we assemble several
    *observable indicators* of relevance and, crucially, a set of *peer award
    shows* (Oscars / Emmys / Grammys) that share the same secular headwind
    (the collapse of linear TV). The peer panel is what lets us move from
    "the Tonys' ratings fell" (true but trivial — everything on linear TV fell)
    toward "the Tonys fell *faster / harder / older* than their peers"
    (the actually-interesting, closer-to-causal claim).

Tables built:
    award_broadcasts      one row per (award, ceremony_year): linear viewership,
                          network, host, measurement basis, confidence, source
    audience_demographics median viewer age snapshots by award (sparse)
    tv_universe           per-year denominators: US TV households, pay-TV
                          penetration, total primetime linear viewing index
    attention_index       (schema only, seeded sparse) Google-Trends / Wikipedia
                          pageview style attention proxies — the "something else"
                          beyond Nielsen. Left mostly empty for the analyst to
                          backfill from the Trends/Wiki APIs (see RESEARCH_PLAN).

Run:
    python3 tony_relevance/build_db.py
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "tony_relevance.db"
SRC = ROOT / "sources"
SRC.mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------------------------
# 1. AWARD BROADCASTS — the core panel
# -----------------------------------------------------------------------------
# columns: award, year, air_date, network, host, viewers_m, measurement,
#          confidence, source_key, notes
#
# measurement:
#   "linear"  = US linear TV viewers, Nielsen Live+Same-Day (the long-run,
#               apples-to-apples basis used for almost all historical figures)
#   "xplat"   = "across platforms" — linear PLUS streaming/digital. Networks
#               increasingly headline this number; it is NOT comparable to the
#               historical linear series and BIASES THE RECENT TREND UPWARD.
#               Flagged so the analysis can exclude it from the clean series.
#
# confidence: high / med / low  (low = single secondary source, or a figure
#             that conflicts across outlets; used for leave-one-out sensitivity)
# -----------------------------------------------------------------------------

AWARD_BROADCASTS = [
    # ---- TONY AWARDS (CBS) ----
    ("Tony",   2001, "2001-06-03", "CBS", "Rosie O'Donnell",            8.30, "linear", "med",  "nytix",     "Pre-cord-cutting baseline."),
    ("Tony",   2003, "2003-06-08", "CBS", "Hugh Jackman",              5.40, "linear", "low",  "nytix",     "Notably low year; figure varies by source."),
    ("Tony",   2011, "2011-06-12", "CBS", "Neil Patrick Harris",       6.95, "linear", "med",  "nytix",     "NPH era, generally strong reviews."),
    ("Tony",   2012, "2012-06-10", "CBS", "Neil Patrick Harris",       6.01, "linear", "med",  "nytix",     ""),
    ("Tony",   2013, "2013-06-09", "CBS", "Neil Patrick Harris",       7.24, "linear", "med",  "nytix",     "NPH 'Bigger' opening number; local ratings peak."),
    ("Tony",   2014, "2014-06-08", "CBS", "Hugh Jackman",              7.00, "linear", "med",  "nytix",     ""),
    ("Tony",   2015, "2015-06-07", "CBS", "Kristin Chenoweth/A.Cumming",6.35, "linear", "med",  "nytix",     ""),
    ("Tony",   2016, "2016-06-12", "CBS", "James Corden",              8.70, "linear", "high", "statista",  "Hamilton year — positive cultural shock; highest since 2001."),
    ("Tony",   2017, "2017-06-11", "CBS", "Kevin Spacey",              6.00, "linear", "med",  "nytix",     ""),
    ("Tony",   2018, "2018-06-10", "CBS", "Sara Bareilles/J.Groban",   6.30, "linear", "med",  "nytix",     ""),
    ("Tony",   2019, "2019-06-09", "CBS", "James Corden",              5.40, "linear", "high", "statista",  "Last pre-pandemic ceremony."),
    # 2020: no ceremony (pandemic; 74th held Sept 2021)
    ("Tony",   2021, "2021-09-26", "CBS", "Leslie Odom Jr.",           2.62, "linear", "high", "deadline",  "74th, delayed to Sept 2021. CBS broadcast hour only; the 2hr Paramount+ concert preceded it. All-time-low context."),
    ("Tony",   2022, "2022-06-12", "CBS", "Ariana DeBose",             3.86, "linear", "high", "variety",   "First live coast-to-coast telecast; time-zone-adjusted L+SD."),
    ("Tony",   2023, "2023-06-11", "CBS", "Ariana DeBose",             4.30, "linear", "med",  "variety",   "Variety final 4.3M ('most-watched since 2019'); TheWrap reported 4.12M L+SD — conflict noted."),
    ("Tony",   2024, "2024-06-16", "CBS", "Ariana DeBose",             3.51, "linear", "high", "thewrap",   "Down 14% YoY; lowest non-pandemic linear number on record. (Deadline rounds to 3.53M.)"),
    ("Tony",   2025, "2025-06-08", "CBS", "Cynthia Erivo",             4.85, "linear", "high", "deadline",  "CORRECTED: 4.85M is the CBS Live+Same-Day LINEAR average — most-watched Tonys since 2019; +38% vs 2024. (Earlier this cell was mis-tagged 'xplat' and wrongly excluded from the trend.)"),
    ("Tony",   2025, "2025-06-08", "CBS", "Cynthia Erivo",             5.10, "xplat",  "high", "thewrap",   "Across-platforms incl. Paramount+ (streaming +208% YoY). NOT comparable to the linear series — excluded from the clean trend."),
    # 79th Tonys aired 2026-06-07 (Radio City; host Pink; CBS's final contracted year).
    # Nielsen next-day figure NOT yet released as of 2026-06-08 — left NULL on purpose.
    # Do not invent it; backfill from Deadline/Variety/Nielsen when published.
    ("Tony",   2026, "2026-06-07", "CBS", "Pink",                      None, "linear", "pending", "pending", "Aired 2026-06-07. Official next-day Nielsen viewership NOT released as of 2026-06-08; awaiting trade-press report. Update this row when published."),

    # ---- ACADEMY AWARDS / OSCARS (ABC) ----
    ("Oscars", 2014, "2014-03-02", "ABC", "Ellen DeGeneres",          43.74, "linear", "high", "statista",  "12 Years a Slave / Gravity year."),
    ("Oscars", 2015, "2015-02-22", "ABC", "Neil Patrick Harris",      37.26, "linear", "high", "statista",  ""),
    ("Oscars", 2016, "2016-02-28", "ABC", "Chris Rock",               34.43, "linear", "high", "statista",  "#OscarsSoWhite year."),
    ("Oscars", 2017, "2017-02-26", "ABC", "Jimmy Kimmel",             32.94, "linear", "high", "statista",  "La La Land/Moonlight envelope mix-up."),
    ("Oscars", 2018, "2018-03-04", "ABC", "Jimmy Kimmel",             26.50, "linear", "high", "statista",  ""),
    ("Oscars", 2019, "2019-02-24", "ABC", "(no host)",                29.56, "linear", "high", "statista",  "Green Book wins; hostless bump."),
    ("Oscars", 2020, "2020-02-09", "ABC", "(no host)",                23.64, "linear", "high", "statista",  "Parasite."),
    ("Oscars", 2021, "2021-04-25", "ABC", "(no host)",                10.40, "linear", "high", "statista",  "Pandemic, Union Station; all-time low."),
    ("Oscars", 2022, "2022-03-27", "ABC", "Schumer/Hall/Sykes",       16.62, "linear", "high", "statista",  "The 'slap' year."),
    ("Oscars", 2023, "2023-03-12", "ABC", "Jimmy Kimmel",             18.76, "linear", "high", "statista",  "Everything Everywhere All at Once."),
    ("Oscars", 2024, "2024-03-10", "ABC", "Jimmy Kimmel",             19.50, "linear", "high", "cbsnews",   "Oppenheimer; 4-year high."),
    ("Oscars", 2025, "2025-03-02", "ABC", "Conan O'Brien",            19.69, "linear", "high", "variety",   "Nielsen incl. digital; 5-year high."),

    # ---- PRIMETIME EMMY AWARDS (rotating network) ----
    # ceremony_year = the awards' year; note Jan air dates where applicable.
    ("Emmys",  2014, "2014-08-25", "NBC", "Seth Meyers",              15.60, "linear", "med",  "statista",  ""),
    ("Emmys",  2015, "2015-09-20", "FOX", "Andy Samberg",             11.90, "linear", "med",  "statista",  ""),
    ("Emmys",  2016, "2016-09-18", "ABC", "Jimmy Kimmel",             11.38, "linear", "med",  "statista",  ""),
    ("Emmys",  2017, "2017-09-17", "CBS", "Stephen Colbert",          11.40, "linear", "med",  "thr",       ""),
    ("Emmys",  2018, "2018-09-17", "NBC", "Che/Jost",                 10.17, "linear", "high", "deadline",  "Then-record low; NFL counterprogramming."),
    ("Emmys",  2019, "2019-09-22", "FOX", "(no host)",                 6.90, "linear", "high", "statista",  ""),
    ("Emmys",  2020, "2020-09-20", "ABC", "Jimmy Kimmel",              6.36, "linear", "high", "statista",  "Virtual / pandemic."),
    ("Emmys",  2021, "2021-09-19", "CBS", "Cedric the Entertainer",    7.40, "linear", "med",  "variety",   ""),
    ("Emmys",  2022, "2022-09-12", "NBC", "Kenan Thompson",            5.92, "linear", "high", "variety",   ""),
    ("Emmys",  2023, "2024-01-15", "FOX", "Anthony Anderson",          4.30, "linear", "high", "thr",       "Strike-delayed to Jan 2024; all-time low."),
    ("Emmys",  2024, "2024-09-15", "ABC", "Eugene/Dan Levy",           6.90, "linear", "high", "variety",   "+54% off the Jan low."),
    ("Emmys",  2025, "2025-09-14", "CBS", "Nate Bargatze",             7.40, "linear", "med",  "axios",     "4-year high."),

    # ---- GRAMMY AWARDS (CBS) ----
    ("Grammys",2010, "2010-01-31", "CBS", "(no host)",                25.80, "linear", "med",  "chartdata", ""),
    ("Grammys",2011, "2011-02-13", "CBS", "(no host)",                26.50, "linear", "med",  "chartdata", ""),
    ("Grammys",2012, "2012-02-12", "CBS", "LL Cool J",                39.90, "linear", "high", "chartdata", "Whitney Houston died the night before — anomalous spike."),
    ("Grammys",2013, "2013-02-10", "CBS", "LL Cool J",                28.40, "linear", "med",  "chartdata", ""),
    ("Grammys",2014, "2014-01-26", "CBS", "LL Cool J",                28.50, "linear", "med",  "chartdata", ""),
    ("Grammys",2015, "2015-02-08", "CBS", "LL Cool J",                25.30, "linear", "med",  "chartdata", ""),
    ("Grammys",2016, "2016-02-15", "CBS", "LL Cool J",                24.95, "linear", "med",  "chartdata", ""),
    ("Grammys",2017, "2017-02-12", "CBS", "James Corden",             26.10, "linear", "med",  "chartdata", ""),
    ("Grammys",2018, "2018-01-28", "CBS", "James Corden",             19.80, "linear", "med",  "chartdata", ""),
    ("Grammys",2019, "2019-02-10", "CBS", "Alicia Keys",              19.90, "linear", "med",  "chartdata", ""),
    ("Grammys",2020, "2020-01-26", "CBS", "Alicia Keys",              18.70, "linear", "high", "chartdata", "Kobe Bryant died that day."),
    ("Grammys",2021, "2021-03-14", "CBS", "Trevor Noah",               9.20, "linear", "high", "chartdata", "Pandemic; all-time low."),
    ("Grammys",2022, "2022-04-03", "CBS", "Trevor Noah",               9.60, "linear", "high", "chartdata", "Moved to Las Vegas."),
    ("Grammys",2023, "2023-02-05", "CBS", "Trevor Noah",              12.50, "linear", "high", "chartdata", ""),
    ("Grammys",2024, "2024-02-04", "CBS", "Trevor Noah",              16.90, "linear", "high", "chartdata", "Post-pandemic high."),
    ("Grammys",2025, "2025-02-02", "CBS", "Trevor Noah",              15.40, "linear", "high", "thewrap",   ""),
    ("Grammys",2026, "2026-02-01", "CBS", "Trevor Noah",              14.40, "linear", "high", "thr",       "Final year on CBS."),
]


# -----------------------------------------------------------------------------
# 2. AUDIENCE DEMOGRAPHICS — median viewer age (sparse snapshots)
# -----------------------------------------------------------------------------
# These are not a full panel; they are the best-documented snapshots. The
# headline finding lives here: the Tony audience is the OLDEST of any major
# award show. Backfill from Nielsen / Statista demographic breakouts.
# columns: award, year, median_viewer_age, source_key, notes
AUDIENCE_DEMOGRAPHICS = [
    ("Tony",    2008, 61.3, "adage",    "Oldest median age of any award show surveyed."),
    ("Emmys",   2008, 52.1, "adage",    ""),
    ("Oscars",  2008, 49.5, "adage",    ""),
    ("Grammys", 2008, 45.2, "adage",    "Youngest of the big four."),
    ("Oscars",  2024, 55.0, "statista", "Majority of 96th Oscars viewers were 55+; 18-34 only ~11%."),
]


# -----------------------------------------------------------------------------
# 3. TV UNIVERSE — per-year denominators (to strip out the all-TV decline)
# -----------------------------------------------------------------------------
# us_tv_households_m : Nielsen-estimated US TV households (millions), approximate
# pay_tv_penetration : % of US households with a traditional pay-TV subscription
# These let us express each ceremony as a SHARE of the available TV audience,
# so we can ask: are the Tonys losing the audience that *still has a TV*, or
# just riding the same cord-cutting tide as everything else?
# columns: year, us_tv_households_m, pay_tv_penetration_pct, source_key, notes
TV_UNIVERSE = [
    (2001, 102.0, 86.0, "approx", "Approximate; pre-cord-cutting peak era."),
    (2010, 114.9, 88.0, "approx", "Pay-TV penetration peak (~88%)."),
    (2011, 114.7, 87.0, "approx", ""),
    (2012, 114.2, 86.0, "approx", ""),
    (2013, 115.6, 85.0, "approx", ""),
    (2014, 115.6, 84.0, "approx", ""),
    (2015, 116.3, 82.0, "approx", ""),
    (2016, 118.4, 81.0, "approx", ""),
    (2017, 118.6, 78.0, "approx", ""),
    (2018, 119.6, 75.0, "approx", ""),
    (2019, 120.6, 72.0, "approx", ""),
    (2020, 121.0, 69.0, "approx", "Pandemic."),
    (2021, 121.0, 67.0, "approx", ""),
    (2022, 122.4, 65.0, "approx", ""),
    (2023, 123.8, 64.0, "approx", "Pay-TV penetration ~64% per Statista."),
    (2024, 125.0, 60.0, "approx", ""),
    (2025, 125.8, 57.0, "approx", "Approximate."),
]


# -----------------------------------------------------------------------------
# 4. ATTENTION INDEX — the "something else" beyond Nielsen (schema + sparse seed)
# -----------------------------------------------------------------------------
# This is where the analyst plugs in non-TV relevance proxies that DO NOT depend
# on owning a television — the cleanest evidence on "cultural relevance" as
# distinct from "linear-TV ratings". Suggested metrics (see RESEARCH_PLAN.md):
#   gtrends_ceremony_week : Google Trends interest for "<award> awards", the week
#                           of the ceremony (0-100 within-award index)
#   wiki_pageviews_spike  : Wikipedia pageviews of the ceremony article in the
#                           week of the ceremony (Wikimedia REST pageviews API)
#   social_mentions       : X/Reddit/TikTok mention volume (vendor data)
# Seeded empty by design; backfill is a documented next step.
# columns: award, year, metric, value, source_key, notes
ATTENTION_INDEX: list[tuple] = [
    # e.g. ("Tony", 2024, "gtrends_ceremony_week", 12, "gtrends", "relative to Oscars=100")
]


SCHEMA = """
DROP TABLE IF EXISTS award_broadcasts;
CREATE TABLE award_broadcasts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    award           TEXT    NOT NULL,
    ceremony_year   INTEGER NOT NULL,
    air_date        TEXT,
    network         TEXT,
    host            TEXT,
    viewers_m       REAL,
    measurement     TEXT,            -- 'linear' | 'xplat'
    confidence      TEXT,            -- 'high' | 'med' | 'low'
    source_key      TEXT,
    notes           TEXT,
    UNIQUE(award, ceremony_year, measurement)
);

DROP TABLE IF EXISTS audience_demographics;
CREATE TABLE audience_demographics (
    award             TEXT NOT NULL,
    year              INTEGER NOT NULL,
    median_viewer_age REAL,
    source_key        TEXT,
    notes             TEXT
);

DROP TABLE IF EXISTS tv_universe;
CREATE TABLE tv_universe (
    year                   INTEGER PRIMARY KEY,
    us_tv_households_m     REAL,
    pay_tv_penetration_pct REAL,
    source_key             TEXT,
    notes                  TEXT
);

DROP TABLE IF EXISTS attention_index;
CREATE TABLE attention_index (
    award      TEXT NOT NULL,
    year       INTEGER NOT NULL,
    metric     TEXT NOT NULL,
    value      REAL,
    source_key TEXT,
    notes      TEXT
);

-- Convenience view: clean, comparable linear series only (drops 'xplat' rows),
-- joined to the per-year TV-universe denominators.
DROP VIEW IF EXISTS v_relevance;
CREATE VIEW v_relevance AS
SELECT b.award,
       b.ceremony_year                       AS year,
       b.viewers_m,
       b.network,
       b.confidence,
       u.us_tv_households_m,
       u.pay_tv_penetration_pct,
       1000.0 * b.viewers_m / u.us_tv_households_m AS viewers_per_1000_tvhh
FROM award_broadcasts b
LEFT JOIN tv_universe u ON u.year = b.ceremony_year
WHERE b.measurement = 'linear';
"""


def build():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript(SCHEMA)

    cur.executemany(
        "INSERT INTO award_broadcasts "
        "(award, ceremony_year, air_date, network, host, viewers_m, measurement, confidence, source_key, notes) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        AWARD_BROADCASTS,
    )
    cur.executemany(
        "INSERT INTO audience_demographics (award, year, median_viewer_age, source_key, notes) "
        "VALUES (?,?,?,?,?)",
        AUDIENCE_DEMOGRAPHICS,
    )
    cur.executemany(
        "INSERT INTO tv_universe (year, us_tv_households_m, pay_tv_penetration_pct, source_key, notes) "
        "VALUES (?,?,?,?,?)",
        TV_UNIVERSE,
    )
    if ATTENTION_INDEX:
        cur.executemany(
            "INSERT INTO attention_index (award, year, metric, value, source_key, notes) "
            "VALUES (?,?,?,?,?,?)",
            ATTENTION_INDEX,
        )

    con.commit()

    # Export CSV snapshots for downstream / spreadsheet use
    _dump_csv(con, "award_broadcasts", SRC / "award_broadcasts.csv")
    _dump_csv(con, "audience_demographics", SRC / "audience_demographics.csv")
    _dump_csv(con, "tv_universe", SRC / "tv_universe.csv")

    # Report
    n = cur.execute("SELECT COUNT(*) FROM award_broadcasts").fetchone()[0]
    by = cur.execute(
        "SELECT award, COUNT(*), MIN(ceremony_year), MAX(ceremony_year) "
        "FROM award_broadcasts WHERE measurement='linear' GROUP BY award ORDER BY award"
    ).fetchall()
    con.close()

    print(f"Built {DB_PATH}  ({n} broadcast rows)")
    for award, c, y0, y1 in by:
        print(f"   {award:8s}: {c:2d} linear years  ({y0}–{y1})")
    print(f"CSV snapshots written to {SRC}/")


def _dump_csv(con, table, path):
    cur = con.execute(f"SELECT * FROM {table}")
    cols = [d[0] for d in cur.description]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(cur.fetchall())


if __name__ == "__main__":
    build()

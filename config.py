"""Central configuration for the Critics-Impact analysis project.

Path layout (relative to this file at the project root):

    data/critics_impact.db     SQLite database (committed)
    data/exports/              CSV / Parquet exports (committed)
    data/raw_html/             Scraper HTML cache (gitignored; built locally)
    data/checkpoints/          Scraper checkpoint state (gitignored)
    logs/                      Scraper logs (gitignored)

The pipeline writes everything under `data/` except `logs/`. The analysis
scripts only read from `data/critics_impact.db`.
"""
from pathlib import Path
import os

# --- Project Paths ---
ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "critics_impact.db"
RAW_HTML_DIR = ROOT / "data" / "raw_html"
EXPORTS_DIR = ROOT / "data" / "exports"
CHECKPOINTS_DIR = ROOT / "data" / "checkpoints"
LOGS_DIR = ROOT / "logs"

# --- Optional external assets ---
# Set these env vars if you want the import scripts to seed the DB from
# pre-existing files (broadway-world grosses xlsx, IBDB Tony CSV, etc.).
# If unset, the pipeline will scrape these from scratch.
EXISTING_GROSSES_XLSX = Path(os.environ.get("CIA_GROSSES_XLSX", "")) or None
EXISTING_TONY_CSV     = Path(os.environ.get("CIA_TONY_CSV", ""))     or None
EXISTING_SHOWS_CSV    = Path(os.environ.get("CIA_SHOWS_CSV", ""))    or None

# --- Source URLs ---
DTLI_BASE = "https://didtheylikeit.com"
DTLI_BROADWAY_ARCHIVE = f"{DTLI_BASE}/broadway/"
DTLI_SHOW_URL = f"{DTLI_BASE}/shows/{{slug}}/"

BWW_GROSSES_URL = "https://www.broadwayworld.com/json_grosses.cfm"

NYT_THEATER_BASE = "https://www.nytimes.com/section/theater"
NYT_CRITICS_PICKS_URL = "https://www.nytimes.com/section/theater/critics-picks"

# --- Scraping Behavior ---
RATE_LIMIT_MIN = 1.5   # seconds between requests
RATE_LIMIT_MAX = 3.5
MAX_WORKERS = 6        # concurrent fetches
HTML_CACHE_MAX_AGE_DAYS = 7        # re-fetch cache older than this
CLOSED_SHOW_CACHE_MAX_AGE_DAYS = 365  # closed shows almost never change

# Review window: reviews published within this many days of opening night
# count as the "opening night consensus" signal.
# Broadway critics typically publish within 1–4 weeks of opening.
# 21 days covers the standard window; set higher for Off-Broadway transfers.
OPENING_WINDOW_DAYS = 21

# --- Show Matching ---
FUZZY_MATCH_THRESHOLD = 85  # rapidfuzz score (0-100) to consider a match
REVIVAL_YEAR_WINDOW = 2     # years of tolerance when matching revivals

# --- BroadwayWorld scraper (reused from existing project) ---
BWW_START_DATE_STR = "2010-01-03"

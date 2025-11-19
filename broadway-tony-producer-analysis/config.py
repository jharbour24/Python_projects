"""
Configuration file for Broadway Tony Producer Analysis pipeline.

Contains constants, paths, and settings used across the project.
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.absolute()

# Data directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_TABLES_DIR = OUTPUT_DIR / "tables"
OUTPUT_FIGURES_DIR = OUTPUT_DIR / "figures"

# Ensure directories exist
for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUT_TABLES_DIR, OUTPUT_FIGURES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Analysis parameters
START_SEASON = "2010-2011"
START_TONY_YEAR = 2011  # Tony year is typically the spring year (2011 for 2010-2011 season)
END_TONY_YEAR = 2025    # Update annually

# Tony ceremony dates (approximate - typically early June)
# Used to compute post_tony_period indicator
TONY_CEREMONY_DATES = {
    2011: "2011-06-12",
    2012: "2012-06-10",
    2013: "2013-06-09",
    2014: "2014-06-08",
    2015: "2015-06-07",
    2016: "2016-06-12",
    2017: "2017-06-11",
    2018: "2018-06-10",
    2019: "2019-06-09",
    2020: "2020-10-04",  # Postponed due to COVID
    2021: "2021-09-26",  # Postponed due to COVID
    2022: "2022-06-12",
    2023: "2023-06-11",
    2024: "2024-06-16",
    2025: "2025-06-08",  # Estimated
}

# Tony categories that determine "major win"
MAJOR_TONY_CATEGORIES = [
    "Best Musical",
    "Best Play",
    "Best Revival of a Musical",
    "Best Revival of a Play",
]

# Web scraping settings
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
REQUEST_TIMEOUT = 30  # seconds
RATE_LIMIT_DELAY = 1.5  # seconds between requests

# Title matching settings
FUZZY_MATCH_THRESHOLD = 85  # Minimum similarity score (0-100) for fuzzy matching

# Data quality settings
MIN_PRODUCER_COUNT = 0  # Minimum plausible producer count
MAX_PRODUCER_COUNT = 100  # Maximum plausible producer count (flag if exceeded)

# Output file names
SHOWS_CSV = PROCESSED_DATA_DIR / "shows.csv"
WEEKLY_GROSSES_CSV = PROCESSED_DATA_DIR / "weekly_grosses.csv"
SURVIVAL_PANEL_CSV = PROCESSED_DATA_DIR / "survival_panel.csv"
TONY_NOMINATIONS_RAW_CSV = RAW_DATA_DIR / "tony_nominations_raw.csv"
PRODUCERS_RAW_CSV = RAW_DATA_DIR / "producers_raw.csv"
PRODUCERS_CLEAN_CSV = RAW_DATA_DIR / "producers_clean.csv"
GROSSES_RAW_CSV = RAW_DATA_DIR / "grosses_raw.csv"

# Season to year conversion helper
def season_to_tony_year(season: str) -> int:
    """
    Convert season string (e.g., '2010-2011') to Tony year (e.g., 2011).

    Tony ceremonies typically occur in June of the second year in the season.
    """
    if '-' in season:
        return int(season.split('-')[1])
    return int(season)

def tony_year_to_season(tony_year: int) -> str:
    """
    Convert Tony year (e.g., 2011) to season string (e.g., '2010-2011').
    """
    return f"{tony_year - 1}-{tony_year}"

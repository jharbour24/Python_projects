"""
Master data builder: merge all data sources into final analytical datasets.

Builds three core tables:
1. shows.csv - one row per show with all metadata
2. weekly_grosses.csv - panel data (show × week)
3. survival_panel.csv - for hazard models

Author: Broadway Analysis Pipeline
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import config
from utils import (
    normalize_title, create_show_id, fuzzy_match_titles,
    parse_date, compute_days_running, compute_weeks_running,
    get_season_from_date, setup_logger
)

logger = setup_logger(__name__)


class MasterDataBuilder:
    """Build master analytical datasets from raw sources."""

    def __init__(self):
        self.tony_df = None
        self.producers_df = None
        self.grosses_df = None
        self.shows_df = None

    def load_raw_data(self):
        """Load all raw data files."""
        logger.info("Loading raw data files...")

        # Load Tony outcomes
        tony_path = config.RAW_DATA_DIR / "tony_outcomes_aggregated.csv"
        if tony_path.exists():
            self.tony_df = pd.read_csv(tony_path)
            logger.info(f"Loaded {len(self.tony_df)} shows from Tony outcomes")
        else:
            logger.warning(f"Tony outcomes file not found: {tony_path}")
            self.tony_df = pd.DataFrame()

        # Load producers
        producers_path = config.PRODUCERS_CLEAN_CSV
        if producers_path.exists():
            self.producers_df = pd.read_csv(producers_path)
            logger.info(f"Loaded {len(self.producers_df)} shows from producer data")
        else:
            logger.warning(f"Producer data file not found: {producers_path}")
            self.producers_df = pd.DataFrame()

        # Load grosses
        grosses_path = config.PROCESSED_DATA_DIR / "weekly_grosses_preliminary.csv"
        if grosses_path.exists():
            self.grosses_df = pd.read_csv(grosses_path)
            self.grosses_df['week_ending_date'] = pd.to_datetime(self.grosses_df['week_ending_date'])
            logger.info(f"Loaded {len(self.grosses_df)} weekly grosses records")
        else:
            logger.warning(f"Grosses data file not found: {grosses_path}")
            logger.warning("Proceeding without grosses data. Analysis will be limited.")
            self.grosses_df = pd.DataFrame()

    def build_shows_table(self) -> pd.DataFrame:
        """
        Build the master shows.csv table.

        Returns
        -------
        pd.DataFrame
            One row per show with all metadata
        """
        logger.info("Building shows table...")

        if self.tony_df.empty:
            logger.error("Cannot build shows table without Tony data.")
            return pd.DataFrame()

        # Start with Tony data
        shows = self.tony_df.copy()

        # Add normalized title for matching
        shows['title_normalized'] = shows['title'].apply(normalize_title)

        # Merge producer data
        if not self.producers_df.empty:
            producers = self.producers_df.copy()
            producers['title_normalized'] = producers['title'].apply(normalize_title)

            # Merge on normalized title and year
            shows = shows.merge(
                producers[['title_normalized', 'producer_count_total',
                          'lead_producer_count', 'co_producer_count', 'scrape_success']],
                on='title_normalized',
                how='left',
                suffixes=('', '_producer')
            )

            logger.info(f"Merged producer data for {shows['scrape_success'].sum()} shows")
        else:
            # Add placeholder columns
            shows['producer_count_total'] = np.nan
            shows['lead_producer_count'] = np.nan
            shows['co_producer_count'] = np.nan
            shows['scrape_success'] = False

        # Add show_id
        shows['show_id'] = shows.apply(
            lambda row: create_show_id(row['title'], row['tony_year']), axis=1
        )

        # Add placeholder columns for fields not yet implemented
        shows['opening_date'] = pd.NaT
        shows['closing_date'] = pd.NaT
        shows['theatre_name'] = np.nan
        shows['theatre_size'] = np.nan
        shows['category'] = np.nan
        shows['musical_vs_play'] = np.nan
        shows['ip_familiarity'] = np.nan
        shows['capitalization_bracket'] = np.nan
        shows['nyt_review_score'] = np.nan
        shows['critic_pick'] = np.nan
        shows['star_power'] = np.nan

        # Compute run length (will be NaN for now, needs opening/closing dates)
        shows['days_running_total'] = shows.apply(
            lambda row: compute_days_running(row['opening_date'], row['closing_date']),
            axis=1
        )
        shows['weeks_running_total'] = shows.apply(
            lambda row: compute_weeks_running(row['opening_date'], row['closing_date']),
            axis=1
        )

        # Reorder columns
        column_order = [
            'show_id', 'title', 'season', 'tony_year',
            'opening_date', 'closing_date', 'days_running_total', 'weeks_running_total',
            'theatre_name', 'theatre_size', 'category', 'musical_vs_play',
            'ip_familiarity', 'capitalization_bracket',
            'nyt_review_score', 'critic_pick', 'star_power',
            'tony_nom_count', 'tony_win_count', 'tony_win_any', 'tony_major_win',
            'producer_count_total', 'lead_producer_count', 'co_producer_count',
        ]

        shows = shows[[col for col in column_order if col in shows.columns]]

        logger.info(f"Built shows table with {len(shows)} shows")

        self.shows_df = shows
        return shows

    def build_weekly_grosses_table(self) -> pd.DataFrame:
        """
        Build the weekly_grosses.csv table (panel data).

        Returns
        -------
        pd.DataFrame
            One row per show-week
        """
        logger.info("Building weekly grosses table...")

        if self.grosses_df.empty:
            logger.warning("No grosses data available. Creating empty weekly_grosses table.")
            return pd.DataFrame()

        if self.shows_df is None or self.shows_df.empty:
            logger.error("Shows table not built. Cannot build weekly grosses table.")
            return pd.DataFrame()

        grosses = self.grosses_df.copy()

        # Normalize titles for matching
        grosses['title_normalized'] = grosses['show_title'].apply(normalize_title)

        # Match grosses to shows via fuzzy matching
        show_titles = self.shows_df['title'].tolist()
        show_ids = self.shows_df['show_id'].tolist()
        show_title_to_id = dict(zip(show_titles, show_ids))

        def match_show_id(gross_title):
            best_match, score = fuzzy_match_titles(gross_title, show_titles, threshold=85)
            if best_match:
                return show_title_to_id.get(best_match)
            return None

        grosses['show_id'] = grosses['show_title'].apply(match_show_id)

        # Drop unmatched shows
        unmatched = grosses['show_id'].isna().sum()
        if unmatched > 0:
            logger.warning(f"Could not match {unmatched} grosses records to shows. Dropping.")
            grosses = grosses.dropna(subset=['show_id'])

        # Add season based on week ending date
        grosses['season'] = grosses['week_ending_date'].apply(get_season_from_date)

        # Compute week_number_since_open
        # For this, we need opening_date from shows
        # Since opening_date is placeholder (NaN), week_number will be NaN
        # TODO: Once opening_date is populated, compute this properly

        grosses = grosses.merge(
            self.shows_df[['show_id', 'opening_date']],
            on='show_id',
            how='left'
        )

        def compute_week_number(row):
            if pd.isna(row['opening_date']) or pd.isna(row['week_ending_date']):
                return np.nan
            days_diff = (row['week_ending_date'] - row['opening_date']).days
            return max(1, int(days_diff / 7))

        grosses['week_number_since_open'] = grosses.apply(compute_week_number, axis=1)

        # Add post_tony_period indicator
        grosses = grosses.merge(
            self.shows_df[['show_id', 'tony_year']],
            on='show_id',
            how='left'
        )

        def compute_post_tony(row):
            if pd.isna(row['tony_year']):
                return 0
            tony_year = int(row['tony_year'])
            tony_date_str = config.TONY_CEREMONY_DATES.get(tony_year)
            if tony_date_str:
                tony_date = pd.to_datetime(tony_date_str)
                return int(row['week_ending_date'] >= tony_date)
            return 0

        grosses['post_tony_period'] = grosses.apply(compute_post_tony, axis=1)

        # Select and order columns
        column_order = [
            'show_id', 'show_title', 'week_ending_date', 'week_number_since_open',
            'season', 'weekly_gross', 'capacity_pct', 'avg_ticket_price',
            'post_tony_period'
        ]

        grosses = grosses[[col for col in column_order if col in grosses.columns]]

        logger.info(f"Built weekly grosses table with {len(grosses)} records")

        return grosses

    def build_survival_panel(self) -> pd.DataFrame:
        """
        Build the survival_panel.csv table for hazard models.

        Returns
        -------
        pd.DataFrame
            One row per show-week with survival analysis variables
        """
        logger.info("Building survival panel...")

        if self.shows_df is None or self.shows_df.empty:
            logger.error("Shows table not built. Cannot build survival panel.")
            return pd.DataFrame()

        # For survival analysis, we need:
        # - show_id
        # - week_number_since_open (duration)
        # - event_close_this_week (1 if show closed this week, else 0)
        # - censored (1 if still running at end of observation, else 0)
        # - covariates from shows table

        # Since we don't have opening/closing dates yet, create a simplified version
        # using weeks_running_total as duration

        survival = self.shows_df[['show_id', 'weeks_running_total']].copy()
        survival = survival.dropna(subset=['weeks_running_total'])

        if survival.empty:
            logger.warning("No shows with run length data. Creating placeholder survival panel.")
            # Create a minimal placeholder
            survival = self.shows_df[['show_id']].copy()
            survival['duration'] = np.nan
            survival['event'] = 0
            survival['censored'] = 1
        else:
            # Duration = weeks_running_total
            survival['duration'] = survival['weeks_running_total']

            # Event: 1 if show has closed (closing_date is not NaN)
            # For now, assume all shows in dataset have closed (event=1)
            # TODO: Update when we have actual closing_date data
            survival['event'] = 1
            survival['censored'] = 0

        # Merge show-level covariates
        covariates = self.shows_df[[
            'show_id', 'producer_count_total', 'lead_producer_count', 'co_producer_count',
            'nyt_review_score', 'critic_pick', 'musical_vs_play', 'theatre_size',
            'capitalization_bracket', 'tony_win_any', 'tony_nom_count'
        ]]

        survival = survival.merge(covariates, on='show_id', how='left')

        logger.info(f"Built survival panel with {len(survival)} shows")

        return survival

    def add_metadata_from_ibdb(self):
        """
        Placeholder for scraping additional metadata from IBDB.

        This would include:
        - opening_date
        - closing_date
        - theatre_name
        - theatre_size
        - category (musical, play, revival)

        TODO: Implement IBDB metadata scraping
        """
        logger.warning("IBDB metadata scraping not yet implemented.")
        logger.warning("Placeholder columns (opening_date, closing_date, etc.) will be NaN.")
        logger.warning("TODO: Scrape IBDB for opening/closing dates, theatre info, category.")

    def add_review_scores(self):
        """
        Placeholder for adding NYT review scores.

        This would require:
        - Scraping NYT theater reviews
        - Matching reviews to shows
        - Coding sentiment: +1 (positive), 0 (mixed), -1 (negative)
        - Extracting "Critic's Pick" indicator

        TODO: Implement review scraping/manual coding
        """
        logger.warning("NYT review scores not yet implemented.")
        logger.warning("Placeholder columns (nyt_review_score, critic_pick) will be NaN.")
        logger.warning("TODO: Add review sentiment analysis or manual coding.")

    def build_all(self):
        """
        Build all master tables and save to CSV.
        """
        logger.info("=" * 60)
        logger.info("BUILDING MASTER DATASETS")
        logger.info("=" * 60)

        # Load raw data
        self.load_raw_data()

        # Build shows table
        shows = self.build_shows_table()
        if not shows.empty:
            shows.to_csv(config.SHOWS_CSV, index=False)
            logger.info(f"Saved shows table to: {config.SHOWS_CSV}")

        # Build weekly grosses table
        weekly_grosses = self.build_weekly_grosses_table()
        if not weekly_grosses.empty:
            weekly_grosses.to_csv(config.WEEKLY_GROSSES_CSV, index=False)
            logger.info(f"Saved weekly grosses table to: {config.WEEKLY_GROSSES_CSV}")

        # Build survival panel
        survival_panel = self.build_survival_panel()
        if not survival_panel.empty:
            survival_panel.to_csv(config.SURVIVAL_PANEL_CSV, index=False)
            logger.info(f"Saved survival panel to: {config.SURVIVAL_PANEL_CSV}")

        # Log limitations
        logger.info("=" * 60)
        logger.info("DATA LIMITATIONS AND TODOs")
        logger.info("=" * 60)
        self.add_metadata_from_ibdb()
        self.add_review_scores()

        logger.info("")
        logger.info("Master datasets built successfully!")
        logger.info("Review the CSV files in data/processed/ for completeness.")


def main():
    """
    Main function: build all master datasets.
    """
    builder = MasterDataBuilder()
    builder.build_all()


if __name__ == "__main__":
    main()

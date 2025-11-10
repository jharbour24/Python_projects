#!/usr/bin/env python3
"""
Google Trends Data Collector

Collects weekly search interest data from Google Trends for Broadway shows.
Uses pytrends unofficial API (no authentication required).

Output schema:
- show: Show name
- query: Search query used
- week_start: Week start date (YYYY-MM-DD)
- gt_index: Interest index 0-100
- is_partial: Boolean, True if week is incomplete
"""

import pandas as pd
import logging
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError

from ..common.timebins import to_week_start, week_agg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleTrendsCollector:
    """Collects Google Trends data for Broadway shows."""

    def __init__(self, output_dir: str = "public_signals/data/raw/google_trends"):
        """
        Initialize Google Trends collector.

        Args:
            output_dir: Directory to save raw data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize pytrends
        self.pytrends = TrendReq(
            hl='en-US',
            tz=300,  # US Eastern Time
            timeout=(10, 25),
            retries=2,
            backoff_factor=0.5
        )

        logger.info("Initialized Google Trends collector")

    def fetch_interest_over_time(
        self,
        query: str,
        start_date: str,
        end_date: str,
        geo: str = 'US-NY'  # New York state
    ) -> pd.DataFrame:
        """
        Fetch weekly interest data for a query.

        Args:
            query: Search query (e.g., "Maybe Happy Ending tickets")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            geo: Geographic location (US for nationwide, US-NY for NY state)

        Returns:
            DataFrame with date, interest (0-100), and is_partial flag

        Example:
            >>> collector = GoogleTrendsCollector()
            >>> df = collector.fetch_interest_over_time("Hamilton tickets", "2024-01-01", "2024-12-31")
        """
        try:
            # Build payload
            timeframe = f"{start_date} {end_date}"

            logger.info(f"Fetching Google Trends: '{query}' in {geo}, {timeframe}")

            self.pytrends.build_payload(
                kw_list=[query],
                timeframe=timeframe,
                geo=geo
            )

            # Fetch interest over time
            interest_df = self.pytrends.interest_over_time()

            if interest_df.empty:
                logger.warning(f"No data returned for query: {query}")
                return pd.DataFrame()

            # Reset index to get date as column
            interest_df = interest_df.reset_index()

            # Extract query column and is_partial
            result = pd.DataFrame({
                'date': interest_df['date'],
                'interest': interest_df[query],
                'is_partial': interest_df['isPartial']
            })

            logger.info(f"  ✓ Retrieved {len(result)} data points")

            return result

        except ResponseError as e:
            logger.error(f"Google Trends API error for '{query}': {e}")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Unexpected error fetching '{query}': {e}")
            return pd.DataFrame()

    def collect_show_queries(
        self,
        show_name: str,
        queries: List[str],
        start_date: str,
        end_date: str,
        geo: str = 'US-NY'
    ) -> pd.DataFrame:
        """
        Collect trends data for all queries of a show.

        Args:
            show_name: Name of the show
            queries: List of search queries to try
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            geo: Geographic location

        Returns:
            DataFrame with columns: show, query, date, interest, is_partial
        """
        all_data = []

        for query in queries:
            df = self.fetch_interest_over_time(query, start_date, end_date, geo)

            if not df.empty:
                df['show'] = show_name
                df['query'] = query
                all_data.append(df)

            # Rate limiting between queries
            import time
            import random
            time.sleep(random.uniform(2, 4))

        if not all_data:
            logger.warning(f"No Google Trends data collected for {show_name}")
            return pd.DataFrame()

        combined = pd.concat(all_data, ignore_index=True)

        # Save raw data
        raw_file = self.output_dir / f"{show_name.replace(' ', '_').replace(':', '')}_raw.csv"
        combined.to_csv(raw_file, index=False)
        logger.info(f"  💾 Saved raw data: {raw_file}")

        return combined

    def to_weekly_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert to weekly aggregated format with week_start.

        Args:
            df: DataFrame from collect_show_queries()

        Returns:
            DataFrame with schema: show, query, week_start, gt_index, is_partial
        """
        if df.empty:
            return pd.DataFrame(columns=['show', 'query', 'week_start', 'gt_index', 'is_partial'])

        df = df.copy()

        # Ensure date is datetime
        df['date'] = pd.to_datetime(df['date'])

        # Add week_start
        df['week_start'] = df['date'].apply(to_week_start)

        # Aggregate to weekly (keep max interest per week, and flag if any point is partial)
        weekly = df.groupby(['show', 'query', 'week_start']).agg({
            'interest': 'max',  # Peak interest during the week
            'is_partial': 'any'  # Flag if any data point is partial
        }).reset_index()

        weekly = weekly.rename(columns={'interest': 'gt_index'})

        # Sort
        weekly = weekly.sort_values(['show', 'query', 'week_start'])

        return weekly


def collect_google_trends(
    shows_config: List[Dict[str, Any]],
    start_date: str,
    end_date: str,
    output_dir: str = "public_signals/data/raw/google_trends"
) -> pd.DataFrame:
    """
    Main function to collect Google Trends for all shows.

    Args:
        shows_config: List of show configs with 'name' and 'queries' fields
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        output_dir: Directory for raw data

    Returns:
        Combined weekly DataFrame for all shows

    Example:
        >>> shows = [
        ...     {'name': 'Maybe Happy Ending', 'queries': ['Maybe Happy Ending tickets', 'Maybe Happy Ending Broadway']},
        ...     {'name': 'John Proctor', 'queries': ['John Proctor is the Villain tickets']}
        ... ]
        >>> df = collect_google_trends(shows, '2024-01-01', '2024-12-31')
    """
    collector = GoogleTrendsCollector(output_dir)

    all_weekly = []

    for show_config in shows_config:
        show_name = show_config['name']
        queries = show_config.get('queries', [])

        if not queries:
            logger.warning(f"No queries defined for {show_name}, skipping Google Trends")
            continue

        logger.info(f"\n{'='*70}")
        logger.info(f"Collecting Google Trends: {show_name}")
        logger.info(f"{'='*70}")

        # Collect raw data
        raw_df = collector.collect_show_queries(show_name, queries, start_date, end_date)

        if not raw_df.empty:
            # Convert to weekly
            weekly_df = collector.to_weekly_format(raw_df)
            all_weekly.append(weekly_df)

    if not all_weekly:
        logger.error("No Google Trends data collected for any show")
        return pd.DataFrame()

    # Combine all shows
    combined = pd.concat(all_weekly, ignore_index=True)

    logger.info(f"\n✓ Collected Google Trends data:")
    logger.info(f"  Shows: {combined['show'].nunique()}")
    logger.info(f"  Queries: {combined['query'].nunique()}")
    logger.info(f"  Weeks: {combined['week_start'].nunique()}")
    logger.info(f"  Total rows: {len(combined)}")

    return combined

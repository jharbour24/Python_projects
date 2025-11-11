#!/usr/bin/env python3
"""
Wikipedia Pageviews Collector

Collects daily pageview data from Wikipedia for Broadway shows using the
Wikimedia REST API (public, no authentication).

Output schema:
- show: Show name
- week_start: Week start date (YYYY-MM-DD)
- wiki_views: Total pageviews for the week
"""

import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from ..common.net import fetch
from ..common.timebins import to_week_start, week_agg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WikipediaCollector:
    """Collects Wikipedia pageview data for Broadway shows."""

    def __init__(self, output_dir: str = "public_signals/data/raw/wikipedia"):
        """
        Initialize Wikipedia collector.

        Args:
            output_dir: Directory to save raw data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.base_url = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"

        logger.info("Initialized Wikipedia pageviews collector")

    def fetch_pageviews(
        self,
        article_title: str,
        start_date: str,
        end_date: str,
        project: str = "en.wikipedia"
    ) -> pd.DataFrame:
        """
        Fetch daily pageviews for an article.

        Args:
            article_title: Wikipedia article title (e.g., "Maybe_Happy_Ending_(musical)")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            project: Wikipedia project (default: en.wikipedia)

        Returns:
            DataFrame with date and views columns

        Example:
            >>> collector = WikipediaCollector()
            >>> df = collector.fetch_pageviews("Hamilton_(musical)", "2024-01-01", "2024-12-31")
        """
        # Format dates for API (YYYYMMDD00)
        start_fmt = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y%m%d00')
        end_fmt = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d00')

        # Build URL
        # Format: /project/access/agent/article/granularity/start/end
        url = f"{self.base_url}/{project}/all-access/user/{article_title}/daily/{start_fmt}/{end_fmt}"

        logger.info(f"Fetching Wikipedia pageviews: {article_title}")

        try:
            response = fetch(url, check_robots=False, sleep_range=(1, 2))  # Wikipedia allows API access
            data = response.json()

            if 'items' not in data:
                logger.warning(f"No items in response for {article_title}")
                return pd.DataFrame()

            # Parse items
            records = []
            for item in data['items']:
                timestamp = item['timestamp']
                # Parse YYYYMMDD00 format
                date = datetime.strptime(timestamp[:8], '%Y%m%d')

                records.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'views': item['views']
                })

            df = pd.DataFrame(records)
            logger.info(f"  ✓ Retrieved {len(df)} days of pageview data")

            return df

        except ValueError as e:
            # Article not found or invalid title
            logger.warning(f"Article not found or invalid: {article_title}")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching pageviews for {article_title}: {e}")
            return pd.DataFrame()

    def find_article_title(
        self,
        show_name: str,
        possible_titles: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Find the correct Wikipedia article title for a show.

        Tries various conventions:
        - Show_Name_(musical)
        - Show_Name_(play)
        - Show_Name
        - Custom provided titles

        Args:
            show_name: Show name
            possible_titles: Optional list of titles to try

        Returns:
            Valid article title or None
        """
        # Normalize show name for URL
        base_title = show_name.replace(' ', '_').replace(':', '').replace('!', '')

        # Try various suffixes
        titles_to_try = possible_titles or []
        titles_to_try.extend([
            f"{base_title}_(musical)",
            f"{base_title}_(play)",
            f"{base_title}_(2024_musical)",
            f"{base_title}_(2024_play)",
            base_title
        ])

        logger.debug(f"Trying {len(titles_to_try)} possible titles for {show_name}")

        # Test with a short date range
        test_start = "2024-01-01"
        test_end = "2024-01-07"

        for title in titles_to_try:
            try:
                df = self.fetch_pageviews(title, test_start, test_end)
                if not df.empty:
                    logger.info(f"  ✓ Found article: {title}")
                    return title
            except:
                continue

        logger.warning(f"Could not find Wikipedia article for {show_name}")
        return None

    def collect_show_pageviews(
        self,
        show_name: str,
        start_date: str,
        end_date: str,
        article_title: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Collect pageviews for a show.

        Args:
            show_name: Name of the show
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            article_title: Optional Wikipedia article title (will auto-detect if None)

        Returns:
            DataFrame with show, date, and views columns
        """
        # Find article if not provided
        if article_title is None:
            article_title = self.find_article_title(show_name)

        if article_title is None:
            logger.error(f"Could not find Wikipedia article for {show_name}")
            return pd.DataFrame()

        # Fetch pageviews
        df = self.fetch_pageviews(article_title, start_date, end_date)

        if df.empty:
            return pd.DataFrame()

        df['show'] = show_name
        df['article_title'] = article_title

        # Save raw data
        raw_file = self.output_dir / f"{show_name.replace(' ', '_').replace(':', '')}_raw.csv"
        df.to_csv(raw_file, index=False)
        logger.info(f"  💾 Saved raw data: {raw_file}")

        return df

    def to_weekly_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert daily pageviews to weekly aggregates.

        Args:
            df: DataFrame from collect_show_pageviews()

        Returns:
            DataFrame with schema: show, week_start, wiki_views
        """
        if df.empty:
            return pd.DataFrame(columns=['show', 'week_start', 'wiki_views'])

        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])

        # Aggregate to weekly
        weekly = week_agg(
            df,
            date_col='date',
            group_cols=['show'],
            agg_spec={'views': 'sum'}
        )

        weekly = weekly.rename(columns={'views': 'wiki_views'})

        return weekly


def collect_wikipedia(
    shows_config: List[Dict[str, Any]],
    start_date: str,
    end_date: str,
    output_dir: str = "public_signals/data/raw/wikipedia"
) -> pd.DataFrame:
    """
    Main function to collect Wikipedia pageviews for all shows.

    Args:
        shows_config: List of show configs with 'name' field (and optional 'wikipedia_title')
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        output_dir: Directory for raw data

    Returns:
        Combined weekly DataFrame for all shows

    Example:
        >>> shows = [
        ...     {'name': 'Maybe Happy Ending', 'wikipedia_title': 'Maybe_Happy_Ending_(musical)'},
        ...     {'name': 'Hamilton'}
        ... ]
        >>> df = collect_wikipedia(shows, '2024-01-01', '2024-12-31')
    """
    collector = WikipediaCollector(output_dir)

    all_weekly = []

    for show_config in shows_config:
        show_name = show_config['name']
        article_title = show_config.get('wikipedia_title')

        logger.info(f"\n{'='*70}")
        logger.info(f"Collecting Wikipedia pageviews: {show_name}")
        logger.info(f"{'='*70}")

        # Collect raw data
        raw_df = collector.collect_show_pageviews(show_name, start_date, end_date, article_title)

        if not raw_df.empty:
            # Convert to weekly
            weekly_df = collector.to_weekly_format(raw_df)
            all_weekly.append(weekly_df)

    if not all_weekly:
        logger.error("No Wikipedia data collected for any show")
        return pd.DataFrame()

    # Combine all shows
    combined = pd.concat(all_weekly, ignore_index=True)

    logger.info(f"\n✓ Collected Wikipedia data:")
    logger.info(f"  Shows: {combined['show'].nunique()}")
    logger.info(f"  Weeks: {combined['week_start'].nunique()}")
    logger.info(f"  Total views: {combined['wiki_views'].sum():,.0f}")
    logger.info(f"  Total rows: {len(combined)}")

    return combined

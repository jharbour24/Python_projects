"""
Google Trends scraper for Broadway shows.
Uses pytrends library to fetch interest over time data.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import json
from .base import BaseScraper


class GoogleTrendsScraper(BaseScraper):
    """Scraper for Google Trends data using pytrends."""

    def __init__(self, cache_dir: Path, rate_limit: float = 0.5):
        super().__init__(cache_dir, rate_limit=rate_limit)
        self.pytrends = None

    def _init_pytrends(self):
        """Lazy initialization of pytrends client."""
        if self.pytrends is None:
            try:
                from pytrends.request import TrendReq

                self.pytrends = TrendReq(
                    hl="en-US",
                    tz=360,
                    timeout=(10, 25),
                    retries=2,
                    backoff_factor=0.1,
                )
            except ImportError:
                raise ImportError(
                    "pytrends is required for Google Trends data. "
                    "Install with: pip install pytrends"
                )

    def fetch_interest_over_time(
        self,
        queries: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        geo: str = "US",
        frequency: str = "weekly",
    ) -> pd.DataFrame:
        """
        Fetch Google Trends interest over time data.

        Args:
            queries: List of search terms (max 5 per API call)
            start_date: Start date for data
            end_date: End date for data
            geo: Geographic location code (default: US)
            frequency: Frequency ('daily', 'weekly', 'monthly')

        Returns:
            DataFrame with date index and columns for each query
        """
        self._init_pytrends()

        # Default to last year if no dates provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=365)

        # Format timeframe for pytrends
        timeframe = f"{start_date.strftime('%Y-%m-%d')} {end_date.strftime('%Y-%m-%d')}"

        # Google Trends limits to 5 queries at once
        if len(queries) > 5:
            print(
                f"Warning: Google Trends limits to 5 queries per request. "
                f"Processing {len(queries)} queries in batches."
            )
            dfs = []
            for i in range(0, len(queries), 5):
                batch = queries[i : i + 5]
                df = self._fetch_batch(batch, timeframe, geo)
                dfs.append(df)

            # Combine results
            result = pd.concat(dfs, axis=1)
            return result

        return self._fetch_batch(queries, timeframe, geo)

    def _fetch_batch(
        self, queries: List[str], timeframe: str, geo: str
    ) -> pd.DataFrame:
        """
        Fetch a batch of queries (max 5).

        Args:
            queries: List of search terms
            timeframe: Pytrends timeframe string
            geo: Geographic location

        Returns:
            DataFrame with interest over time
        """
        cache_key = f"trends_{'_'.join(queries)}_{timeframe}_{geo}"

        # Check cache
        cache_path = self._get_cache_path(cache_key)
        if self._is_cache_valid(cache_path):
            cached = self._read_cache(cache_key)
            if cached and "data" in cached:
                return pd.DataFrame(cached["data"])

        # Enforce rate limiting
        self._rate_limit_wait()

        try:
            self.pytrends.build_payload(
                queries, cat=0, timeframe=timeframe, geo=geo, gprop=""
            )

            df = self.pytrends.interest_over_time()

            if df.empty:
                print(f"No Google Trends data found for queries: {queries}")
                return self._empty_trends_df(queries)

            # Drop 'isPartial' column if present
            if "isPartial" in df.columns:
                df = df.drop(columns=["isPartial"])

            # Cache the result
            self._write_cache(
                cache_key,
                {
                    "queries": queries,
                    "timeframe": timeframe,
                    "geo": geo,
                    "data": df.to_dict(orient="index"),
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return df

        except Exception as e:
            print(f"Error fetching Google Trends data for {queries}: {e}")
            return self._empty_trends_df(queries)

    def fetch_related_queries(
        self, query: str, timeframe: str = "today 12-m", geo: str = "US"
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch related queries for a search term.

        Args:
            query: Search term
            timeframe: Timeframe string (default: last 12 months)
            geo: Geographic location

        Returns:
            Dict with 'top' and 'rising' DataFrames
        """
        self._init_pytrends()

        cache_key = f"trends_related_{query}_{timeframe}_{geo}"

        # Check cache
        cache_path = self._get_cache_path(cache_key)
        if self._is_cache_valid(cache_path):
            cached = self._read_cache(cache_key)
            if cached and "data" in cached:
                data = cached["data"]
                return {
                    "top": pd.DataFrame(data.get("top", [])),
                    "rising": pd.DataFrame(data.get("rising", [])),
                }

        # Enforce rate limiting
        self._rate_limit_wait()

        try:
            self.pytrends.build_payload([query], timeframe=timeframe, geo=geo)
            related = self.pytrends.related_queries()

            result = related.get(query, {"top": pd.DataFrame(), "rising": pd.DataFrame()})

            # Cache the result
            self._write_cache(
                cache_key,
                {
                    "query": query,
                    "timeframe": timeframe,
                    "geo": geo,
                    "data": {
                        "top": result["top"].to_dict(orient="records") if not result["top"].empty else [],
                        "rising": result["rising"].to_dict(orient="records") if not result["rising"].empty else [],
                    },
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return result

        except Exception as e:
            print(f"Error fetching related queries for {query}: {e}")
            return {"top": pd.DataFrame(), "rising": pd.DataFrame()}

    def _empty_trends_df(self, queries: List[str]) -> pd.DataFrame:
        """Return empty DataFrame with expected structure."""
        return pd.DataFrame(columns=queries)


def fetch_google_trends_iot(
    queries: List[str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    geo: str = "US",
    freq: str = "weekly",
    cache_dir: Path = Path("data/raw/trends"),
) -> pd.DataFrame:
    """
    Convenience function to fetch Google Trends interest over time.

    Args:
        queries: List of search terms
        start_date: Start date
        end_date: End date
        geo: Geographic location code
        freq: Frequency ('daily', 'weekly', 'monthly')
        cache_dir: Cache directory

    Returns:
        DataFrame with date index and interest scores
    """
    scraper = GoogleTrendsScraper(cache_dir=cache_dir)
    return scraper.fetch_interest_over_time(queries, start_date, end_date, geo, freq)

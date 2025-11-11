"""
Ticket price scrapers for Broadway shows.
Scrapes public listing data from SeatGeek, TodayTix, and similar platforms.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import re
from .base import BaseScraper


class TicketPriceScraper(BaseScraper):
    """Scraper for public ticket listing prices."""

    def __init__(self, cache_dir: Path, rate_limit: float = 2.0):
        super().__init__(cache_dir, rate_limit=rate_limit)

    def scrape_seatgeek_listings(self, show_query: str) -> pd.DataFrame:
        """
        Scrape public ticket listings from SeatGeek.

        Note: SeatGeek's public web interface has limited scraping capabilities.
        Full pricing data typically requires API access.

        Args:
            show_query: Show name to search

        Returns:
            DataFrame with columns: date_scraped, show_name, min_price, avg_price, max_price, listings_count
        """
        # SeatGeek search URL
        query_encoded = show_query.replace(" ", "-").lower()
        url = f"https://seatgeek.com/{query_encoded}-tickets"

        cache_key = f"seatgeek_{query_encoded}"
        html = self.fetch_url(url, cache_key=cache_key)

        if not html:
            print(f"Warning: Could not fetch SeatGeek data for '{show_query}'")
            return self._empty_prices_df()

        soup = self.parse_html(html)
        if not soup:
            return self._empty_prices_df()

        # Try to extract pricing info from the page
        prices = self._extract_seatgeek_prices(soup, show_query)

        if not prices:
            print(
                f"Warning: Could not extract price data from SeatGeek for '{show_query}'. "
                f"May require API access or show not available."
            )
            return self._empty_prices_df()

        return pd.DataFrame([prices])

    def scrape_todaytix_listings(self, show_query: str) -> pd.DataFrame:
        """
        Scrape public ticket listings from TodayTix.

        Note: TodayTix uses dynamic JavaScript loading. Full access may require
        browser automation (Playwright/Selenium).

        Args:
            show_query: Show name to search

        Returns:
            DataFrame with pricing data
        """
        # TodayTix browse URL
        url = "https://www.todaytix.com/x/nyc/shows"

        cache_key = f"todaytix_browse"
        html = self.fetch_url(url, cache_key=cache_key)

        if not html:
            print("Warning: Could not fetch TodayTix data")
            return self._empty_prices_df()

        soup = self.parse_html(html)
        if not soup:
            return self._empty_prices_df()

        # Try to extract show data
        # TodayTix uses JavaScript rendering, so static scraping is limited
        print(
            f"Warning: TodayTix requires dynamic JavaScript rendering. "
            f"Static scraping provides limited data. Consider using Playwright for full access."
        )

        return self._empty_prices_df()

    def _extract_seatgeek_prices(self, soup, show_query: str) -> Optional[Dict]:
        """
        Extract pricing information from SeatGeek HTML.

        Args:
            soup: BeautifulSoup object
            show_query: Show name

        Returns:
            Dict with price data or None
        """
        prices = {
            "date_scraped": datetime.now(),
            "show_name": show_query,
            "min_price": None,
            "avg_price": None,
            "max_price": None,
            "listings_count": 0,
        }

        # Look for price indicators in the HTML
        # SeatGeek often shows "Get in for $XX" or similar
        price_pattern = r'\$[\d,]+(?:\.\d{2})?'

        # Find all price mentions
        price_texts = soup.find_all(text=re.compile(price_pattern))

        found_prices = []
        for text in price_texts:
            matches = re.findall(price_pattern, text)
            for match in matches:
                price = float(match.replace('$', '').replace(',', ''))
                found_prices.append(price)

        if found_prices:
            prices["min_price"] = min(found_prices)
            prices["max_price"] = max(found_prices)
            prices["avg_price"] = sum(found_prices) / len(found_prices)
            prices["listings_count"] = len(found_prices)
            return prices

        return None

    def scrape_generic_listings(self, show_name: str, source_url: str) -> pd.DataFrame:
        """
        Generic scraper for ticket listing pages.

        Args:
            show_name: Name of show
            source_url: URL to scrape

        Returns:
            DataFrame with extracted price data
        """
        cache_key = f"generic_prices_{show_name}"
        html = self.fetch_url(source_url, cache_key=cache_key)

        if not html:
            return self._empty_prices_df()

        soup = self.parse_html(html)
        if not soup:
            return self._empty_prices_df()

        # Generic price extraction
        price_pattern = r'\$[\d,]+(?:\.\d{2})?'
        price_texts = soup.find_all(text=re.compile(price_pattern))

        found_prices = []
        for text in price_texts:
            matches = re.findall(price_pattern, text)
            for match in matches:
                try:
                    price = float(match.replace('$', '').replace(',', ''))
                    # Filter reasonable ticket prices ($20-$1000)
                    if 20 <= price <= 1000:
                        found_prices.append(price)
                except ValueError:
                    continue

        if not found_prices:
            return self._empty_prices_df()

        return pd.DataFrame(
            [
                {
                    "date_scraped": datetime.now(),
                    "show_name": show_name,
                    "source_url": source_url,
                    "min_price": min(found_prices),
                    "avg_price": sum(found_prices) / len(found_prices),
                    "max_price": max(found_prices),
                    "listings_count": len(found_prices),
                }
            ]
        )

    def _empty_prices_df(self) -> pd.DataFrame:
        """Return empty DataFrame with expected columns."""
        return pd.DataFrame(
            columns=[
                "date_scraped",
                "show_name",
                "min_price",
                "avg_price",
                "max_price",
                "listings_count",
            ]
        )


def scrape_prices_todaytix_or_seatgeek(
    show_query: str,
    cache_dir: Path = Path("data/raw/prices"),
) -> pd.DataFrame:
    """
    Convenience function to scrape ticket prices.

    Args:
        show_query: Show name to search
        cache_dir: Cache directory

    Returns:
        DataFrame with price data
    """
    scraper = TicketPriceScraper(cache_dir=cache_dir)

    # Try SeatGeek first
    df = scraper.scrape_seatgeek_listings(show_query)

    if df.empty:
        # Fall back to TodayTix
        df = scraper.scrape_todaytix_listings(show_query)

    return df

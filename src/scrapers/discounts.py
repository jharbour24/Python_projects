"""
BroadwayBox discount scraper for Broadway shows.
Scrapes public discount listings as a demand proxy.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import re
from .base import BaseScraper


class BroadwayBoxScraper(BaseScraper):
    """Scraper for BroadwayBox discount listings."""

    def __init__(self, cache_dir: Path, rate_limit: float = 1.0):
        super().__init__(cache_dir, rate_limit=rate_limit)

    def scrape_show_discounts(self, show_name: str) -> pd.DataFrame:
        """
        Scrape discount listings for a Broadway show.

        BroadwayBox publishes available discounts for shows. More discounts
        typically indicates lower demand / need to fill seats.

        Args:
            show_name: Name of Broadway show

        Returns:
            DataFrame with columns: date_scraped, show_name, discount_count, discount_types
        """
        # BroadwayBox show page URL
        show_slug = self._normalize_show_name(show_name)
        url = f"https://www.broadwaybox.com/shows/{show_slug}/"

        cache_key = f"broadwaybox_{show_slug}"
        html = self.fetch_url(url, cache_key=cache_key)

        if not html:
            # Try searching for the show
            search_results = self._search_show(show_name)
            if search_results:
                # Use first result
                url = search_results[0]["url"]
                html = self.fetch_url(url, cache_key=f"broadwaybox_{show_slug}_alt")

        if not html:
            print(f"Warning: Could not find BroadwayBox page for '{show_name}'")
            return self._empty_discounts_df()

        soup = self.parse_html(html)
        if not soup:
            return self._empty_discounts_df()

        # Extract discount information
        discounts = self._extract_discounts(soup, show_name)

        if not discounts:
            # Show exists but no discounts listed
            return pd.DataFrame(
                [
                    {
                        "date_scraped": datetime.now(),
                        "show_name": show_name,
                        "discount_count": 0,
                        "discount_types": [],
                    }
                ]
            )

        return pd.DataFrame([discounts])

    def scrape_all_discounts(self) -> pd.DataFrame:
        """
        Scrape discount listings for all Broadway shows.

        Returns:
            DataFrame with discount data for all shows
        """
        url = "https://www.broadwaybox.com/shows/"
        cache_key = "broadwaybox_all_shows"

        html = self.fetch_url(url, cache_key=cache_key)

        if not html:
            print("Warning: Could not fetch BroadwayBox shows list")
            return self._empty_discounts_df()

        soup = self.parse_html(html)
        if not soup:
            return self._empty_discounts_df()

        # Parse the shows list
        shows = self._parse_shows_list(soup)

        if not shows:
            return self._empty_discounts_df()

        return pd.DataFrame(shows)

    def _extract_discounts(self, soup, show_name: str) -> Optional[Dict]:
        """
        Extract discount information from show page.

        Args:
            soup: BeautifulSoup object
            show_name: Show name

        Returns:
            Dict with discount data or None
        """
        discount_types = []

        # Look for discount sections
        # BroadwayBox typically has sections like "Discount Codes", "Lottery", "Rush", "Student Discounts"
        discount_keywords = [
            "discount code",
            "promo code",
            "lottery",
            "rush",
            "student discount",
            "standing room",
            "tkts",
        ]

        # Search for discount indicators in the page
        page_text = soup.get_text().lower()

        for keyword in discount_keywords:
            if keyword in page_text:
                discount_types.append(keyword)

        # Look for specific discount elements
        discount_sections = soup.find_all(["div", "section"], class_=re.compile(r"discount|offer|deal"))

        return {
            "date_scraped": datetime.now(),
            "show_name": show_name,
            "discount_count": len(discount_types),
            "discount_types": discount_types,
        }

    def _search_show(self, show_name: str) -> List[Dict]:
        """
        Search for a show on BroadwayBox.

        Args:
            show_name: Show name to search

        Returns:
            List of search results
        """
        # BroadwayBox search URL
        query = show_name.replace(" ", "+")
        url = f"https://www.broadwaybox.com/search/?q={query}"

        cache_key = f"broadwaybox_search_{show_name}"
        html = self.fetch_url(url, cache_key=cache_key)

        if not html:
            return []

        soup = self.parse_html(html)
        if not soup:
            return []

        results = []

        # Look for show links in search results
        links = soup.find_all("a", href=re.compile(r"/shows/"))

        for link in links:
            title = link.get_text(strip=True)
            href = link.get("href", "")

            if href and title:
                full_url = href if href.startswith("http") else f"https://www.broadwaybox.com{href}"
                results.append({"title": title, "url": full_url})

        return results

    def _parse_shows_list(self, soup) -> List[Dict]:
        """
        Parse the list of all Broadway shows with discounts.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of show data dicts
        """
        shows = []

        # Find show cards or listings
        show_elements = soup.find_all(["div", "article"], class_=re.compile(r"show|production"))

        for element in show_elements:
            title_elem = element.find(["h1", "h2", "h3", "h4"])
            if not title_elem:
                continue

            show_name = title_elem.get_text(strip=True)

            # Count visible discount indicators
            discount_count = len(element.find_all(text=re.compile(r"discount|code|lottery|rush", re.I)))

            shows.append(
                {
                    "date_scraped": datetime.now(),
                    "show_name": show_name,
                    "discount_count": discount_count,
                    "discount_types": [],
                }
            )

        return shows

    def _normalize_show_name(self, show_name: str) -> str:
        """Normalize show name for URL slugs."""
        slug = show_name.lower()
        # Remove special characters except spaces and hyphens
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        # Replace spaces with hyphens
        slug = re.sub(r"[\s]+", "-", slug)
        return slug

    def _empty_discounts_df(self) -> pd.DataFrame:
        """Return empty DataFrame with expected columns."""
        return pd.DataFrame(
            columns=["date_scraped", "show_name", "discount_count", "discount_types"]
        )


def scrape_broadwaybox_discounts(
    show_name: str,
    cache_dir: Path = Path("data/raw/discounts"),
) -> pd.DataFrame:
    """
    Convenience function to scrape BroadwayBox discounts.

    Args:
        show_name: Name of Broadway show
        cache_dir: Cache directory

    Returns:
        DataFrame with discount data
    """
    scraper = BroadwayBoxScraper(cache_dir=cache_dir)
    return scraper.scrape_show_discounts(show_name)

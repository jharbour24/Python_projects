"""
TikTok public scraper for Broadway shows.
Scrapes public hashtag and sound data without authentication.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import re
import json
from .base import BaseScraper


class TikTokScraper(BaseScraper):
    """Scraper for public TikTok hashtag and sound data."""

    def __init__(self, cache_dir: Path, rate_limit: float = 1.5):
        super().__init__(cache_dir, rate_limit=rate_limit)

    def scrape_hashtag_videos(
        self,
        hashtags: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Scrape public videos for given hashtags.

        Note: TikTok's web interface has limited public access. This scraper
        attempts to extract what's available from public hashtag pages, but
        full historical data requires TikTok Research API access.

        Args:
            hashtags: List of hashtags (without #)
            start_date: Start of date range (optional)
            end_date: End of date range (optional)

        Returns:
            DataFrame with columns: video_id, hashtag, date, creator, likes, comments, shares, is_official
        """
        all_videos = []

        for hashtag in hashtags:
            videos = self._scrape_single_hashtag(hashtag)
            all_videos.extend(videos)

        if not all_videos:
            print(
                f"Warning: Could not extract TikTok videos for hashtags {hashtags}. "
                "TikTok requires authentication for full access."
            )
            return self._empty_videos_df()

        df = pd.DataFrame(all_videos)

        # Filter by date range if provided
        if "date" in df.columns and not df.empty:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            if start_date:
                df = df[df["date"] >= start_date]
            if end_date:
                df = df[df["date"] <= end_date]

        return df

    def _scrape_single_hashtag(self, hashtag: str) -> List[Dict]:
        """
        Scrape videos for a single hashtag.

        Args:
            hashtag: Hashtag without #

        Returns:
            List of video data dicts
        """
        url = f"https://www.tiktok.com/tag/{hashtag}"
        cache_key = f"tiktok_hashtag_{hashtag}"

        html = self.fetch_url(url, cache_key=cache_key)
        if not html:
            return []

        # TikTok embeds data in <script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">
        videos = self._extract_videos_from_html(html, hashtag)
        return videos

    def _extract_videos_from_html(self, html: str, hashtag: str) -> List[Dict]:
        """
        Extract video data from TikTok HTML.

        TikTok embeds JSON data in script tags.
        """
        videos = []

        # Look for __UNIVERSAL_DATA_FOR_REHYDRATION__ or SIGI_STATE
        patterns = [
            r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
            r'<script id="SIGI_STATE"[^>]*>(.*?)</script>',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))

                    # Structure varies; try to find video list
                    # Typical structure: __DEFAULT_SCOPE__ -> webapp.video-detail or challenge-detail
                    if "__DEFAULT_SCOPE__" in data:
                        scope = data["__DEFAULT_SCOPE__"]

                        # Look for challenge data
                        if "webapp.challenge-detail" in scope:
                            challenge_data = scope["webapp.challenge-detail"]
                            item_list = challenge_data.get("itemList", [])

                            for item in item_list:
                                videos.append(self._parse_video_item(item, hashtag))

                        # Look for video list in other structures
                        for key in scope:
                            if "ItemModule" in key or "itemList" in key:
                                items = scope.get(key, {})
                                if isinstance(items, dict):
                                    for video_id, video_data in items.items():
                                        if isinstance(video_data, dict):
                                            videos.append(self._parse_video_item(video_data, hashtag))

                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    print(f"Error parsing TikTok JSON for #{hashtag}: {e}")

        return videos

    def _parse_video_item(self, item: Dict, hashtag: str) -> Dict:
        """Parse a single video item from TikTok data."""
        author = item.get("author", {})
        stats = item.get("stats", {})

        return {
            "video_id": item.get("id"),
            "hashtag": hashtag,
            "date": datetime.fromtimestamp(item.get("createTime", 0)) if item.get("createTime") else None,
            "creator": author.get("uniqueId", ""),
            "creator_verified": author.get("verified", False),
            "likes": stats.get("diggCount", 0),
            "comments": stats.get("commentCount", 0),
            "shares": stats.get("shareCount", 0),
            "plays": stats.get("playCount", 0),
            "description": item.get("desc", ""),
            "is_official": author.get("verified", False),  # Approximation
        }

    def _empty_videos_df(self) -> pd.DataFrame:
        """Return empty DataFrame with expected columns."""
        return pd.DataFrame(
            columns=[
                "video_id",
                "hashtag",
                "date",
                "creator",
                "creator_verified",
                "likes",
                "comments",
                "shares",
                "plays",
                "description",
                "is_official",
            ]
        )

    def get_hashtag_stats(self, hashtag: str) -> Dict[str, int]:
        """
        Get basic hashtag statistics.

        Args:
            hashtag: Hashtag without #

        Returns:
            Dict with keys: video_count, view_count
        """
        url = f"https://www.tiktok.com/tag/{hashtag}"
        cache_key = f"tiktok_hashtag_stats_{hashtag}"

        html = self.fetch_url(url, cache_key=cache_key)
        if not html:
            return {"video_count": 0, "view_count": 0}

        # Try to extract from JSON or HTML
        soup = self.parse_html(html)
        if soup:
            # Look for view count in page (often displayed as "X.XM views")
            view_text = soup.find(text=re.compile(r'[\d.]+[KMB]?\s+views?', re.I))
            if view_text:
                match = re.search(r'([\d.]+)([KMB])?', view_text)
                if match:
                    num = float(match.group(1))
                    suffix = match.group(2)
                    multiplier = {"K": 1000, "M": 1000000, "B": 1000000000}.get(suffix, 1)
                    return {"video_count": 0, "view_count": int(num * multiplier)}

        return {"video_count": 0, "view_count": 0}

    def scrape_sound_usage(
        self,
        sound_id: Optional[str] = None,
        sound_name: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Get usage statistics for a TikTok sound.

        Args:
            sound_id: TikTok sound ID
            sound_name: Sound name for search

        Returns:
            Dict with keys: video_count, usage_trend
        """
        if not sound_id and not sound_name:
            return {"video_count": 0, "usage_trend": 0}

        # For now, return placeholder
        # Full implementation would require TikTok API or deeper scraping
        print(
            "Warning: Sound usage tracking requires TikTok API access. "
            "Returning placeholder data."
        )
        return {"video_count": 0, "usage_trend": 0}


def scrape_tiktok_public(
    hashtags: List[str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    cache_dir: Path = Path("data/raw/tiktok"),
) -> pd.DataFrame:
    """
    Convenience function to scrape TikTok hashtag data.

    Args:
        hashtags: List of hashtags (without #)
        start_date: Start of date range (optional)
        end_date: End of date range (optional)
        cache_dir: Directory for caching

    Returns:
        DataFrame with video data
    """
    scraper = TikTokScraper(cache_dir=cache_dir)
    return scraper.scrape_hashtag_videos(hashtags, start_date, end_date)

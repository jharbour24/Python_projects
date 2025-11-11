"""
Instagram public scraper for Broadway shows.
Scrapes public profile data without authentication.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import re
import json
from .base import BaseScraper


class InstagramScraper(BaseScraper):
    """Scraper for public Instagram profile data."""

    def __init__(self, cache_dir: Path, rate_limit: float = 1.0):
        super().__init__(cache_dir, rate_limit=rate_limit)

    def scrape_profile_posts(
        self,
        handle: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Scrape public posts from an Instagram profile.

        Note: Instagram's web interface requires authentication to see full post data.
        This implementation provides a fallback that attempts to extract what's available
        from public pages, but may return limited data.

        Args:
            handle: Instagram handle (without @)
            start_date: Start of date range (optional)
            end_date: End of date range (optional)

        Returns:
            DataFrame with columns: post_id, date, likes, comments, caption, media_type
        """
        url = f"https://www.instagram.com/{handle}/"
        cache_key = f"instagram_profile_{handle}"

        html = self.fetch_url(url, cache_key=cache_key)
        if not html:
            print(f"Warning: Could not fetch Instagram profile for @{handle}")
            return self._empty_posts_df()

        # Try to extract JSON data from Instagram's page structure
        posts_data = self._extract_posts_from_html(html)

        if not posts_data:
            print(
                f"Warning: Could not extract post data for @{handle}. "
                "Instagram requires login for full access."
            )
            return self._empty_posts_df()

        df = pd.DataFrame(posts_data)

        # Filter by date range if provided
        if start_date or end_date:
            df["date"] = pd.to_datetime(df["date"])
            if start_date:
                df = df[df["date"] >= start_date]
            if end_date:
                df = df[df["date"] <= end_date]

        return df

    def _extract_posts_from_html(self, html: str) -> List[Dict]:
        """
        Extract post data from Instagram HTML.

        Instagram embeds JSON data in <script> tags. This attempts to extract it.
        """
        posts = []

        # Look for window._sharedData or similar embedded JSON
        # Pattern: <script type="text/javascript">window._sharedData = {...}</script>
        pattern = r'window\._sharedData\s*=\s*({.*?});'
        match = re.search(pattern, html, re.DOTALL)

        if match:
            try:
                data = json.loads(match.group(1))

                # Navigate the nested structure to find posts
                # Structure varies, but typically:
                # _sharedData -> entry_data -> ProfilePage -> graphql -> user -> edge_owner_to_timeline_media
                profile_page = data.get("entry_data", {}).get("ProfilePage", [])
                if profile_page:
                    user_data = (
                        profile_page[0]
                        .get("graphql", {})
                        .get("user", {})
                    )
                    edges = (
                        user_data.get("edge_owner_to_timeline_media", {})
                        .get("edges", [])
                    )

                    for edge in edges:
                        node = edge.get("node", {})
                        posts.append(
                            {
                                "post_id": node.get("id"),
                                "shortcode": node.get("shortcode"),
                                "date": datetime.fromtimestamp(node.get("taken_at_timestamp", 0)),
                                "likes": node.get("edge_liked_by", {}).get("count", 0),
                                "comments": node.get("edge_media_to_comment", {}).get("count", 0),
                                "caption": self._extract_caption(node),
                                "media_type": "video" if node.get("is_video") else "photo",
                                "display_url": node.get("display_url"),
                            }
                        )

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"Error parsing Instagram JSON data: {e}")

        return posts

    def _extract_caption(self, node: Dict) -> str:
        """Extract caption text from post node."""
        edges = node.get("edge_media_to_caption", {}).get("edges", [])
        if edges:
            return edges[0].get("node", {}).get("text", "")
        return ""

    def _empty_posts_df(self) -> pd.DataFrame:
        """Return empty DataFrame with expected columns."""
        return pd.DataFrame(
            columns=[
                "post_id",
                "shortcode",
                "date",
                "likes",
                "comments",
                "caption",
                "media_type",
                "display_url",
            ]
        )

    def get_profile_stats(self, handle: str) -> Dict[str, int]:
        """
        Get basic profile statistics (followers, following, posts count).

        Args:
            handle: Instagram handle (without @)

        Returns:
            Dict with keys: followers, following, posts
        """
        url = f"https://www.instagram.com/{handle}/"
        cache_key = f"instagram_stats_{handle}"

        html = self.fetch_url(url, cache_key=cache_key)
        if not html:
            return {"followers": 0, "following": 0, "posts": 0}

        # Try to extract from JSON data
        pattern = r'window\._sharedData\s*=\s*({.*?});'
        match = re.search(pattern, html, re.DOTALL)

        if match:
            try:
                data = json.loads(match.group(1))
                profile_page = data.get("entry_data", {}).get("ProfilePage", [])
                if profile_page:
                    user_data = profile_page[0].get("graphql", {}).get("user", {})
                    return {
                        "followers": user_data.get("edge_followed_by", {}).get("count", 0),
                        "following": user_data.get("edge_follow", {}).get("count", 0),
                        "posts": user_data.get("edge_owner_to_timeline_media", {}).get("count", 0),
                    }
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback: try to extract from meta tags
        soup = self.parse_html(html)
        if soup:
            # Look for meta tags with user stats
            meta_desc = soup.find("meta", {"property": "og:description"})
            if meta_desc:
                desc = meta_desc.get("content", "")
                # Pattern: "X Followers, Y Following, Z Posts"
                followers_match = re.search(r'([\d,]+)\s+Followers', desc)
                following_match = re.search(r'([\d,]+)\s+Following', desc)
                posts_match = re.search(r'([\d,]+)\s+Posts', desc)

                return {
                    "followers": int(followers_match.group(1).replace(",", "")) if followers_match else 0,
                    "following": int(following_match.group(1).replace(",", "")) if following_match else 0,
                    "posts": int(posts_match.group(1).replace(",", "")) if posts_match else 0,
                }

        return {"followers": 0, "following": 0, "posts": 0}


def scrape_instagram_public(
    handle: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    cache_dir: Path = Path("data/raw/instagram"),
) -> pd.DataFrame:
    """
    Convenience function to scrape Instagram profile data.

    Args:
        handle: Instagram handle (without @)
        start_date: Start of date range (optional)
        end_date: End of date range (optional)
        cache_dir: Directory for caching

    Returns:
        DataFrame with post data
    """
    scraper = InstagramScraper(cache_dir=cache_dir)
    return scraper.scrape_profile_posts(handle, start_date, end_date)

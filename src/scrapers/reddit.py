"""
Reddit public scraper for Broadway shows.
Scrapes public posts and comments without authentication.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import re
import json
from .base import BaseScraper


class RedditScraper(BaseScraper):
    """Scraper for public Reddit posts and comments."""

    def __init__(self, cache_dir: Path, rate_limit: float = 2.0):
        super().__init__(cache_dir, rate_limit=rate_limit)

    def scrape_subreddit_search(
        self,
        queries: List[str],
        subreddit: str = "Broadway",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Search for posts in a subreddit.

        Uses Reddit's public JSON endpoints (no auth required).

        Args:
            queries: List of search terms
            subreddit: Subreddit name (without r/)
            start_date: Start of date range (optional)
            end_date: End of date range (optional)

        Returns:
            DataFrame with columns: post_id, title, date, score, num_comments, author, url, text
        """
        all_posts = []

        for query in queries:
            posts = self._search_subreddit(query, subreddit)
            all_posts.extend(posts)

        if not all_posts:
            return self._empty_posts_df()

        df = pd.DataFrame(all_posts)

        # Remove duplicates based on post_id
        df = df.drop_duplicates(subset=["post_id"])

        # Filter by date range if provided
        if "date" in df.columns and not df.empty:
            df["date"] = pd.to_datetime(df["date"], unit="s", errors="coerce")
            if start_date:
                df = df[df["date"] >= start_date]
            if end_date:
                df = df[df["date"] <= end_date]

        return df

    def _search_subreddit(self, query: str, subreddit: str) -> List[Dict]:
        """
        Search a subreddit for posts matching query.

        Args:
            query: Search term
            subreddit: Subreddit name

        Returns:
            List of post data dicts
        """
        # Reddit's public JSON endpoint: /r/subreddit/search.json
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = f"?q={query}&restrict_sr=1&sort=relevance&limit=100"
        full_url = url + params

        cache_key = f"reddit_search_{subreddit}_{query}"

        data = self.fetch_json(full_url, cache_key=cache_key)
        if not data:
            return []

        posts = []
        children = data.get("data", {}).get("children", [])

        for child in children:
            post_data = child.get("data", {})
            posts.append(self._parse_post(post_data, query))

        return posts

    def _parse_post(self, post_data: Dict, query: str) -> Dict:
        """Parse a single Reddit post."""
        return {
            "post_id": post_data.get("id"),
            "title": post_data.get("title", ""),
            "date": post_data.get("created_utc", 0),
            "score": post_data.get("score", 0),
            "num_comments": post_data.get("num_comments", 0),
            "author": post_data.get("author", ""),
            "url": post_data.get("url", ""),
            "permalink": "https://www.reddit.com" + post_data.get("permalink", ""),
            "text": post_data.get("selftext", ""),
            "subreddit": post_data.get("subreddit", ""),
            "query": query,
        }

    def scrape_post_comments(self, post_id: str, subreddit: str) -> pd.DataFrame:
        """
        Scrape comments from a specific post.

        Args:
            post_id: Reddit post ID
            subreddit: Subreddit name

        Returns:
            DataFrame with columns: comment_id, author, date, score, text, parent_id
        """
        # Reddit public JSON endpoint for comments
        url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
        cache_key = f"reddit_post_{post_id}"

        data = self.fetch_json(url, cache_key=cache_key)
        if not data or len(data) < 2:
            return self._empty_comments_df()

        # data[0] is the post, data[1] is the comments
        comments_data = data[1].get("data", {}).get("children", [])

        comments = []
        self._extract_comments_recursive(comments_data, comments)

        if not comments:
            return self._empty_comments_df()

        return pd.DataFrame(comments)

    def _extract_comments_recursive(
        self, children: List[Dict], comments: List[Dict]
    ) -> None:
        """
        Recursively extract comments from nested structure.

        Args:
            children: List of comment children
            comments: List to append parsed comments to
        """
        for child in children:
            if child.get("kind") == "more":
                # "more comments" placeholder, skip
                continue

            comment_data = child.get("data", {})

            # Skip if deleted/removed
            if comment_data.get("author") in ["[deleted]", "[removed]"]:
                continue

            comments.append(
                {
                    "comment_id": comment_data.get("id"),
                    "author": comment_data.get("author", ""),
                    "date": comment_data.get("created_utc", 0),
                    "score": comment_data.get("score", 0),
                    "text": comment_data.get("body", ""),
                    "parent_id": comment_data.get("parent_id", ""),
                }
            )

            # Recurse into replies
            replies = comment_data.get("replies")
            if replies and isinstance(replies, dict):
                reply_children = replies.get("data", {}).get("children", [])
                self._extract_comments_recursive(reply_children, comments)

    def get_subreddit_activity(
        self,
        queries: List[str],
        subreddit: str = "Broadway",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Get comprehensive activity data for queries in a subreddit.

        Args:
            queries: List of search terms
            subreddit: Subreddit name
            start_date: Start date filter
            end_date: End date filter

        Returns:
            Dict with keys 'posts' and 'all_comments' containing DataFrames
        """
        # Get all posts
        posts_df = self.scrape_subreddit_search(queries, subreddit, start_date, end_date)

        # Get comments for each post
        all_comments = []
        for _, post in posts_df.iterrows():
            post_id = post["post_id"]
            subreddit_name = post.get("subreddit", subreddit)
            comments_df = self.scrape_post_comments(post_id, subreddit_name)

            if not comments_df.empty:
                comments_df["post_id"] = post_id
                all_comments.append(comments_df)

        comments_df = (
            pd.concat(all_comments, ignore_index=True) if all_comments else self._empty_comments_df()
        )

        return {"posts": posts_df, "comments": comments_df}

    def _empty_posts_df(self) -> pd.DataFrame:
        """Return empty DataFrame with expected columns."""
        return pd.DataFrame(
            columns=[
                "post_id",
                "title",
                "date",
                "score",
                "num_comments",
                "author",
                "url",
                "permalink",
                "text",
                "subreddit",
                "query",
            ]
        )

    def _empty_comments_df(self) -> pd.DataFrame:
        """Return empty DataFrame with expected columns."""
        return pd.DataFrame(
            columns=["comment_id", "author", "date", "score", "text", "parent_id"]
        )


def scrape_reddit_public(
    queries: List[str],
    subreddit: str = "Broadway",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    cache_dir: Path = Path("data/raw/reddit"),
) -> Dict[str, pd.DataFrame]:
    """
    Convenience function to scrape Reddit data.

    Args:
        queries: List of search terms
        subreddit: Subreddit name (default: Broadway)
        start_date: Start date filter
        end_date: End date filter
        cache_dir: Directory for caching

    Returns:
        Dict with 'posts' and 'comments' DataFrames
    """
    scraper = RedditScraper(cache_dir=cache_dir)
    return scraper.get_subreddit_activity(queries, subreddit, start_date, end_date)

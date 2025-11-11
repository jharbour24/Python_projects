#!/usr/bin/env python3
"""
TikTok Public Profile Scraper

Collects public engagement metrics from TikTok profile pages using Playwright.
No authentication required - only scrapes publicly visible data.

Output schema:
- show: Show name
- week_start: Week start date (YYYY-MM-DD)
- tt_posts: Number of posts in week
- tt_sum_views: Total views
- tt_sum_likes: Total likes
- tt_sum_comments: Total comments
- tt_sum_shares: Total shares
- tt_unique_hashtags: Unique hashtags used
"""

import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
import re
import asyncio

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from ..common.net import respect_robots
from ..common.timebins import to_week_start, week_agg
from ..common.snapshots import save_snapshot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TikTokPost:
    """Structured representation of a TikTok post."""
    post_id: str
    post_url: str
    post_datetime: str  # ISO format YYYY-MM-DD
    views: int
    likes: int
    comments: int
    shares: int
    caption: str
    hashtags: List[str]
    is_video: bool = True  # TikTok is primarily video

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class TikTokPublicCollector:
    """Collects public TikTok engagement data without authentication."""

    def __init__(self, output_dir: str = "public_signals/data/raw/tiktok"):
        """
        Initialize TikTok collector.

        Args:
            output_dir: Directory to save raw data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.base_url = "https://www.tiktok.com"

        logger.info("Initialized TikTok public collector")

    async def fetch_profile_posts(
        self,
        handle: str,
        max_posts: int = 30
    ) -> List[TikTokPost]:
        """
        Fetch recent public posts from a TikTok profile.

        Args:
            handle: TikTok handle (e.g., "@broadwayshow")
            max_posts: Maximum number of recent posts to collect

        Returns:
            List of TikTokPost objects

        Example:
            >>> collector = TikTokPublicCollector()
            >>> posts = await collector.fetch_profile_posts("@hamiltonmusical")
        """
        # Normalize handle
        if not handle.startswith('@'):
            handle = f"@{handle}"

        profile_url = f"{self.base_url}/{handle}"

        # Check robots.txt
        if not respect_robots(profile_url):
            logger.warning(f"TikTok profile blocked by robots.txt: {handle}")
            return []

        logger.info(f"Fetching TikTok profile: {handle}")

        posts = []

        try:
            async with async_playwright() as p:
                # Launch browser (headless)
                browser = await p.chromium.launch(headless=True)

                # Create context with realistic settings
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    viewport={"width": 1280, "height": 720}
                )

                page = await context.new_page()

                # Navigate to profile
                await page.goto(profile_url, wait_until="networkidle", timeout=30000)

                # Wait for video grid to load
                try:
                    await page.wait_for_selector('[data-e2e="user-post-item"]', timeout=10000)
                except PlaywrightTimeout:
                    logger.warning(f"No posts found or page not loaded: {handle}")
                    await browser.close()
                    return []

                # Scroll to load more posts
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1)

                # Extract post elements
                post_items = await page.query_selector_all('[data-e2e="user-post-item"]')

                logger.info(f"  Found {len(post_items)} post elements")

                for idx, item in enumerate(post_items[:max_posts]):
                    try:
                        post_data = await self._parse_post_element(item, page)
                        if post_data:
                            posts.append(post_data)
                    except Exception as e:
                        logger.debug(f"Could not parse post {idx}: {e}")
                        continue

                await browser.close()

        except Exception as e:
            logger.error(f"Error fetching TikTok profile {handle}: {e}")
            return []

        logger.info(f"  ✓ Retrieved {len(posts)} posts")

        return posts

    async def _parse_post_element(self, element, page) -> Optional[TikTokPost]:
        """
        Parse a single post element to extract metrics.

        Args:
            element: Playwright element handle
            page: Playwright page object

        Returns:
            TikTokPost object or None
        """
        try:
            # Extract post URL
            link = await element.query_selector('a')
            if not link:
                return None

            post_url = await link.get_attribute('href')
            if not post_url:
                return None

            # Extract post ID from URL (e.g., /video/1234567890)
            post_id_match = re.search(r'/video/(\d+)', post_url)
            post_id = post_id_match.group(1) if post_id_match else None

            # Click to open post detail (get full metrics)
            await link.click()
            await asyncio.sleep(2)  # Wait for modal to load

            # Extract metrics from detail view
            metrics = {}

            # Views
            views_elem = await page.query_selector('[data-e2e="video-views"]')
            if views_elem:
                views_text = await views_elem.inner_text()
                metrics['views'] = self._parse_count(views_text)

            # Likes
            likes_elem = await page.query_selector('[data-e2e="like-count"]')
            if likes_elem:
                likes_text = await likes_elem.inner_text()
                metrics['likes'] = self._parse_count(likes_text)

            # Comments
            comments_elem = await page.query_selector('[data-e2e="comment-count"]')
            if comments_elem:
                comments_text = await comments_elem.inner_text()
                metrics['comments'] = self._parse_count(comments_text)

            # Shares
            shares_elem = await page.query_selector('[data-e2e="share-count"]')
            if shares_elem:
                shares_text = await shares_elem.inner_text()
                metrics['shares'] = self._parse_count(shares_text)

            # Caption and hashtags
            caption_elem = await page.query_selector('[data-e2e="video-desc"]')
            caption = ""
            hashtags = []
            if caption_elem:
                caption = await caption_elem.inner_text()
                hashtags = re.findall(r'#(\w+)', caption)

            # Timestamp (try to extract from post)
            timestamp_elem = await page.query_selector('span[data-e2e="browser-nickname"] + span')
            timestamp = None
            if timestamp_elem:
                timestamp_text = await timestamp_elem.inner_text()
                timestamp = self._parse_timestamp(timestamp_text)

            # Close modal
            await page.keyboard.press('Escape')
            await asyncio.sleep(0.5)

            return TikTokPost(
                post_id=post_id or "",
                post_url=f"{self.base_url}{post_url}",
                post_datetime=timestamp or "",
                views=metrics.get('views', 0),
                likes=metrics.get('likes', 0),
                comments=metrics.get('comments', 0),
                shares=metrics.get('shares', 0),
                caption=caption,
                hashtags=hashtags,
                is_video=True
            )

        except Exception as e:
            logger.debug(f"Error parsing post element: {e}")
            return None

    def _parse_count(self, text: str) -> int:
        """
        Parse count string (e.g., "1.2K", "3.5M") to integer.

        Args:
            text: Count text

        Returns:
            Integer count
        """
        text = text.strip().upper()

        # Remove any non-numeric prefix
        text = re.sub(r'^[^\d.]+', '', text)

        try:
            if 'K' in text:
                return int(float(text.replace('K', '')) * 1000)
            elif 'M' in text:
                return int(float(text.replace('M', '')) * 1000000)
            elif 'B' in text:
                return int(float(text.replace('B', '')) * 1000000000)
            else:
                return int(float(text))
        except:
            return 0

    def _parse_timestamp(self, text: str) -> Optional[str]:
        """
        Parse relative timestamp (e.g., "2d ago", "3w ago") to date string.

        Args:
            text: Timestamp text

        Returns:
            Date string (YYYY-MM-DD) or None
        """
        try:
            now = datetime.now()

            # Match patterns like "2d ago", "3w ago", "1m ago"
            match = re.search(r'(\d+)([smhdw])', text.lower())
            if not match:
                return None

            value = int(match.group(1))
            unit = match.group(2)

            if unit == 's':
                delta = timedelta(seconds=value)
            elif unit == 'm':
                delta = timedelta(minutes=value)
            elif unit == 'h':
                delta = timedelta(hours=value)
            elif unit == 'd':
                delta = timedelta(days=value)
            elif unit == 'w':
                delta = timedelta(weeks=value)
            else:
                return None

            post_date = now - delta
            return post_date.strftime('%Y-%m-%d')

        except:
            return None

    def collect_show_tiktok(
        self,
        show_name: str,
        handle: str,
        max_posts: int = 30
    ) -> pd.DataFrame:
        """
        Collect TikTok posts for a show.

        Args:
            show_name: Name of the show
            handle: TikTok handle
            max_posts: Maximum posts to collect

        Returns:
            DataFrame with show, date, and metrics columns
        """
        # Run async fetch
        posts = asyncio.run(self.fetch_profile_posts(handle, max_posts))

        if not posts:
            logger.error(f"No TikTok data collected for {show_name}")
            return pd.DataFrame()

        # Convert TikTokPost objects to DataFrame
        post_dicts = [post.to_dict() for post in posts]
        df = pd.DataFrame(post_dicts)
        df['show'] = show_name
        df['handle'] = handle

        # Filter to posts with timestamps
        df = df[df['post_datetime'].notna() & (df['post_datetime'] != "")].copy()

        if df.empty:
            logger.warning(f"No posts with timestamps for {show_name}")
            return pd.DataFrame()

        # Save per-post CSV with timestamp in filename
        timestamp = datetime.now().strftime("%Y%m%d")
        raw_file = self.output_dir / f"{show_name.replace(' ', '_').replace(':', '')}_posts_{timestamp}.csv"
        df.to_csv(raw_file, index=False)
        logger.info(f"  💾 Saved raw data: {raw_file}")

        return df

    def to_weekly_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert daily TikTok posts to weekly aggregates.

        Args:
            df: DataFrame from collect_show_tiktok()

        Returns:
            DataFrame with schema: show, week_start, tt_posts, tt_sum_views, tt_sum_likes,
                                  tt_sum_comments, tt_sum_shares, tt_unique_hashtags
        """
        if df.empty:
            return pd.DataFrame(columns=[
                'show', 'week_start', 'tt_posts', 'tt_sum_views', 'tt_sum_likes',
                'tt_sum_comments', 'tt_sum_shares', 'tt_unique_hashtags'
            ])

        df = df.copy()
        df['post_datetime'] = pd.to_datetime(df['post_datetime'])

        # Aggregate to weekly
        weekly = week_agg(
            df,
            date_col='post_datetime',
            group_cols=['show'],
            agg_spec={
                'post_id': 'count',
                'views': 'sum',
                'likes': 'sum',
                'comments': 'sum',
                'shares': 'sum'
            }
        )

        # Count unique hashtags per week
        hashtag_counts = df.groupby(['show']).apply(
            lambda x: pd.Series({
                'week_start': to_week_start(x['post_datetime'].iloc[0]),
                'unique_hashtags': len(set([tag for tags in x['hashtags'] for tag in tags]))
            })
        ).reset_index()

        # Merge
        weekly = weekly.merge(hashtag_counts, on=['show', 'week_start'], how='left')

        # Rename columns
        weekly = weekly.rename(columns={
            'post_id': 'tt_posts',
            'views': 'tt_sum_views',
            'likes': 'tt_sum_likes',
            'comments': 'tt_sum_comments',
            'shares': 'tt_sum_shares',
            'unique_hashtags': 'tt_unique_hashtags'
        })

        return weekly


def collect_tiktok(
    shows_config: List[Dict[str, Any]],
    max_posts: int = 30,
    output_dir: str = "public_signals/data/raw/tiktok"
) -> pd.DataFrame:
    """
    Main function to collect TikTok data for all shows.

    Args:
        shows_config: List of show configs with 'name' and 'tiktok_handle' fields
        max_posts: Maximum posts per show
        output_dir: Directory for raw data

    Returns:
        Combined weekly DataFrame for all shows

    Example:
        >>> shows = [
        ...     {'name': 'Maybe Happy Ending', 'tiktok_handle': '@maybehappyending'},
        ...     {'name': 'Hamilton', 'tiktok_handle': '@hamiltonmusical'}
        ... ]
        >>> df = collect_tiktok(shows)
    """
    collector = TikTokPublicCollector(output_dir)

    all_weekly = []

    for show_config in shows_config:
        show_name = show_config['name']
        handle = show_config.get('tiktok_handle')

        if not handle:
            logger.warning(f"No TikTok handle for {show_name}, skipping")
            continue

        logger.info(f"\n{'='*70}")
        logger.info(f"Collecting TikTok data: {show_name}")
        logger.info(f"{'='*70}")

        # Collect raw data
        raw_df = collector.collect_show_tiktok(show_name, handle, max_posts)

        if not raw_df.empty:
            # Convert to weekly
            weekly_df = collector.to_weekly_format(raw_df)
            all_weekly.append(weekly_df)

    if not all_weekly:
        logger.error("No TikTok data collected for any show")
        return pd.DataFrame()

    # Combine all shows
    combined = pd.concat(all_weekly, ignore_index=True)

    logger.info(f"\n✓ Collected TikTok data:")
    logger.info(f"  Shows: {combined['show'].nunique()}")
    logger.info(f"  Weeks: {combined['week_start'].nunique()}")
    logger.info(f"  Total posts: {combined['tt_posts'].sum():,.0f}")
    logger.info(f"  Total views: {combined['tt_sum_views'].sum():,.0f}")
    logger.info(f"  Total rows: {len(combined)}")

    return combined

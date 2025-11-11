#!/usr/bin/env python3
"""
Instagram Public Profile Scraper

Collects public engagement metrics from Instagram profile pages using Playwright.
No authentication required - only scrapes publicly visible data.

Note: Instagram often hides exact counts for non-authenticated users.
Metrics may be approximate or null.

Output schema:
- show: Show name
- week_start: Week start date (YYYY-MM-DD)
- ig_posts: Number of posts in week
- ig_sum_likes: Total likes (may be null if hidden)
- ig_sum_comments: Total comments (may be null if hidden)
- ig_unique_hashtags: Unique hashtags used
- ig_reel_ct: Number of reels
"""

import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import re
import asyncio

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from ..common.net import respect_robots
from ..common.timebins import to_week_start, week_agg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InstagramPublicCollector:
    """Collects public Instagram engagement data without authentication."""

    def __init__(self, output_dir: str = "public_signals/data/raw/instagram"):
        """
        Initialize Instagram collector.

        Args:
            output_dir: Directory to save raw data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.base_url = "https://www.instagram.com"

        logger.info("Initialized Instagram public collector")

    async def fetch_profile_posts(
        self,
        handle: str,
        max_posts: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent public posts from an Instagram profile.

        Args:
            handle: Instagram handle (without @)
            max_posts: Maximum number of recent posts to collect

        Returns:
            List of post dictionaries with metrics

        Example:
            >>> collector = InstagramPublicCollector()
            >>> posts = await collector.fetch_profile_posts("hamiltonmusical")
        """
        # Normalize handle (remove @ if present)
        handle = handle.lstrip('@')

        profile_url = f"{self.base_url}/{handle}/"

        # Check robots.txt
        if not respect_robots(profile_url):
            logger.warning(f"Instagram profile blocked by robots.txt: {handle}")
            return []

        logger.info(f"Fetching Instagram profile: @{handle}")

        posts = []

        try:
            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(headless=True)

                # Create context with realistic settings
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    viewport={"width": 1280, "height": 720}
                )

                page = await context.new_page()

                # Navigate to profile
                await page.goto(profile_url, wait_until="networkidle", timeout=30000)

                # Wait for post grid to load
                try:
                    await page.wait_for_selector('article a[href*="/p/"], article a[href*="/reel/"]', timeout=10000)
                except PlaywrightTimeout:
                    logger.warning(f"No posts found or page not loaded: @{handle}")
                    await browser.close()
                    return []

                # Scroll to load more posts
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1.5)

                # Extract post links
                post_links = await page.query_selector_all('article a[href*="/p/"], article a[href*="/reel/"]')

                logger.info(f"  Found {len(post_links)} post links")

                # Get unique post URLs
                post_urls = []
                for link in post_links[:max_posts * 2]:  # Get extra in case duplicates
                    href = await link.get_attribute('href')
                    if href and href not in post_urls:
                        post_urls.append(href)

                post_urls = post_urls[:max_posts]

                logger.info(f"  Processing {len(post_urls)} unique posts")

                # Visit each post
                for idx, post_url in enumerate(post_urls):
                    try:
                        full_url = f"{self.base_url}{post_url}" if not post_url.startswith('http') else post_url
                        post_data = await self._fetch_post_detail(page, full_url)
                        if post_data:
                            posts.append(post_data)

                        # Rate limit
                        if idx < len(post_urls) - 1:
                            await asyncio.sleep(2)

                    except Exception as e:
                        logger.debug(f"Could not fetch post {post_url}: {e}")
                        continue

                await browser.close()

        except Exception as e:
            logger.error(f"Error fetching Instagram profile @{handle}: {e}")
            return []

        logger.info(f"  ✓ Retrieved {len(posts)} posts")

        return posts

    async def _fetch_post_detail(self, page, post_url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch details for a single Instagram post.

        Args:
            page: Playwright page object
            post_url: Full post URL

        Returns:
            Dict with post data or None
        """
        try:
            await page.goto(post_url, wait_until="networkidle", timeout=20000)
            await asyncio.sleep(1)

            # Extract post ID from URL
            post_id_match = re.search(r'/(p|reel)/([A-Za-z0-9_-]+)', post_url)
            if not post_id_match:
                return None

            post_type = post_id_match.group(1)  # 'p' or 'reel'
            post_id = post_id_match.group(2)

            is_reel = (post_type == 'reel')

            # Likes (often hidden without login)
            likes = None
            try:
                # Try various selectors for likes
                likes_elem = await page.query_selector('button[aria-label*="like"] + span, section span[class*="Likes"]')
                if likes_elem:
                    likes_text = await likes_elem.inner_text()
                    likes = self._parse_count(likes_text)
            except:
                pass

            # Comments (may be visible)
            comments = None
            try:
                # Count comment sections or find comment count text
                comments_elems = await page.query_selector_all('ul li div[role="button"] span')
                if comments_elems and len(comments_elems) > 0:
                    # Try to find explicit comment count
                    for elem in comments_elems:
                        text = await elem.inner_text()
                        if 'comment' in text.lower():
                            comments = self._parse_count(text)
                            break
            except:
                pass

            # Caption and hashtags
            caption = ""
            hashtags = []
            try:
                # Try to find caption
                caption_elem = await page.query_selector('article div[data-testid="post-comment-root"] span, h1 + div span')
                if caption_elem:
                    caption = await caption_elem.inner_text()
                    hashtags = re.findall(r'#(\w+)', caption)
            except:
                pass

            # Timestamp
            timestamp = None
            try:
                time_elem = await page.query_selector('time[datetime]')
                if time_elem:
                    datetime_str = await time_elem.get_attribute('datetime')
                    if datetime_str:
                        # Parse ISO format
                        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                        timestamp = dt.strftime('%Y-%m-%d')
            except:
                pass

            # If no timestamp, try relative time
            if not timestamp:
                try:
                    time_elem = await page.query_selector('time')
                    if time_elem:
                        time_text = await time_elem.inner_text()
                        timestamp = self._parse_relative_time(time_text)
                except:
                    pass

            return {
                'post_id': post_id,
                'post_url': post_url,
                'timestamp': timestamp,
                'likes': likes,
                'comments': comments,
                'caption': caption,
                'hashtags': hashtags,
                'is_reel': is_reel
            }

        except Exception as e:
            logger.debug(f"Error fetching post detail {post_url}: {e}")
            return None

    def _parse_count(self, text: str) -> Optional[int]:
        """
        Parse count string (e.g., "1,234", "1.2K", "3.5M") to integer.

        Args:
            text: Count text

        Returns:
            Integer count or None
        """
        try:
            text = text.strip().upper()

            # Remove commas
            text = text.replace(',', '')

            # Extract first number-like substring
            match = re.search(r'([\d.]+)([KMB])?', text)
            if not match:
                return None

            num_str = match.group(1)
            suffix = match.group(2)

            num = float(num_str)

            if suffix == 'K':
                return int(num * 1000)
            elif suffix == 'M':
                return int(num * 1000000)
            elif suffix == 'B':
                return int(num * 1000000000)
            else:
                return int(num)

        except:
            return None

    def _parse_relative_time(self, text: str) -> Optional[str]:
        """
        Parse relative timestamp (e.g., "2d", "3w", "1h") to date string.

        Args:
            text: Timestamp text

        Returns:
            Date string (YYYY-MM-DD) or None
        """
        try:
            now = datetime.now()

            # Match patterns like "2d", "3w", "1h"
            match = re.search(r'(\d+)\s*([smhdw])', text.lower())
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

    def collect_show_instagram(
        self,
        show_name: str,
        handle: str,
        max_posts: int = 30
    ) -> pd.DataFrame:
        """
        Collect Instagram posts for a show.

        Args:
            show_name: Name of the show
            handle: Instagram handle (without @)
            max_posts: Maximum posts to collect

        Returns:
            DataFrame with show, date, and metrics columns
        """
        # Run async fetch
        posts = asyncio.run(self.fetch_profile_posts(handle, max_posts))

        if not posts:
            logger.error(f"No Instagram data collected for {show_name}")
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(posts)
        df['show'] = show_name
        df['handle'] = handle

        # Filter to posts with timestamps
        df = df[df['timestamp'].notna()].copy()

        if df.empty:
            logger.warning(f"No posts with timestamps for {show_name}")
            return pd.DataFrame()

        # Save raw data
        raw_file = self.output_dir / f"{show_name.replace(' ', '_').replace(':', '')}_raw.csv"
        df.to_csv(raw_file, index=False)
        logger.info(f"  💾 Saved raw data: {raw_file}")

        return df

    def to_weekly_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert daily Instagram posts to weekly aggregates.

        Args:
            df: DataFrame from collect_show_instagram()

        Returns:
            DataFrame with schema: show, week_start, ig_posts, ig_sum_likes,
                                  ig_sum_comments, ig_unique_hashtags, ig_reel_ct
        """
        if df.empty:
            return pd.DataFrame(columns=[
                'show', 'week_start', 'ig_posts', 'ig_sum_likes',
                'ig_sum_comments', 'ig_unique_hashtags', 'ig_reel_ct'
            ])

        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Add week_start
        df['week_start'] = df['timestamp'].apply(to_week_start)

        # Aggregate numeric columns (handling nulls)
        weekly = df.groupby(['show', 'week_start']).agg({
            'post_id': 'count',
            'likes': lambda x: x.sum() if x.notna().any() else None,
            'comments': lambda x: x.sum() if x.notna().any() else None,
            'is_reel': 'sum'
        }).reset_index()

        # Count unique hashtags per week
        hashtag_counts = df.groupby(['show', 'week_start']).apply(
            lambda x: len(set([tag for tags in x['hashtags'] for tag in tags]))
        ).reset_index(name='unique_hashtags')

        # Merge
        weekly = weekly.merge(hashtag_counts, on=['show', 'week_start'], how='left')

        # Rename columns
        weekly = weekly.rename(columns={
            'post_id': 'ig_posts',
            'likes': 'ig_sum_likes',
            'comments': 'ig_sum_comments',
            'unique_hashtags': 'ig_unique_hashtags',
            'is_reel': 'ig_reel_ct'
        })

        return weekly


def collect_instagram(
    shows_config: List[Dict[str, Any]],
    max_posts: int = 30,
    output_dir: str = "public_signals/data/raw/instagram"
) -> pd.DataFrame:
    """
    Main function to collect Instagram data for all shows.

    Args:
        shows_config: List of show configs with 'name' and 'instagram_handle' fields
        max_posts: Maximum posts per show
        output_dir: Directory for raw data

    Returns:
        Combined weekly DataFrame for all shows

    Example:
        >>> shows = [
        ...     {'name': 'Maybe Happy Ending', 'instagram_handle': 'maybehappyending'},
        ...     {'name': 'Hamilton', 'instagram_handle': 'hamiltonmusical'}
        ... ]
        >>> df = collect_instagram(shows)
    """
    collector = InstagramPublicCollector(output_dir)

    all_weekly = []

    for show_config in shows_config:
        show_name = show_config['name']
        handle = show_config.get('instagram_handle')

        if not handle:
            logger.warning(f"No Instagram handle for {show_name}, skipping")
            continue

        logger.info(f"\n{'='*70}")
        logger.info(f"Collecting Instagram data: {show_name}")
        logger.info(f"{'='*70}")

        # Collect raw data
        raw_df = collector.collect_show_instagram(show_name, handle, max_posts)

        if not raw_df.empty:
            # Convert to weekly
            weekly_df = collector.to_weekly_format(raw_df)
            all_weekly.append(weekly_df)

    if not all_weekly:
        logger.error("No Instagram data collected for any show")
        return pd.DataFrame()

    # Combine all shows
    combined = pd.concat(all_weekly, ignore_index=True)

    logger.info(f"\n✓ Collected Instagram data:")
    logger.info(f"  Shows: {combined['show'].nunique()}")
    logger.info(f"  Weeks: {combined['week_start'].nunique()}")
    logger.info(f"  Total posts: {combined['ig_posts'].sum():,.0f}")
    if combined['ig_sum_likes'].notna().any():
        logger.info(f"  Total likes: {combined['ig_sum_likes'].sum():,.0f}")
    logger.info(f"  Total rows: {len(combined)}")

    return combined

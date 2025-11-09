"""
TikTok API scraper using third-party services.
Legal automated collection via Apify or RapidAPI.
"""

import time
import json
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path


class TikTokAPI:
    """TikTok scraper using third-party APIs."""

    def __init__(self, api_service: str = "apify", api_token: str = None):
        """
        Initialize TikTok API scraper.

        Args:
            api_service: 'apify' or 'rapidapi'
            api_token: API token/key
        """
        self.api_service = api_service
        self.api_token = api_token
        self.client = None

        if api_service == "apify":
            self._init_apify()
        elif api_service == "rapidapi":
            self._init_rapidapi()

    def _init_apify(self):
        """Initialize Apify client."""
        try:
            from apify_client import ApifyClient
            self.client = ApifyClient(self.api_token)
            print("✓ Apify client initialized")
        except ImportError:
            print("⚠ Apify client not installed. Run: pip install apify-client")
            self.client = None
        except Exception as e:
            print(f"⚠ Apify initialization error: {e}")
            self.client = None

    def _init_rapidapi(self):
        """Initialize RapidAPI client."""
        import requests
        self.client = requests.Session()
        self.client.headers.update({
            "X-RapidAPI-Key": self.api_token,
            "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com"
        })
        print("✓ RapidAPI client initialized")

    def search_hashtag(self, hashtag: str, max_results: int = 50) -> List[Dict]:
        """
        Search TikTok by hashtag.

        Args:
            hashtag: Hashtag to search (without #)
            max_results: Maximum videos to retrieve

        Returns:
            List of video dictionaries
        """
        if self.api_service == "apify":
            return self._search_hashtag_apify(hashtag, max_results)
        elif self.api_service == "rapidapi":
            return self._search_hashtag_rapidapi(hashtag, max_results)
        else:
            print(f"❌ Unknown API service: {self.api_service}")
            return []

    def _search_hashtag_apify(self, hashtag: str, max_results: int) -> List[Dict]:
        """Search via Apify TikTok scraper."""
        if not self.client:
            print("❌ Apify client not available")
            return []

        print(f"\n🔍 Searching TikTok via Apify: #{hashtag}")
        print(f"   Max results: {max_results}")
        print("   This may take 2-5 minutes...")

        try:
            # Prepare scraper input
            run_input = {
                "hashtags": [hashtag],
                "resultsPerPage": max_results,
                "shouldDownloadVideos": False,
                "shouldDownloadCovers": False,
                "shouldDownloadSlideshowImages": False,
            }

            # Run the Apify TikTok scraper
            print("   Starting scraper...")
            run = self.client.actor("clockworks/tiktok-scraper").call(run_input=run_input)

            # Wait for completion
            print("   Fetching results...")
            videos = []

            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                video = self._format_video_data(item)
                videos.append(video)

            print(f"✓ Collected {len(videos)} videos from #{hashtag}")
            return videos

        except Exception as e:
            print(f"❌ Apify error: {e}")
            print("   Check your API token and credit balance")
            return []

    def _search_hashtag_rapidapi(self, hashtag: str, max_results: int) -> List[Dict]:
        """Search via RapidAPI TikTok scraper."""
        if not self.client:
            print("❌ RapidAPI client not available")
            return []

        print(f"\n🔍 Searching TikTok via RapidAPI: #{hashtag}")

        try:
            url = "https://tiktok-scraper7.p.rapidapi.com/challenge/posts"

            querystring = {
                "challenge_name": hashtag,
                "count": str(max_results)
            }

            response = self.client.get(url, params=querystring, timeout=60)

            if response.status_code == 200:
                data = response.json()
                videos = []

                for item in data.get('data', {}).get('videos', []):
                    video = self._format_video_data(item, source='rapidapi')
                    videos.append(video)

                print(f"✓ Collected {len(videos)} videos")
                return videos
            else:
                print(f"❌ API error: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ RapidAPI error: {e}")
            return []

    def search_multiple_hashtags(self, hashtags: List[str], max_per_tag: int = 50) -> List[Dict]:
        """
        Search multiple hashtags.

        Args:
            hashtags: List of hashtags to search
            max_per_tag: Max results per hashtag

        Returns:
            Combined list of videos
        """
        all_videos = []
        seen_ids = set()

        for hashtag in hashtags:
            videos = self.search_hashtag(hashtag, max_per_tag)

            # Deduplicate
            for video in videos:
                if video['video_id'] not in seen_ids:
                    seen_ids.add(video['video_id'])
                    all_videos.append(video)

            # Rate limiting between searches
            if len(hashtags) > 1:
                time.sleep(2)

        print(f"\n✓ Total unique videos: {len(all_videos)}")
        return all_videos

    def _format_video_data(self, item: Dict, source: str = 'apify') -> Dict:
        """Format video data to standard structure."""
        if source == 'apify':
            return {
                'video_id': item.get('id', ''),
                'url': item.get('webVideoUrl', ''),
                'author': item.get('authorMeta', {}).get('name', ''),
                'caption': item.get('text', ''),
                'hashtags': ','.join([tag.get('name', '') for tag in item.get('hashtags', [])]),
                'likes': item.get('diggCount', 0),
                'comments': item.get('commentCount', 0),
                'shares': item.get('shareCount', 0),
                'views': item.get('playCount', 0),
                'created_at': self._format_timestamp(item.get('createTime', 0)),
                'platform': 'tiktok',
                'scraped_at': datetime.now().isoformat()
            }
        else:  # rapidapi
            return {
                'video_id': item.get('aweme_id', ''),
                'url': f"https://www.tiktok.com/@{item.get('author', {}).get('unique_id', '')}/video/{item.get('aweme_id', '')}",
                'author': item.get('author', {}).get('unique_id', ''),
                'caption': item.get('desc', ''),
                'hashtags': ','.join([tag.get('hashtag_name', '') for tag in item.get('text_extra', [])]),
                'likes': item.get('statistics', {}).get('digg_count', 0),
                'comments': item.get('statistics', {}).get('comment_count', 0),
                'shares': item.get('statistics', {}).get('share_count', 0),
                'views': item.get('statistics', {}).get('play_count', 0),
                'created_at': self._format_timestamp(item.get('create_time', 0)),
                'platform': 'tiktok',
                'scraped_at': datetime.now().isoformat()
            }

    def _format_timestamp(self, timestamp: int) -> str:
        """Format Unix timestamp to ISO string."""
        try:
            return datetime.fromtimestamp(timestamp).isoformat()
        except:
            return datetime.now().isoformat()

    @staticmethod
    def estimate_cost(num_videos: int, service: str = 'apify') -> float:
        """
        Estimate API cost.

        Args:
            num_videos: Number of videos to scrape
            service: API service name

        Returns:
            Estimated cost in USD
        """
        if service == 'apify':
            # Apify: ~$0.02-0.05 per video
            return num_videos * 0.035
        elif service == 'rapidapi':
            # RapidAPI: varies by plan
            return num_videos * 0.01
        else:
            return 0.0

"""
Instagram API scraper using third-party services.
Legal automated collection via Apify or RapidAPI.
"""

import time
import json
from datetime import datetime
from typing import List, Dict, Any


class InstagramAPI:
    """Instagram scraper using third-party APIs."""

    def __init__(self, api_service: str = "apify", api_token: str = None):
        """
        Initialize Instagram API scraper.

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
            "X-RapidAPI-Host": "instagram-scraper-api2.p.rapidapi.com"
        })
        print("✓ RapidAPI client initialized")

    def search_hashtag(self, hashtag: str, max_results: int = 50) -> List[Dict]:
        """
        Search Instagram by hashtag.

        Args:
            hashtag: Hashtag to search (without #)
            max_results: Maximum posts to retrieve

        Returns:
            List of post dictionaries
        """
        if self.api_service == "apify":
            return self._search_hashtag_apify(hashtag, max_results)
        elif self.api_service == "rapidapi":
            return self._search_hashtag_rapidapi(hashtag, max_results)
        else:
            print(f"❌ Unknown API service: {self.api_service}")
            return []

    def _search_hashtag_apify(self, hashtag: str, max_results: int) -> List[Dict]:
        """Search via Apify Instagram scraper."""
        if not self.client:
            print("❌ Apify client not available")
            return []

        print(f"\n📷 Searching Instagram via Apify: #{hashtag}")
        print(f"   Max results: {max_results}")
        print("   This may take 3-7 minutes...")

        try:
            # Prepare scraper input
            run_input = {
                "hashtags": [hashtag],
                "resultsLimit": max_results,
                "addParentData": False,
            }

            # Run the Apify Instagram scraper
            print("   Starting scraper...")
            run = self.client.actor("apify/instagram-scraper").call(run_input=run_input)

            # Wait for completion
            print("   Fetching results...")
            posts = []

            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                post = self._format_post_data(item)
                posts.append(post)

            print(f"✓ Collected {len(posts)} posts from #{hashtag}")
            return posts

        except Exception as e:
            print(f"❌ Apify error: {e}")
            print("   Check your API token and credit balance")
            print("   Note: Instagram scraping is more rate-limited than TikTok")
            return []

    def _search_hashtag_rapidapi(self, hashtag: str, max_results: int) -> List[Dict]:
        """Search via RapidAPI Instagram scraper."""
        if not self.client:
            print("❌ RapidAPI client not available")
            return []

        print(f"\n📷 Searching Instagram via RapidAPI: #{hashtag}")

        try:
            url = "https://instagram-scraper-api2.p.rapidapi.com/v1/hashtag"

            querystring = {
                "hashtag": hashtag,
                "count": str(min(max_results, 50))  # RapidAPI limits
            }

            response = self.client.get(url, params=querystring, timeout=60)

            if response.status_code == 200:
                data = response.json()
                posts = []

                for item in data.get('data', {}).get('items', []):
                    post = self._format_post_data(item, source='rapidapi')
                    posts.append(post)

                print(f"✓ Collected {len(posts)} posts")
                return posts
            else:
                print(f"❌ API error: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ RapidAPI error: {e}")
            return []

    def search_location(self, location_id: str, max_results: int = 50) -> List[Dict]:
        """
        Search Instagram by location.

        Args:
            location_id: Instagram location ID
            max_results: Maximum posts to retrieve

        Returns:
            List of post dictionaries
        """
        if self.api_service != "apify":
            print("⚠ Location search only available with Apify")
            return []

        if not self.client:
            print("❌ Apify client not available")
            return []

        print(f"\n📍 Searching Instagram location: {location_id}")

        try:
            run_input = {
                "searchType": "place",
                "searchLimit": 1,
                "place": location_id,
                "resultsLimit": max_results,
            }

            run = self.client.actor("apify/instagram-scraper").call(run_input=run_input)

            posts = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                post = self._format_post_data(item)
                posts.append(post)

            print(f"✓ Collected {len(posts)} posts from location")
            return posts

        except Exception as e:
            print(f"❌ Error: {e}")
            return []

    def search_multiple_hashtags(self, hashtags: List[str], max_per_tag: int = 50) -> List[Dict]:
        """
        Search multiple hashtags.

        Args:
            hashtags: List of hashtags to search
            max_per_tag: Max results per hashtag

        Returns:
            Combined list of posts
        """
        all_posts = []
        seen_ids = set()

        for hashtag in hashtags:
            posts = self.search_hashtag(hashtag, max_per_tag)

            # Deduplicate
            for post in posts:
                if post['post_id'] not in seen_ids:
                    seen_ids.add(post['post_id'])
                    all_posts.append(post)

            # Rate limiting between searches (important for Instagram)
            if len(hashtags) > 1:
                time.sleep(5)  # Longer delay for Instagram

        print(f"\n✓ Total unique posts: {len(all_posts)}")
        return all_posts

    def _format_post_data(self, item: Dict, source: str = 'apify') -> Dict:
        """Format post data to standard structure."""
        if source == 'apify':
            return {
                'post_id': item.get('shortCode', ''),
                'url': item.get('url', ''),
                'author': item.get('ownerUsername', ''),
                'caption': item.get('caption', ''),
                'hashtags': ','.join(item.get('hashtags', [])),
                'likes': item.get('likesCount', 0),
                'comments_count': item.get('commentsCount', 0),
                'created_at': self._format_timestamp(item.get('timestamp', 0)),
                'post_type': item.get('type', 'photo'),
                'platform': 'instagram',
                'scraped_at': datetime.now().isoformat()
            }
        else:  # rapidapi
            return {
                'post_id': item.get('code', ''),
                'url': f"https://www.instagram.com/p/{item.get('code', '')}/",
                'author': item.get('user', {}).get('username', ''),
                'caption': item.get('caption', {}).get('text', ''),
                'hashtags': self._extract_hashtags(item.get('caption', {}).get('text', '')),
                'likes': item.get('like_count', 0),
                'comments_count': item.get('comment_count', 0),
                'created_at': self._format_timestamp(item.get('taken_at', 0)),
                'post_type': 'photo' if item.get('media_type') == 1 else 'video',
                'platform': 'instagram',
                'scraped_at': datetime.now().isoformat()
            }

    def _extract_hashtags(self, text: str) -> str:
        """Extract hashtags from text."""
        import re
        hashtags = re.findall(r'#(\w+)', text)
        return ','.join(hashtags)

    def _format_timestamp(self, timestamp: int) -> str:
        """Format Unix timestamp to ISO string."""
        try:
            return datetime.fromtimestamp(timestamp).isoformat()
        except:
            return datetime.now().isoformat()

    @staticmethod
    def estimate_cost(num_posts: int, service: str = 'apify') -> float:
        """
        Estimate API cost.

        Args:
            num_posts: Number of posts to scrape
            service: API service name

        Returns:
            Estimated cost in USD
        """
        if service == 'apify':
            # Apify: ~$0.01-0.03 per post
            return num_posts * 0.02
        elif service == 'rapidapi':
            # RapidAPI: varies by plan
            return num_posts * 0.015
        else:
            return 0.0

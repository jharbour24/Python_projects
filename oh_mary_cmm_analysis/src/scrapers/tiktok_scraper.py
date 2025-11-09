"""TikTok scraper for Oh Mary! discourse analysis."""
import requests
import json
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path


class TikTokScraper:
    """Scrapes TikTok for Oh Mary! related content."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize TikTok scraper.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.keywords = config.get('keywords', [])
        self.hashtags = [kw for kw in self.keywords if kw.startswith('#')]

    def collect_all(self) -> List[Dict]:
        """
        Collect TikTok data.

        Note: TikTok has strict anti-scraping measures. This method provides
        guidance for manual collection.

        Returns:
            List of collected data (empty if manual collection needed)
        """
        print("\n⚠ TikTok Scraping Limitations")
        print("=" * 60)
        print("TikTok's anti-bot protection makes automated scraping difficult.")
        print("\nRecommended approaches:")
        print("\n1. MANUAL COLLECTION (Most Reliable):")
        print("   - Search hashtags: #OhMary, #OhMaryBroadway")
        print("   - Document top 50-100 videos manually")
        print("   - Record: URL, caption, likes, comments, shares, date")
        print("   - Save to CSV using template")
        print("\n2. THIRD-PARTY APIs (Requires subscription):")
        print("   - apify.com/clockworks/tiktok-scraper")
        print("   - rapidapi.com/ti-services/api/tiktok-scraper7")
        print("\n3. BROWSER EXTENSION:")
        print("   - Use TikTok Downloader extensions")
        print("   - Export data to JSON")
        print("\n4. TIKTOK ANALYTICS (If you have business account):")
        print("   - TikTok Creator Marketplace")
        print("   - Export hashtag analytics")

        self._create_manual_template()
        return []

    def _create_manual_template(self):
        """Create a template CSV for manual TikTok data entry."""
        import pandas as pd

        template_data = {
            'video_id': ['example_id_123456789'],
            'url': ['https://www.tiktok.com/@username/video/123456789'],
            'author': ['@username'],
            'caption': ['Full video caption with #OhMary hashtag'],
            'hashtags': ['#OhMary,#Broadway,#Musical'],
            'likes': [1000],
            'comments': [50],
            'shares': [25],
            'views': [10000],
            'created_at': ['2024-01-01T12:00:00'],
            'top_comments': ['["Comment 1 text", "Comment 2 text"]']
        }

        df = pd.DataFrame(template_data)
        output_path = Path(__file__).parent.parent.parent / "data" / "raw" / "tiktok_manual_template.csv"
        df.to_csv(output_path, index=False)
        print(f"\n✓ Created manual template at {output_path}")

    def load_manual_data(self, filepath: str) -> List[Dict]:
        """
        Load manually collected TikTok data.

        Args:
            filepath: Path to CSV file with manual data

        Returns:
            List of TikTok data dictionaries
        """
        import pandas as pd

        try:
            df = pd.read_csv(filepath)
            data = df.to_dict('records')

            # Add platform field
            for item in data:
                item['platform'] = 'tiktok'
                item['scraped_at'] = datetime.now().isoformat()

            print(f"✓ Loaded {len(data)} TikTok items from {filepath}")
            return data

        except Exception as e:
            print(f"✗ Error loading TikTok data: {e}")
            return []


def search_tiktok_web(hashtag: str, max_results: int = 50) -> List[Dict]:
    """
    Attempt to search TikTok via web (LIMITED - will likely be blocked).

    Args:
        hashtag: Hashtag to search (without #)
        max_results: Maximum results to retrieve

    Returns:
        List of video data (likely empty due to anti-scraping)
    """
    print(f"\n⚠ Attempting TikTok web search for #{hashtag}...")
    print("Note: This is likely to be blocked by TikTok's bot detection.")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        # TikTok's web API (often blocked)
        url = f"https://www.tiktok.com/tag/{hashtag}"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            print("✓ Retrieved data (parsing required)")
            # Note: Actual parsing would require handling TikTok's dynamic JS
            return []
        else:
            print(f"✗ Request blocked (status {response.status_code})")
            return []

    except Exception as e:
        print(f"✗ Error: {e}")
        return []

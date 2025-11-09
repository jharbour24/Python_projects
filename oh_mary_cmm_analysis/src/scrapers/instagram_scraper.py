"""Instagram scraper for Oh Mary! discourse analysis."""
import requests
import json
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path


class InstagramScraper:
    """Scrapes Instagram for Oh Mary! related content."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Instagram scraper.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.keywords = config.get('keywords', [])
        self.hashtags = [kw.replace('#', '').replace(' ', '') for kw in self.keywords]

    def collect_all(self) -> List[Dict]:
        """
        Collect Instagram data.

        Note: Instagram requires authentication for API access. This method
        provides guidance for manual collection.

        Returns:
            List of collected data (empty if manual collection needed)
        """
        print("\n⚠ Instagram Scraping Limitations")
        print("=" * 60)
        print("Instagram requires authentication and has strict rate limits.")
        print("\nRecommended approaches:")
        print("\n1. MANUAL COLLECTION (Most Reliable):")
        print("   - Search hashtags: #OhMary, #OhMaryBroadway")
        print("   - Search locations: Lyceum Theatre, Times Square")
        print("   - Document top 50-100 posts manually")
        print("   - Record: URL, caption, likes, comments, date")
        print("   - Save to CSV using template")
        print("\n2. INSTAGRAM BASIC DISPLAY API:")
        print("   - Requires Facebook App registration")
        print("   - Limited to user's own content")
        print("   - https://developers.facebook.com/docs/instagram-basic-display-api")
        print("\n3. THIRD-PARTY TOOLS:")
        print("   - apify.com/apify/instagram-scraper")
        print("   - Export hashtag data")
        print("\n4. INSTAGRAM INSIGHTS (If you manage the show's account):")
        print("   - Meta Business Suite")
        print("   - Hashtag analytics")
        print("   - Audience insights")

        self._create_manual_template()
        return []

    def _create_manual_template(self):
        """Create a template CSV for manual Instagram data entry."""
        import pandas as pd

        template_data = {
            'post_id': ['example_post_id'],
            'url': ['https://www.instagram.com/p/ABC123/'],
            'author': ['@username'],
            'caption': ['Full post caption mentioning Oh Mary!'],
            'hashtags': ['#OhMary,#Broadway,#Musical'],
            'likes': [500],
            'comments_count': [25],
            'created_at': ['2024-01-01T12:00:00'],
            'post_type': ['photo'],  # photo, video, carousel
            'top_comments': ['["Comment 1 text", "Comment 2 text"]']
        }

        df = pd.DataFrame(template_data)
        output_path = Path(__file__).parent.parent.parent / "data" / "raw" / "instagram_manual_template.csv"
        df.to_csv(output_path, index=False)
        print(f"\n✓ Created manual template at {output_path}")

    def load_manual_data(self, filepath: str) -> List[Dict]:
        """
        Load manually collected Instagram data.

        Args:
            filepath: Path to CSV file with manual data

        Returns:
            List of Instagram data dictionaries
        """
        import pandas as pd

        try:
            df = pd.read_csv(filepath)
            data = df.to_dict('records')

            # Add platform field
            for item in data:
                item['platform'] = 'instagram'
                item['scraped_at'] = datetime.now().isoformat()

            print(f"✓ Loaded {len(data)} Instagram items from {filepath}")
            return data

        except Exception as e:
            print(f"✗ Error loading Instagram data: {e}")
            return []


def search_instagram_public(hashtag: str) -> List[Dict]:
    """
    Attempt to search Instagram via public endpoints (LIMITED).

    Args:
        hashtag: Hashtag to search (without #)

    Returns:
        List of post data (likely empty due to auth requirements)
    """
    print(f"\n⚠ Attempting Instagram search for #{hashtag}...")
    print("Note: Public access is very limited without authentication.")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        # Instagram's public tag endpoint (requires login for most data)
        url = f"https://www.instagram.com/explore/tags/{hashtag}/"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            print("✓ Page retrieved, but data extraction requires authentication")
            return []
        else:
            print(f"✗ Request failed (status {response.status_code})")
            return []

    except Exception as e:
        print(f"✗ Error: {e}")
        return []

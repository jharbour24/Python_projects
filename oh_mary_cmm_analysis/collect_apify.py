#!/usr/bin/env python3
"""
Apify Automated Collection
Legal third-party API for TikTok and Instagram.
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

try:
    from apify_client import ApifyClient
    APIFY_AVAILABLE = True
except ImportError:
    APIFY_AVAILABLE = False

def load_credentials():
    """Load Apify credentials."""
    creds_path = Path(__file__).parent / "config" / "apify_credentials.py"

    if not creds_path.exists():
        print("❌ No Apify credentials found")
        print("Run: python setup_apify.py")
        sys.exit(1)

    sys.path.insert(0, str(creds_path.parent))
    import apify_credentials
    return apify_credentials.APIFY_API_TOKEN

def collect_tiktok(api_token, hashtags, max_videos=50):
    """Collect TikTok videos via Apify."""
    print("\n📱 Collecting TikTok videos via Apify...")
    print("-" * 70)

    client = ApifyClient(api_token)

    # Prepare input for TikTok scraper
    run_input = {
        "hashtags": hashtags,
        "resultsPerPage": max_videos,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
    }

    print(f"Searching for: {', '.join(hashtags)}")
    print(f"Max videos: {max_videos}")
    print()
    print("Starting scraper... (this may take 2-5 minutes)")

    # Run the TikTok scraper
    run = client.actor("clockworks/tiktok-scraper").call(run_input=run_input)

    # Fetch results
    videos = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        video = {
            'video_id': item.get('id', ''),
            'url': item.get('webVideoUrl', ''),
            'author': item.get('authorMeta', {}).get('name', ''),
            'caption': item.get('text', ''),
            'hashtags': ','.join([tag.get('name', '') for tag in item.get('hashtags', [])]),
            'likes': item.get('diggCount', 0),
            'comments': item.get('commentCount', 0),
            'shares': item.get('shareCount', 0),
            'views': item.get('playCount', 0),
            'created_at': datetime.fromtimestamp(item.get('createTime', 0)).isoformat(),
            'top_comments': '[]'  # Comments require separate scrape
        }
        videos.append(video)

    print(f"✅ Collected {len(videos)} TikTok videos")
    return videos

def collect_instagram(api_token, hashtags, max_posts=50):
    """Collect Instagram posts via Apify."""
    print("\n📷 Collecting Instagram posts via Apify...")
    print("-" * 70)

    client = ApifyClient(api_token)

    # Prepare input for Instagram scraper
    run_input = {
        "hashtags": hashtags,
        "resultsLimit": max_posts,
        "addParentData": False,
    }

    print(f"Searching for: {', '.join(hashtags)}")
    print(f"Max posts: {max_posts}")
    print()
    print("Starting scraper... (this may take 2-5 minutes)")

    # Run the Instagram scraper
    run = client.actor("apify/instagram-scraper").call(run_input=run_input)

    # Fetch results
    posts = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        post = {
            'post_id': item.get('shortCode', ''),
            'url': item.get('url', ''),
            'author': item.get('ownerUsername', ''),
            'caption': item.get('caption', ''),
            'hashtags': ','.join(item.get('hashtags', [])),
            'likes': item.get('likesCount', 0),
            'comments_count': item.get('commentsCount', 0),
            'created_at': datetime.fromtimestamp(item.get('timestamp', 0)).isoformat(),
            'post_type': item.get('type', 'photo'),
            'top_comments': '[]'  # Comments require separate scrape
        }
        posts.append(post)

    print(f"✅ Collected {len(posts)} Instagram posts")
    return posts

def save_to_csv(data, filename):
    """Save data to CSV."""
    import csv

    if not data:
        print(f"⚠️  No data to save for {filename}")
        return

    output_path = Path(__file__).parent / "data" / "raw" / filename

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    print(f"💾 Saved to: {output_path}")

def main():
    if not APIFY_AVAILABLE:
        print("❌ Apify client not installed")
        print("Install with: pip install apify-client")
        sys.exit(1)

    print("="*70)
    print("Apify Automated Collection")
    print("="*70)
    print()

    # Load credentials
    api_token = load_credentials()

    # Configuration
    print("What would you like to collect?")
    print("1. TikTok only")
    print("2. Instagram only")
    print("3. Both")
    print()

    choice = input("Choice (1-3): ").strip()
    print()

    # Get search terms
    print("Enter hashtags to search (comma-separated):")
    print("Example: OhMary, OhMaryBroadway")
    hashtags_input = input("Hashtags: ").strip()
    hashtags = [tag.strip().replace('#', '') for tag in hashtags_input.split(',')]

    print()
    max_items = int(input("Max items per platform (recommended: 50-100): ").strip() or 50)

    print()
    print("💰 Cost Estimate:")
    print("-" * 70)
    if choice in ['1', '3']:
        cost_tiktok = max_items * 0.03  # Approximate
        print(f"TikTok: ~${cost_tiktok:.2f} for {max_items} videos")
    if choice in ['2', '3']:
        cost_instagram = max_items * 0.02  # Approximate
        print(f"Instagram: ~${cost_instagram:.2f} for {max_items} posts")
    print()

    confirm = input("Continue? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled")
        sys.exit(0)

    # Collect data
    tiktok_data = []
    instagram_data = []

    try:
        if choice in ['1', '3']:
            tiktok_data = collect_tiktok(api_token, hashtags, max_items)
            save_to_csv(tiktok_data, 'tiktok_manual.csv')

        if choice in ['2', '3']:
            instagram_data = collect_instagram(api_token, hashtags, max_items)
            save_to_csv(instagram_data, 'instagram_manual.csv')

        print()
        print("="*70)
        print("✅ Collection Complete!")
        print("="*70)
        print()
        print(f"TikTok videos: {len(tiktok_data)}")
        print(f"Instagram posts: {len(instagram_data)}")
        print(f"Total items: {len(tiktok_data) + len(instagram_data)}")
        print()
        print("Next step: Run analysis")
        print("  python src/main.py")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print()
        print("Common issues:")
        print("  • Invalid API token")
        print("  • Insufficient credits")
        print("  • Network connection")
        print("  • Rate limiting")
        print()
        print("Check your Apify dashboard:")
        print("  https://console.apify.com/")

if __name__ == "__main__":
    main()

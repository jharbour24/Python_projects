#!/usr/bin/env python3
"""
Automated TikTok & Instagram Collection
Uses third-party APIs (Apify, RapidAPI) for legal automated scraping.
"""

import sys
import csv
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scrapers.tiktok_api import TikTokAPI
from scrapers.instagram_api import InstagramAPI


def load_api_credentials():
    """Load API credentials from config."""
    config_dir = Path(__file__).parent / "config"

    # Try Apify first
    apify_creds = config_dir / "apify_credentials.py"
    if apify_creds.exists():
        sys.path.insert(0, str(config_dir))
        import apify_credentials
        return {
            'service': 'apify',
            'token': apify_credentials.APIFY_API_TOKEN
        }

    # Try RapidAPI
    rapidapi_creds = config_dir / "rapidapi_credentials.py"
    if rapidapi_creds.exists():
        sys.path.insert(0, str(config_dir))
        import rapidapi_credentials
        return {
            'service': 'rapidapi',
            'token': rapidapi_credentials.RAPIDAPI_KEY
        }

    return None


def print_intro():
    """Print introduction and setup info."""
    print("="*70)
    print("Automated TikTok & Instagram Collection")
    print("="*70)
    print()
    print("This uses third-party APIs to automatically collect social media data.")
    print()
    print("✅ Legal: Uses licensed services (Apify, RapidAPI)")
    print("⚡ Fast: Fully automated, 5-10 minutes")
    print("💰 Paid: ~$5-10 for 200 items")
    print()


def get_collection_config():
    """Get configuration from user."""
    print("\n📋 Collection Configuration")
    print("-" * 70)

    # Platforms
    print("\nWhich platforms?")
    print("1. TikTok only")
    print("2. Instagram only")
    print("3. Both TikTok and Instagram")
    platform_choice = input("\nChoice (1-3): ").strip()

    collect_tiktok = platform_choice in ['1', '3']
    collect_instagram = platform_choice in ['2', '3']

    # Hashtags
    print("\n🏷️  Enter hashtags to search (comma-separated):")
    print("Example: OhMary, OhMaryBroadway, ColeEscola")
    hashtags_input = input("Hashtags: ").strip()
    hashtags = [h.strip().replace('#', '') for h in hashtags_input.split(',') if h.strip()]

    if not hashtags:
        hashtags = ['OhMary', 'OhMaryBroadway']
        print(f"Using default hashtags: {', '.join(hashtags)}")

    # Max results
    print("\n📊 How many items per platform?")
    print("Recommended: 50-100 per platform")
    max_items = int(input("Max items: ").strip() or 50)

    return {
        'collect_tiktok': collect_tiktok,
        'collect_instagram': collect_instagram,
        'hashtags': hashtags,
        'max_items': max_items
    }


def show_cost_estimate(config, credentials):
    """Show cost estimate and get confirmation."""
    service = credentials['service']

    print("\n💰 Cost Estimate")
    print("-" * 70)

    total_cost = 0

    if config['collect_tiktok']:
        cost = TikTokAPI.estimate_cost(config['max_items'], service)
        print(f"TikTok ({config['max_items']} videos):     ${cost:.2f}")
        total_cost += cost

    if config['collect_instagram']:
        cost = InstagramAPI.estimate_cost(config['max_items'], service)
        print(f"Instagram ({config['max_items']} posts):  ${cost:.2f}")
        total_cost += cost

    print("-" * 70)
    print(f"Estimated Total:                ${total_cost:.2f}")
    print()
    print(f"Using: {service.title()}")

    if service == 'apify':
        print("Check balance: https://console.apify.com/")
        print("Free tier includes $5 credit")
    elif service == 'rapidapi':
        print("Check balance: https://rapidapi.com/developer/billing")

    print()
    return total_cost


def collect_tiktok_data(api_token, service, config):
    """Collect TikTok data."""
    print("\n" + "="*70)
    print("TIKTOK COLLECTION")
    print("="*70)

    tiktok_api = TikTokAPI(api_service=service, api_token=api_token)

    videos = tiktok_api.search_multiple_hashtags(
        hashtags=config['hashtags'],
        max_per_tag=config['max_items'] // len(config['hashtags'])
    )

    if videos:
        # Save to CSV
        output_path = Path(__file__).parent / "data" / "raw" / "tiktok_manual.csv"

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            # Use standard template columns
            fieldnames = [
                'video_id', 'url', 'author', 'caption', 'hashtags',
                'likes', 'comments', 'shares', 'views', 'created_at',
                'platform', 'scraped_at'
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(videos)

        print(f"\n💾 Saved {len(videos)} videos to: {output_path}")

    return videos


def collect_instagram_data(api_token, service, config):
    """Collect Instagram data."""
    print("\n" + "="*70)
    print("INSTAGRAM COLLECTION")
    print("="*70)

    instagram_api = InstagramAPI(api_service=service, api_token=api_token)

    posts = instagram_api.search_multiple_hashtags(
        hashtags=config['hashtags'],
        max_per_tag=config['max_items'] // len(config['hashtags'])
    )

    if posts:
        # Save to CSV
        output_path = Path(__file__).parent / "data" / "raw" / "instagram_manual.csv"

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'post_id', 'url', 'author', 'caption', 'hashtags',
                'likes', 'comments_count', 'created_at', 'post_type',
                'platform', 'scraped_at'
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(posts)

        print(f"\n💾 Saved {len(posts)} posts to: {output_path}")

    return posts


def save_collection_log(config, videos, posts, duration):
    """Save collection log for reference."""
    log_path = Path(__file__).parent / "data" / "raw" / "collection_log.json"

    log = {
        'timestamp': datetime.now().isoformat(),
        'config': config,
        'tiktok_count': len(videos),
        'instagram_count': len(posts),
        'total_items': len(videos) + len(posts),
        'duration_seconds': duration
    }

    with open(log_path, 'w') as f:
        json.dump(log, f, indent=2)

    print(f"📝 Collection log saved to: {log_path}")


def main():
    print_intro()

    # Check for credentials
    credentials = load_api_credentials()

    if not credentials:
        print("❌ No API credentials found!")
        print()
        print("Please set up one of:")
        print("  1. Apify:    python setup_apify.py")
        print("  2. RapidAPI: python setup_rapidapi.py")
        print()
        sys.exit(1)

    print(f"✓ Using {credentials['service'].title()} API")

    # Get configuration
    config = get_collection_config()

    # Show cost estimate
    estimated_cost = show_cost_estimate(config, credentials)

    # Confirm
    print("⚠️  This will charge your API account.")
    confirm = input("Proceed with collection? (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("Cancelled.")
        sys.exit(0)

    # Start collection
    print("\n" + "="*70)
    print("STARTING AUTOMATED COLLECTION")
    print("="*70)
    print("This will take 5-15 minutes depending on volume...")
    print()

    start_time = datetime.now()

    videos = []
    posts = []

    try:
        # Collect TikTok
        if config['collect_tiktok']:
            videos = collect_tiktok_data(
                credentials['token'],
                credentials['service'],
                config
            )

        # Collect Instagram
        if config['collect_instagram']:
            posts = collect_instagram_data(
                credentials['token'],
                credentials['service'],
                config
            )

        duration = (datetime.now() - start_time).total_seconds()

        # Save log
        save_collection_log(config, videos, posts, duration)

        # Summary
        print("\n" + "="*70)
        print("✅ COLLECTION COMPLETE!")
        print("="*70)
        print()
        print(f"📊 Results:")
        print(f"   TikTok videos:   {len(videos)}")
        print(f"   Instagram posts: {len(posts)}")
        print(f"   Total items:     {len(videos) + len(posts)}")
        print()
        print(f"⏱️  Time: {duration:.0f} seconds ({duration/60:.1f} minutes)")
        print(f"💰 Estimated cost: ${estimated_cost:.2f}")
        print()
        print("📁 Data saved to:")
        print("   data/raw/tiktok_manual.csv")
        print("   data/raw/instagram_manual.csv")
        print()
        print("🚀 Next step: Run analysis")
        print("   python src/main.py")
        print()

    except KeyboardInterrupt:
        print("\n\n⚠️  Collection interrupted by user")
        print(f"Partial data may have been saved")
        sys.exit(1)

    except Exception as e:
        print(f"\n\n❌ Error during collection: {e}")
        print()
        print("Common issues:")
        print("  • Insufficient API credits")
        print("  • Invalid API token")
        print("  • Network connection")
        print("  • Rate limiting")
        print()
        print(f"Check your {credentials['service'].title()} dashboard")
        sys.exit(1)


if __name__ == "__main__":
    main()

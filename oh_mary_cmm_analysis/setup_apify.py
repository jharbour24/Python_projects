#!/usr/bin/env python3
"""
Apify Integration Setup
Legal third-party API for TikTok and Instagram scraping.
"""

import os
import sys
from pathlib import Path

def main():
    print("="*70)
    print("Apify Integration Setup")
    print("Third-Party API for TikTok & Instagram (Legal)")
    print("="*70)
    print()

    print("🔍 What is Apify?")
    print("-" * 70)
    print("Apify is a web scraping platform with LEGAL scrapers for:")
    print("  • TikTok (videos, profiles, hashtags)")
    print("  • Instagram (posts, profiles, hashtags)")
    print("  • Operates in compliance with platform ToS")
    print("  • Handles anti-bot detection")
    print()

    print("💰 Pricing:")
    print("-" * 70)
    print("  • Free tier: $5 credit (~100-500 posts)")
    print("  • Paid plans: $49+/month for more usage")
    print("  • Pay-as-you-go available")
    print()

    print("📋 Setup Steps:")
    print("-" * 70)
    print()
    print("1. Create Apify account:")
    print("   → https://apify.com/sign-up")
    print()
    print("2. Get your API token:")
    print("   → https://console.apify.com/account/integrations")
    print("   → Copy your 'Personal API token'")
    print()
    print("3. Choose scrapers:")
    print()
    print("   TikTok Scraper:")
    print("   → https://apify.com/clockworks/tiktok-scraper")
    print("   → Cost: ~$0.02-0.05 per video")
    print()
    print("   Instagram Scraper:")
    print("   → https://apify.com/apify/instagram-scraper")
    print("   → Cost: ~$0.01-0.03 per post")
    print()

    input("Press ENTER when you have your API token...")
    print()

    api_token = input("Enter your Apify API token: ").strip()

    if not api_token:
        print("❌ No token provided")
        sys.exit(1)

    # Save token
    config_path = Path(__file__).parent / "config" / "apify_credentials.py"

    with open(config_path, 'w') as f:
        f.write(f"""# Apify API Credentials
# DO NOT COMMIT THIS FILE TO GIT

APIFY_API_TOKEN = '{api_token}'
""")

    print()
    print("✅ Credentials saved!")
    print()

    # Test connection
    print("📋 Testing connection...")
    try:
        from apify_client import ApifyClient

        client = ApifyClient(api_token)
        user = client.user().get()

        print(f"✓ Connected successfully!")
        print(f"  Account: {user.get('username', 'N/A')}")
        print(f"  Email: {user.get('email', 'N/A')}")

    except ImportError:
        print("⚠️  Apify client not installed")
        print("   Install with: pip install apify-client")
        print("   Your token is saved and will work once installed")

    except Exception as e:
        print(f"⚠️  Connection error: {e}")
        print("   Check your API token at: https://console.apify.com/account/integrations")

    print()
    print("📋 Next Steps:")
    print("-" * 70)
    print()
    print("Install Apify client:")
    print("  pip install apify-client")
    print()
    print("Run automated collection:")
    print("  python collect_automated.py")
    print()
    print("💡 The free tier gives you $5 credit, enough for:")
    print("   • 100-250 TikTok videos ($2.50-5)")
    print("   • 150-500 Instagram posts ($1.50-10)")
    print("   • Estimated 200 items: ~$4-8")
    print()
    print("Check balance: https://console.apify.com/")
    print()

if __name__ == "__main__":
    main()

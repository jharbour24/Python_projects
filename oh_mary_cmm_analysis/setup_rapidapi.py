#!/usr/bin/env python3
"""
RapidAPI Setup (Alternative to Apify)
Third-party API for TikTok and Instagram scraping.
"""

import sys
from pathlib import Path


def main():
    print("="*70)
    print("RapidAPI Setup")
    print("Alternative Third-Party API for TikTok & Instagram")
    print("="*70)
    print()

    print("🔍 What is RapidAPI?")
    print("-" * 70)
    print("RapidAPI is a marketplace for APIs including:")
    print("  • TikTok scraper APIs")
    print("  • Instagram scraper APIs")
    print("  • Handles anti-bot detection")
    print("  • Pay-per-use pricing")
    print()

    print("💰 Pricing:")
    print("-" * 70)
    print("  • Basic tier: $9.99/month (5000 requests)")
    print("  • Pro tier: $24.99/month (20000 requests)")
    print("  • For 200 items: ~$0.50-2 depending on plan")
    print()
    print("Compare to Apify:")
    print("  • Apify: $5 free credit, then pay-as-you-go (~$4-8 for 200 items)")
    print("  • RapidAPI: Monthly subscription with request limits")
    print()

    print("📋 Setup Steps:")
    print("-" * 70)
    print()
    print("1. Create RapidAPI account:")
    print("   → https://rapidapi.com/auth/sign-up")
    print()
    print("2. Subscribe to scrapers:")
    print()
    print("   TikTok Scraper:")
    print("   → https://rapidapi.com/ti-services/api/tiktok-scraper7")
    print("   → Click 'Subscribe to Test'")
    print("   → Choose plan (Basic recommended)")
    print()
    print("   Instagram Scraper:")
    print("   → https://rapidapi.com/social-api1-instagram/api/instagram-scraper-api2")
    print("   → Click 'Subscribe to Test'")
    print("   → Choose plan")
    print()
    print("3. Get your API key:")
    print("   → Go to: https://rapidapi.com/developer/security")
    print("   → Copy 'Application Key' (starts with random letters/numbers)")
    print()

    input("Press ENTER when you have your API key...")
    print()

    api_key = input("Enter your RapidAPI key: ").strip()

    if not api_key:
        print("❌ No key provided")
        sys.exit(1)

    # Save credentials
    config_path = Path(__file__).parent / "config" / "rapidapi_credentials.py"

    with open(config_path, 'w') as f:
        f.write(f"""# RapidAPI Credentials
# DO NOT COMMIT THIS FILE TO GIT

RAPIDAPI_KEY = '{api_key}'
""")

    print()
    print("✅ Credentials saved!")
    print()

    # Test connection
    print("📋 Testing connection...")
    try:
        import requests

        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com"
        }

        response = requests.get(
            "https://tiktok-scraper7.p.rapidapi.com/challenge/posts",
            headers=headers,
            params={"challenge_name": "fyp", "count": "1"},
            timeout=10
        )

        if response.status_code == 200:
            print("✓ Connection successful!")
        elif response.status_code == 401:
            print("❌ Invalid API key")
        elif response.status_code == 429:
            print("⚠️  Rate limit reached (but key is valid)")
        else:
            print(f"⚠️  Status: {response.status_code}")

    except Exception as e:
        print(f"⚠️  Connection test error: {e}")
        print("Your key may still work - try collection anyway")

    print()
    print("📋 Next Steps:")
    print("-" * 70)
    print()
    print("Install requests (if needed):")
    print("  pip install requests")
    print()
    print("Run automated collection:")
    print("  python collect_automated.py")
    print()
    print("💡 RapidAPI vs Apify:")
    print("   • RapidAPI: Monthly subscription, predictable cost")
    print("   • Apify: Pay-per-use, $5 free credit")
    print("   • Both are legal and handle anti-bot detection")
    print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Complete Data Collection Workflow
Guides through Reddit API + manual TikTok/Instagram collection.
"""

import sys
import subprocess
from pathlib import Path

def check_file_exists(filepath):
    """Check if data file exists and return count."""
    if filepath.exists():
        with open(filepath, 'r') as f:
            lines = f.readlines()
            return len(lines) - 1 if len(lines) > 1 else 0
    return 0

def print_status():
    """Print current data collection status."""
    data_dir = Path(__file__).parent / "data" / "raw"

    reddit_manual = check_file_exists(data_dir / "reddit_manual.csv")
    tiktok_manual = check_file_exists(data_dir / "tiktok_manual.csv")
    instagram_manual = check_file_exists(data_dir / "instagram_manual.csv")

    creds_path = Path(__file__).parent / "config" / "reddit_credentials.py"
    reddit_api = "✓" if creds_path.exists() else "✗"

    print("\n" + "="*70)
    print("Current Data Collection Status")
    print("="*70)
    print(f"Reddit API:         {reddit_api} {'(configured)' if creds_path.exists() else '(not configured)'}")
    print(f"Reddit Manual:      {reddit_manual} posts")
    print(f"TikTok Manual:      {tiktok_manual} videos")
    print(f"Instagram Manual:   {instagram_manual} posts")
    print("-" * 70)
    print(f"TOTAL:              {reddit_manual + tiktok_manual + instagram_manual} items")
    print("="*70)

    if reddit_manual + tiktok_manual + instagram_manual >= 100:
        print("🎉 Excellent! 100+ items is great for robust analysis")
    elif reddit_manual + tiktok_manual + instagram_manual >= 50:
        print("👍 Good! 50+ items will give solid results")
    elif reddit_manual + tiktok_manual + instagram_manual >= 25:
        print("📊 Decent! 25+ items will work, more is better")
    else:
        print("💡 Recommendation: Aim for at least 50 total items")

    print()

def main():
    print("="*70)
    print("Oh Mary! CMM Analysis - Complete Data Collection")
    print("="*70)
    print()
    print("This guide will help you collect data from all platforms safely.")
    print()

    while True:
        print_status()

        print("\nWhat would you like to do?")
        print("-" * 70)
        print("1. Setup Reddit API (automated collection)")
        print("2. Collect TikTok data (manual, safe)")
        print("3. Collect Instagram data (manual, safe)")
        print("4. Run analysis with current data")
        print("5. View data collection tips")
        print("6. Exit")
        print()

        choice = input("Enter choice (1-6): ").strip()
        print()

        if choice == '1':
            print("🔧 Running Reddit API setup...")
            print()
            subprocess.run([sys.executable, "setup_reddit.py"])

        elif choice == '2':
            print("📱 Starting TikTok collection helper...")
            print()
            subprocess.run([sys.executable, "collect_tiktok.py"])

        elif choice == '3':
            print("📱 Starting Instagram collection helper...")
            print()
            subprocess.run([sys.executable, "collect_instagram.py"])

        elif choice == '4':
            print("🚀 Running analysis...")
            print()
            print("This will:")
            print("  - Collect Reddit data (if API configured)")
            print("  - Load manual TikTok/Instagram data")
            print("  - Analyze all discourse patterns")
            print("  - Generate reports and visualizations")
            print()
            confirm = input("Continue? (y/n): ").strip().lower()
            if confirm == 'y':
                subprocess.run([sys.executable, "src/main.py"])
                print()
                print("="*70)
                print("✅ Analysis complete!")
                print("="*70)
                print()
                print("View results:")
                print("  - Report: outputs/reports/report.md")
                print("  - Visualizations: outputs/visualizations/")
                print("  - Data: data/processed/")
                print()
                input("Press Enter to continue...")

        elif choice == '5':
            print("="*70)
            print("Data Collection Tips")
            print("="*70)
            print()
            print("🎯 RECOMMENDED APPROACH:")
            print("   1. Setup Reddit API first (10 min, automated)")
            print("   2. Manually collect TikTok (30 min, 50 videos)")
            print("   3. Manually collect Instagram (30 min, 50 posts)")
            print("   = Total: ~70 minutes for 200+ data points")
            print()
            print("📊 SAMPLE SIZE RECOMMENDATIONS:")
            print("   - Minimum: 25 total items")
            print("   - Good: 50-100 total items")
            print("   - Excellent: 100+ total items")
            print("   - Professional: 300+ (100 per platform)")
            print()
            print("🔍 WHAT TO LOOK FOR:")
            print("   Reddit:")
            print("     - r/broadway, r/musicals, r/nyc, r/gaybros")
            print("     - Search: 'Oh Mary', sort by relevance")
            print()
            print("   TikTok:")
            print("     - #OhMary, #OhMaryBroadway")
            print("     - Focus on high-engagement videos (1k+ likes)")
            print()
            print("   Instagram:")
            print("     - #OhMary, location: Lyceum Theatre")
            print("     - Audience photos, reviews, fan content")
            print()
            print("⚠️  IMPORTANT:")
            print("   - DO NOT share login credentials")
            print("   - Use public data only")
            print("   - Manual collection is safe and compliant")
            print()
            print("💡 TIME-SAVING TIPS:")
            print("   - Open browser + script side-by-side")
            print("   - You can pause and resume anytime")
            print("   - Data saves automatically as you go")
            print("   - Focus on quality over quantity")
            print()
            input("Press Enter to continue...")

        elif choice == '6':
            print("👋 Goodbye!")
            break

        else:
            print("❌ Invalid choice. Please enter 1-6.")

if __name__ == "__main__":
    main()

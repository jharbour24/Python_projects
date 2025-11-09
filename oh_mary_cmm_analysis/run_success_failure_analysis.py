#!/usr/bin/env python3
"""
Complete Success/Failure Analysis Pipeline
Collects data for all shows and runs PhD-level comparative analysis.
"""

import subprocess
import sys
from pathlib import Path


def print_banner(text: str):
    """Print formatted banner."""
    print("\n" + "="*70)
    print(text)
    print("="*70 + "\n")


def main():
    """Main execution."""
    print_banner("🎓 BROADWAY MARKETING ANALYSIS - 2024-2025 SEASON")

    print("This analysis will:")
    print("  1. Collect Reddit data for 40+ Broadway shows")
    print("     • Original plays (14 shows)")
    print("     • Original musicals (14 shows)")
    print("     • Play revivals (7 shows)")
    print("     • Musical revivals (7 shows)")
    print("\n  2. Collect Broadway Box Office Data")
    print("     • Weekly grosses from BroadwayWorld.com")
    print("     • Capacity percentages")
    print("     • Ticket prices")
    print("     • Full 2024-2025 Tony season")
    print("\n  3. Statistical Analysis (WHAT differs)")
    print("     • Extract 30+ metrics per show")
    print("     • T-tests for significance")
    print("     • Effect size calculations (Cohen's d)")
    print("     • Identify which metrics differentiate success/failure")
    print("\n  4. Qualitative Analysis (WHY it differs)")
    print("     • Analyze conversation themes & patterns")
    print("     • Identify what content goes viral")
    print("     • Examine audience language & tone")
    print("     • Discover messaging that resonates")
    print("\n  5. Correlation Analysis (Fan Engagement vs Financial Success)")
    print("     • Correlate Reddit metrics with box office performance")
    print("     • Identify which engagement patterns predict success")
    print("     • Find over/underperformers")
    print("     • Analyze by show type")
    print("\n  6. Generate comprehensive reports")
    print("     • WHAT: Statistical comparison")
    print("     • WHY: Qualitative insights")
    print("     • FINANCIAL: Reddit buzz vs grosses correlation")
    print("     • Actionable recommendations")

    print("\n⏱️  Estimated time:")
    print("  • Reddit data collection: 2-3 hours (40+ shows, Reddit API rate limits)")
    print("  • Broadway grosses scraping: 10-15 minutes (30+ weeks of data)")
    print("  • Statistical analysis: 5-10 minutes")
    print("  • Qualitative analysis: 5-10 minutes")
    print("  • Correlation analysis: 2-3 minutes")
    print("  • Total: ~2.5-3.5 hours")

    response = input("\nProceed? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("\nAnalysis cancelled.")
        return

    # Step 1: Reddit Data Collection
    print_banner("STEP 1/5: Reddit Data Collection")
    print("Collecting Reddit data for all 40+ shows...")
    print("(This will take 2-3 hours due to Reddit API rate limits)")

    try:
        result = subprocess.run(
            [sys.executable, "multi_show_reddit_scraper.py"],
            check=True
        )
        print("\n✅ Reddit data collection complete!")
    except subprocess.CalledProcessError:
        print("\n⚠️  Data collection had some errors, but continuing...")
    except FileNotFoundError:
        print("\n❌ Error: multi_show_reddit_scraper.py not found")
        return

    # Step 2: Broadway Grosses Data Collection
    print_banner("STEP 2/5: Broadway Box Office Data Collection")
    print("Scraping weekly grosses from BroadwayWorld.com...")
    print("(This will take 10-15 minutes)")

    try:
        result = subprocess.run(
            [sys.executable, "broadway_grosses_scraper.py"],
            check=True
        )
        print("\n✅ Grosses data collection complete!")
    except subprocess.CalledProcessError as e:
        print(f"\n⚠️  Grosses scraping had errors: {e}")
        print("Continuing to analysis...")
    except FileNotFoundError:
        print("\n❌ Error: broadway_grosses_scraper.py not found")
        return

    # Step 3: Statistical Analysis (WHAT)
    print_banner("STEP 3/5: Statistical Analysis (WHAT)")
    print("Analyzing WHAT metrics differ between successful vs unsuccessful campaigns...")

    try:
        result = subprocess.run(
            [sys.executable, "marketing_science_analysis.py"],
            check=True
        )
        print("\n✅ Statistical analysis complete!")
    except subprocess.CalledProcessError as e:
        print(f"\n⚠️  Statistical analysis failed: {e}")
        print("Continuing to qualitative analysis...")
    except FileNotFoundError:
        print("\n⚠️  marketing_science_analysis.py not found, skipping...")

    # Step 4: Qualitative Analysis (WHY)
    print_banner("STEP 4/5: Qualitative Analysis (WHY)")
    print("Analyzing WHY campaigns succeed - themes, content, messaging...")

    try:
        result = subprocess.run(
            [sys.executable, "why_campaigns_succeed_analysis.py"],
            check=True
        )
        print("\n✅ Qualitative analysis complete!")
    except subprocess.CalledProcessError as e:
        print(f"\n⚠️  Qualitative analysis failed: {e}")
        print("Continuing to correlation analysis...")
    except FileNotFoundError:
        print("\n⚠️  why_campaigns_succeed_analysis.py not found, skipping...")

    # Step 5: Correlation Analysis (Reddit vs Grosses)
    print_banner("STEP 5/5: Correlation Analysis (Fan Engagement vs Financial Success)")
    print("Correlating Reddit engagement with box office performance...")

    try:
        result = subprocess.run(
            [sys.executable, "reddit_grosses_correlation_analysis.py"],
            check=True
        )
        print("\n✅ Correlation analysis complete!")
    except subprocess.CalledProcessError as e:
        print(f"\n⚠️  Correlation analysis failed: {e}")
    except FileNotFoundError:
        print("\n❌ Error: reddit_grosses_correlation_analysis.py not found")

    # Show results
    print_banner("✅ COMPLETE!")

    print("📁 Results saved to:")

    print("\n**1️⃣  REDDIT DATA:**")
    print("  • data/raw/reddit_[show_name].csv - Individual show data")

    print("\n**2️⃣  BOX OFFICE DATA:**")
    print("  • data/grosses/broadway_grosses_2024_2025.csv - Weekly grosses")
    print("  • data/grosses/grosses_summary.csv - Summary by show")

    print("\n**3️⃣  WHAT Analysis (Statistical):**")
    print("  • outputs/marketing_science_all_metrics.csv")
    print("  • outputs/statistical_comparison.csv")
    print("  • outputs/marketing_science_report.json")

    print("\n**4️⃣  WHY Analysis (Qualitative):**")
    print("  • outputs/why_campaigns_succeed_report.md")
    print("  • outputs/why_analysis_raw_data.json")

    print("\n**5️⃣  CORRELATION Analysis (Reddit vs Grosses):**")
    print("  • outputs/reddit_grosses_correlation_report.md - Full analysis")
    print("  • outputs/merged_reddit_grosses.csv - Combined dataset")
    print("  • outputs/reddit_grosses_correlation.png - Visualizations")
    print("  • outputs/correlation_analysis_data.json - Raw correlation data")

    print("\n🎯 Key Questions Answered:")

    print("\n  1️⃣  WHAT differs between successful and unsuccessful campaigns?")
    print("    → Open 'outputs/statistical_comparison.csv'")
    print("    → See which metrics are statistically different")
    print("    → Understand effect sizes and significance")

    print("\n  2️⃣  WHY do some campaigns succeed?")
    print("    → Open 'outputs/why_campaigns_succeed_report.md'")
    print("    → See actual themes, language, and content patterns")
    print("    → Understand what messaging resonates")
    print("    → Discover what makes content go viral")

    print("\n  3️⃣  How does fan engagement correlate with financial success?")
    print("    → Open 'outputs/reddit_grosses_correlation_report.md'")
    print("    → See which Reddit metrics predict box office performance")
    print("    → Identify over/underperformers")
    print("    → Understand patterns by show type")

    print("\n💡 Actionable Insights:")
    print("  Combine all three analyses to understand:")
    print("  • WHAT to measure (metrics that matter)")
    print("  • WHY it matters (content strategies that work)")
    print("  • FINANCIAL CONTEXT (how buzz translates to revenue)")
    print("  • HOW to improve (specific recommendations)")

    print("\n" + "="*70)


if __name__ == "__main__":
    main()

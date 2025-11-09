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
    print_banner("🎓 BROADWAY MARKETING SUCCESS/FAILURE ANALYSIS")

    print("This analysis will:")
    print("  1. Collect Reddit data for 10 Broadway shows")
    print("     • 3 Successful campaigns (Oh Mary!, John Proctor, Maybe Happy Ending)")
    print("     • 7 Unsuccessful campaigns (Dead Outlaw, Smash, Real Women Have Curves,")
    print("       Redwood, Tammy Faye, Gypsy, Sunset Boulevard)")
    print("\n  2. Statistical Analysis (WHAT differs)")
    print("     • Extract 30+ metrics per show")
    print("     • T-tests for significance")
    print("     • Effect size calculations (Cohen's d)")
    print("     • Identify which metrics differentiate success/failure")
    print("\n  3. Qualitative Analysis (WHY it differs)")
    print("     • Analyze conversation themes & patterns")
    print("     • Identify what content goes viral")
    print("     • Examine audience language & tone")
    print("     • Discover messaging that resonates")
    print("\n  4. Generate comprehensive reports")
    print("     • WHAT: Statistical comparison")
    print("     • WHY: Qualitative insights")
    print("     • Actionable recommendations")

    print("\n⏱️  Estimated time:")
    print("  • Data collection: 60-90 minutes (Reddit API rate limits)")
    print("  • Statistical analysis: 5 minutes")
    print("  • Qualitative analysis: 5 minutes")
    print("  • Total: ~1.5-2 hours")

    response = input("\nProceed? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("\nAnalysis cancelled.")
        return

    # Step 1: Data Collection
    print_banner("STEP 1/2: Data Collection")
    print("Collecting Reddit data for all 10 shows...")
    print("(This will take 60-90 minutes)")

    try:
        result = subprocess.run(
            [sys.executable, "multi_show_reddit_scraper.py"],
            check=True
        )
        print("\n✅ Data collection complete!")
    except subprocess.CalledProcessError:
        print("\n⚠️  Data collection had some errors, but continuing...")
    except FileNotFoundError:
        print("\n❌ Error: multi_show_reddit_scraper.py not found")
        return

    # Step 2: Statistical Analysis (WHAT)
    print_banner("STEP 2/3: Statistical Analysis (WHAT)")
    print("Analyzing WHAT metrics differ between successful vs unsuccessful campaigns...")

    try:
        result = subprocess.run(
            [sys.executable, "marketing_science_analysis.py"],
            check=True
        )
        print("\n✅ Statistical analysis complete!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Statistical analysis failed: {e}")
        print("Continuing to qualitative analysis...")
    except FileNotFoundError:
        print("\n❌ Error: marketing_science_analysis.py not found")
        return

    # Step 3: Qualitative Analysis (WHY)
    print_banner("STEP 3/3: Qualitative Analysis (WHY)")
    print("Analyzing WHY campaigns succeed - themes, content, messaging...")

    try:
        result = subprocess.run(
            [sys.executable, "why_campaigns_succeed_analysis.py"],
            check=True
        )
        print("\n✅ Qualitative analysis complete!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Qualitative analysis failed: {e}")
    except FileNotFoundError:
        print("\n❌ Error: why_campaigns_succeed_analysis.py not found")

    # Show results
    print_banner("✅ COMPLETE!")

    print("📁 Results saved to:")
    print("\n**WHAT Analysis (Statistical):**")
    print("  • outputs/marketing_science_all_metrics.csv")
    print("  • outputs/statistical_comparison.csv")
    print("  • outputs/marketing_science_report.json")

    print("\n**WHY Analysis (Qualitative):**")
    print("  • outputs/why_campaigns_succeed_report.md")
    print("  • outputs/why_analysis_raw_data.json")

    print("\n🎯 Key Questions Answered:")
    print("\n  WHAT differs?")
    print("    → Open 'outputs/statistical_comparison.csv'")
    print("    → See which metrics are statistically different")
    print("    → Understand effect sizes and significance")

    print("\n  WHY does it differ?")
    print("    → Open 'outputs/why_campaigns_succeed_report.md'")
    print("    → See actual themes, language, and content patterns")
    print("    → Understand what messaging resonates")
    print("    → Discover what makes content go viral")

    print("\n💡 Actionable Insights:")
    print("  Combine both reports to understand:")
    print("  • WHAT to measure (metrics that matter)")
    print("  • WHY it matters (content strategies that work)")
    print("  • HOW to improve (specific recommendations)")

    print("\n" + "="*70)


if __name__ == "__main__":
    main()

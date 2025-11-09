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
    print("\n  2. Extract 30+ metrics per show across:")
    print("     • Volume & Reach")
    print("     • Engagement & Virality")
    print("     • Sentiment & Emotion")
    print("     • Word-of-Mouth & Advocacy")
    print("     • Temporal Patterns")
    print("     • Community Dynamics")
    print("\n  3. Perform statistical analysis:")
    print("     • T-tests for significance")
    print("     • Effect size calculations (Cohen's d)")
    print("     • Identify key success factors")
    print("\n  4. Generate actionable recommendations")

    print("\n⏱️  Estimated time:")
    print("  • Data collection: 60-90 minutes (Reddit API rate limits)")
    print("  • Analysis: 5 minutes")
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

    # Step 2: Advanced Analysis
    print_banner("STEP 2/2: PhD-Level Statistical Analysis")
    print("Analyzing what makes campaigns succeed vs fail...")

    try:
        result = subprocess.run(
            [sys.executable, "marketing_science_analysis.py"],
            check=True
        )
        print("\n✅ Analysis complete!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Analysis failed: {e}")
        return
    except FileNotFoundError:
        print("\n❌ Error: marketing_science_analysis.py not found")
        return

    # Show results
    print_banner("✅ COMPLETE!")

    print("📁 Results saved to:")
    print("  • outputs/marketing_science_all_metrics.csv")
    print("  • outputs/statistical_comparison.csv")
    print("  • outputs/marketing_science_report.json")

    print("\n🎯 Key Findings:")
    print("  Open 'outputs/statistical_comparison.csv' to see:")
    print("  • Which metrics differ significantly between successful/unsuccessful shows")
    print("  • Effect sizes (how big the differences are)")
    print("  • p-values (statistical confidence)")

    print("\n💡 Recommendations:")
    print("  Check 'outputs/marketing_science_report.json' for:")
    print("  • Identified success factors")
    print("  • Actionable recommendations")

    print("\n" + "="*70)


if __name__ == "__main__":
    main()

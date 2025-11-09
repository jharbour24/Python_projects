#!/usr/bin/env python3
"""
Full Comparative CMM Analysis Pipeline
Complete workflow from data collection to final report.
"""

import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime


def print_banner(text: str):
    """Print formatted banner."""
    print("\n" + "="*70)
    print(text)
    print("="*70 + "\n")


def clean_old_data():
    """Clean all previous data to ensure fresh analysis."""
    print_banner("🧹 Cleaning Previous Data")

    # Directories to clean
    dirs_to_clean = [
        Path("data/raw"),
        Path("data/processed"),
        Path("outputs/visualizations"),
        Path("outputs/reports"),
        Path("outputs")
    ]

    files_to_remove = [
        Path("outputs/comparative_summary.csv"),
        Path("outputs/detailed_results.json"),
        Path("data/raw/collection_summary.json")
    ]

    print("This will delete:")
    print("  • All raw data (data/raw/)")
    print("  • All processed data (data/processed/)")
    print("  • All previous outputs (outputs/)")
    print("  • All visualizations")
    print("  • All reports")

    response = input("\n⚠️  Delete all old data? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("⏭  Skipping cleanup. Old data will be overwritten during analysis.")
        return

    print("\n🗑️  Removing old data...")

    # Remove specific files first
    for file_path in files_to_remove:
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"  ✓ Removed: {file_path}")
            except Exception as e:
                print(f"  ⚠ Could not remove {file_path}: {e}")

    # Clean directories
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            try:
                # Remove all files in directory but keep the directory
                for item in dir_path.iterdir():
                    if item.is_file():
                        item.unlink()
                        print(f"  ✓ Removed: {item}")
                    elif item.is_dir():
                        shutil.rmtree(item)
                        print(f"  ✓ Removed directory: {item}")
            except Exception as e:
                print(f"  ⚠ Could not clean {dir_path}: {e}")

    print("\n✅ Cleanup complete! Starting fresh analysis.")
    print("="*70)


def run_step(step_name: str, script_name: str, skip_prompt: bool = False) -> bool:
    """
    Run an analysis step.

    Args:
        step_name: Name of the step for display
        script_name: Python script to run
        skip_prompt: Skip user confirmation

    Returns:
        True if successful, False otherwise
    """
    print_banner(step_name)

    if not skip_prompt:
        response = input(f"Run {step_name}? (yes/no/skip): ").strip().lower()
        if response == 'skip':
            print(f"⏭  Skipping {step_name}")
            return True
        elif response not in ['yes', 'y']:
            print(f"⏭  Cancelled")
            return False

    print(f"\n🚀 Running: {script_name}\n")

    try:
        result = subprocess.run(
            [sys.executable, script_name],
            check=True,
            capture_output=False
        )
        print(f"\n✅ {step_name} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {step_name} failed with error code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"\n❌ Script not found: {script_name}")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    print_banner("Checking Dependencies")

    required = ['praw', 'pandas', 'yaml', 'matplotlib', 'seaborn']
    missing = []

    for package in required:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - MISSING")
            missing.append(package)

    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("\nInstall with:")
        print("  pip install praw pandas pyyaml matplotlib seaborn")
        response = input("\nContinue anyway? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            return False

    return True


def main():
    """Main execution function."""
    print("\n" + "="*70)
    print("🎭 BROADWAY COMPARATIVE CMM ANALYSIS")
    print("="*70)
    print("\nComplete Pipeline:")
    print("  0. Clean old data (fresh start)")
    print("  1. Data Collection (Reddit scraping)")
    print("  2. Discourse Analysis (CMM metrics)")
    print("  3. Visualizations (Comparative charts)")
    print("  4. Report Generation (Markdown report)")
    print("\n⏱️  Estimated time: 30-60 minutes")
    print("    (mostly waiting for Reddit API rate limits)")

    response = input("\nProceed with full analysis? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("\nAnalysis cancelled.")
        return

    start_time = datetime.now()

    # Step 0: Clean old data
    clean_old_data()

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependency check failed. Exiting.")
        return

    # Step 1: Data Collection
    print("\n" + "─"*70)
    print("STEP 1/4: Data Collection")
    print("─"*70)
    print("\nThis will collect Reddit data for all three shows.")
    print("⚠️  This step may take 20-40 minutes due to API rate limits.")

    if not run_step("Data Collection", "multi_show_reddit_scraper.py"):
        print("\n❌ Pipeline failed at data collection")
        return

    # Step 2: Analysis
    print("\n" + "─"*70)
    print("STEP 2/4: CMM Analysis")
    print("─"*70)
    print("\nThis will analyze discourse and calculate CMM metrics.")

    if not run_step("CMM Analysis", "run_comparative_analysis.py", skip_prompt=True):
        print("\n❌ Pipeline failed at analysis")
        return

    # Step 3: Visualizations
    print("\n" + "─"*70)
    print("STEP 3/4: Visualizations")
    print("─"*70)
    print("\nThis will generate comparative charts.")

    if not run_step("Visualizations", "generate_comparative_visualizations.py", skip_prompt=True):
        print("\n⚠️  Visualization generation failed, but continuing...")

    # Step 4: Report
    print("\n" + "─"*70)
    print("STEP 4/4: Report Generation")
    print("─"*70)
    print("\nThis will create the final comparative report.")

    if not run_step("Report Generation", "generate_comparative_report.py", skip_prompt=True):
        print("\n⚠️  Report generation failed")

    # Complete
    end_time = datetime.now()
    duration = end_time - start_time

    print_banner("✅ ANALYSIS COMPLETE!")

    print(f"⏱️  Total time: {duration}")
    print("\n📁 Outputs:")
    print("  • Comparative summary: outputs/comparative_summary.csv")
    print("  • Detailed report: outputs/reports/comparative_analysis_report.md")
    print("  • Visualizations: outputs/visualizations/")
    print("  • Processed data: data/processed/")

    print("\n🚀 Next steps:")
    print("  1. Open: outputs/reports/comparative_analysis_report.md")
    print("  2. Review: outputs/comparative_summary.csv")
    print("  3. View charts in: outputs/visualizations/")


if __name__ == "__main__":
    main()

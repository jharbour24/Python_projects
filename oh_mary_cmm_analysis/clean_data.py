#!/usr/bin/env python3
"""
Clean Data Script
Removes all previous analysis data to start fresh.
"""

import shutil
from pathlib import Path


def clean_all_data():
    """Remove all data, outputs, and analysis results."""
    print("\n" + "="*70)
    print("🧹 DATA CLEANUP UTILITY")
    print("="*70 + "\n")

    print("This script will permanently delete:")
    print("\n📂 Raw Data:")
    print("  • data/raw/*.csv (collected Reddit posts)")
    print("  • data/raw/*.json (collection metadata)")

    print("\n📂 Processed Data:")
    print("  • data/processed/*.csv (analyzed data)")

    print("\n📂 Outputs:")
    print("  • outputs/visualizations/*.png (all charts)")
    print("  • outputs/reports/*.md (analysis reports)")
    print("  • outputs/*.csv (summary tables)")
    print("  • outputs/*.json (detailed results)")

    print("\n⚠️  WARNING: This action cannot be undone!")

    response = input("\nType 'DELETE' to confirm cleanup: ").strip()

    if response != 'DELETE':
        print("\n❌ Cleanup cancelled. No files were deleted.")
        return

    print("\n🗑️  Deleting files...\n")

    # Directories to clean
    dirs_to_clean = {
        "data/raw": "Raw data",
        "data/processed": "Processed data",
        "outputs/visualizations": "Visualizations",
        "outputs/reports": "Reports",
        "outputs": "Output files"
    }

    total_removed = 0

    for dir_str, description in dirs_to_clean.items():
        dir_path = Path(dir_str)

        if not dir_path.exists():
            print(f"  ⏭  {description}: Directory doesn't exist")
            continue

        removed_count = 0

        try:
            for item in dir_path.iterdir():
                if item.is_file():
                    item.unlink()
                    removed_count += 1
                    total_removed += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    removed_count += 1
                    total_removed += 1

            print(f"  ✓ {description}: Removed {removed_count} items")

        except Exception as e:
            print(f"  ⚠ {description}: Error - {e}")

    print("\n" + "="*70)
    print(f"✅ Cleanup Complete!")
    print(f"   Removed {total_removed} files/directories")
    print("="*70)
    print("\n💡 You can now run a fresh analysis:")
    print("   python run_full_analysis.py")
    print("\n")


def main():
    """Main execution."""
    clean_all_data()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Public Signals Collection CLI

Orchestrates collection of all public demand proxy signals:
- Google Trends
- Wikipedia pageviews
- TikTok engagement
- Instagram engagement

Outputs weekly data files for each source.
"""

import argparse
import yaml
import logging
from pathlib import Path
from datetime import datetime
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.sources.google_trends import collect_google_trends
from src.sources.wikipedia import collect_wikipedia
from src.sources.tiktok_public import collect_tiktok
from src.sources.instagram_public import collect_instagram

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_shows_config(config_path: str) -> list:
    """
    Load shows configuration from YAML file.

    Args:
        config_path: Path to shows.yaml config file

    Returns:
        List of show configuration dicts
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    shows = config.get('shows', [])
    logger.info(f"Loaded {len(shows)} shows from config")

    return shows


def collect_all_signals(
    shows_config: list,
    start_date: str,
    end_date: str,
    output_base: str = "public_signals/data",
    sources: list = None,
    max_posts: int = 30
):
    """
    Collect all public signals for configured shows.

    Args:
        shows_config: List of show configs
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        output_base: Base output directory
        sources: List of sources to collect (default: all)
        max_posts: Maximum posts per show for social media
    """
    output_path = Path(output_base)
    output_path.mkdir(parents=True, exist_ok=True)

    all_sources = ['google_trends', 'wikipedia', 'tiktok', 'instagram']
    sources_to_run = sources if sources else all_sources

    results = {}

    # Google Trends
    if 'google_trends' in sources_to_run:
        logger.info("\n" + "="*70)
        logger.info("COLLECTING GOOGLE TRENDS")
        logger.info("="*70 + "\n")

        try:
            gt_df = collect_google_trends(
                shows_config=shows_config,
                start_date=start_date,
                end_date=end_date,
                output_dir=str(output_path / "raw" / "google_trends")
            )

            if not gt_df.empty:
                # Save combined weekly data
                weekly_file = output_path / "weekly" / "google_trends_weekly.csv"
                weekly_file.parent.mkdir(parents=True, exist_ok=True)
                gt_df.to_csv(weekly_file, index=False)
                logger.info(f"✓ Saved: {weekly_file}")
                results['google_trends'] = {'status': 'success', 'rows': len(gt_df)}
            else:
                results['google_trends'] = {'status': 'no_data', 'rows': 0}

        except Exception as e:
            logger.error(f"Google Trends collection failed: {e}")
            results['google_trends'] = {'status': 'error', 'error': str(e)}

    # Wikipedia
    if 'wikipedia' in sources_to_run:
        logger.info("\n" + "="*70)
        logger.info("COLLECTING WIKIPEDIA PAGEVIEWS")
        logger.info("="*70 + "\n")

        try:
            wiki_df = collect_wikipedia(
                shows_config=shows_config,
                start_date=start_date,
                end_date=end_date,
                output_dir=str(output_path / "raw" / "wikipedia")
            )

            if not wiki_df.empty:
                weekly_file = output_path / "weekly" / "wikipedia_weekly.csv"
                weekly_file.parent.mkdir(parents=True, exist_ok=True)
                wiki_df.to_csv(weekly_file, index=False)
                logger.info(f"✓ Saved: {weekly_file}")
                results['wikipedia'] = {'status': 'success', 'rows': len(wiki_df)}
            else:
                results['wikipedia'] = {'status': 'no_data', 'rows': 0}

        except Exception as e:
            logger.error(f"Wikipedia collection failed: {e}")
            results['wikipedia'] = {'status': 'error', 'error': str(e)}

    # TikTok
    if 'tiktok' in sources_to_run:
        logger.info("\n" + "="*70)
        logger.info("COLLECTING TIKTOK DATA")
        logger.info("="*70 + "\n")

        try:
            tt_df = collect_tiktok(
                shows_config=shows_config,
                max_posts=max_posts,
                output_dir=str(output_path / "raw" / "tiktok")
            )

            if not tt_df.empty:
                weekly_file = output_path / "weekly" / "tiktok_weekly.csv"
                weekly_file.parent.mkdir(parents=True, exist_ok=True)
                tt_df.to_csv(weekly_file, index=False)
                logger.info(f"✓ Saved: {weekly_file}")
                results['tiktok'] = {'status': 'success', 'rows': len(tt_df)}
            else:
                results['tiktok'] = {'status': 'no_data', 'rows': 0}

        except Exception as e:
            logger.error(f"TikTok collection failed: {e}")
            results['tiktok'] = {'status': 'error', 'error': str(e)}

    # Instagram
    if 'instagram' in sources_to_run:
        logger.info("\n" + "="*70)
        logger.info("COLLECTING INSTAGRAM DATA")
        logger.info("="*70 + "\n")

        try:
            ig_df = collect_instagram(
                shows_config=shows_config,
                max_posts=max_posts,
                output_dir=str(output_path / "raw" / "instagram")
            )

            if not ig_df.empty:
                weekly_file = output_path / "weekly" / "instagram_weekly.csv"
                weekly_file.parent.mkdir(parents=True, exist_ok=True)
                ig_df.to_csv(weekly_file, index=False)
                logger.info(f"✓ Saved: {weekly_file}")
                results['instagram'] = {'status': 'success', 'rows': len(ig_df)}
            else:
                results['instagram'] = {'status': 'no_data', 'rows': 0}

        except Exception as e:
            logger.error(f"Instagram collection failed: {e}")
            results['instagram'] = {'status': 'error', 'error': str(e)}

    # Summary
    logger.info("\n" + "="*70)
    logger.info("COLLECTION SUMMARY")
    logger.info("="*70)

    for source, result in results.items():
        status = result['status']
        if status == 'success':
            logger.info(f"  ✓ {source}: {result['rows']} rows")
        elif status == 'no_data':
            logger.warning(f"  ⚠ {source}: No data collected")
        elif status == 'error':
            logger.error(f"  ✗ {source}: {result.get('error', 'Unknown error')}")

    logger.info(f"\nOutput directory: {output_path}")

    return results


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Collect public demand proxy signals for Broadway shows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect all signals for 2024 season
  python3 pull_public_signals.py --config shows.yaml --start 2024-01-01 --end 2024-12-31

  # Collect only Google Trends and Wikipedia
  python3 pull_public_signals.py --config shows.yaml --start 2024-01-01 --end 2024-12-31 --sources google_trends wikipedia

  # Collect with custom output directory
  python3 pull_public_signals.py --config shows.yaml --start 2024-01-01 --end 2024-12-31 --output data/public_signals
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Path to shows config YAML file'
    )

    parser.add_argument(
        '--start',
        type=str,
        required=True,
        help='Start date (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end',
        type=str,
        required=True,
        help='End date (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='public_signals/data',
        help='Base output directory (default: public_signals/data)'
    )

    parser.add_argument(
        '--sources',
        nargs='+',
        choices=['google_trends', 'wikipedia', 'tiktok', 'instagram'],
        help='Specific sources to collect (default: all)'
    )

    parser.add_argument(
        '--max-posts',
        type=int,
        default=30,
        help='Maximum posts per show for social media (default: 30)'
    )

    args = parser.parse_args()

    # Validate dates
    try:
        datetime.strptime(args.start, '%Y-%m-%d')
        datetime.strptime(args.end, '%Y-%m-%d')
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        sys.exit(1)

    # Load config
    try:
        shows_config = load_shows_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    # Run collection
    logger.info(f"Start date: {args.start}")
    logger.info(f"End date: {args.end}")
    logger.info(f"Shows: {len(shows_config)}")
    logger.info(f"Sources: {args.sources if args.sources else 'all'}")

    results = collect_all_signals(
        shows_config=shows_config,
        start_date=args.start,
        end_date=args.end,
        output_base=args.output,
        sources=args.sources,
        max_posts=args.max_posts
    )

    # Exit with error code if any source failed
    if any(r['status'] == 'error' for r in results.values()):
        sys.exit(1)


if __name__ == '__main__':
    main()

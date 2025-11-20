#!/usr/bin/env python3
"""
Full producer scraping for all 535 Broadway shows (2010-2025).

This script will:
1. Load all shows from raw/all_broadway_shows_2010_2025.csv
2. Search Google for IBDB URL for each show
3. Parse producer counts from IBDB pages
4. Save results to data/show_producer_counts_ibdb.csv
5. Create detailed logs and progress reports

Features:
- Checkpointing (can resume from interruption)
- Progress tracking
- Error handling (continues on failures)
- Polite rate limiting
- Detailed logging

Expected runtime: 30-60 minutes for 535 shows
"""

import sys
from pathlib import Path
import pandas as pd
import time
from datetime import datetime

from advanced_ibdb_scraper import AdvancedIBDBScraper
from utils import setup_logger

logger = setup_logger(__name__, log_file='logs/full_scrape.log')


def load_checkpoint(checkpoint_file: Path) -> pd.DataFrame:
    """Load checkpoint if it exists."""
    if checkpoint_file.exists():
        logger.info(f"Found checkpoint file: {checkpoint_file}")
        df = pd.read_csv(checkpoint_file)
        logger.info(f"  Loaded {len(df)} previously scraped shows")
        return df
    return pd.DataFrame()


def save_checkpoint(df: pd.DataFrame, checkpoint_file: Path):
    """Save checkpoint."""
    df.to_csv(checkpoint_file, index=False)
    logger.info(f"✓ Checkpoint saved: {checkpoint_file}")


def run_full_scrape():
    """Main scraping workflow."""

    logger.info("="*70)
    logger.info("BROADWAY PRODUCER FULL SCRAPE - ALL 535 SHOWS")
    logger.info("="*70)
    logger.info(f"Start time: {datetime.now()}")

    # Load show list
    show_list_path = Path('raw/all_broadway_shows_2010_2025.csv')
    if not show_list_path.exists():
        logger.error(f"Show list not found: {show_list_path}")
        logger.error("Please run create_complete_show_list.py first")
        return 1

    shows_df = pd.read_csv(show_list_path)
    logger.info(f"\n✓ Loaded {len(shows_df)} shows from {show_list_path}")

    # Setup output paths
    output_path = Path('data/show_producer_counts_ibdb.csv')
    checkpoint_path = Path('data/checkpoint_producer_scrape.csv')
    failed_path = Path('data/failed_shows.csv')

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load checkpoint if exists
    checkpoint_df = load_checkpoint(checkpoint_path)

    if len(checkpoint_df) > 0:
        # Resume from checkpoint
        scraped_shows = set(checkpoint_df['show_name'].values)
        remaining_shows = shows_df[~shows_df['show_name'].isin(scraped_shows)]
        results_df = checkpoint_df

        logger.info(f"\nResuming from checkpoint:")
        logger.info(f"  Already scraped: {len(checkpoint_df)} shows")
        logger.info(f"  Remaining: {len(remaining_shows)} shows")
    else:
        # Start from beginning
        remaining_shows = shows_df
        results_df = pd.DataFrame()

        logger.info(f"\nStarting fresh scrape of {len(shows_df)} shows")

    # Initialize scraper
    logger.info("\nInitializing scraper...")
    scraper = AdvancedIBDBScraper(rate_limit_delay=4.0)  # 4 seconds between requests

    # Track statistics
    start_time = time.time()
    successful = 0
    failed = 0
    not_found = 0
    failed_shows = []

    # Process each show
    total_remaining = len(remaining_shows)

    logger.info(f"\n{'='*70}")
    logger.info("STARTING SCRAPE")
    logger.info(f"{'='*70}\n")

    for idx, row in remaining_shows.iterrows():
        show_id = row['show_id']
        show_name = row['show_name']

        # Progress indicator
        current = idx - remaining_shows.index[0] + 1
        progress_pct = (len(results_df) + current) / len(shows_df) * 100

        logger.info(f"\n[{len(results_df) + current}/{len(shows_df)}] ({progress_pct:.1f}%) Processing: {show_name}")
        logger.info("-" * 70)

        try:
            # Scrape this show
            result = scraper.get_producers_for_show(show_name)

            # Add show_id
            result['show_id'] = show_id

            # Track status
            if result['scrape_status'] == 'ok':
                successful += 1
                logger.info(f"✓ SUCCESS: Found {result['num_total_producers']} producers")
            elif result['scrape_status'] == 'not_found':
                not_found += 1
                logger.warning(f"⚠ NOT FOUND: Could not locate IBDB page")
                failed_shows.append({
                    'show_id': show_id,
                    'show_name': show_name,
                    'reason': 'not_found'
                })
            else:
                failed += 1
                logger.error(f"✗ FAILED: {result['scrape_status']}")
                failed_shows.append({
                    'show_id': show_id,
                    'show_name': show_name,
                    'reason': result['scrape_status']
                })

            # Add to results
            result_row = pd.DataFrame([result])
            results_df = pd.concat([results_df, result_row], ignore_index=True)

            # Save checkpoint every 10 shows
            if (current % 10 == 0) or (current == total_remaining):
                save_checkpoint(results_df, checkpoint_path)

                # Progress report
                elapsed = time.time() - start_time
                rate = (len(results_df)) / elapsed if elapsed > 0 else 0
                remaining_time = (len(shows_df) - len(results_df)) / rate if rate > 0 else 0

                logger.info(f"\n{'='*70}")
                logger.info("PROGRESS REPORT")
                logger.info(f"{'='*70}")
                logger.info(f"  Completed: {len(results_df)}/{len(shows_df)}")
                logger.info(f"  Successful: {successful}")
                logger.info(f"  Not found: {not_found}")
                logger.info(f"  Failed: {failed}")
                logger.info(f"  Rate: {rate:.2f} shows/sec")
                logger.info(f"  Elapsed: {elapsed/60:.1f} minutes")
                logger.info(f"  Est. remaining: {remaining_time/60:.1f} minutes")
                logger.info(f"{'='*70}\n")

        except KeyboardInterrupt:
            logger.warning("\n\n⚠ Interrupted by user!")
            logger.info("Saving progress before exiting...")
            save_checkpoint(results_df, checkpoint_path)
            logger.info("✓ Progress saved. Run again to resume from this point.")
            return 1

        except Exception as e:
            logger.error(f"✗ Unexpected error processing {show_name}: {e}")
            import traceback
            traceback.print_exc()

            failed += 1
            failed_shows.append({
                'show_id': show_id,
                'show_name': show_name,
                'reason': f'error: {str(e)}'
            })

            # Continue with next show
            continue

    # Final save
    logger.info(f"\n{'='*70}")
    logger.info("SCRAPE COMPLETE - SAVING RESULTS")
    logger.info(f"{'='*70}\n")

    # Reorder columns
    column_order = ['show_id', 'show_name', 'ibdb_url', 'num_total_producers',
                   'num_lead_producers', 'num_co_producers', 'scrape_status', 'scrape_notes']
    results_df = results_df[[col for col in column_order if col in results_df.columns]]

    # Save final results
    results_df.to_csv(output_path, index=False)
    logger.info(f"✓ Saved results: {output_path}")

    # Save failed shows list
    if failed_shows:
        failed_df = pd.DataFrame(failed_shows)
        failed_df.to_csv(failed_path, index=False)
        logger.info(f"✓ Saved failed shows: {failed_path}")

    # Remove checkpoint
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        logger.info(f"✓ Removed checkpoint file")

    # Final statistics
    total_time = time.time() - start_time

    logger.info(f"\n{'='*70}")
    logger.info("FINAL STATISTICS")
    logger.info(f"{'='*70}")
    logger.info(f"Total shows: {len(shows_df)}")
    logger.info(f"Successfully scraped: {successful} ({successful/len(shows_df)*100:.1f}%)")
    logger.info(f"Not found on IBDB: {not_found} ({not_found/len(shows_df)*100:.1f}%)")
    logger.info(f"Failed: {failed} ({failed/len(shows_df)*100:.1f}%)")
    logger.info(f"")
    logger.info(f"Total time: {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)")
    logger.info(f"Average rate: {len(shows_df)/total_time:.2f} shows/second")
    logger.info(f"")
    logger.info(f"Producer statistics (successful scrapes):")
    if successful > 0:
        success_df = results_df[results_df['scrape_status'] == 'ok']
        logger.info(f"  Mean producers per show: {success_df['num_total_producers'].mean():.1f}")
        logger.info(f"  Median producers per show: {success_df['num_total_producers'].median():.1f}")
        logger.info(f"  Range: {success_df['num_total_producers'].min():.0f} - {success_df['num_total_producers'].max():.0f}")

    logger.info(f"\n{'='*70}")
    logger.info("✓✓✓ SCRAPE COMPLETE ✓✓✓")
    logger.info(f"{'='*70}")
    logger.info(f"\nResults saved to: {output_path}")
    logger.info(f"Logs saved to: logs/full_scrape.log")
    logger.info(f"\nNext step: Run analysis/producer_tony_analysis.py")

    return 0


if __name__ == '__main__':
    try:
        exit_code = run_full_scrape()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

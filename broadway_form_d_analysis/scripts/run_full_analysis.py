#!/usr/bin/env python3
"""
Broadway Form D Analysis - Main Orchestration Script
Runs complete data collection, analysis, and visualization pipeline
"""

import sys
import logging
from pathlib import Path
import argparse

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from generate_sample_data import SampleDataGenerator
from analyze_form_d_data import BroadwayFormDAnalyzer
from visualize_form_d_data import BroadwayFormDVisualizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_complete_pipeline(use_sample_data: bool = True, num_samples: int = 200):
    """
    Execute complete analysis pipeline

    Args:
        use_sample_data: If True, generates sample data instead of fetching from SEC
        num_samples: Number of sample records to generate
    """
    project_dir = Path(__file__).parent.parent

    logger.info("=" * 80)
    logger.info("BROADWAY FORM D ANALYSIS - COMPLETE PIPELINE")
    logger.info("=" * 80)

    # Step 1: Data Collection/Generation
    logger.info("\n" + "=" * 80)
    logger.info("STEP 1: DATA COLLECTION")
    logger.info("=" * 80)

    processed_dir = project_dir / 'data' / 'processed'
    data_file = processed_dir / 'broadway_form_d_2010_2025.csv'

    if use_sample_data:
        logger.info("Generating sample data for demonstration...")
        generator = SampleDataGenerator(processed_dir, num_filings=num_samples)
        df = generator.generate_sample_data()
        data_path = generator.save_sample_data(df)
        logger.info(f"✓ Sample data generated: {data_path}")
    else:
        logger.info("NOTE: Live SEC EDGAR data collection requires internet access")
        logger.info("      and compliance with SEC rate limits (10 requests/second).")
        logger.info("      This process may take several hours for 2010-2025 data.")

        from collect_form_d_data import BroadwayFormDCollector

        data_dir = project_dir / 'data'
        collector = BroadwayFormDCollector(data_dir)
        df = collector.run_full_collection(2010, 2025)

        if df.empty:
            logger.error("No data collected. Exiting.")
            return

        logger.info(f"✓ Data collection complete: {len(df)} filings")
        data_path = data_file

    # Step 2: Quantitative Analysis
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2: QUANTITATIVE ANALYSIS")
    logger.info("=" * 80)

    analysis_dir = project_dir / 'analysis'
    analysis_dir.mkdir(exist_ok=True)

    analyzer = BroadwayFormDAnalyzer(data_path)
    results = analyzer.run_full_analysis()
    analyzer.save_results(analysis_dir)

    logger.info(f"✓ Analysis complete: {len(results)} analysis modules executed")

    # Print key insights
    logger.info("\n" + "=" * 80)
    logger.info("KEY INSIGHTS")
    logger.info("=" * 80)

    if 'summary_insights' in results:
        for i, insight in enumerate(results['summary_insights']['insights'], 1):
            logger.info(f"\n{i}. {insight['title']}")
            logger.info(f"   {insight['finding']}")

    # Step 3: Visualization
    logger.info("\n" + "=" * 80)
    logger.info("STEP 3: VISUALIZATION")
    logger.info("=" * 80)

    visuals_dir = project_dir / 'visuals'
    visualizer = BroadwayFormDVisualizer(data_path, visuals_dir)
    visualizer.generate_all_visualizations()

    logger.info(f"✓ Visualizations complete: saved to {visuals_dir}")

    # Step 4: Summary
    logger.info("\n" + "=" * 80)
    logger.info("PIPELINE COMPLETE - DELIVERABLES")
    logger.info("=" * 80)

    deliverables = [
        (data_path, "Master Dataset (CSV)"),
        (analysis_dir / 'analysis_results.json', "Analysis Results (JSON)"),
        (visuals_dir / 'annual_offering_trends.png', "Annual Offering Trends"),
        (visuals_dir / 'investor_trends.png', "Investor Base Evolution"),
        (visuals_dir / 'covid_impact_comparison.png', "COVID Impact Analysis"),
        (visuals_dir / 'geographic_distribution.png', "Geographic Distribution"),
        (visuals_dir / 'securities_and_exemptions.png', "Securities & Exemptions"),
        (visuals_dir / 'correlation_matrix.png', "Correlation Matrix"),
        (visuals_dir / 'offering_size_distribution.png', "Offering Size Distribution")
    ]

    logger.info("\nGenerated files:")
    for path, description in deliverables:
        if path.exists():
            logger.info(f"  ✓ {description:<40} → {path}")
        else:
            logger.info(f"  ✗ {description:<40} → NOT FOUND")

    logger.info("\n" + "=" * 80)
    logger.info("Analysis complete! Review the files above for detailed results.")
    logger.info("=" * 80)


def main():
    """Main entry point with CLI arguments"""
    parser = argparse.ArgumentParser(
        description='Broadway Form D Analysis Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with sample data (recommended for testing)
  python run_full_analysis.py --sample

  # Generate 500 sample filings
  python run_full_analysis.py --sample --num-samples 500

  # Collect live data from SEC EDGAR (requires internet, takes hours)
  python run_full_analysis.py --live

Note: Live data collection requires compliance with SEC EDGAR rate limits
and may take several hours to complete for 15+ years of data.
        """
    )

    parser.add_argument(
        '--sample',
        action='store_true',
        help='Use sample data generation (recommended for testing)'
    )

    parser.add_argument(
        '--live',
        action='store_true',
        help='Collect live data from SEC EDGAR (requires internet access)'
    )

    parser.add_argument(
        '--num-samples',
        type=int,
        default=200,
        help='Number of sample filings to generate (default: 200)'
    )

    args = parser.parse_args()

    # Default to sample if neither specified
    if not args.sample and not args.live:
        logger.info("No data source specified. Using --sample by default.")
        logger.info("Use --live to collect real SEC EDGAR data.\n")
        args.sample = True

    use_sample = args.sample

    try:
        run_complete_pipeline(use_sample_data=use_sample, num_samples=args.num_samples)
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Create sample data to demonstrate the analysis pipeline.
Uses realistic but SYNTHETIC data for testing purposes.
"""

import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)  # Reproducible results


def create_sample_data():
    """Create realistic sample data for demonstration."""

    print("Creating sample data for pipeline demonstration...")

    # Load show list
    shows_df = pd.read_csv('raw/all_broadway_shows_2010_2025.csv')

    # Sample 50 shows for demonstration
    sample_shows = shows_df.sample(n=min(50, len(shows_df)), random_state=42)

    # Create synthetic producer counts
    # Realistic distribution: mean ~12, range 1-35
    producer_counts = np.random.gamma(shape=4, scale=3, size=len(sample_shows))
    producer_counts = np.clip(producer_counts, 1, 35).astype(int)

    # Lead producers: typically 1-5
    lead_producers = np.random.choice([1, 2, 3, 4, 5], size=len(sample_shows), p=[0.3, 0.3, 0.2, 0.15, 0.05])

    # Co-producers: the rest
    co_producers = producer_counts - lead_producers
    co_producers = np.maximum(co_producers, 0)  # Ensure non-negative

    # Create producer counts dataframe
    producer_df = sample_shows.copy()
    producer_df['ibdb_url'] = 'https://www.ibdb.com/broadway-production/sample-' + producer_df['show_id'].astype(str)
    producer_df['num_lead_producers'] = lead_producers
    producer_df['num_co_producers'] = co_producers
    producer_df['num_total_producers'] = producer_counts
    producer_df['scrape_status'] = 'sample_data'
    producer_df['scrape_notes'] = 'Synthetic data for demonstration'

    # Create Tony outcomes
    # Realistically, ~8-12% of shows win major Tonys
    tony_df = sample_shows.copy()

    # Simulate slight positive correlation with producer count (for demonstration)
    # More producers → slightly higher chance of win (but not strong)
    win_probability = 0.05 + 0.003 * producer_counts  # Base 5% + small boost
    win_probability = np.clip(win_probability, 0, 0.3)  # Cap at 30%

    tony_wins = np.random.binomial(1, win_probability)

    tony_df['tony_win'] = tony_wins
    tony_df['tony_category'] = np.where(
        tony_wins == 1,
        np.random.choice(['Best Musical', 'Best Play', 'Best Revival of a Musical', 'Best Revival of a Play'], len(tony_df)),
        None
    )
    tony_df['tony_year'] = np.where(
        tony_wins == 1,
        np.random.choice(range(2010, 2025), len(tony_df)),
        None
    )

    # Save files
    Path('data').mkdir(exist_ok=True)

    producer_path = 'data/show_producer_counts_manual.csv'
    tony_path = 'data/tony_outcomes_manual.csv'

    producer_df.to_csv(producer_path, index=False)
    tony_df.to_csv(tony_path, index=False)

    print(f"\n✓ Created sample producer data: {producer_path}")
    print(f"  - {len(producer_df)} shows")
    print(f"  - Mean producers: {producer_counts.mean():.1f}")
    print(f"  - Range: {producer_counts.min()} - {producer_counts.max()}")

    print(f"\n✓ Created sample Tony data: {tony_path}")
    print(f"  - {len(tony_df)} shows")
    print(f"  - Tony winners: {tony_wins.sum()} ({tony_wins.mean()*100:.1f}%)")
    print(f"  - Non-winners: {len(tony_df) - tony_wins.sum()}")

    print(f"\n" + "="*70)
    print("SAMPLE DATA CREATED - READY FOR ANALYSIS")
    print("="*70)
    print("\nThis is SYNTHETIC data for demonstration purposes only.")
    print("Replace with real data from manual collection for actual research.")
    print("\nTo run analysis with sample data:")
    print("  python3 analysis/producer_tony_analysis.py")


if __name__ == '__main__':
    create_sample_data()

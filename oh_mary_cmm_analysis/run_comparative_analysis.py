#!/usr/bin/env python3
"""
Comparative CMM Analysis for Multiple Broadway Shows
Analyzes and compares campaign effectiveness across shows.
"""

import yaml
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Import analysis modules
from src.analysis.discourse_extractor import DiscourseExtractor
from src.analysis.cmm_metrics import CMMMetricsCalculator


class ComparativeShowAnalysis:
    """Performs comparative CMM analysis across multiple Broadway shows."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize comparative analysis.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.shows = self.config.get('shows', {})
        self.data_dir = Path("data/raw")
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize analysis components
        self.discourse_extractor = DiscourseExtractor(self.config)
        self.cmm_calculator = CMMMetricsCalculator(self.config)

        print("🔧 Comparative Analysis initialized")
        print(f"  • Shows: {len(self.shows)}")

    def load_show_data(self, show_id: str) -> pd.DataFrame:
        """
        Load collected Reddit data for a show.

        Args:
            show_id: Show identifier

        Returns:
            DataFrame with show data
        """
        csv_path = self.data_dir / f"reddit_{show_id}.csv"

        if not csv_path.exists():
            print(f"⚠ No data found for {show_id} at {csv_path}")
            return pd.DataFrame()

        df = pd.read_csv(csv_path)
        print(f"  ✓ Loaded {len(df)} posts for {self.shows[show_id]['name']}")
        return df

    def process_show_discourse(self, df: pd.DataFrame, show_name: str) -> pd.DataFrame:
        """
        Process discourse features for a show's data.

        Args:
            df: DataFrame with show data
            show_name: Name of the show

        Returns:
            DataFrame with discourse features added
        """
        if df.empty:
            return df

        print(f"\n  🔍 Extracting discourse features for {show_name}...")

        # Combine title and text for analysis
        df['full_text'] = df['title'].fillna('') + ' ' + df['text'].fillna('')

        # Extract discourse features for each post
        discourse_features = []
        for idx, row in df.iterrows():
            features = self.discourse_extractor.extract_features(row['full_text'])
            discourse_features.append(features)

        # Add features to dataframe
        features_df = pd.DataFrame(discourse_features)
        df = pd.concat([df, features_df], axis=1)

        # Parse comments if available
        if 'comments_json' in df.columns:
            df['comments_parsed'] = df['comments_json'].apply(
                lambda x: json.loads(x) if pd.notna(x) and x != '' else []
            )
        else:
            df['comments_parsed'] = [[] for _ in range(len(df))]

        print(f"  ✓ Processed {len(df)} posts")
        return df

    def calculate_show_metrics(self, df: pd.DataFrame, show_name: str) -> Dict[str, Any]:
        """
        Calculate CMM metrics for a show.

        Args:
            df: DataFrame with processed show data
            show_name: Name of the show

        Returns:
            Dictionary with all CMM metrics
        """
        if df.empty:
            return self._empty_metrics(show_name)

        print(f"\n  📊 Calculating CMM metrics for {show_name}...")

        # Calculate engagement (use Reddit score)
        df['engagement'] = df['score'].fillna(0)

        # Identify collective voice posts
        df['collective_voice'] = df['collective_pronouns_count'] >= 2

        metrics = {}

        # Calculate all 8 CMM metrics
        try:
            metrics['mss'] = self.cmm_calculator.calculate_movement_sentiment_score(df)
            metrics['iri'] = self.cmm_calculator.calculate_identity_resonance_index(df)
            metrics['er'] = self.cmm_calculator.calculate_evangelism_ratio(df)
            metrics['ras'] = self.cmm_calculator.calculate_repeat_attendance_signal(df)
            metrics['bis'] = self.cmm_calculator.calculate_belonging_intensity_score(df)
            metrics['gim'] = self.cmm_calculator.calculate_gatekeeping_markers(df)
            metrics['cfs'] = self.cmm_calculator.calculate_community_formation(df)
            metrics['mpi'] = self.cmm_calculator.calculate_mimetic_propagation(df)

            # Calculate overall CMM score
            scores = [
                metrics['mss'].get('score', 0),
                metrics['iri'].get('score', 0),
                metrics['er'].get('score', 0),
                metrics['ras'].get('score', 0),
                metrics['bis'].get('score', 0),
                metrics['gim'].get('score', 0),
                metrics['cfs'].get('score', 0),
                metrics['mpi'].get('score', 0)
            ]
            metrics['overall_cmm'] = {
                'score': np.mean(scores),
                'min': min(scores),
                'max': max(scores),
                'std': np.std(scores)
            }

            print(f"  ✓ Overall CMM Score: {metrics['overall_cmm']['score']:.1f}/100")

        except Exception as e:
            print(f"  ⚠ Error calculating metrics: {e}")
            metrics = self._empty_metrics(show_name)

        metrics['show_name'] = show_name
        metrics['posts_analyzed'] = len(df)
        metrics['date_analyzed'] = datetime.now().isoformat()

        return metrics

    def _empty_metrics(self, show_name: str) -> Dict[str, Any]:
        """
        Return empty metrics structure for shows with no data.

        Args:
            show_name: Name of the show

        Returns:
            Dictionary with zeroed metrics
        """
        return {
            'show_name': show_name,
            'posts_analyzed': 0,
            'overall_cmm': {'score': 0, 'min': 0, 'max': 0, 'std': 0},
            'mss': {'score': 0},
            'iri': {'score': 0},
            'er': {'score': 0},
            'ras': {'score': 0},
            'bis': {'score': 0},
            'gim': {'score': 0},
            'cfs': {'score': 0},
            'mpi': {'score': 0}
        }

    def run_complete_analysis(self) -> Dict[str, Any]:
        """
        Run complete comparative analysis for all shows.

        Returns:
            Dictionary with results for all shows
        """
        print("\n" + "="*70)
        print("🎭 COMPARATIVE BROADWAY CMM ANALYSIS")
        print("="*70)

        results = {}

        # Process each show
        for show_id, show_config in self.shows.items():
            show_name = show_config['name']

            print(f"\n{'─'*70}")
            print(f"Processing: {show_name}")
            print(f"{'─'*70}")

            # Load data
            df = self.load_show_data(show_id)

            if df.empty:
                print(f"  ⚠ Skipping {show_name} - no data")
                results[show_id] = {
                    'show_name': show_name,
                    'data': df,
                    'metrics': self._empty_metrics(show_name)
                }
                continue

            # Process discourse
            df_processed = self.process_show_discourse(df, show_name)

            # Calculate metrics
            metrics = self.calculate_show_metrics(df_processed, show_name)

            # Store results
            results[show_id] = {
                'show_name': show_name,
                'data': df_processed,
                'metrics': metrics
            }

            # Save processed data
            processed_path = Path("data/processed") / f"{show_id}_processed.csv"
            processed_path.parent.mkdir(parents=True, exist_ok=True)
            df_processed.to_csv(processed_path, index=False)
            print(f"  💾 Saved processed data: {processed_path}")

        return results

    def generate_comparative_summary(self, results: Dict[str, Any]):
        """
        Generate comparative summary across all shows.

        Args:
            results: Dictionary with results for all shows
        """
        print("\n" + "="*70)
        print("📊 COMPARATIVE SUMMARY")
        print("="*70)

        # Create comparison table
        comparison = []
        for show_id, result in results.items():
            metrics = result['metrics']
            comparison.append({
                'Show': result['show_name'],
                'Posts': metrics.get('posts_analyzed', 0),
                'Overall CMM': round(metrics.get('overall_cmm', {}).get('score', 0), 1),
                'MSS': round(metrics.get('mss', {}).get('score', 0), 1),
                'IRI': round(metrics.get('iri', {}).get('score', 0), 1),
                'ER': round(metrics.get('er', {}).get('score', 0), 1),
                'RAS': round(metrics.get('ras', {}).get('score', 0), 1),
                'BIS': round(metrics.get('bis', {}).get('score', 0), 1),
                'GIM': round(metrics.get('gim', {}).get('score', 0), 1),
                'CFS': round(metrics.get('cfs', {}).get('score', 0), 1),
                'MPI': round(metrics.get('mpi', {}).get('score', 0), 1)
            })

        df_comparison = pd.DataFrame(comparison)
        df_comparison = df_comparison.sort_values('Overall CMM', ascending=False)

        print("\n" + df_comparison.to_string(index=False))

        # Determine most effective campaign
        if len(df_comparison) > 0 and df_comparison['Overall CMM'].max() > 0:
            winner = df_comparison.iloc[0]
            print(f"\n🏆 Most Effective Campaign: {winner['Show']}")
            print(f"   CMM Score: {winner['Overall CMM']:.1f}/100")
        else:
            print("\n⚠ Insufficient data to determine most effective campaign")

        # Save comparison
        comparison_path = self.output_dir / "comparative_summary.csv"
        df_comparison.to_csv(comparison_path, index=False)
        print(f"\n💾 Saved comparison: {comparison_path}")

        # Save detailed results
        results_path = self.output_dir / "detailed_results.json"

        # Prepare JSON-serializable results
        json_results = {}
        for show_id, result in results.items():
            json_results[show_id] = {
                'show_name': result['show_name'],
                'metrics': result['metrics']
                # Skip DataFrame as it's not JSON serializable
            }

        with open(results_path, 'w') as f:
            json.dump(json_results, f, indent=2, default=str)
        print(f"💾 Saved detailed results: {results_path}")


def main():
    """Main execution function."""
    print("\n" + "="*70)
    print("🎭 Multi-Show Comparative CMM Analysis")
    print("="*70)
    print("\nThis analysis will:")
    print("  1. Load Reddit data for all shows")
    print("  2. Extract movement discourse features")
    print("  3. Calculate CMM metrics for each show")
    print("  4. Compare campaign effectiveness")
    print("  5. Generate visualizations and reports")

    # Initialize and run analysis
    analyzer = ComparativeShowAnalysis()
    results = analyzer.run_complete_analysis()
    analyzer.generate_comparative_summary(results)

    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE")
    print("="*70)
    print("\n📁 Outputs:")
    print("  • Comparative summary: outputs/comparative_summary.csv")
    print("  • Detailed results: outputs/detailed_results.json")
    print("  • Processed data: data/processed/")

    print("\n🚀 Next steps:")
    print("  1. Review outputs/comparative_summary.csv")
    print("  2. Check detailed metrics in outputs/detailed_results.json")
    print("  3. Run visualization script (coming next)")


if __name__ == "__main__":
    main()

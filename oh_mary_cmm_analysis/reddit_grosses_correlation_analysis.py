#!/usr/bin/env python3
"""
Reddit Engagement vs Box Office Correlation Analysis
Analyzes relationship between social media buzz and financial success.
"""

import pandas as pd
import numpy as np
import yaml
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr, spearmanr


class RedditGrossesCorrelationAnalysis:
    """Correlates Reddit engagement with Broadway box office grosses."""

    def __init__(self):
        """Initialize analysis."""
        self.data_dir = Path("data")
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load config
        with open("config/config.yaml", "r") as f:
            self.config = yaml.safe_load(f)

    def load_reddit_data(self) -> Dict[str, pd.DataFrame]:
        """Load Reddit data for all shows."""
        reddit_data = {}
        raw_dir = self.data_dir / "raw"

        if not raw_dir.exists():
            print("⚠️  No Reddit data found. Run multi_show_reddit_scraper.py first.")
            return reddit_data

        for csv_file in raw_dir.glob("reddit_*.csv"):
            # Extract show identifier from filename
            # e.g., reddit_oh_mary.csv -> oh_mary
            show_id = csv_file.stem.replace('reddit_', '')

            df = pd.read_csv(csv_file)
            if not df.empty:
                # Parse dates
                df['created_utc'] = pd.to_datetime(df['created_utc'])
                df['week_ending'] = df['created_utc'].apply(
                    lambda x: x + timedelta(days=(6 - x.weekday()))
                )
                reddit_data[show_id] = df

        return reddit_data

    def load_grosses_data(self) -> pd.DataFrame:
        """Load Broadway grosses data."""
        grosses_file = self.data_dir / "grosses" / "broadway_grosses_2024_2025.csv"

        if not grosses_file.exists():
            print("⚠️  No grosses data found. Run broadway_grosses_scraper.py first.")
            return pd.DataFrame()

        df = pd.read_csv(grosses_file)
        df['week_ending'] = pd.to_datetime(df['week_ending'])
        return df

    def calculate_weekly_reddit_metrics(self, reddit_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate Reddit data by week."""
        weekly = reddit_df.groupby('week_ending').agg({
            'score': ['sum', 'mean', 'max'],
            'num_comments': ['sum', 'mean'],
            'upvote_ratio': 'mean',
            'id': 'count',  # post count
            'subreddit': 'nunique',  # subreddit diversity
            'author': 'nunique'  # unique contributors
        }).reset_index()

        # Flatten column names
        weekly.columns = [
            'week_ending',
            'total_upvotes',
            'avg_upvotes',
            'max_upvotes',
            'total_comments',
            'avg_comments',
            'avg_upvote_ratio',
            'post_count',
            'subreddit_diversity',
            'unique_contributors'
        ]

        # Calculate engagement metrics
        weekly['total_engagement'] = weekly['total_upvotes'] + weekly['total_comments']
        weekly['viral_score'] = weekly['max_upvotes'] * weekly['subreddit_diversity']

        return weekly

    def merge_reddit_and_grosses(
        self,
        reddit_data: Dict[str, pd.DataFrame],
        grosses_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge Reddit and grosses data by show and week."""
        merged_data = []

        for show_id, reddit_df in reddit_data.items():
            # Get weekly Reddit metrics
            weekly_reddit = self.calculate_weekly_reddit_metrics(reddit_df)

            # Get grosses for this show
            show_grosses = grosses_df[grosses_df['show_id'] == show_id].copy()

            if show_grosses.empty:
                print(f"  ⚠️  No grosses data for {show_id}")
                continue

            # Merge on week_ending
            merged = pd.merge(
                show_grosses,
                weekly_reddit,
                on='week_ending',
                how='outer'
            )

            merged['show_id'] = show_id
            merged['show_name'] = self.config['shows'][show_id]['name']
            merged['show_type'] = self.config['shows'][show_id].get('show_type', 'unknown')

            merged_data.append(merged)

        if not merged_data:
            return pd.DataFrame()

        combined = pd.concat(merged_data, ignore_index=True)

        # Fill missing values
        combined['post_count'] = combined['post_count'].fillna(0)
        combined['total_upvotes'] = combined['total_upvotes'].fillna(0)
        combined['total_engagement'] = combined['total_engagement'].fillna(0)

        return combined

    def calculate_correlations(self, merged_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate correlations between Reddit metrics and box office."""
        if merged_df.empty:
            return {}

        # Filter to weeks where we have both Reddit and grosses data
        complete_data = merged_df.dropna(subset=['gross', 'total_upvotes'])

        if len(complete_data) < 10:
            print("⚠️  Not enough overlapping data for correlation analysis")
            return {}

        reddit_metrics = [
            'total_upvotes',
            'avg_upvotes',
            'max_upvotes',
            'total_comments',
            'avg_comments',
            'post_count',
            'subreddit_diversity',
            'unique_contributors',
            'total_engagement',
            'viral_score'
        ]

        box_office_metrics = [
            'gross',
            'capacity_percent',
            'avg_ticket_price'
        ]

        correlations = {}

        for reddit_metric in reddit_metrics:
            for bo_metric in box_office_metrics:
                # Remove rows where either metric is missing
                valid_data = complete_data[[reddit_metric, bo_metric]].dropna()

                if len(valid_data) < 10:
                    continue

                # Calculate Pearson correlation
                try:
                    pearson_r, pearson_p = pearsonr(
                        valid_data[reddit_metric],
                        valid_data[bo_metric]
                    )

                    # Calculate Spearman (rank) correlation
                    spearman_r, spearman_p = spearmanr(
                        valid_data[reddit_metric],
                        valid_data[bo_metric]
                    )

                    correlations[f"{reddit_metric}_vs_{bo_metric}"] = {
                        'pearson_r': round(pearson_r, 3),
                        'pearson_p': round(pearson_p, 4),
                        'spearman_r': round(spearman_r, 3),
                        'spearman_p': round(spearman_p, 4),
                        'n_samples': len(valid_data),
                        'significant': pearson_p < 0.05
                    }
                except Exception as e:
                    print(f"  ⚠️  Error calculating {reddit_metric} vs {bo_metric}: {e}")

        return correlations

    def analyze_by_show_type(self, merged_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze patterns by show type (original play, musical, revival, etc.)."""
        if merged_df.empty:
            return {}

        results = {}

        for show_type in ['original_play', 'original_musical', 'play_revival', 'musical_revival']:
            type_data = merged_df[merged_df['show_type'] == show_type]

            if type_data.empty:
                continue

            # Aggregate metrics
            results[show_type] = {
                'shows_count': type_data['show_id'].nunique(),
                'avg_weekly_gross': type_data['gross'].mean(),
                'avg_capacity': type_data['capacity_percent'].mean(),
                'avg_reddit_engagement': type_data['total_engagement'].mean(),
                'avg_posts_per_week': type_data['post_count'].mean(),
                'total_reddit_posts': type_data['post_count'].sum()
            }

        return results

    def identify_outliers(self, merged_df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """Identify shows that over/under-perform relative to Reddit buzz."""
        if merged_df.empty:
            return {}

        # Calculate show-level aggregates
        show_summary = merged_df.groupby('show_id').agg({
            'gross': 'mean',
            'capacity_percent': 'mean',
            'total_engagement': 'sum',
            'post_count': 'sum'
        }).reset_index()

        show_summary['show_name'] = show_summary['show_id'].map(
            lambda x: self.config['shows'][x]['name']
        )

        # Remove shows with no data
        show_summary = show_summary.dropna(subset=['gross', 'total_engagement'])

        if show_summary.empty:
            return {}

        # Normalize metrics (0-100 scale)
        show_summary['gross_normalized'] = (
            (show_summary['gross'] - show_summary['gross'].min()) /
            (show_summary['gross'].max() - show_summary['gross'].min()) * 100
        )

        show_summary['engagement_normalized'] = (
            (show_summary['total_engagement'] - show_summary['total_engagement'].min()) /
            (show_summary['total_engagement'].max() - show_summary['total_engagement'].min()) * 100
        )

        # Calculate over/under performance
        show_summary['performance_gap'] = (
            show_summary['gross_normalized'] - show_summary['engagement_normalized']
        )

        # Identify outliers
        overperformers = show_summary.nlargest(5, 'performance_gap')[
            ['show_name', 'gross', 'capacity_percent', 'total_engagement', 'performance_gap']
        ].to_dict('records')

        underperformers = show_summary.nsmallest(5, 'performance_gap')[
            ['show_name', 'gross', 'capacity_percent', 'total_engagement', 'performance_gap']
        ].to_dict('records')

        return {
            'overperformers': overperformers,  # High grosses, low Reddit buzz
            'underperformers': underperformers  # High Reddit buzz, low grosses
        }

    def generate_visualizations(self, merged_df: pd.DataFrame):
        """Generate correlation visualizations."""
        if merged_df.empty:
            return

        # Set style
        sns.set_style("whitegrid")

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Reddit Engagement vs Box Office Performance', fontsize=16)

        # Complete data only
        complete = merged_df.dropna(subset=['gross', 'total_engagement'])

        if complete.empty:
            print("⚠️  Not enough data for visualizations")
            return

        # 1. Total Engagement vs Gross
        axes[0, 0].scatter(complete['total_engagement'], complete['gross'], alpha=0.6)
        axes[0, 0].set_xlabel('Total Reddit Engagement (upvotes + comments)')
        axes[0, 0].set_ylabel('Weekly Gross ($)')
        axes[0, 0].set_title('Reddit Engagement vs Box Office Gross')

        # 2. Post Count vs Capacity
        complete_cap = complete.dropna(subset=['capacity_percent'])
        if not complete_cap.empty:
            axes[0, 1].scatter(complete_cap['post_count'], complete_cap['capacity_percent'], alpha=0.6)
            axes[0, 1].set_xlabel('Reddit Posts per Week')
            axes[0, 1].set_ylabel('Capacity %')
            axes[0, 1].set_title('Reddit Activity vs Theater Capacity')

        # 3. Viral Score vs Gross
        complete_viral = complete.dropna(subset=['viral_score'])
        if not complete_viral.empty:
            axes[1, 0].scatter(complete_viral['viral_score'], complete_viral['gross'], alpha=0.6)
            axes[1, 0].set_xlabel('Viral Score (max upvotes × subreddit diversity)')
            axes[1, 0].set_ylabel('Weekly Gross ($)')
            axes[1, 0].set_title('Viral Content vs Box Office')

        # 4. Box plot by show type
        axes[1, 1].boxplot(
            [complete[complete['show_type'] == st]['gross'].dropna()
             for st in ['original_play', 'original_musical', 'play_revival', 'musical_revival']
             if not complete[complete['show_type'] == st].empty],
            labels=['Original\nPlay', 'Original\nMusical', 'Play\nRevival', 'Musical\nRevival']
        )
        axes[1, 1].set_ylabel('Weekly Gross ($)')
        axes[1, 1].set_title('Box Office by Show Type')

        plt.tight_layout()

        # Save figure
        viz_path = self.output_dir / "reddit_grosses_correlation.png"
        plt.savefig(viz_path, dpi=300, bbox_inches='tight')
        print(f"📊 Saved visualization: {viz_path}")
        plt.close()

    def generate_report(
        self,
        merged_df: pd.DataFrame,
        correlations: Dict,
        show_type_analysis: Dict,
        outliers: Dict
    ):
        """Generate comprehensive markdown report."""
        report_path = self.output_dir / "reddit_grosses_correlation_report.md"

        with open(report_path, 'w') as f:
            f.write("# Reddit Engagement vs Box Office Correlation Analysis\n\n")
            f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d')}\n\n")

            # Overview
            f.write("## Overview\n\n")
            f.write("This analysis examines the relationship between Reddit fan engagement ")
            f.write("and Broadway box office performance for the 2024-2025 Tony season.\n\n")

            if not merged_df.empty:
                f.write(f"- **Shows analyzed:** {merged_df['show_id'].nunique()}\n")
                f.write(f"- **Total weeks tracked:** {len(merged_df)}\n")
                complete = merged_df.dropna(subset=['gross', 'total_engagement'])
                f.write(f"- **Weeks with both Reddit + grosses data:** {len(complete)}\n\n")

            # Key Correlations
            f.write("## Key Correlations\n\n")
            f.write("Correlation between Reddit metrics and box office performance:\n\n")

            if correlations:
                # Sort by absolute Pearson correlation
                sorted_corr = sorted(
                    correlations.items(),
                    key=lambda x: abs(x[1]['pearson_r']),
                    reverse=True
                )

                f.write("| Reddit Metric | Box Office Metric | Correlation (r) | P-Value | Significant? |\n")
                f.write("|--------------|-------------------|-----------------|---------|-------------|\n")

                for metric_pair, stats in sorted_corr[:15]:  # Top 15
                    parts = metric_pair.split('_vs_')
                    reddit_metric = parts[0].replace('_', ' ').title()
                    bo_metric = parts[1].replace('_', ' ').title()

                    sig = "✅ Yes" if stats['significant'] else "No"

                    f.write(f"| {reddit_metric} | {bo_metric} | {stats['pearson_r']:.3f} | "
                           f"{stats['pearson_p']:.4f} | {sig} |\n")

                f.write("\n")
            else:
                f.write("*No correlation data available*\n\n")

            # Analysis by Show Type
            f.write("## Analysis by Show Type\n\n")

            if show_type_analysis:
                f.write("| Show Type | Shows | Avg Weekly Gross | Avg Capacity % | Avg Reddit Engagement |\n")
                f.write("|-----------|-------|------------------|----------------|----------------------|\n")

                for show_type, metrics in show_type_analysis.items():
                    type_name = show_type.replace('_', ' ').title()
                    f.write(f"| {type_name} | {metrics['shows_count']} | "
                           f"${metrics['avg_weekly_gross']:,.0f} | "
                           f"{metrics['avg_capacity']:.1f}% | "
                           f"{metrics['avg_reddit_engagement']:.0f} |\n")

                f.write("\n")

            # Outliers
            f.write("## Performance Outliers\n\n")

            if outliers:
                f.write("### Overperformers (High Grosses, Low Reddit Buzz)\n\n")
                f.write("Shows that are financially successful despite lower social media engagement:\n\n")

                for show in outliers.get('overperformers', []):
                    f.write(f"- **{show['show_name']}**: ${show['gross']:,.0f} avg gross, "
                           f"{show['capacity_percent']:.1f}% capacity, "
                           f"{show['total_engagement']:.0f} total Reddit engagement\n")

                f.write("\n### Underperformers (High Reddit Buzz, Lower Grosses)\n\n")
                f.write("Shows generating significant online discussion but lower box office:\n\n")

                for show in outliers.get('underperformers', []):
                    f.write(f"- **{show['show_name']}**: ${show['gross']:,.0f} avg gross, "
                           f"{show['capacity_percent']:.1f}% capacity, "
                           f"{show['total_engagement']:.0f} total Reddit engagement\n")

                f.write("\n")

            # Key Insights
            f.write("## Key Insights\n\n")
            f.write("### What the data tells us:\n\n")

            if correlations:
                # Find strongest correlation
                strongest = max(correlations.items(), key=lambda x: abs(x[1]['pearson_r']))
                metric_pair = strongest[0]
                stats = strongest[1]

                f.write(f"1. **Strongest correlation:** {metric_pair.replace('_', ' ')} "
                       f"(r={stats['pearson_r']:.3f}, p={stats['pearson_p']:.4f})\n")

                # Count significant correlations
                sig_count = sum(1 for c in correlations.values() if c['significant'])
                f.write(f"2. **Significant correlations:** {sig_count} out of {len(correlations)} "
                       f"metric pairs show statistical significance (p < 0.05)\n")

            f.write("\n### Actionable Recommendations:\n\n")
            f.write("- Monitor Reddit engagement as an early indicator of audience interest\n")
            f.write("- Track viral content (high upvotes + cross-subreddit sharing) as it may predict capacity\n")
            f.write("- Investigate overperformers to understand success factors beyond social media\n")
            f.write("- Engage with underperformers' online communities to convert buzz into ticket sales\n\n")

        print(f"📄 Saved report: {report_path}")

    def run_analysis(self):
        """Run complete correlation analysis."""
        print("\n" + "="*70)
        print("📊 REDDIT ENGAGEMENT vs BOX OFFICE CORRELATION ANALYSIS")
        print("="*70)

        # Load data
        print("\n🔄 Loading data...")
        reddit_data = self.load_reddit_data()
        print(f"  ✓ Loaded Reddit data for {len(reddit_data)} shows")

        grosses_df = self.load_grosses_data()
        print(f"  ✓ Loaded grosses data: {len(grosses_df)} records")

        if not reddit_data or grosses_df.empty:
            print("\n❌ Insufficient data. Please run data collection scripts first:")
            print("  1. multi_show_reddit_scraper.py")
            print("  2. broadway_grosses_scraper.py")
            return

        # Merge datasets
        print("\n🔗 Merging Reddit and grosses data...")
        merged_df = self.merge_reddit_and_grosses(reddit_data, grosses_df)

        if merged_df.empty:
            print("❌ No overlapping data found")
            return

        print(f"  ✓ Merged data: {len(merged_df)} week-show combinations")

        # Save merged data
        merged_path = self.output_dir / "merged_reddit_grosses.csv"
        merged_df.to_csv(merged_path, index=False)
        print(f"  💾 Saved: {merged_path}")

        # Calculate correlations
        print("\n📈 Calculating correlations...")
        correlations = self.calculate_correlations(merged_df)
        print(f"  ✓ Calculated {len(correlations)} correlation pairs")

        # Analyze by show type
        print("\n🎭 Analyzing by show type...")
        show_type_analysis = self.analyze_by_show_type(merged_df)

        # Identify outliers
        print("\n🔍 Identifying performance outliers...")
        outliers = self.identify_outliers(merged_df)

        # Generate visualizations
        print("\n📊 Generating visualizations...")
        self.generate_visualizations(merged_df)

        # Generate report
        print("\n📝 Generating report...")
        self.generate_report(merged_df, correlations, show_type_analysis, outliers)

        # Save raw analysis data
        analysis_data = {
            'correlations': correlations,
            'show_type_analysis': show_type_analysis,
            'outliers': outliers,
            'analysis_date': datetime.now().isoformat()
        }

        json_path = self.output_dir / "correlation_analysis_data.json"
        with open(json_path, 'w') as f:
            json.dump(analysis_data, f, indent=2, default=str)
        print(f"  💾 Saved: {json_path}")

        print("\n" + "="*70)
        print("✅ CORRELATION ANALYSIS COMPLETE")
        print("="*70)
        print("\n📁 Results saved to:")
        print("  • outputs/merged_reddit_grosses.csv - Combined dataset")
        print("  • outputs/reddit_grosses_correlation_report.md - Full analysis report")
        print("  • outputs/reddit_grosses_correlation.png - Visualizations")
        print("  • outputs/correlation_analysis_data.json - Raw analysis data")


def main():
    """Main execution."""
    analyzer = RedditGrossesCorrelationAnalysis()
    analyzer.run_analysis()


if __name__ == "__main__":
    main()

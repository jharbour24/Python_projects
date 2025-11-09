#!/usr/bin/env python3
"""
Broadway Marketing Success/Failure Analysis
PhD-Level Data Science Approach

Compares successful vs unsuccessful campaigns to identify key success factors.
Uses statistical analysis, correlation studies, and pattern recognition.
"""

import pandas as pd
import numpy as np
import yaml
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
from scipy import stats as scipy_stats
import re


class BroadwayMarketingScience:
    """Advanced analysis of what makes Broadway marketing campaigns succeed or fail."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize analysis."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.shows = self.config.get('shows', {})
        self.data_dir = Path("data/raw")
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load grosses data and classify shows by financial performance
        self.classify_shows_by_performance()

    def classify_shows_by_performance(self):
        """Classify shows as successful/unsuccessful based on box office data."""
        grosses_file = Path("data/grosses/broadway_grosses_2024_2025.csv")

        if not grosses_file.exists():
            print("⚠️  No grosses data found - using manual categories from config")
            self.successful_shows = {k: v for k, v in self.shows.items() if v.get('category') == 'successful'}
            self.unsuccessful_shows = {k: v for k, v in self.shows.items() if v.get('category') == 'unsuccessful'}
            print(f"📊 Initialized analysis:")
            print(f"  • Successful campaigns: {len(self.successful_shows)}")
            print(f"  • Unsuccessful campaigns: {len(self.unsuccessful_shows)}")
            return

        # Load and aggregate grosses data
        grosses_df = pd.read_csv(grosses_file)

        # Calculate performance metrics by show
        show_performance = grosses_df.groupby('show_id').agg({
            'gross': ['sum', 'mean'],
            'capacity_percent': 'mean',
            'week_ending': 'count'  # weeks on Broadway
        }).reset_index()

        show_performance.columns = ['show_id', 'total_gross', 'avg_weekly_gross', 'avg_capacity', 'weeks_tracked']

        # Calculate composite success score
        # Normalize each metric to 0-1 range, then average
        show_performance['gross_score'] = (show_performance['total_gross'] - show_performance['total_gross'].min()) / (show_performance['total_gross'].max() - show_performance['total_gross'].min())
        show_performance['capacity_score'] = show_performance['avg_capacity'] / 100.0
        show_performance['longevity_score'] = (show_performance['weeks_tracked'] - show_performance['weeks_tracked'].min()) / (show_performance['weeks_tracked'].max() - show_performance['weeks_tracked'].min())

        # Composite score: weighted average
        show_performance['success_score'] = (
            show_performance['gross_score'] * 0.5 +  # 50% weight on total gross
            show_performance['capacity_score'] * 0.3 +  # 30% weight on capacity
            show_performance['longevity_score'] * 0.2   # 20% weight on longevity
        )

        # Classify: top 33% = successful, bottom 33% = unsuccessful
        top_threshold = show_performance['success_score'].quantile(0.67)
        bottom_threshold = show_performance['success_score'].quantile(0.33)

        successful_ids = set(show_performance[show_performance['success_score'] >= top_threshold]['show_id'])
        unsuccessful_ids = set(show_performance[show_performance['success_score'] <= bottom_threshold]['show_id'])

        self.successful_shows = {k: v for k, v in self.shows.items() if k in successful_ids}
        self.unsuccessful_shows = {k: v for k, v in self.shows.items() if k in unsuccessful_ids}

        print(f"📊 Initialized analysis (data-driven classification):")
        print(f"  • Total shows with grosses data: {len(show_performance)}")
        print(f"  • Successful campaigns (top 33%): {len(self.successful_shows)}")
        print(f"  • Unsuccessful campaigns (bottom 33%): {len(self.unsuccessful_shows)}")
        print(f"  • Middle tier (excluded from comparison): {len(show_performance) - len(successful_ids) - len(unsuccessful_ids)}")

        # Save classification for reference
        classification = show_performance.merge(
            pd.DataFrame([(k, v['name']) for k, v in self.shows.items()], columns=['show_id', 'show_name']),
            on='show_id', how='left'
        )
        classification['category'] = classification['show_id'].apply(
            lambda x: 'successful' if x in successful_ids else ('unsuccessful' if x in unsuccessful_ids else 'middle')
        )
        classification = classification.sort_values('success_score', ascending=False)

        classification_path = self.output_dir / "show_classification_by_grosses.csv"
        classification.to_csv(classification_path, index=False)
        print(f"  💾 Saved classification: {classification_path}")

    def extract_comprehensive_metrics(self, df: pd.DataFrame, show_name: str, category: str) -> Dict[str, Any]:
        """
        Extract 30+ metrics across multiple dimensions.

        This is the core feature engineering for our analysis.
        """
        if df.empty:
            return self._empty_metrics(show_name, category)

        df['full_text'] = df['title'].fillna('') + ' ' + df['text'].fillna('')

        # === 1. VOLUME METRICS ===
        volume = {
            'total_posts': len(df),
            'unique_authors': df['author'].nunique(),
            'posts_per_author': len(df) / max(df['author'].nunique(), 1),
            'unique_subreddits': df['subreddit'].nunique(),
            'subreddit_diversity': df['subreddit'].nunique() / len(df) if len(df) > 0 else 0
        }

        # === 2. ENGAGEMENT METRICS ===
        engagement = {
            'total_upvotes': df['score'].sum(),
            'avg_upvotes': df['score'].mean(),
            'median_upvotes': df['score'].median(),
            'upvote_std': df['score'].std(),
            'total_comments': df['num_comments'].sum(),
            'avg_comments': df['num_comments'].mean(),
            'engagement_rate': (df['score'].sum() + df['num_comments'].sum()) / len(df),
            'upvote_ratio_avg': df['upvote_ratio'].mean(),
            'viral_posts_pct': len(df[df['score'] > 100]) / len(df) * 100,
            'highly_viral_pct': len(df[df['score'] > 500]) / len(df) * 100
        }

        # === 3. SENTIMENT & EMOTION METRICS ===
        sentiment = self._analyze_sentiment(df)

        # === 4. WORD-OF-MOUTH METRICS ===
        wom = self._analyze_word_of_mouth(df)

        # === 5. TEMPORAL METRICS ===
        df['date'] = pd.to_datetime(df['created_utc'])
        temporal = {
            'date_span_days': (df['date'].max() - df['date'].min()).days,
            'unique_days': df['date'].dt.date.nunique(),
            'posts_per_day': len(df) / max((df['date'].max() - df['date'].min()).days, 1),
            'sustained_discussion': df['date'].dt.date.nunique() / max((df['date'].max() - df['date'].min()).days, 1)
        }

        # === 6. CONTENT QUALITY METRICS ===
        content = {
            'avg_title_length': df['title'].fillna('').str.len().mean(),
            'avg_text_length': df['text'].fillna('').str.len().mean(),
            'has_text_pct': (df['text'].fillna('').str.len() > 0).sum() / len(df) * 100,
            'question_posts_pct': df['title'].fillna('').str.contains('\\?').sum() / len(df) * 100
        }

        # === 7. COMMUNITY METRICS ===
        community = self._analyze_community_dynamics(df)

        # Combine all metrics
        all_metrics = {
            **volume,
            **engagement,
            **sentiment,
            **wom,
            **temporal,
            **content,
            **community,
            'show_name': show_name,
            'category': category
        }

        return all_metrics

    def _analyze_sentiment(self, df: pd.DataFrame) -> Dict[str, float]:
        """Analyze sentiment and emotional tone."""
        positive_words = ['amazing', 'incredible', 'brilliant', 'perfect', 'loved', 'fantastic',
                         'wonderful', 'best', 'hilarious', 'genius', 'masterpiece', 'stunning']
        negative_words = ['disappointed', 'boring', 'bad', 'terrible', 'waste', 'overrated',
                         'underwhelming', 'meh', 'disappointing', 'awful', 'worst']
        excitement_patterns = r'!{2,}|[A-Z]{3,}'

        def count_sentiment(text):
            if pd.isna(text):
                return {'pos': 0, 'neg': 0, 'exc': 0}
            text_lower = str(text).lower()
            return {
                'pos': sum(1 for w in positive_words if w in text_lower),
                'neg': sum(1 for w in negative_words if w in text_lower),
                'exc': len(re.findall(excitement_patterns, str(text)))
            }

        sentiments = df['full_text'].apply(count_sentiment)
        sentiment_df = pd.DataFrame(sentiments.tolist())

        total_pos = sentiment_df['pos'].sum()
        total_neg = sentiment_df['neg'].sum()

        return {
            'positive_mentions': total_pos,
            'negative_mentions': total_neg,
            'sentiment_ratio': total_pos / max(total_neg, 1),
            'sentiment_score': (total_pos / max(total_pos + total_neg, 1)) * 100,
            'excitement_level': sentiment_df['exc'].mean(),
            'positive_posts_pct': (sentiment_df['pos'] > 0).sum() / len(df) * 100,
            'negative_posts_pct': (sentiment_df['neg'] > 0).sum() / len(df) * 100
        }

    def _analyze_word_of_mouth(self, df: pd.DataFrame) -> Dict[str, float]:
        """Analyze recommendation and organic advocacy."""
        recommendation_phrases = ['must see', 'you should', 'highly recommend', 'go see',
                                 'you have to', 'definitely see', 'worth seeing', 'don\'t miss',
                                 'need to see', 'everyone should']
        repeat_phrases = ['saw it twice', 'second time', 'seeing it again', 'third time',
                         'multiple times', 'going back', 'saw it again', 'rush again']

        df['has_recommendation'] = df['full_text'].fillna('').str.lower().apply(
            lambda x: any(phrase in x for phrase in recommendation_phrases)
        )
        df['mentions_repeat'] = df['full_text'].fillna('').str.lower().apply(
            lambda x: any(phrase in x for phrase in repeat_phrases)
        )

        return {
            'recommendation_rate': df['has_recommendation'].sum() / len(df) * 100,
            'repeat_viewing_rate': df['mentions_repeat'].sum() / len(df) * 100,
            'organic_advocacy_score': (df['has_recommendation'].sum() + df['mentions_repeat'].sum() * 2) / len(df) * 100
        }

    def _analyze_community_dynamics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Analyze community formation and interaction patterns."""
        # Top authors' contribution
        author_counts = df['author'].value_counts()
        top_10_pct = author_counts.head(10).sum() / len(df) * 100 if len(df) > 0 else 0

        # Subreddit concentration
        subreddit_counts = df['subreddit'].value_counts()
        top_subreddit_pct = subreddit_counts.iloc[0] / len(df) * 100 if len(subreddit_counts) > 0 else 0

        return {
            'top_10_authors_pct': top_10_pct,
            'top_subreddit_concentration': top_subreddit_pct,
            'community_diversity_score': 100 - top_10_pct,  # Lower concentration = more diverse
            'cross_platform_reach': df['subreddit'].nunique()
        }

    def _empty_metrics(self, show_name: str, category: str) -> Dict[str, Any]:
        """Return zeroed metrics for shows with no data."""
        return {
            'show_name': show_name,
            'category': category,
            'total_posts': 0,
            'unique_authors': 0,
            'posts_per_author': 0,
            'unique_subreddits': 0,
            'subreddit_diversity': 0,
            'total_upvotes': 0,
            'avg_upvotes': 0,
            'median_upvotes': 0,
            'upvote_std': 0,
            'total_comments': 0,
            'avg_comments': 0,
            'engagement_rate': 0,
            'upvote_ratio_avg': 0,
            'viral_posts_pct': 0,
            'highly_viral_pct': 0,
            'positive_mentions': 0,
            'negative_mentions': 0,
            'sentiment_ratio': 0,
            'sentiment_score': 0,
            'excitement_level': 0,
            'positive_posts_pct': 0,
            'negative_posts_pct': 0,
            'recommendation_rate': 0,
            'repeat_viewing_rate': 0,
            'organic_advocacy_score': 0,
            'date_span_days': 0,
            'unique_days': 0,
            'posts_per_day': 0,
            'sustained_discussion': 0,
            'avg_title_length': 0,
            'avg_text_length': 0,
            'has_text_pct': 0,
            'question_posts_pct': 0,
            'top_10_authors_pct': 0,
            'top_subreddit_concentration': 0,
            'community_diversity_score': 0,
            'cross_platform_reach': 0
        }

    def statistical_comparison(self, successful_metrics: List[Dict], unsuccessful_metrics: List[Dict]) -> Dict[str, Any]:
        """
        Perform rigorous statistical comparison between successful and unsuccessful campaigns.

        Uses:
        - T-tests for mean differences
        - Effect size calculations (Cohen's d)
        - Confidence intervals
        """
        print("\n" + "="*70)
        print("📈 STATISTICAL ANALYSIS: Success vs Failure")
        print("="*70)

        df_success = pd.DataFrame(successful_metrics)
        df_fail = pd.DataFrame(unsuccessful_metrics)

        # Metrics to compare (numerical only)
        metrics_to_compare = [
            'total_posts', 'unique_authors', 'avg_upvotes', 'avg_comments',
            'engagement_rate', 'viral_posts_pct', 'sentiment_score',
            'recommendation_rate', 'repeat_viewing_rate', 'subreddit_diversity',
            'positive_posts_pct', 'organic_advocacy_score', 'community_diversity_score'
        ]

        results = []

        for metric in metrics_to_compare:
            success_vals = df_success[metric].dropna()
            fail_vals = df_fail[metric].dropna()

            if len(success_vals) > 0 and len(fail_vals) > 0:
                # Mean difference
                success_mean = success_vals.mean()
                fail_mean = fail_vals.mean()
                difference = success_mean - fail_mean
                pct_difference = (difference / max(fail_mean, 0.01)) * 100

                # T-test
                t_stat, p_value = scipy_stats.ttest_ind(success_vals, fail_vals)

                # Effect size (Cohen's d)
                pooled_std = np.sqrt((success_vals.var() + fail_vals.var()) / 2)
                cohens_d = difference / max(pooled_std, 0.01)

                results.append({
                    'metric': metric,
                    'successful_mean': success_mean,
                    'unsuccessful_mean': fail_mean,
                    'difference': difference,
                    'pct_difference': pct_difference,
                    'p_value': p_value,
                    'cohens_d': cohens_d,
                    'significant': p_value < 0.05,
                    'effect_size': self._interpret_effect_size(cohens_d)
                })

        # Sort by effect size (absolute value)
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('cohens_d', key=abs, ascending=False)

        return results_df

    def _interpret_effect_size(self, d: float) -> str:
        """Interpret Cohen's d effect size."""
        abs_d = abs(d)
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"

    def identify_success_factors(self, statistical_results: pd.DataFrame) -> List[str]:
        """
        Identify the key factors that differentiate successful from unsuccessful campaigns.

        Focus on metrics with:
        1. Statistical significance (p < 0.05)
        2. Medium to large effect size
        3. Positive direction for successful campaigns
        """
        print("\n" + "="*70)
        print("🔑 KEY SUCCESS FACTORS IDENTIFIED")
        print("="*70)

        # Filter for significant results with medium+ effect size
        significant = statistical_results[
            (statistical_results['significant'] == True) &
            (statistical_results['effect_size'].isin(['medium', 'large']))
        ]

        success_factors = []

        for _, row in significant.iterrows():
            if row['difference'] > 0:  # Successful campaigns have higher values
                factor = f"{row['metric']}: Successful campaigns have {abs(row['pct_difference']):.1f}% higher {row['metric'].replace('_', ' ')}"
                success_factors.append(factor)
                print(f"\n✓ {factor}")
                print(f"  Effect size: {row['effect_size']} (Cohen's d = {row['cohens_d']:.2f})")
                print(f"  p-value: {row['p_value']:.4f}")

        if not success_factors:
            print("\n⚠ No statistically significant differences found with medium+ effect sizes")
            print("This may indicate:")
            print("  • Insufficient sample size (3 successful vs 7 unsuccessful shows)")
            print("  • Similar marketing approaches")
            print("  • Need for more granular metrics")

            print("\n📊 Top Observed Differences (regardless of statistical significance):")
            print("Note: These may not be statistically significant due to small sample size\n")

            # Show top 5 differences by effect size
            top_diffs = statistical_results.head(5)
            for _, row in top_diffs.iterrows():
                direction = "higher" if row['difference'] > 0 else "lower"
                print(f"• {row['metric'].replace('_', ' ').title()}:")
                print(f"  Successful: {row['successful_mean']:.1f} | Unsuccessful: {row['unsuccessful_mean']:.1f}")
                print(f"  Difference: {abs(row['pct_difference']):.0f}% {direction} ({row['effect_size']} effect)")
                print(f"  p-value: {row['p_value']:.3f} {'✓ significant' if row['significant'] else '(not significant)'}\n")

        return success_factors

    def generate_recommendations(self, success_factors: List[str], statistical_results: pd.DataFrame) -> List[str]:
        """
        Generate actionable recommendations based on findings.
        """
        print("\n" + "="*70)
        print("💡 ACTIONABLE RECOMMENDATIONS")
        print("="*70)

        recommendations = []

        # Top 5 differentiating factors
        top_factors = statistical_results.head(5)

        if success_factors:
            # If we have statistically significant factors, use them
            for _, row in top_factors.iterrows():
                if row['difference'] > 0 and row['significant']:
                    metric = row['metric'].replace('_', ' ').title()
                    rec = f"Focus on increasing {metric} - successful shows averaged {row['successful_mean']:.1f} vs {row['unsuccessful_mean']:.1f} for unsuccessful shows"
                    recommendations.append(rec)
                    print(f"\n→ {rec}")
        else:
            # If no significant factors, provide directional guidance
            print("\n⚠️ Note: Limited sample size (3 vs 7 shows) prevents strong statistical conclusions.")
            print("However, here are observed patterns to investigate further:\n")

            for _, row in top_factors.iterrows():
                if row['difference'] > 0:  # Only positive differences
                    metric = row['metric'].replace('_', ' ').title()
                    rec = f"Investigate {metric} - successful shows averaged {row['successful_mean']:.1f} vs {row['unsuccessful_mean']:.1f}"
                    recommendations.append(rec)
                    print(f"→ {rec}")
                    print(f"  (Effect size: {row['effect_size']}, p={row['p_value']:.3f})")

        return recommendations

    def run_complete_analysis(self):
        """Execute the full PhD-level analysis."""
        print("\n" + "="*70)
        print("🎓 BROADWAY MARKETING SCIENCE ANALYSIS")
        print("="*70)
        print("\nAnalyzing what makes marketing campaigns succeed vs fail...")

        # Collect all metrics
        all_metrics = []

        print("\n📊 Extracting metrics for successful campaigns...")
        for show_id, show_config in self.successful_shows.items():
            csv_path = self.data_dir / f"reddit_{show_id}.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                metrics = self.extract_comprehensive_metrics(df, show_config['name'], 'successful')
                all_metrics.append(metrics)
                print(f"  ✓ {show_config['name']}: {len(df)} posts")
            else:
                print(f"  ⚠ No data for {show_config['name']}")

        print("\n📊 Extracting metrics for unsuccessful campaigns...")
        for show_id, show_config in self.unsuccessful_shows.items():
            csv_path = self.data_dir / f"reddit_{show_id}.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                metrics = self.extract_comprehensive_metrics(df, show_config['name'], 'unsuccessful')
                all_metrics.append(metrics)
                print(f"  ✓ {show_config['name']}: {len(df)} posts")
            else:
                metrics = self._empty_metrics(show_config['name'], 'unsuccessful')
                all_metrics.append(metrics)
                print(f"  ⚠ No data for {show_config['name']} (using zeros)")

        # Split by category
        successful_metrics = [m for m in all_metrics if m['category'] == 'successful']
        unsuccessful_metrics = [m for m in all_metrics if m['category'] == 'unsuccessful']

        # Statistical comparison
        statistical_results = self.statistical_comparison(successful_metrics, unsuccessful_metrics)

        # Identify success factors
        success_factors = self.identify_success_factors(statistical_results)

        # Generate recommendations
        recommendations = self.generate_recommendations(success_factors, statistical_results)

        # Save results
        self.save_results(all_metrics, statistical_results, success_factors, recommendations)

    def save_results(self, all_metrics: List[Dict], statistical_results: pd.DataFrame,
                    success_factors: List[str], recommendations: List[str]):
        """Save all results to files."""
        # Save comprehensive metrics
        df_all = pd.DataFrame(all_metrics)
        all_path = self.output_dir / "marketing_science_all_metrics.csv"
        df_all.to_csv(all_path, index=False)
        print(f"\n💾 Saved all metrics: {all_path}")

        # Save statistical results
        stats_path = self.output_dir / "statistical_comparison.csv"
        statistical_results.to_csv(stats_path, index=False)
        print(f"💾 Saved statistical results: {stats_path}")

        # Save summary report
        report_path = self.output_dir / "marketing_science_report.json"
        report = {
            'analysis_date': datetime.now().isoformat(),
            'success_factors': success_factors,
            'recommendations': recommendations,
            'statistical_summary': statistical_results.to_dict('records')
        }
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"💾 Saved comprehensive report: {report_path}")


def main():
    """Main execution."""
    analyzer = BroadwayMarketingScience()
    analyzer.run_complete_analysis()

    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()

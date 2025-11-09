#!/usr/bin/env python3
"""
Broadway Marketing Effectiveness Analysis
Simple, measurable metrics from Reddit data.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import re


class MarketingEffectivenessAnalysis:
    """Analyzes marketing effectiveness using straightforward Reddit metrics."""

    def __init__(self):
        """Initialize analysis."""
        self.data_dir = Path("data/raw")
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_show_data(self, show_file: str) -> pd.DataFrame:
        """Load Reddit data for a show."""
        csv_path = self.data_dir / show_file
        if not csv_path.exists():
            return pd.DataFrame()
        return pd.read_csv(csv_path)

    def calculate_engagement_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate engagement metrics.

        Measures: How much are people interacting?
        """
        if df.empty:
            return self._empty_metrics()

        return {
            'total_posts': len(df),
            'avg_score': df['score'].mean(),
            'median_score': df['score'].median(),
            'total_score': df['score'].sum(),
            'avg_comments': df['num_comments'].mean(),
            'total_comments': df['num_comments'].sum(),
            'engagement_rate': (df['score'].sum() + df['num_comments'].sum()) / len(df),
            'viral_posts': len(df[df['score'] > 100]),  # Posts with 100+ upvotes
            'highly_viral_posts': len(df[df['score'] > 500]),  # 500+ upvotes
            'upvote_ratio_avg': df['upvote_ratio'].mean()
        }

    def calculate_reach_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate reach and spread metrics.

        Measures: How far is the word spreading?
        """
        if df.empty:
            return {}

        unique_subreddits = df['subreddit'].nunique()
        subreddit_list = df['subreddit'].value_counts().head(5).to_dict()

        # Parse dates
        df['date'] = pd.to_datetime(df['created_utc'])
        unique_days = df['date'].dt.date.nunique()
        date_range = (df['date'].max() - df['date'].min()).days

        return {
            'unique_subreddits': unique_subreddits,
            'top_subreddits': subreddit_list,
            'unique_days_posted': unique_days,
            'date_range_days': date_range,
            'cross_subreddit_diversity': unique_subreddits / len(df) if len(df) > 0 else 0
        }

    def calculate_sentiment_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate sentiment and tone metrics.

        Measures: What's the emotional tone?
        """
        if df.empty:
            return {}

        def analyze_text(text):
            if pd.isna(text):
                return {'positive': 0, 'negative': 0, 'excited': 0}

            text_lower = str(text).lower()

            # Positive indicators
            positive_words = ['amazing', 'incredible', 'brilliant', 'perfect', 'loved',
                            'fantastic', 'wonderful', 'best', 'hilarious', 'genius']
            positive_count = sum(1 for word in positive_words if word in text_lower)

            # Negative indicators
            negative_words = ['disappointed', 'boring', 'bad', 'terrible', 'waste',
                            'overrated', 'underwhelming', 'meh', 'disappointing']
            negative_count = sum(1 for word in negative_words if word in text_lower)

            # Excitement indicators
            exclamation_count = text.count('!')
            caps_words = len(re.findall(r'\b[A-Z]{2,}\b', str(text)))

            return {
                'positive': positive_count,
                'negative': negative_count,
                'excited': exclamation_count + caps_words
            }

        # Analyze titles (most visible)
        sentiments = df['title'].apply(analyze_text)
        sentiment_df = pd.DataFrame(sentiments.tolist())

        total_positive = sentiment_df['positive'].sum()
        total_negative = sentiment_df['negative'].sum()
        total_excited = sentiment_df['excited'].sum()

        # Sentiment score: positive vs negative ratio
        sentiment_score = 0
        if total_positive + total_negative > 0:
            sentiment_score = (total_positive / (total_positive + total_negative)) * 100

        return {
            'positive_mentions': int(total_positive),
            'negative_mentions': int(total_negative),
            'excitement_indicators': int(total_excited),
            'sentiment_score': round(sentiment_score, 1),  # 0-100, higher = more positive
            'positive_posts_pct': round((sentiment_df['positive'] > 0).sum() / len(df) * 100, 1)
        }

    def calculate_recommendation_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate word-of-mouth and recommendation metrics.

        Measures: Are people recommending it?
        """
        if df.empty:
            return {}

        def has_recommendation(text):
            if pd.isna(text):
                return False
            text_lower = str(text).lower()
            rec_phrases = ['must see', 'you should', 'highly recommend', 'go see',
                          'you have to', 'definitely see', 'worth seeing', 'don\'t miss']
            return any(phrase in text_lower for phrase in rec_phrases)

        def mentions_repeat_viewing(text):
            if pd.isna(text):
                return False
            text_lower = str(text).lower()
            repeat_phrases = ['saw it twice', 'second time', 'seeing it again',
                            'third time', 'multiple times', 'going back']
            return any(phrase in text_lower for phrase in repeat_phrases)

        # Analyze both title and text
        df['full_text'] = df['title'].fillna('') + ' ' + df['text'].fillna('')
        df['has_recommendation'] = df['full_text'].apply(has_recommendation)
        df['mentions_repeat'] = df['full_text'].apply(mentions_repeat_viewing)

        recommendation_posts = df['has_recommendation'].sum()
        repeat_viewing_posts = df['mentions_repeat'].sum()

        return {
            'recommendation_posts': int(recommendation_posts),
            'recommendation_rate': round(recommendation_posts / len(df) * 100, 1),
            'repeat_viewing_mentions': int(repeat_viewing_posts),
            'repeat_viewing_rate': round(repeat_viewing_posts / len(df) * 100, 1),
            'organic_wom_score': round((recommendation_posts + repeat_viewing_posts * 2) / len(df) * 50, 1)
        }

    def calculate_overall_score(self, metrics: Dict) -> float:
        """
        Calculate overall marketing effectiveness score (0-100).

        Weights different factors:
        - 30% Engagement (scores, comments)
        - 25% Reach (subreddit diversity, volume)
        - 25% Sentiment (positive buzz)
        - 20% Word-of-mouth (recommendations)
        """
        engagement_metrics = metrics.get('engagement', {})
        reach_metrics = metrics.get('reach', {})
        sentiment_metrics = metrics.get('sentiment', {})
        recommendation_metrics = metrics.get('recommendations', {})

        # Engagement score (0-100)
        avg_engagement = engagement_metrics.get('engagement_rate', 0)
        engagement_score = min(avg_engagement / 50 * 100, 100)  # Normalize

        # Reach score (0-100)
        unique_subs = reach_metrics.get('unique_subreddits', 0)
        total_posts = engagement_metrics.get('total_posts', 1)
        reach_score = min((unique_subs / 10) * 50 + (total_posts / 100) * 50, 100)

        # Sentiment score (already 0-100)
        sentiment_score = sentiment_metrics.get('sentiment_score', 50)

        # WOM score (already 0-100)
        wom_score = recommendation_metrics.get('organic_wom_score', 0)

        # Weighted overall score
        overall = (
            engagement_score * 0.30 +
            reach_score * 0.25 +
            sentiment_score * 0.25 +
            wom_score * 0.20
        )

        return round(overall, 1)

    def analyze_show(self, show_name: str, show_file: str) -> Dict[str, Any]:
        """Analyze a single show."""
        print(f"\n{'='*70}")
        print(f"📊 Analyzing: {show_name}")
        print(f"{'='*70}")

        df = self.load_show_data(show_file)

        if df.empty:
            print(f"  ⚠ No data found")
            return {'show_name': show_name, 'metrics': self._empty_metrics()}

        print(f"  ✓ Loaded {len(df)} posts")

        # Calculate all metrics
        engagement = self.calculate_engagement_metrics(df)
        reach = self.calculate_reach_metrics(df)
        sentiment = self.calculate_sentiment_metrics(df)
        recommendations = self.calculate_recommendation_metrics(df)

        metrics = {
            'engagement': engagement,
            'reach': reach,
            'sentiment': sentiment,
            'recommendations': recommendations
        }

        # Calculate overall score
        overall_score = self.calculate_overall_score(metrics)

        print(f"\n  📈 Overall Marketing Effectiveness: {overall_score}/100")
        print(f"  💬 Total Engagement: {engagement['total_score']:,} upvotes, {engagement['total_comments']:,} comments")
        print(f"  🌍 Reach: {reach['unique_subreddits']} subreddits")
        print(f"  ❤️  Sentiment: {sentiment['sentiment_score']}% positive")
        print(f"  🗣️  Recommendations: {recommendations['recommendation_rate']}% of posts")

        return {
            'show_name': show_name,
            'overall_score': overall_score,
            'metrics': metrics,
            'data': df
        }

    def _empty_metrics(self) -> Dict:
        """Return empty metrics structure."""
        return {
            'engagement': {},
            'reach': {},
            'sentiment': {},
            'recommendations': {}
        }

    def generate_comparison_report(self, results: Dict[str, Any]):
        """Generate comparative report."""
        print("\n" + "="*70)
        print("🏆 MARKETING EFFECTIVENESS RANKING")
        print("="*70)

        # Create comparison table
        comparison = []
        for show_id, result in results.items():
            metrics = result['metrics']
            comparison.append({
                'Show': result['show_name'],
                'Overall Score': result['overall_score'],
                'Posts': metrics['engagement'].get('total_posts', 0),
                'Avg Score': round(metrics['engagement'].get('avg_score', 0), 1),
                'Comments': metrics['engagement'].get('total_comments', 0),
                'Subreddits': metrics['reach'].get('unique_subreddits', 0),
                'Sentiment': metrics['sentiment'].get('sentiment_score', 0),
                'Recommendation%': metrics['recommendations'].get('recommendation_rate', 0)
            })

        df_comp = pd.DataFrame(comparison)
        df_comp = df_comp.sort_values('Overall Score', ascending=False)

        print("\n" + df_comp.to_string(index=False))

        if len(df_comp) > 0:
            winner = df_comp.iloc[0]
            print(f"\n🥇 WINNER: {winner['Show']}")
            print(f"   Marketing Effectiveness Score: {winner['Overall Score']}/100")
            print(f"   {winner['Posts']} Reddit posts across {winner['Subreddits']} subreddits")

        # Save results
        comparison_path = self.output_dir / "marketing_effectiveness_summary.csv"
        df_comp.to_csv(comparison_path, index=False)
        print(f"\n💾 Saved: {comparison_path}")

        # Save detailed results
        detailed_path = self.output_dir / "detailed_marketing_metrics.json"
        json_results = {}
        for show_id, result in results.items():
            json_results[show_id] = {
                'show_name': result['show_name'],
                'overall_score': result['overall_score'],
                'metrics': result['metrics']
            }

        with open(detailed_path, 'w') as f:
            json.dump(json_results, f, indent=2, default=str)
        print(f"💾 Saved: {detailed_path}")


def main():
    """Main execution."""
    print("\n" + "="*70)
    print("🎭 BROADWAY MARKETING EFFECTIVENESS ANALYSIS")
    print("="*70)
    print("\nSimple, Measurable Metrics:")
    print("  📊 Engagement (upvotes, comments)")
    print("  🌍 Reach (subreddit spread)")
    print("  ❤️  Sentiment (positive buzz)")
    print("  🗣️  Word-of-Mouth (recommendations)")

    analyzer = MarketingEffectivenessAnalysis()

    # Analyze all shows
    results = {}
    shows = {
        'oh_mary': ('Oh Mary!', 'reddit_oh_mary.csv'),
        'john_proctor': ('John Proctor is the Villain', 'reddit_john_proctor.csv'),
        'maybe_happy_ending': ('Maybe Happy Ending', 'reddit_maybe_happy_ending.csv')
    }

    for show_id, (show_name, filename) in shows.items():
        results[show_id] = analyzer.analyze_show(show_name, filename)

    # Generate comparison
    analyzer.generate_comparison_report(results)

    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()

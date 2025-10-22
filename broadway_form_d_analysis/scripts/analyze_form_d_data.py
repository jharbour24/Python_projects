#!/usr/bin/env python3
"""
Broadway Form D Quantitative Analysis
Performs comprehensive statistical analysis on Form D filings
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BroadwayFormDAnalyzer:
    """Comprehensive quantitative analyzer for Broadway Form D data"""

    def __init__(self, data_path: Path):
        """
        Initialize analyzer with parsed Form D data

        Args:
            data_path: Path to CSV file with parsed Form D data
        """
        self.data_path = Path(data_path)
        self.df = None
        self.analysis_results = {}

        self._load_data()

    def _load_data(self):
        """Load and preprocess Form D data"""
        logger.info(f"Loading data from {self.data_path}")

        try:
            self.df = pd.read_csv(self.data_path)

            # Convert date columns
            date_columns = ['filing_date', 'amendment_date', 'offering_date']
            for col in date_columns:
                if col in self.df.columns:
                    self.df[col] = pd.to_datetime(self.df[col], errors='coerce')

            # Extract year and month
            self.df['filing_year'] = self.df['filing_date'].dt.year
            self.df['filing_month'] = self.df['filing_date'].dt.month
            self.df['filing_quarter'] = self.df['filing_date'].dt.quarter

            # Classify show types based on entity name
            self.df['show_type'] = self.df['entity_name'].apply(self._classify_show_type)

            # Create pre/post COVID indicator
            self.df['is_post_covid'] = self.df['filing_year'] >= 2020

            # Calculate offering utilization
            self.df['offering_utilization'] = (
                self.df['total_amount_sold'] / self.df['total_offering_amount'] * 100
            ).round(2)

            logger.info(f"Loaded {len(self.df)} Form D filings")
            logger.info(f"Date range: {self.df['filing_date'].min()} to {self.df['filing_date'].max()}")

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise

    def _classify_show_type(self, entity_name: str) -> str:
        """Classify production as musical, play, or unknown"""
        if pd.isna(entity_name):
            return 'Unknown'

        name_lower = entity_name.lower()

        musical_keywords = ['musical', 'music', 'songs', 'singing']
        play_keywords = ['play', 'drama', 'comedy']

        for keyword in musical_keywords:
            if keyword in name_lower:
                return 'Musical'

        for keyword in play_keywords:
            if keyword in name_lower:
                return 'Play'

        return 'Unknown'

    def analyze_capitalization_trends(self) -> Dict:
        """
        Analysis 1: Capitalization Trends

        Returns:
            Dictionary with annual statistics
        """
        logger.info("Analyzing capitalization trends...")

        # Annual offering statistics
        annual_stats = self.df.groupby('filing_year').agg({
            'total_offering_amount': ['count', 'mean', 'median', 'min', 'max', 'sum'],
            'total_amount_sold': ['mean', 'median', 'sum'],
            'total_remaining': ['mean', 'median']
        }).round(2)

        # Top 10 largest offerings by year
        top_by_year = {}
        for year in sorted(self.df['filing_year'].dropna().unique()):
            year_data = self.df[self.df['filing_year'] == year].nlargest(
                10, 'total_offering_amount'
            )[['entity_name', 'total_offering_amount', 'filing_date']]
            top_by_year[int(year)] = year_data.to_dict('records')

        # Top 10 overall
        top_10_overall = self.df.nlargest(10, 'total_offering_amount')[
            ['entity_name', 'total_offering_amount', 'filing_date', 'filing_year']
        ].to_dict('records')

        # Musical vs Play comparison
        show_type_stats = self.df.groupby('show_type').agg({
            'total_offering_amount': ['count', 'mean', 'median', 'sum']
        }).round(2)

        results = {
            'annual_statistics': annual_stats.to_dict(),
            'top_10_by_year': top_by_year,
            'top_10_overall': top_10_overall,
            'show_type_comparison': show_type_stats.to_dict()
        }

        self.analysis_results['capitalization_trends'] = results
        return results

    def analyze_investor_base_evolution(self) -> Dict:
        """
        Analysis 2: Investor Base Evolution

        Returns:
            Dictionary with investor trends
        """
        logger.info("Analyzing investor base evolution...")

        # Annual investor statistics
        investor_stats = self.df.groupby('filing_year').agg({
            'total_number_of_investors': ['mean', 'median', 'min', 'max', 'sum'],
            'minimum_investment': ['mean', 'median', 'min', 'max'],
            'has_non_accredited_investors': 'sum'
        }).round(2)

        # Calculate percentage with non-accredited investors
        annual_counts = self.df.groupby('filing_year').size()
        pct_non_accredited = (
            self.df.groupby('filing_year')['has_non_accredited_investors'].sum() / annual_counts * 100
        ).round(2)

        # Minimum investment trends over time
        min_investment_trend = self.df.groupby('filing_year')['minimum_investment'].agg([
            'mean', 'median', 'count'
        ]).round(2)

        # Investor concentration (offerings with high investor counts)
        high_investor_threshold = self.df['total_number_of_investors'].quantile(0.9)
        high_investor_filings = self.df[
            self.df['total_number_of_investors'] > high_investor_threshold
        ][['entity_name', 'total_number_of_investors', 'filing_year', 'minimum_investment']]

        results = {
            'annual_investor_statistics': investor_stats.to_dict(),
            'pct_non_accredited_by_year': pct_non_accredited.to_dict(),
            'minimum_investment_trends': min_investment_trend.to_dict(),
            'high_investor_filings': high_investor_filings.to_dict('records'),
            'high_investor_threshold': float(high_investor_threshold) if pd.notna(high_investor_threshold) else None
        }

        self.analysis_results['investor_base_evolution'] = results
        return results

    def analyze_post_covid_shifts(self) -> Dict:
        """
        Analysis 3: Post-COVID Shifts (2020-2025)

        Returns:
            Dictionary comparing pre/post COVID periods
        """
        logger.info("Analyzing post-COVID shifts...")

        # Split data
        pre_covid = self.df[self.df['filing_year'] < 2020]
        post_covid = self.df[self.df['filing_year'] >= 2020]

        # Comparative statistics
        comparison_metrics = ['total_offering_amount', 'total_amount_sold',
                            'total_number_of_investors', 'minimum_investment']

        comparison = {}
        for metric in comparison_metrics:
            comparison[metric] = {
                'pre_covid_mean': float(pre_covid[metric].mean()) if len(pre_covid) > 0 else None,
                'pre_covid_median': float(pre_covid[metric].median()) if len(pre_covid) > 0 else None,
                'post_covid_mean': float(post_covid[metric].mean()) if len(post_covid) > 0 else None,
                'post_covid_median': float(post_covid[metric].median()) if len(post_covid) > 0 else None,
                'percent_change_mean': None,
                'percent_change_median': None
            }

            # Calculate percent change
            if comparison[metric]['pre_covid_mean'] and comparison[metric]['post_covid_mean']:
                comparison[metric]['percent_change_mean'] = round(
                    (comparison[metric]['post_covid_mean'] - comparison[metric]['pre_covid_mean']) /
                    comparison[metric]['pre_covid_mean'] * 100, 2
                )

            if comparison[metric]['pre_covid_median'] and comparison[metric]['post_covid_median']:
                comparison[metric]['percent_change_median'] = round(
                    (comparison[metric]['post_covid_median'] - comparison[metric]['pre_covid_median']) /
                    comparison[metric]['pre_covid_median'] * 100, 2
                )

        # Rule 506(c) usage (general solicitation allowed)
        rule_506c_usage = {
            'pre_covid_count': int(pre_covid['rule_506c'].sum()) if len(pre_covid) > 0 else 0,
            'pre_covid_pct': round(pre_covid['rule_506c'].sum() / len(pre_covid) * 100, 2) if len(pre_covid) > 0 else 0,
            'post_covid_count': int(post_covid['rule_506c'].sum()) if len(post_covid) > 0 else 0,
            'post_covid_pct': round(post_covid['rule_506c'].sum() / len(post_covid) * 100, 2) if len(post_covid) > 0 else 0
        }

        # Offering duration analysis
        duration_comparison = {
            'pre_covid_avg_more_than_one_year': round(
                pre_covid['more_than_one_year'].sum() / len(pre_covid) * 100, 2
            ) if len(pre_covid) > 0 else None,
            'post_covid_avg_more_than_one_year': round(
                post_covid['more_than_one_year'].sum() / len(post_covid) * 100, 2
            ) if len(post_covid) > 0 else None
        }

        # Annual filing counts
        annual_counts = self.df.groupby('filing_year').size().to_dict()

        results = {
            'pre_covid_count': len(pre_covid),
            'post_covid_count': len(post_covid),
            'metric_comparison': comparison,
            'rule_506c_usage': rule_506c_usage,
            'offering_duration': duration_comparison,
            'annual_filing_counts': annual_counts
        }

        self.analysis_results['post_covid_shifts'] = results
        return results

    def analyze_structural_patterns(self) -> Dict:
        """
        Analysis 4: Structural Patterns

        Returns:
            Dictionary with entity and structural patterns
        """
        logger.info("Analyzing structural patterns...")

        # Extract management/production companies from entity names
        # Look for patterns like "Seaview", "Ambassador", etc.
        def extract_producer(entity_name):
            if pd.isna(entity_name):
                return 'Unknown'

            # Common producer patterns
            producers = ['seaview', 'ambassador', 'pankake', 'jujamcyn', 'nederlander',
                        'shubert', 'disney', 'roundabout', 'second stage', 'manhattan theatre club']

            name_lower = entity_name.lower()
            for producer in producers:
                if producer in name_lower:
                    return producer.title()

            return 'Other'

        self.df['producer_group'] = self.df['entity_name'].apply(extract_producer)

        # Count filings by producer
        producer_counts = self.df['producer_group'].value_counts().to_dict()

        # Amendment analysis
        amendment_stats = {
            'total_amendments': int(self.df['is_amendment'].sum()),
            'amendment_rate': round(self.df['is_amendment'].sum() / len(self.df) * 100, 2),
            'amendments_by_year': self.df.groupby('filing_year')['is_amendment'].sum().to_dict()
        }

        # Entity type distribution
        entity_type_dist = self.df['entity_type'].value_counts().to_dict()

        # Securities type analysis
        securities_analysis = {
            'equity_offerings': int(self.df['equity_type'].sum()),
            'debt_offerings': int(self.df['debt_type'].sum()),
            'partnership_interests': int(self.df['partnership_interest'].sum()),
            'equity_pct': round(self.df['equity_type'].sum() / len(self.df) * 100, 2),
            'debt_pct': round(self.df['debt_type'].sum() / len(self.df) * 100, 2)
        }

        results = {
            'producer_groups': producer_counts,
            'amendment_statistics': amendment_stats,
            'entity_types': entity_type_dist,
            'securities_types': securities_analysis
        }

        self.analysis_results['structural_patterns'] = results
        return results

    def analyze_geographic_trends(self) -> Dict:
        """
        Analysis 5: Geographic and Legal Trends

        Returns:
            Dictionary with geographic patterns
        """
        logger.info("Analyzing geographic and legal trends...")

        # Jurisdiction of incorporation
        jurisdiction_counts = self.df['jurisdiction_of_incorporation'].value_counts().head(10).to_dict()

        # Statistics by state
        state_stats = self.df.groupby('jurisdiction_of_incorporation').agg({
            'total_offering_amount': ['count', 'mean', 'median', 'sum'],
            'total_number_of_investors': ['mean', 'median']
        }).round(2)

        # Principal place of business
        business_state_counts = self.df['issuer_state'].value_counts().head(10).to_dict()

        # Exemption usage by jurisdiction
        top_jurisdictions = self.df['jurisdiction_of_incorporation'].value_counts().head(5).index
        exemption_by_jurisdiction = {}

        for jurisdiction in top_jurisdictions:
            jur_data = self.df[self.df['jurisdiction_of_incorporation'] == jurisdiction]
            exemption_by_jurisdiction[jurisdiction] = {
                'rule_506b_pct': round(jur_data['rule_506b'].sum() / len(jur_data) * 100, 2),
                'rule_506c_pct': round(jur_data['rule_506c'].sum() / len(jur_data) * 100, 2),
                'count': len(jur_data)
            }

        results = {
            'top_incorporation_jurisdictions': jurisdiction_counts,
            'state_statistics': state_stats.to_dict(),
            'principal_business_states': business_state_counts,
            'exemption_by_jurisdiction': exemption_by_jurisdiction
        }

        self.analysis_results['geographic_trends'] = results
        return results

    def analyze_comparative_benchmarks(self) -> Dict:
        """
        Analysis 6: Comparative Benchmarks

        Returns:
            Dictionary with benchmark comparisons
        """
        logger.info("Analyzing comparative benchmarks...")

        # Calculate key benchmarks
        benchmarks = {
            'median_offering_size': float(self.df['total_offering_amount'].median()),
            'mean_offering_size': float(self.df['total_offering_amount'].mean()),
            'median_investors': float(self.df['total_number_of_investors'].median()),
            'mean_investors': float(self.df['total_number_of_investors'].mean()),
            'median_min_investment': float(self.df['minimum_investment'].median()),
            'mean_min_investment': float(self.df['minimum_investment'].mean()),
            'avg_offering_utilization': float(self.df['offering_utilization'].mean()),
            'median_offering_utilization': float(self.df['offering_utilization'].median())
        }

        # Quartile analysis
        offering_quartiles = {
            '25th_percentile': float(self.df['total_offering_amount'].quantile(0.25)),
            '50th_percentile': float(self.df['total_offering_amount'].quantile(0.50)),
            '75th_percentile': float(self.df['total_offering_amount'].quantile(0.75)),
            '90th_percentile': float(self.df['total_offering_amount'].quantile(0.90))
        }

        # Year-over-year growth rates
        annual_totals = self.df.groupby('filing_year')['total_offering_amount'].sum().sort_index()
        yoy_growth = annual_totals.pct_change() * 100
        yoy_growth = yoy_growth.round(2).to_dict()

        results = {
            'benchmarks': benchmarks,
            'offering_quartiles': offering_quartiles,
            'year_over_year_growth': yoy_growth
        }

        self.analysis_results['comparative_benchmarks'] = results
        return results

    def detect_outliers(self) -> Dict:
        """
        Analysis 7: Outlier Detection

        Returns:
            Dictionary with outlier analysis
        """
        logger.info("Detecting outliers...")

        # Extreme offerings (>$50M)
        large_offerings = self.df[self.df['total_offering_amount'] > 50_000_000][
            ['entity_name', 'total_offering_amount', 'filing_date', 'total_number_of_investors']
        ].sort_values('total_offering_amount', ascending=False)

        # High investor counts (top 5%)
        investor_threshold = self.df['total_number_of_investors'].quantile(0.95)
        high_investor_offerings = self.df[
            self.df['total_number_of_investors'] > investor_threshold
        ][['entity_name', 'total_number_of_investors', 'minimum_investment', 'filing_year']].sort_values(
            'total_number_of_investors', ascending=False
        )

        # Unusually low minimum investments
        low_min_threshold = self.df['minimum_investment'].quantile(0.05)
        low_minimum_offerings = self.df[
            self.df['minimum_investment'] < low_min_threshold
        ][['entity_name', 'minimum_investment', 'total_number_of_investors', 'filing_year']].sort_values(
            'minimum_investment'
        )

        # Cross-reference with known major shows
        major_shows = ['hamilton', 'lion king', 'wicked', 'harry potter', 'phantom',
                      'chicago', 'moulin rouge', 'hadestown', 'book of mormon']

        matched_major_shows = []
        for show in major_shows:
            matches = self.df[self.df['entity_name'].str.contains(show, case=False, na=False)]
            if len(matches) > 0:
                for _, row in matches.iterrows():
                    matched_major_shows.append({
                        'show': show.title(),
                        'entity_name': row['entity_name'],
                        'offering_amount': row['total_offering_amount'],
                        'filing_date': str(row['filing_date'])
                    })

        results = {
            'large_offerings': large_offerings.to_dict('records'),
            'large_offering_threshold': 50_000_000,
            'high_investor_offerings': high_investor_offerings.to_dict('records'),
            'high_investor_threshold': float(investor_threshold) if pd.notna(investor_threshold) else None,
            'low_minimum_offerings': low_minimum_offerings.to_dict('records'),
            'low_minimum_threshold': float(low_min_threshold) if pd.notna(low_min_threshold) else None,
            'major_show_matches': matched_major_shows
        }

        self.analysis_results['outliers'] = results
        return results

    def generate_summary_insights(self) -> Dict:
        """
        Generate 3-5 key insights from the analysis

        Returns:
            Dictionary with key findings
        """
        logger.info("Generating summary insights...")

        insights = []

        # Insight 1: Overall market size and growth
        total_capital = self.df['total_offering_amount'].sum()
        annual_totals = self.df.groupby('filing_year')['total_offering_amount'].sum()
        growth_2010_to_recent = ((annual_totals.iloc[-1] - annual_totals.iloc[0]) / annual_totals.iloc[0] * 100)

        insights.append({
            'title': 'Broadway Capital Markets Scale',
            'finding': f"Total capital raised through Form D: ${total_capital:,.0f}. "
                      f"Annual offering volume grew {growth_2010_to_recent:.1f}% from 2010 to present."
        })

        # Insight 2: Post-COVID impact
        if 'post_covid_shifts' in self.analysis_results:
            covid_data = self.analysis_results['post_covid_shifts']['metric_comparison']['total_offering_amount']
            if covid_data['percent_change_mean']:
                insights.append({
                    'title': 'Post-COVID Capitalization Shift',
                    'finding': f"Average offering size {covid_data['percent_change_mean']:+.1f}% post-2020, "
                              f"from ${covid_data['pre_covid_mean']:,.0f} to ${covid_data['post_covid_mean']:,.0f}."
                })

        # Insight 3: Democratization of investment
        if 'investor_base_evolution' in self.analysis_results:
            min_inv_trend = self.df.groupby('filing_year')['minimum_investment'].median()
            if len(min_inv_trend) >= 2:
                early_min = min_inv_trend.iloc[:3].mean()
                recent_min = min_inv_trend.iloc[-3:].mean()
                change_pct = (recent_min - early_min) / early_min * 100

                insights.append({
                    'title': 'Investment Accessibility Trend',
                    'finding': f"Median minimum investment {change_pct:+.1f}% from early period "
                              f"(${early_min:,.0f}) to recent years (${recent_min:,.0f})."
                })

        # Insight 4: Regulatory exemption preferences
        rule_506b_pct = self.df['rule_506b'].sum() / len(self.df) * 100
        rule_506c_pct = self.df['rule_506c'].sum() / len(self.df) * 100

        insights.append({
            'title': 'Regulatory Exemption Usage',
            'finding': f"Rule 506(b) used in {rule_506b_pct:.1f}% of filings, "
                      f"while Rule 506(c) (general solicitation) used in {rule_506c_pct:.1f}%."
        })

        # Insight 5: Geographic concentration
        if 'geographic_trends' in self.analysis_results:
            top_jurisdiction = list(self.analysis_results['geographic_trends']['top_incorporation_jurisdictions'].items())[0]
            total_filings = len(self.df)
            concentration = top_jurisdiction[1] / total_filings * 100

            insights.append({
                'title': 'Geographic Concentration',
                'finding': f"{top_jurisdiction[0]} leads with {concentration:.1f}% of all incorporations "
                          f"({top_jurisdiction[1]} out of {total_filings} filings)."
            })

        return {'insights': insights, 'total_insights': len(insights)}

    def run_full_analysis(self) -> Dict:
        """
        Execute all analysis modules

        Returns:
            Complete analysis results dictionary
        """
        logger.info("=" * 80)
        logger.info("Running Complete Analysis Pipeline")
        logger.info("=" * 80)

        # Run all analyses
        self.analyze_capitalization_trends()
        self.analyze_investor_base_evolution()
        self.analyze_post_covid_shifts()
        self.analyze_structural_patterns()
        self.analyze_geographic_trends()
        self.analyze_comparative_benchmarks()
        self.detect_outliers()

        # Generate insights
        insights = self.generate_summary_insights()
        self.analysis_results['summary_insights'] = insights

        logger.info("Analysis complete!")
        return self.analysis_results

    def save_results(self, output_dir: Path):
        """Save analysis results to JSON file"""
        output_path = output_dir / 'analysis_results.json'

        # Convert numpy/pandas types to native Python types for JSON serialization
        def clean_for_json(obj):
            """Recursively clean objects for JSON serialization"""
            if isinstance(obj, dict):
                # Convert dict with tuple keys to dict with string keys
                return {str(k): clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [clean_for_json(item) for item in obj]
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif pd.isna(obj):
                return None
            elif isinstance(obj, (pd.Timestamp, datetime)):
                return str(obj)
            elif isinstance(obj, (np.bool_)):
                return bool(obj)
            else:
                return obj

        # Clean results
        clean_results = clean_for_json(self.analysis_results)

        with open(output_path, 'w') as f:
            json.dump(clean_results, f, indent=2, default=str)

        logger.info(f"Saved analysis results to {output_path}")


def main():
    """Main execution"""
    project_dir = Path(__file__).parent.parent
    data_path = project_dir / 'data' / 'processed' / 'broadway_form_d_2010_2025.csv'
    analysis_dir = project_dir / 'analysis'

    analysis_dir.mkdir(exist_ok=True)

    # Check if data file exists
    if not data_path.exists():
        logger.error(f"Data file not found: {data_path}")
        logger.info("Please run collect_form_d_data.py first to gather the data")
        return

    # Run analysis
    analyzer = BroadwayFormDAnalyzer(data_path)
    results = analyzer.run_full_analysis()

    # Save results
    analyzer.save_results(analysis_dir)

    # Print summary insights
    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    for i, insight in enumerate(results['summary_insights']['insights'], 1):
        print(f"\n{i}. {insight['title']}")
        print(f"   {insight['finding']}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

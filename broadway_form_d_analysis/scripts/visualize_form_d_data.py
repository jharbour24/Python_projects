#!/usr/bin/env python3
"""
Broadway Form D Visualization
Creates comprehensive visualizations and charts for analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set style
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10


class BroadwayFormDVisualizer:
    """Creates visualizations for Broadway Form D analysis"""

    def __init__(self, data_path: Path, output_dir: Path):
        """
        Initialize visualizer

        Args:
            data_path: Path to processed Form D CSV
            output_dir: Directory to save visualizations
        """
        self.data_path = Path(data_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.df = None
        self._load_data()

    def _load_data(self):
        """Load and preprocess data"""
        logger.info(f"Loading data from {self.data_path}")

        self.df = pd.read_csv(self.data_path)

        # Convert dates
        date_cols = ['filing_date', 'amendment_date', 'offering_date']
        for col in date_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_datetime(self.df[col], errors='coerce')

        # Extract temporal features
        self.df['filing_year'] = self.df['filing_date'].dt.year
        self.df['filing_quarter'] = self.df['filing_date'].dt.quarter
        self.df['filing_month'] = self.df['filing_date'].dt.month

        # Add derived metrics
        self.df['is_post_covid'] = self.df['filing_year'] >= 2020
        self.df['offering_utilization'] = (
            self.df['total_amount_sold'] / self.df['total_offering_amount'] * 100
        )

        logger.info(f"Loaded {len(self.df)} records")

    def plot_annual_offering_trends(self):
        """Time series of offering amounts by year"""
        logger.info("Creating annual offering trends visualization...")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Total offering amount per year
        annual_totals = self.df.groupby('filing_year')['total_offering_amount'].sum() / 1_000_000
        axes[0, 0].bar(annual_totals.index, annual_totals.values, color='steelblue', alpha=0.7)
        axes[0, 0].set_title('Total Capital Raised per Year', fontsize=14, fontweight='bold')
        axes[0, 0].set_xlabel('Year')
        axes[0, 0].set_ylabel('Amount ($ Millions)')
        axes[0, 0].grid(axis='y', alpha=0.3)

        # 2. Mean and median offering size
        annual_stats = self.df.groupby('filing_year')['total_offering_amount'].agg(['mean', 'median']) / 1_000_000
        axes[0, 1].plot(annual_stats.index, annual_stats['mean'], marker='o', label='Mean', linewidth=2)
        axes[0, 1].plot(annual_stats.index, annual_stats['median'], marker='s', label='Median', linewidth=2)
        axes[0, 1].set_title('Average Offering Size per Year', fontsize=14, fontweight='bold')
        axes[0, 1].set_xlabel('Year')
        axes[0, 1].set_ylabel('Amount ($ Millions)')
        axes[0, 1].legend()
        axes[0, 1].grid(alpha=0.3)

        # 3. Number of filings per year
        filing_counts = self.df.groupby('filing_year').size()
        axes[1, 0].bar(filing_counts.index, filing_counts.values, color='coral', alpha=0.7)
        axes[1, 0].set_title('Number of Form D Filings per Year', fontsize=14, fontweight='bold')
        axes[1, 0].set_xlabel('Year')
        axes[1, 0].set_ylabel('Count')
        axes[1, 0].grid(axis='y', alpha=0.3)

        # 4. Amount sold vs offered
        annual_offered = self.df.groupby('filing_year')['total_offering_amount'].sum() / 1_000_000
        annual_sold = self.df.groupby('filing_year')['total_amount_sold'].sum() / 1_000_000

        x = np.arange(len(annual_offered))
        width = 0.35

        axes[1, 1].bar(x - width/2, annual_offered.values, width, label='Offered', alpha=0.7)
        axes[1, 1].bar(x + width/2, annual_sold.values, width, label='Sold', alpha=0.7)
        axes[1, 1].set_title('Offered vs Sold Amount per Year', fontsize=14, fontweight='bold')
        axes[1, 1].set_xlabel('Year')
        axes[1, 1].set_ylabel('Amount ($ Millions)')
        axes[1, 1].set_xticks(x)
        axes[1, 1].set_xticklabels(annual_offered.index)
        axes[1, 1].legend()
        axes[1, 1].grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / 'annual_offering_trends.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved to {output_path}")
        plt.close()

    def plot_investor_trends(self):
        """Investor base evolution visualizations"""
        logger.info("Creating investor trends visualization...")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Average number of investors per year
        investor_stats = self.df.groupby('filing_year')['total_number_of_investors'].agg(['mean', 'median'])
        axes[0, 0].plot(investor_stats.index, investor_stats['mean'], marker='o', label='Mean', linewidth=2)
        axes[0, 0].plot(investor_stats.index, investor_stats['median'], marker='s', label='Median', linewidth=2)
        axes[0, 0].set_title('Average Number of Investors per Filing', fontsize=14, fontweight='bold')
        axes[0, 0].set_xlabel('Year')
        axes[0, 0].set_ylabel('Number of Investors')
        axes[0, 0].legend()
        axes[0, 0].grid(alpha=0.3)

        # 2. Minimum investment trends
        min_inv_stats = self.df.groupby('filing_year')['minimum_investment'].agg(['mean', 'median']) / 1000
        axes[0, 1].plot(min_inv_stats.index, min_inv_stats['mean'], marker='o', label='Mean', linewidth=2, color='green')
        axes[0, 1].plot(min_inv_stats.index, min_inv_stats['median'], marker='s', label='Median', linewidth=2, color='darkgreen')
        axes[0, 1].set_title('Minimum Investment Required per Year', fontsize=14, fontweight='bold')
        axes[0, 1].set_xlabel('Year')
        axes[0, 1].set_ylabel('Amount ($1,000s)')
        axes[0, 1].legend()
        axes[0, 1].grid(alpha=0.3)

        # 3. Non-accredited investor participation
        non_accredited = self.df.groupby('filing_year')['has_non_accredited_investors'].sum()
        total_filings = self.df.groupby('filing_year').size()
        pct_non_accredited = (non_accredited / total_filings * 100)

        axes[1, 0].bar(pct_non_accredited.index, pct_non_accredited.values, color='orange', alpha=0.7)
        axes[1, 0].set_title('% of Filings with Non-Accredited Investors', fontsize=14, fontweight='bold')
        axes[1, 0].set_xlabel('Year')
        axes[1, 0].set_ylabel('Percentage (%)')
        axes[1, 0].grid(axis='y', alpha=0.3)

        # 4. Distribution of investor counts (histogram)
        axes[1, 1].hist(self.df['total_number_of_investors'].dropna(), bins=30, color='purple', alpha=0.7, edgecolor='black')
        axes[1, 1].set_title('Distribution of Investor Counts', fontsize=14, fontweight='bold')
        axes[1, 1].set_xlabel('Number of Investors')
        axes[1, 1].set_ylabel('Frequency')
        axes[1, 1].grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / 'investor_trends.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved to {output_path}")
        plt.close()

    def plot_covid_comparison(self):
        """Pre/Post COVID comparison"""
        logger.info("Creating COVID impact comparison...")

        pre_covid = self.df[self.df['filing_year'] < 2020]
        post_covid = self.df[self.df['filing_year'] >= 2020]

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Offering size comparison
        data_to_plot = [
            pre_covid['total_offering_amount'].dropna() / 1_000_000,
            post_covid['total_offering_amount'].dropna() / 1_000_000
        ]
        axes[0, 0].boxplot(data_to_plot, labels=['Pre-COVID\n(2010-2019)', 'Post-COVID\n(2020-2025)'])
        axes[0, 0].set_title('Offering Amount Distribution', fontsize=14, fontweight='bold')
        axes[0, 0].set_ylabel('Amount ($ Millions)')
        axes[0, 0].grid(axis='y', alpha=0.3)

        # 2. Investor count comparison
        data_to_plot = [
            pre_covid['total_number_of_investors'].dropna(),
            post_covid['total_number_of_investors'].dropna()
        ]
        axes[0, 1].boxplot(data_to_plot, labels=['Pre-COVID\n(2010-2019)', 'Post-COVID\n(2020-2025)'])
        axes[0, 1].set_title('Number of Investors Distribution', fontsize=14, fontweight='bold')
        axes[0, 1].set_ylabel('Number of Investors')
        axes[0, 1].grid(axis='y', alpha=0.3)

        # 3. Rule 506(c) usage
        rule_506c_data = [
            [pre_covid['rule_506c'].sum(), len(pre_covid) - pre_covid['rule_506c'].sum()],
            [post_covid['rule_506c'].sum(), len(post_covid) - post_covid['rule_506c'].sum()]
        ]

        x = np.arange(2)
        width = 0.35

        axes[1, 0].bar(x - width/2, [d[0] for d in rule_506c_data], width, label='Rule 506(c)', alpha=0.7)
        axes[1, 0].bar(x + width/2, [d[1] for d in rule_506c_data], width, label='Other', alpha=0.7)
        axes[1, 0].set_title('Exemption Rule Usage', fontsize=14, fontweight='bold')
        axes[1, 0].set_ylabel('Count')
        axes[1, 0].set_xticks(x)
        axes[1, 0].set_xticklabels(['Pre-COVID', 'Post-COVID'])
        axes[1, 0].legend()
        axes[1, 0].grid(axis='y', alpha=0.3)

        # 4. Annual timeline with COVID marker
        annual_totals = self.df.groupby('filing_year')['total_offering_amount'].sum() / 1_000_000
        axes[1, 1].bar(annual_totals.index, annual_totals.values, color=['steelblue' if y < 2020 else 'coral' for y in annual_totals.index], alpha=0.7)
        axes[1, 1].axvline(x=2019.5, color='red', linestyle='--', linewidth=2, label='COVID-19 Onset')
        axes[1, 1].set_title('Total Capital Raised (Pre vs Post COVID)', fontsize=14, fontweight='bold')
        axes[1, 1].set_xlabel('Year')
        axes[1, 1].set_ylabel('Amount ($ Millions)')
        axes[1, 1].legend()
        axes[1, 1].grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / 'covid_impact_comparison.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved to {output_path}")
        plt.close()

    def plot_geographic_distribution(self):
        """Geographic and jurisdiction visualizations"""
        logger.info("Creating geographic distribution...")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Top incorporation jurisdictions
        top_jurisdictions = self.df['jurisdiction_of_incorporation'].value_counts().head(10)
        axes[0, 0].barh(range(len(top_jurisdictions)), top_jurisdictions.values, color='teal', alpha=0.7)
        axes[0, 0].set_yticks(range(len(top_jurisdictions)))
        axes[0, 0].set_yticklabels(top_jurisdictions.index)
        axes[0, 0].set_title('Top 10 Incorporation Jurisdictions', fontsize=14, fontweight='bold')
        axes[0, 0].set_xlabel('Number of Filings')
        axes[0, 0].grid(axis='x', alpha=0.3)
        axes[0, 0].invert_yaxis()

        # 2. Principal business states
        top_states = self.df['issuer_state'].value_counts().head(10)
        axes[0, 1].barh(range(len(top_states)), top_states.values, color='green', alpha=0.7)
        axes[0, 1].set_yticks(range(len(top_states)))
        axes[0, 1].set_yticklabels(top_states.index)
        axes[0, 1].set_title('Top 10 Principal Business States', fontsize=14, fontweight='bold')
        axes[0, 1].set_xlabel('Number of Filings')
        axes[0, 1].grid(axis='x', alpha=0.3)
        axes[0, 1].invert_yaxis()

        # 3. Average offering by jurisdiction (top 5)
        top_5_jur = self.df['jurisdiction_of_incorporation'].value_counts().head(5).index
        jur_avg = self.df[self.df['jurisdiction_of_incorporation'].isin(top_5_jur)].groupby(
            'jurisdiction_of_incorporation'
        )['total_offering_amount'].mean() / 1_000_000

        axes[1, 0].bar(range(len(jur_avg)), jur_avg.values, color='purple', alpha=0.7)
        axes[1, 0].set_xticks(range(len(jur_avg)))
        axes[1, 0].set_xticklabels(jur_avg.index, rotation=45, ha='right')
        axes[1, 0].set_title('Average Offering Size by Jurisdiction (Top 5)', fontsize=14, fontweight='bold')
        axes[1, 0].set_ylabel('Amount ($ Millions)')
        axes[1, 0].grid(axis='y', alpha=0.3)

        # 4. Entity type distribution
        entity_types = self.df['entity_type'].value_counts().head(8)
        axes[1, 1].pie(entity_types.values, labels=entity_types.index, autopct='%1.1f%%', startangle=90)
        axes[1, 1].set_title('Entity Type Distribution', fontsize=14, fontweight='bold')

        plt.tight_layout()
        output_path = self.output_dir / 'geographic_distribution.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved to {output_path}")
        plt.close()

    def plot_securities_and_exemptions(self):
        """Securities types and exemption rules"""
        logger.info("Creating securities and exemptions visualization...")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Securities type distribution
        securities_data = {
            'Equity': self.df['equity_type'].sum(),
            'Debt': self.df['debt_type'].sum(),
            'Partnership': self.df['partnership_interest'].sum()
        }

        axes[0, 0].bar(securities_data.keys(), securities_data.values(), color=['steelblue', 'coral', 'green'], alpha=0.7)
        axes[0, 0].set_title('Securities Type Distribution', fontsize=14, fontweight='bold')
        axes[0, 0].set_ylabel('Count')
        axes[0, 0].grid(axis='y', alpha=0.3)

        # 2. Exemption rule usage over time
        rule_506b_annual = self.df.groupby('filing_year')['rule_506b'].sum()
        rule_506c_annual = self.df.groupby('filing_year')['rule_506c'].sum()

        axes[0, 1].plot(rule_506b_annual.index, rule_506b_annual.values, marker='o', label='Rule 506(b)', linewidth=2)
        axes[0, 1].plot(rule_506c_annual.index, rule_506c_annual.values, marker='s', label='Rule 506(c)', linewidth=2)
        axes[0, 1].set_title('Exemption Rule Usage Over Time', fontsize=14, fontweight='bold')
        axes[0, 1].set_xlabel('Year')
        axes[0, 1].set_ylabel('Count')
        axes[0, 1].legend()
        axes[0, 1].grid(alpha=0.3)

        # 3. Amendment rate by year
        amendment_rate = self.df.groupby('filing_year')['is_amendment'].sum() / self.df.groupby('filing_year').size() * 100
        axes[1, 0].bar(amendment_rate.index, amendment_rate.values, color='orange', alpha=0.7)
        axes[1, 0].set_title('Amendment Rate by Year', fontsize=14, fontweight='bold')
        axes[1, 0].set_xlabel('Year')
        axes[1, 0].set_ylabel('Percentage (%)')
        axes[1, 0].grid(axis='y', alpha=0.3)

        # 4. Overall exemption distribution
        exemption_data = {
            'Rule 506(b)': self.df['rule_506b'].sum(),
            'Rule 506(c)': self.df['rule_506c'].sum(),
            'Rule 504(b)': self.df['rule_504b'].sum()
        }

        axes[1, 1].pie(exemption_data.values(), labels=exemption_data.keys(), autopct='%1.1f%%', startangle=90)
        axes[1, 1].set_title('Overall Exemption Rule Distribution', fontsize=14, fontweight='bold')

        plt.tight_layout()
        output_path = self.output_dir / 'securities_and_exemptions.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved to {output_path}")
        plt.close()

    def plot_correlation_matrix(self):
        """Correlation matrix of key numerical variables"""
        logger.info("Creating correlation matrix...")

        # Select numerical columns
        numeric_cols = [
            'total_offering_amount',
            'total_amount_sold',
            'total_number_of_investors',
            'minimum_investment',
            'offering_utilization'
        ]

        # Filter columns that exist
        available_cols = [col for col in numeric_cols if col in self.df.columns]

        if len(available_cols) < 2:
            logger.warning("Not enough numerical columns for correlation matrix")
            return

        corr_data = self.df[available_cols].corr()

        plt.figure(figsize=(10, 8))
        sns.heatmap(corr_data, annot=True, fmt='.2f', cmap='coolwarm', center=0,
                   square=True, linewidths=1, cbar_kws={"shrink": 0.8})
        plt.title('Correlation Matrix of Key Variables', fontsize=14, fontweight='bold')
        plt.tight_layout()

        output_path = self.output_dir / 'correlation_matrix.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved to {output_path}")
        plt.close()

    def plot_offering_size_distribution(self):
        """Distribution and histogram of offering sizes"""
        logger.info("Creating offering size distribution...")

        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        # 1. Histogram with log scale
        offering_amounts = self.df['total_offering_amount'].dropna() / 1_000_000

        axes[0].hist(offering_amounts, bins=50, color='steelblue', alpha=0.7, edgecolor='black')
        axes[0].set_title('Distribution of Offering Amounts', fontsize=14, fontweight='bold')
        axes[0].set_xlabel('Offering Amount ($ Millions)')
        axes[0].set_ylabel('Frequency')
        axes[0].grid(axis='y', alpha=0.3)

        # 2. Box plot by year
        years_to_plot = sorted(self.df['filing_year'].dropna().unique())
        data_by_year = [
            self.df[self.df['filing_year'] == year]['total_offering_amount'].dropna() / 1_000_000
            for year in years_to_plot
        ]

        axes[1].boxplot(data_by_year, labels=years_to_plot)
        axes[1].set_title('Offering Amount Distribution by Year', fontsize=14, fontweight='bold')
        axes[1].set_xlabel('Year')
        axes[1].set_ylabel('Offering Amount ($ Millions)')
        axes[1].grid(axis='y', alpha=0.3)
        plt.xticks(rotation=45)

        plt.tight_layout()
        output_path = self.output_dir / 'offering_size_distribution.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved to {output_path}")
        plt.close()

    def generate_all_visualizations(self):
        """Generate all visualization outputs"""
        logger.info("=" * 80)
        logger.info("Generating All Visualizations")
        logger.info("=" * 80)

        self.plot_annual_offering_trends()
        self.plot_investor_trends()
        self.plot_covid_comparison()
        self.plot_geographic_distribution()
        self.plot_securities_and_exemptions()
        self.plot_correlation_matrix()
        self.plot_offering_size_distribution()

        logger.info("All visualizations complete!")


def main():
    """Main execution"""
    project_dir = Path(__file__).parent.parent
    data_path = project_dir / 'data' / 'processed' / 'broadway_form_d_2010_2025.csv'
    visuals_dir = project_dir / 'visuals'

    if not data_path.exists():
        logger.error(f"Data file not found: {data_path}")
        logger.info("Please run collect_form_d_data.py first")
        return

    visualizer = BroadwayFormDVisualizer(data_path, visuals_dir)
    visualizer.generate_all_visualizations()


if __name__ == "__main__":
    main()

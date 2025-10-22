#!/usr/bin/env python3
"""
Sample Data Generator for Broadway Form D Analysis
Generates realistic sample data for demonstration and testing
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SampleDataGenerator:
    """Generates realistic sample Form D data for Broadway productions"""

    SHOW_NAMES = [
        "Hamilton Productions LLC", "Hadestown Broadway LLC", "Lion King Theatrical LP",
        "Wicked Broadway Productions", "Phantom of the Opera LLC", "Chicago Musical Productions",
        "Moulin Rouge! The Musical LLC", "Funny Girl Broadway LP", "Music Man Productions LLC",
        "Harry Potter and the Cursed Child LLC", "Beetlejuice Productions", "Back to the Future Musical LLC",
        "Les Misérables Broadway Productions", "Dear Evan Hansen LLC", "Come From Away Productions",
        "Six the Musical LLC", "Mrs. Doubtfire Broadway LP", "Mean Girls Musical Productions",
        "Frozen Broadway LLC", "Aladdin Theatrical Productions", "Book of Mormon LLC",
        "Jersey Boys Productions", "Kinky Boots Broadway LLC", "Waitress Musical Productions",
        "Anastasia Broadway LLC", "Spring Awakening Productions", "Cabaret Revival LLC",
        "Company Broadway Productions", "Into the Woods Musical LLC", "Sweeney Todd Productions",
        "A Strange Loop LLC", "MJ the Musical Productions", "Some Like It Hot Broadway LLC",
        "& Juliet Musical Productions", "Almost Famous Broadway LLC", "Paradise Square Productions",
        "Kimberly Akimbo LLC", "Leopoldstadt Broadway Productions", "Ohio State Murders LLC",
        "The Kite Runner Theatrical LP", "Life of Pi Broadway LLC", "POTUS Broadway Productions"
    ]

    JURISDICTIONS = ['DE', 'NY', 'CA', 'NV', 'CT', 'NJ', 'IL']
    STATES = ['NY', 'CA', 'IL', 'MA', 'CT', 'NJ', 'PA', 'TX']
    ENTITY_TYPES = ['Limited Liability Company', 'Limited Partnership', 'Corporation']

    def __init__(self, output_dir: Path, num_filings: int = 150):
        """
        Initialize generator

        Args:
            output_dir: Directory to save generated data
            num_filings: Number of sample filings to generate
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.num_filings = num_filings

    def generate_filing_date(self, year: int) -> datetime:
        """Generate random filing date within year"""
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
        time_between = end_date - start_date
        days_between = time_between.days
        random_days = random.randrange(days_between)
        return start_date + timedelta(days=random_days)

    def generate_offering_amount(self, year: int) -> float:
        """Generate realistic offering amount (increases over time)"""
        # Base amount increases over years
        base_multiplier = 1 + (year - 2010) * 0.05

        # Different tiers of productions
        tier = random.choices(
            ['small', 'medium', 'large', 'blockbuster'],
            weights=[0.3, 0.4, 0.25, 0.05]
        )[0]

        if tier == 'small':
            amount = random.uniform(500_000, 3_000_000)
        elif tier == 'medium':
            amount = random.uniform(3_000_000, 10_000_000)
        elif tier == 'large':
            amount = random.uniform(10_000_000, 30_000_000)
        else:  # blockbuster
            amount = random.uniform(30_000_000, 75_000_000)

        return round(amount * base_multiplier, 2)

    def generate_sample_data(self) -> pd.DataFrame:
        """Generate complete sample dataset"""
        logger.info(f"Generating {self.num_filings} sample Form D filings...")

        data = []

        for i in range(self.num_filings):
            # Random year between 2010 and 2025
            year = random.randint(2010, 2024)

            # Select random show
            entity_name = random.choice(self.SHOW_NAMES)

            # Generate filing data
            filing_date = self.generate_filing_date(year)
            is_amendment = random.random() < 0.15  # 15% are amendments

            # Financial data
            total_offering = self.generate_offering_amount(year)
            sold_percentage = random.uniform(0.4, 1.0)
            total_sold = round(total_offering * sold_percentage, 2)
            total_remaining = round(total_offering - total_sold, 2)

            # Investor data
            has_non_accredited = random.random() < 0.3  # 30% have non-accredited

            # Number of investors (more in recent years, post-COVID)
            if year >= 2020:
                num_investors = random.randint(50, 500)
            elif year >= 2015:
                num_investors = random.randint(30, 200)
            else:
                num_investors = random.randint(10, 100)

            # Minimum investment (decreases over time - democratization)
            if year >= 2020:
                min_investment = random.choice([25000, 50000, 100000, 250000])
            elif year >= 2015:
                min_investment = random.choice([50000, 100000, 250000, 500000])
            else:
                min_investment = random.choice([100000, 250000, 500000, 1000000])

            # Securities type
            equity_type = random.random() < 0.7  # 70% equity
            debt_type = random.random() < 0.2  # 20% debt
            partnership_interest = random.random() < 0.3  # 30% partnership

            # Exemptions (506b more common pre-2013, 506c increases after)
            if year >= 2013:
                rule_506b = random.random() < 0.6
                rule_506c = random.random() < 0.35
            else:
                rule_506b = random.random() < 0.85
                rule_506c = False

            rule_504b = random.random() < 0.05

            # Create filing record
            filing = {
                'accession_number': f'0001234567-{year % 100:02d}-{i:06d}',
                'filing_date': filing_date.strftime('%Y-%m-%d'),
                'amendment_date': None,
                'is_amendment': is_amendment,
                'entity_name': entity_name,
                'jurisdiction_of_incorporation': random.choice(self.JURISDICTIONS),
                'year_of_incorporation': year - random.randint(0, 3),
                'entity_type': random.choice(self.ENTITY_TYPES),
                'issuer_street1': f'{random.randint(1, 999)} Broadway',
                'issuer_street2': f'Suite {random.randint(100, 2000)}' if random.random() < 0.5 else None,
                'issuer_city': 'New York',
                'issuer_state': random.choice(self.STATES),
                'issuer_zip': f'{random.randint(10000, 10999)}',
                'issuer_phone': f'212-555-{random.randint(1000, 9999)}',
                'naics_code': '711110',  # Theatre companies and dinner theatres
                'industry_group': 'Theatrical Production',
                'total_offering_amount': total_offering,
                'total_amount_sold': total_sold,
                'total_remaining': total_remaining,
                'has_non_accredited_investors': has_non_accredited,
                'total_number_of_investors': num_investors,
                'minimum_investment': min_investment,
                'equity_type': equity_type,
                'debt_type': debt_type,
                'partnership_interest': partnership_interest,
                'securities_other_desc': None,
                'business_combination': False,
                'revenue_range': random.choice(['$1-5M', '$5-25M', '$25-100M', 'Over $100M']),
                'aggregate_net_asset_value_range': None,
                'rule_506b': rule_506b,
                'rule_506c': rule_506c,
                'rule_504b': rule_504b,
                'section_3c': False,
                'section_3c1': False,
                'section_3c7': False,
                'primary_officer_name': f'John Doe {i}',
                'primary_officer_title': 'Managing Member',
                'related_person_names': f'John Doe {i}, Jane Smith {i}',
                'broker_dealer_name': 'Broadway Capital Partners' if random.random() < 0.3 else None,
                'broker_dealer_crd': str(random.randint(100000, 999999)) if random.random() < 0.3 else None,
                'uses_intermediary': random.random() < 0.3,
                'offering_sales_commissions': round(total_sold * 0.05, 2) if random.random() < 0.3 else None,
                'finders_fees': round(total_sold * 0.02, 2) if random.random() < 0.2 else None,
                'offering_date': (filing_date - timedelta(days=random.randint(30, 180))).strftime('%Y-%m-%d'),
                'termination_date': None,
                'more_than_one_year': random.random() < 0.4
            }

            data.append(filing)

        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} sample filings")

        return df

    def save_sample_data(self, df: pd.DataFrame, filename: str = 'broadway_form_d_2010_2025.csv'):
        """Save sample data to CSV"""
        output_path = self.output_dir / filename
        df.to_csv(output_path, index=False)
        logger.info(f"Saved sample data to {output_path}")

        # Also save summary
        summary = {
            'total_filings': len(df),
            'date_range': f"{df['filing_date'].min()} to {df['filing_date'].max()}",
            'total_capital_offered': df['total_offering_amount'].sum(),
            'total_capital_sold': df['total_amount_sold'].sum(),
            'unique_shows': df['entity_name'].nunique(),
            'years_covered': sorted(df['filing_date'].apply(lambda x: x[:4]).unique())
        }

        logger.info("\nSample Data Summary:")
        for key, value in summary.items():
            logger.info(f"  {key}: {value}")

        return output_path


def main():
    """Main execution"""
    project_dir = Path(__file__).parent.parent
    output_dir = project_dir / 'data' / 'processed'

    # Generate 200 sample filings
    generator = SampleDataGenerator(output_dir, num_filings=200)
    df = generator.generate_sample_data()
    generator.save_sample_data(df)

    logger.info("\nSample data generation complete!")
    logger.info("You can now run analyze_form_d_data.py and visualize_form_d_data.py")


if __name__ == "__main__":
    main()

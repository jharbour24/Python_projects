#!/usr/bin/env python3
"""
Form D XML Parser
Extracts detailed financial and structural data from SEC Form D XML filings
"""

import xml.etree.ElementTree as ET
import pandas as pd
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FormDParser:
    """Parses SEC Form D XML filings and extracts structured data"""

    # XML namespaces used in Form D filings
    NAMESPACES = {
        '': 'http://www.sec.gov/edgar/document/thirteenf/informationtable',
        'ns1': 'http://www.sec.gov/edgar/formd'
    }

    def __init__(self):
        self.parsed_filings = []

    def parse_xml_filing(self, xml_content: str, accession_number: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single Form D XML filing

        Args:
            xml_content: Raw XML content string
            accession_number: SEC accession number for tracking

        Returns:
            Dictionary containing extracted fields
        """
        try:
            root = ET.fromstring(xml_content)

            filing_data = {
                'accession_number': accession_number,
                'filing_date': None,
                'amendment_date': None,
                'is_amendment': False,
                'entity_name': None,
                'jurisdiction_of_incorporation': None,
                'year_of_incorporation': None,
                'entity_type': None,
                'issuer_street1': None,
                'issuer_street2': None,
                'issuer_city': None,
                'issuer_state': None,
                'issuer_zip': None,
                'issuer_phone': None,
                'naics_code': None,
                'industry_group': None,
                'total_offering_amount': None,
                'total_amount_sold': None,
                'total_remaining': None,
                'has_non_accredited_investors': None,
                'total_number_of_investors': None,
                'minimum_investment': None,
                'equity_type': None,
                'debt_type': None,
                'partnership_interest': None,
                'securities_other_desc': None,
                'business_combination': False,
                'revenue_range': None,
                'aggregate_net_asset_value_range': None,
                'rule_506b': False,
                'rule_506c': False,
                'rule_504b': False,
                'section_3c': False,
                'section_3c1': False,
                'section_3c7': False,
                'primary_officer_name': None,
                'primary_officer_title': None,
                'related_person_names': [],
                'broker_dealer_name': None,
                'broker_dealer_crd': None,
                'uses_intermediary': False,
                'offering_sales_commissions': None,
                'finders_fees': None,
                'offering_date': None,
                'termination_date': None,
                'more_than_one_year': None
            }

            # Parse header information
            filing_data['filing_date'] = self._get_element_text(root, './/filingDate')
            filing_data['is_amendment'] = self._get_element_text(root, './/isAmendment') == 'true'

            # Parse issuer information
            issuer = root.find('.//issuer')
            if issuer is not None:
                filing_data['entity_name'] = self._get_element_text(issuer, './/entityName')
                filing_data['jurisdiction_of_incorporation'] = self._get_element_text(
                    issuer, './/jurisdictionOfInc')
                filing_data['year_of_incorporation'] = self._get_element_text(
                    issuer, './/yearOfInc//value')
                filing_data['entity_type'] = self._get_element_text(issuer, './/entityType')

                # Address
                address = issuer.find('.//issuerAddress')
                if address is not None:
                    filing_data['issuer_street1'] = self._get_element_text(address, './/street1')
                    filing_data['issuer_street2'] = self._get_element_text(address, './/street2')
                    filing_data['issuer_city'] = self._get_element_text(address, './/city')
                    filing_data['issuer_state'] = self._get_element_text(address, './/stateOrCountry')
                    filing_data['issuer_zip'] = self._get_element_text(address, './/zipCode')

                filing_data['issuer_phone'] = self._get_element_text(issuer, './/issuerPhoneNumber')

                # Industry classification
                filing_data['industry_group'] = self._get_element_text(
                    issuer, './/industryGroup//industryGroupType')

                # NAICS code (if present)
                naics = issuer.find('.//naicsCode')
                if naics is not None:
                    filing_data['naics_code'] = naics.text

                # Revenue/asset ranges
                filing_data['revenue_range'] = self._get_element_text(issuer, './/revenueRange')
                filing_data['aggregate_net_asset_value_range'] = self._get_element_text(
                    issuer, './/aggregateNetAssetValueRange')

            # Parse offering data
            offering_data = root.find('.//offeringData')
            if offering_data is not None:
                # Industry group
                filing_data['industry_group'] = self._get_element_text(
                    offering_data, './/industryGroup//industryGroupType')

                # Financial amounts
                size_of_offering = offering_data.find('.//sizeOfOffering')
                if size_of_offering is not None:
                    filing_data['total_offering_amount'] = self._parse_amount(
                        self._get_element_text(size_of_offering, './/totalOfferingAmount'))
                    filing_data['total_amount_sold'] = self._parse_amount(
                        self._get_element_text(size_of_offering, './/totalAmountSold'))
                    filing_data['total_remaining'] = self._parse_amount(
                        self._get_element_text(size_of_offering, './/totalRemaining'))

                # Investor information
                filing_data['has_non_accredited_investors'] = self._get_element_text(
                    offering_data, './/hasNonAccreditedInvestors') == 'true'
                filing_data['total_number_of_investors'] = self._parse_int(
                    self._get_element_text(offering_data, './/totalNumberAlreadyInvested'))

                # Minimum investment
                filing_data['minimum_investment'] = self._parse_amount(
                    self._get_element_text(offering_data, './/minimumInvestmentAccepted'))

                # Securities offered
                types = offering_data.find('.//typeOfSecuritiesOffered')
                if types is not None:
                    filing_data['equity_type'] = self._get_element_text(types, './/isEquityType') == 'true'
                    filing_data['debt_type'] = self._get_element_text(types, './/isDebtType') == 'true'
                    filing_data['partnership_interest'] = self._get_element_text(
                        types, './/isPooledInvestmentFundType') == 'true'
                    filing_data['securities_other_desc'] = self._get_element_text(types, './/otherType')

                filing_data['business_combination'] = self._get_element_text(
                    offering_data, './/isBusinessCombinationTransaction') == 'true'

                # Sales compensation
                sales_comp = offering_data.find('.//salesCompensationList//salesCompensation')
                if sales_comp is not None:
                    filing_data['uses_intermediary'] = True
                    recipient = sales_comp.find('.//recipient')
                    if recipient is not None:
                        filing_data['broker_dealer_name'] = self._get_element_text(recipient, './/recipientName')
                        filing_data['broker_dealer_crd'] = self._get_element_text(
                            recipient, './/recipientCRDNumber')

                        # Commission amounts
                        states = sales_comp.find('.//statesOfSolicitationList//statesOfSolicitation')
                        if states is not None:
                            filing_data['offering_sales_commissions'] = self._parse_amount(
                                self._get_element_text(states, './/dollarAmountOfSalesCommissions'))
                            filing_data['finders_fees'] = self._parse_amount(
                                self._get_element_text(states, './/dollarAmountOfFindersFees'))

                # Offering dates
                filing_data['offering_date'] = self._get_element_text(offering_data, './/firstSale')
                filing_data['more_than_one_year'] = self._get_element_text(
                    offering_data, './/moreThanOneYear') == 'true'

            # Parse exemptions
            exemptions = root.find('.//federalExemptionsExclusions')
            if exemptions is not None:
                filing_data['rule_506b'] = self._get_element_text(exemptions, './/item06') == 'true'
                filing_data['rule_506c'] = self._get_element_text(exemptions, './/item06b') == 'true'
                filing_data['rule_504b'] = self._get_element_text(exemptions, './/item04') == 'true'
                filing_data['section_3c'] = self._get_element_text(exemptions, './/item3C') == 'true'
                filing_data['section_3c1'] = self._get_element_text(exemptions, './/item3C1') == 'true'
                filing_data['section_3c7'] = self._get_element_text(exemptions, './/item3C7') == 'true'

            # Parse related persons (officers, directors, promoters)
            related_persons = root.findall('.//relatedPersonInfo//relatedPersonsList//relatedPersons')
            related_names = []

            for person in related_persons:
                name = self._get_element_text(person, './/relatedPersonName//firstName')
                last_name = self._get_element_text(person, './/relatedPersonName//lastName')
                if name or last_name:
                    full_name = f"{name} {last_name}".strip() if name and last_name else (name or last_name)
                    related_names.append(full_name)

                    # Capture primary officer
                    if filing_data['primary_officer_name'] is None:
                        filing_data['primary_officer_name'] = full_name
                        relationships = person.findall('.//relatedPersonRelationshipList//relationship')
                        if relationships:
                            filing_data['primary_officer_title'] = self._get_element_text(
                                relationships[0], '.')

            filing_data['related_person_names'] = ', '.join(related_names) if related_names else None

            # Signature info (often contains most recent officer info)
            signature = root.find('.//signatureBlock')
            if signature is not None:
                signer_name = self._get_element_text(signature, './/signature//issuerName')
                if signer_name and not filing_data['primary_officer_name']:
                    filing_data['primary_officer_name'] = signer_name

            return filing_data

        except ET.ParseError as e:
            logger.error(f"XML parsing error for {accession_number}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing {accession_number}: {e}")
            return None

    def _get_element_text(self, parent: ET.Element, xpath: str) -> Optional[str]:
        """Safely extract text from XML element"""
        if parent is None:
            return None
        element = parent.find(xpath)
        if element is not None and element.text:
            return element.text.strip()
        return None

    def _parse_amount(self, value: Optional[str]) -> Optional[float]:
        """Convert string amount to float"""
        if not value:
            return None
        try:
            # Remove commas and convert to float
            cleaned = re.sub(r'[,\s$]', '', value)
            return float(cleaned)
        except (ValueError, AttributeError):
            return None

    def _parse_int(self, value: Optional[str]) -> Optional[int]:
        """Convert string to integer"""
        if not value:
            return None
        try:
            return int(value)
        except (ValueError, AttributeError):
            return None

    def parse_multiple_filings(self, filings: List[tuple]) -> pd.DataFrame:
        """
        Parse multiple Form D XML filings

        Args:
            filings: List of tuples (xml_content, accession_number)

        Returns:
            DataFrame with all parsed filings
        """
        parsed_data = []

        for xml_content, accession_number in filings:
            logger.info(f"Parsing filing {accession_number}")
            filing_data = self.parse_xml_filing(xml_content, accession_number)
            if filing_data:
                parsed_data.append(filing_data)

        if parsed_data:
            return pd.DataFrame(parsed_data)
        else:
            return pd.DataFrame()

    def save_parsed_data(self, df: pd.DataFrame, output_path: Path):
        """Save parsed data to CSV"""
        df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(df)} parsed filings to {output_path}")


def main():
    """Example usage"""
    parser = FormDParser()

    # Example: This would be called with actual XML content
    # filings = [(xml_content1, acc_num1), (xml_content2, acc_num2), ...]
    # df = parser.parse_multiple_filings(filings)
    # parser.save_parsed_data(df, Path('output.csv'))

    logger.info("Form D Parser initialized and ready")


if __name__ == "__main__":
    main()

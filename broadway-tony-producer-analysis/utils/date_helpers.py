"""
Date parsing and computation utilities.

Handles date normalization, season assignment, and run-length calculations.
"""

import re
from datetime import datetime
from typing import Optional, Union
import pandas as pd
from dateutil import parser


def parse_date(date_str: Union[str, datetime, pd.Timestamp, None],
               default: Optional[datetime] = None) -> Optional[pd.Timestamp]:
    """
    Parse a date string into a pandas Timestamp.

    Parameters
    ----------
    date_str : str, datetime, pd.Timestamp, or None
        Date to parse
    default : datetime, optional
        Default value to return if parsing fails

    Returns
    -------
    pd.Timestamp or None
        Parsed date, or default/None if parsing fails
    """
    if date_str is None or (isinstance(date_str, float) and pd.isna(date_str)):
        return default

    if isinstance(date_str, pd.Timestamp):
        return date_str

    if isinstance(date_str, datetime):
        return pd.Timestamp(date_str)

    if isinstance(date_str, str):
        # Handle "still running" or similar indicators
        if date_str.lower() in ['still running', 'open', 'running', 'n/a', '']:
            return default

        try:
            # Try dateutil parser first (handles many formats)
            parsed = parser.parse(date_str)
            return pd.Timestamp(parsed)
        except (ValueError, TypeError, parser.ParserError):
            pass

        # Try common Broadway date formats
        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%Y',
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str.strip(), fmt)
                return pd.Timestamp(parsed)
            except ValueError:
                continue

    return default


def compute_days_running(opening_date: pd.Timestamp,
                         closing_date: Optional[pd.Timestamp],
                         as_of_date: Optional[pd.Timestamp] = None) -> Optional[float]:
    """
    Compute the number of days a show has been running.

    Parameters
    ----------
    opening_date : pd.Timestamp
        Date the show opened
    closing_date : pd.Timestamp or None
        Date the show closed (None if still running)
    as_of_date : pd.Timestamp, optional
        If show is still running, compute days as of this date
        (default: today)

    Returns
    -------
    float or None
        Number of days running, or None if cannot compute
    """
    if pd.isna(opening_date):
        return None

    if pd.isna(closing_date):
        # Still running
        if as_of_date is None:
            as_of_date = pd.Timestamp.now()
        end_date = as_of_date
    else:
        end_date = closing_date

    return (end_date - opening_date).days


def compute_weeks_running(opening_date: pd.Timestamp,
                          closing_date: Optional[pd.Timestamp],
                          as_of_date: Optional[pd.Timestamp] = None) -> Optional[float]:
    """
    Compute the number of weeks a show has been running.

    Parameters
    ----------
    opening_date : pd.Timestamp
        Date the show opened
    closing_date : pd.Timestamp or None
        Date the show closed (None if still running)
    as_of_date : pd.Timestamp, optional
        If show is still running, compute weeks as of this date
        (default: today)

    Returns
    -------
    float or None
        Number of weeks running (as float), or None if cannot compute
    """
    days = compute_days_running(opening_date, closing_date, as_of_date)
    if days is None:
        return None
    return days / 7.0


def get_season_from_date(date: pd.Timestamp) -> str:
    """
    Determine the Broadway season from a date.

    Broadway seasons run from approximately May to April.
    A show opening in September 2010 is in the 2010-2011 season.
    A show opening in March 2011 is also in the 2010-2011 season.

    Parameters
    ----------
    date : pd.Timestamp
        Opening date

    Returns
    -------
    str
        Season string, e.g., '2010-2011'
    """
    if pd.isna(date):
        return None

    year = date.year
    month = date.month

    # Season cutoff: May 1
    # If show opens May-December, it's in the year-year+1 season
    # If show opens January-April, it's in the year-1-year season
    if month >= 5:
        season_start = year
    else:
        season_start = year - 1

    return f"{season_start}-{season_start + 1}"


def extract_year_from_title(title: str) -> Optional[int]:
    """
    Extract a year from a show title if present (e.g., "Hamilton (2015)").

    Parameters
    ----------
    title : str
        Show title

    Returns
    -------
    int or None
        Extracted year, or None if not found
    """
    match = re.search(r'\((\d{4})\)', title)
    if match:
        return int(match.group(1))
    return None

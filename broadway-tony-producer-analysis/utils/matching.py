"""
Title normalization and fuzzy matching utilities.

Provides functions to normalize Broadway show titles and match them
across different data sources (Tony Awards, IBDB, grosses data, etc.).
"""

import re
from typing import Optional, Tuple, List
from fuzzywuzzy import fuzz
import pandas as pd


def normalize_title(title: str) -> str:
    """
    Normalize a Broadway show title for matching.

    Steps:
    1. Convert to lowercase
    2. Remove articles (a, an, the) from the beginning
    3. Remove punctuation except spaces and hyphens
    4. Remove extra whitespace
    5. Strip leading/trailing spaces

    Parameters
    ----------
    title : str
        Raw show title

    Returns
    -------
    str
        Normalized title
    """
    if not isinstance(title, str):
        return ""

    # Lowercase
    normalized = title.lower().strip()

    # Remove leading articles
    normalized = re.sub(r'^(the|a|an)\s+', '', normalized)

    # Remove common suffixes like (Revival), (2023), etc. for matching
    normalized = re.sub(r'\s*\(.*?\)\s*', ' ', normalized)

    # Remove punctuation except spaces and hyphens, keep apostrophes
    normalized = re.sub(r'[^\w\s\-\']', '', normalized)

    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    return normalized


def create_show_id(title: str, year: Optional[int] = None, opening_date: Optional[pd.Timestamp] = None) -> str:
    """
    Create a stable show_id from title and year.

    Format: Title_Year (e.g., "Hadestown_2019")

    Parameters
    ----------
    title : str
        Show title
    year : int, optional
        Year (preferably opening year)
    opening_date : pd.Timestamp, optional
        Opening date (year will be extracted if year not provided)

    Returns
    -------
    str
        Stable show ID
    """
    # Normalize title for ID (more aggressive than for matching)
    normalized = title.strip()
    normalized = re.sub(r'\s*\(.*?\)\s*', '', normalized)  # Remove parentheticals
    normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove all punctuation
    normalized = re.sub(r'\s+', '_', normalized.strip())  # Replace spaces with underscores
    normalized = normalized.title()  # Title case

    # Determine year
    if year is None and opening_date is not None and not pd.isna(opening_date):
        year = opening_date.year

    if year:
        return f"{normalized}_{year}"
    else:
        return normalized


def fuzzy_match_titles(source_title: str,
                       target_titles: List[str],
                       threshold: int = 85) -> Tuple[Optional[str], int]:
    """
    Find the best fuzzy match for source_title among target_titles.

    Uses fuzzywuzzy token_sort_ratio, which is robust to word order.

    Parameters
    ----------
    source_title : str
        Title to match
    target_titles : list of str
        Candidate titles to match against
    threshold : int
        Minimum similarity score (0-100) to consider a match

    Returns
    -------
    tuple of (str or None, int)
        (best_match, best_score) where best_match is None if no match above threshold
    """
    source_norm = normalize_title(source_title)

    if not target_titles:
        return None, 0

    best_match = None
    best_score = 0

    for target in target_titles:
        target_norm = normalize_title(target)
        score = fuzz.token_sort_ratio(source_norm, target_norm)

        if score > best_score:
            best_score = score
            best_match = target

    if best_score >= threshold:
        return best_match, best_score
    else:
        return None, best_score


def clean_producer_name(name: str) -> str:
    """
    Clean and normalize a producer name.

    Parameters
    ----------
    name : str
        Raw producer name

    Returns
    -------
    str
        Cleaned name
    """
    if not isinstance(name, str):
        return ""

    cleaned = name.strip()

    # Remove common suffixes
    cleaned = re.sub(r',?\s*(Jr\.?|Sr\.?|III|II|IV)$', '', cleaned, flags=re.IGNORECASE)

    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned


def parse_producer_list(producer_text: str) -> List[str]:
    """
    Parse a raw producer text block into a list of individual producer names.

    Handles various separators: commas, semicolons, "and", newlines, etc.

    Parameters
    ----------
    producer_text : str
        Raw text containing producer names

    Returns
    -------
    list of str
        Individual producer names
    """
    if not isinstance(producer_text, str):
        return []

    # Replace common separators with semicolons
    text = producer_text.replace('\n', ';')
    text = re.sub(r'\s+and\s+', ';', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*,\s*', ';', text)

    # Split on semicolons
    producers = [p.strip() for p in text.split(';') if p.strip()]

    # Clean each name
    producers = [clean_producer_name(p) for p in producers]

    # Remove empty strings
    producers = [p for p in producers if p]

    # Remove duplicates while preserving order
    seen = set()
    unique_producers = []
    for p in producers:
        p_lower = p.lower()
        if p_lower not in seen:
            seen.add(p_lower)
            unique_producers.append(p)

    return unique_producers

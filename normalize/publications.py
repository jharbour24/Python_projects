"""
Publication name canonicalization.

DTLI uses publication logo image alt-text as the publication name,
which can vary: "NY Times", "New York Times", "The New York Times", "NYT".
This module maps all variants to a canonical form.
"""
import re

# Canonical name → list of known aliases / alt-text variants
_CANONICAL_MAP: dict[str, list[str]] = {
    "New York Times": [
        "ny times", "nyt", "new york times", "the new york times",
        "new-york-times", "nytimes",
    ],
    "Variety": ["variety", "variety.com"],
    "Hollywood Reporter": ["the hollywood reporter", "hollywood reporter", "thr"],
    "Time Out New York": ["time out new york", "time out ny", "timeout new york", "timeout ny"],
    "Vulture": ["vulture", "vulture.com"],
    "New York Post": ["ny post", "new york post", "nypost"],
    "New York Daily News": ["ny daily news", "new york daily news", "daily news"],
    "New York Observer": ["new york observer", "ny observer", "observer"],
    "The Wrap": ["the wrap", "wrap", "thewrap"],
    "Deadline": ["deadline", "deadline hollywood", "deadline.com"],
    "Entertainment Weekly": ["ew", "entertainment weekly", "ew.com"],
    "AM New York": ["am new york", "amny", "am-new york"],
    "Associated Press": ["ap", "associated press"],
    "Washington Post": ["washington post", "the washington post", "wapo"],
    "Los Angeles Times": ["la times", "los angeles times", "latimes"],
    "USA Today": ["usa today", "usatoday"],
    "TheaterMania": ["theatermania", "theater mania"],
    "New York Theatre Guide": ["new york theatre guide", "nytg", "ny theatre guide"],
    "Broadway.com": ["broadway.com", "broadway com"],
    "BroadwayWorld": ["broadwayworld", "broadway world", "broadwayworld.com"],
    "Theatrely": ["theatrely"],
    "New York Stage Review": ["new york stage review", "nysr", "ny stage review"],
    "New York Theater": ["new york theater", "ny theater", "newyorktheater.me"],
    "Backstage": ["backstage", "backstage.com"],
    "Stage Door": ["stage door", "stagedoor"],
    "Playbill": ["playbill", "playbill.com"],
    "People Magazine": ["people", "people magazine", "people.com"],
    "Mashable": ["mashable"],
    "New York Magazine": ["new york magazine", "new york mag", "nymag"],
}

# Build reverse lookup: alias → canonical
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in _CANONICAL_MAP.items():
    _ALIAS_TO_CANONICAL[canonical.lower()] = canonical
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias.lower()] = canonical


def canonicalize(raw_name: str) -> str:
    """
    Return the canonical publication name for a raw string.
    Falls back to title-casing the input if no match found.
    """
    norm = re.sub(r"\s+", " ", raw_name.lower().strip())
    if norm in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[norm]
    # Partial match: if any canonical key is contained in norm
    for alias, canonical in _ALIAS_TO_CANONICAL.items():
        if alias in norm and len(alias) > 4:
            return canonical
    return raw_name.strip().title()


def is_nyt(publication_name: str) -> bool:
    """Return True if this publication is the New York Times."""
    return canonicalize(publication_name) == "New York Times"

"""
Constitutional rules and checks for meme content.

Implements safety and community guidelines as code.
See CONSTITUTION.md for full documentation.
"""

import re
from typing import Optional

from .io_schemas import MemeCandidate


# ============================================================================
# Constitutional Rules
# ============================================================================

class ConstitutionalViolation(Exception):
    """Raised when content violates constitutional rules."""

    def __init__(self, rule: str, reason: str):
        self.rule = rule
        self.reason = reason
        super().__init__(f"Violation of {rule}: {reason}")


# Blocked patterns (case-insensitive)
BLOCKED_PATTERNS = {
    "slurs": [
        # Placeholder patterns; real implementation would have comprehensive list
        r"\bf[a4]gg[o0]t\b",
        r"\btr[a4]nny\b",
        r"\bd[y1]ke\b",  # Context-dependent; may need allowlist
    ],
    "explicit_sexual": [
        r"\bsex\s+worker\b",  # Avoid outing
        r"\bhook\s*up\s+spot\b",  # Avoid doxxing
        r"\bcruising\s+at\b",  # Avoid doxxing specific venues
    ],
    "doxxing": [
        r"\d{3}[-.\s]?\d{3}[-.\s]?\d{4}",  # Phone numbers
        r"\b\d{1,5}\s+\w+\s+(street|st|avenue|ave|road|rd|blvd)\b",  # Street addresses
        r"lives?\s+at\b",
        r"works?\s+at\s+[A-Z]",  # "works at XYZ"
    ],
    "violence": [
        r"\bkill\b",
        r"\bmurder\b",
        r"\bassault\b",
        r"\bharm\b",
    ],
}

# Strong profanity (allow PG-13, block R-rated)
BLOCKED_PROFANITY = [
    r"\bf+u+c+k+",
    r"\bs+h+i+t+",
    r"\bc+u+n+t+",
    r"\bd+i+c+k+",
]

# Required elements (at least one must be present)
REQUIRED_LOCAL_TERMS = [
    "Brooklyn", "Bushwick", "Bed-Stuy", "Williamsburg", "Ridgewood",
    "L train", "G train", "JMZ", "MTA",
    "venue", "cover", "line", "queue",
]


def check_constitution(candidate: MemeCandidate) -> tuple[bool, Optional[str]]:
    """
    Check if candidate violates constitutional rules.

    Returns:
        (is_valid, violation_reason)
    """
    text = f"{candidate.caption} {candidate.local_hook}".lower()

    # Rule 1: No slurs or hate speech
    for pattern in BLOCKED_PATTERNS["slurs"]:
        if re.search(pattern, text, re.IGNORECASE):
            return False, f"Contains blocked slur (pattern: {pattern})"

    # Rule 2: No explicit sexual content
    for pattern in BLOCKED_PATTERNS["explicit_sexual"]:
        if re.search(pattern, text, re.IGNORECASE):
            return False, f"Contains explicit sexual content (pattern: {pattern})"

    # Rule 3: No doxxing or private info
    for pattern in BLOCKED_PATTERNS["doxxing"]:
        if re.search(pattern, text, re.IGNORECASE):
            return False, f"Contains potential doxxing info (pattern: {pattern})"

    # Rule 4: No violence or threats
    for pattern in BLOCKED_PATTERNS["violence"]:
        if re.search(pattern, text, re.IGNORECASE):
            return False, f"Contains violent content (pattern: {pattern})"

    # Rule 5: No strong profanity
    for pattern in BLOCKED_PROFANITY:
        if re.search(pattern, text, re.IGNORECASE):
            return False, f"Contains blocked profanity (pattern: {pattern})"

    # Rule 6: Must have local specificity
    has_local = any(
        term.lower() in text
        for term in REQUIRED_LOCAL_TERMS
    )
    if not has_local:
        return False, "Missing required local/Brooklyn reference"

    # Rule 7: No ALL CAPS unless tone is "slightly unhinged"
    if candidate.caption.isupper() and candidate.tone != "slightly unhinged":
        return False, "ALL CAPS only allowed for 'slightly unhinged' tone"

    # Rule 8: No hashtags
    if "#" in candidate.caption:
        return False, "Hashtags not allowed in caption"

    # Rule 9: No venue names (specific check)
    # This is context-dependent; for now just check for "at [Venue]" pattern
    if re.search(r"\bat\s+[A-Z][a-z]+(?:'s)?\b", candidate.caption):
        # Could be "at Elsewhere" or similar
        # More sophisticated check would use venue name list
        pass  # Placeholder; implement with venue name list if available

    return True, None


def punch_up_check(candidate: MemeCandidate) -> tuple[bool, Optional[str]]:
    """
    Check if content punches up (at systems/situations) vs down (at people).

    This is a heuristic check; real implementation would be more sophisticated.

    Returns:
        (is_ok, warning)
    """
    text = f"{candidate.caption} {candidate.local_hook}".lower()

    # Good targets (systems, institutions, situations)
    punch_up_targets = [
        "mta", "train", "subway", "transit",
        "cover charge", "bouncer", "line",
        "gentrification", "rent", "landlord",
        "weather", "dress code",
    ]

    # Potentially problematic targets (people, groups)
    punch_down_indicators = [
        "they", "them", "those people",
        "tourists", "transplants",  # Can be punch-down
    ]

    has_punch_up = any(target in text for target in punch_up_targets)
    has_punch_down = any(indicator in text for indicator in punch_down_indicators)

    if has_punch_down and not has_punch_up:
        return False, "May be punching down at people rather than systems"

    return True, None


def self_deprecation_check(candidate: MemeCandidate) -> bool:
    """
    Check if content includes healthy self-deprecation.

    This is encouraged but not required.
    """
    text = f"{candidate.caption} {candidate.local_hook}".lower()

    self_indicators = ["i", "me", "my", "we", "us", "our"]
    return any(indicator in text for indicator in self_indicators)


def get_constitution_summary() -> dict[str, str]:
    """
    Get summary of all constitutional rules.

    Returns:
        Dict mapping rule names to descriptions
    """
    return {
        "no_slurs": "No slurs or hate speech targeting protected classes",
        "no_explicit_sexual": "No explicit sexual content or outing people",
        "no_doxxing": "No private info, addresses, phone numbers, or venue outing",
        "no_violence": "No violent content or threats",
        "no_strong_profanity": "Limit profanity to PG-13 level",
        "local_specificity": "Must include Brooklyn/transit/venue references",
        "no_all_caps": "No ALL CAPS unless tone is 'slightly unhinged'",
        "no_hashtags": "No hashtags in captions",
        "punch_up": "Punch up at systems, not down at people",
        "affectionate": "Affectionate scene in-jokes preferred",
    }

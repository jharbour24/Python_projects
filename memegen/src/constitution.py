"""
Constitutional rules for meme content - what's allowed and what's not.
"""

import re
from typing import Literal

from .io_schemas import MemeCandidate

# Constitutional rules as regex patterns and semantic checks
RULES = {
    "no_slurs": {
        "description": "No slurs or hate speech targeting protected groups",
        "patterns": [
            r"\b(f[a@]gg[o0]t|tr[a@]nn[y1]|dyke)\b",  # Common slurs (even reclaimed, avoid)
            r"\bretard(ed)?\b",
        ],
        "severity": "block",
    },
    "no_doxxing": {
        "description": "No private addresses, phone numbers, or personal identifying info",
        "patterns": [
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone numbers
            r"\b\d{1,5}\s+\w+\s+(street|st|avenue|ave|road|rd|place|pl)\b",  # Addresses
        ],
        "severity": "block",
    },
    "no_explicit_sexual": {
        "description": "No explicit sexual content beyond PG-13",
        "patterns": [
            r"\b(cock|dick|pussy|cum|fuck(ing)?|shit|bitch)\b",
        ],
        "severity": "warn",  # PG-13 is flexible
    },
    "no_real_names": {
        "description": "Don't name specific people unless they're public figures/promoters",
        "patterns": [
            r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+(said|told|did)\b",  # "Jane Doe said"
        ],
        "severity": "warn",
    },
    "require_local_hook": {
        "description": "Must reference Brooklyn/NYC/transit",
        "patterns": [],  # Checked semantically
        "severity": "block",
    },
    "punch_up": {
        "description": "Punch up, not down; self-deprecate, don't target vulnerable groups",
        "patterns": [],  # Checked semantically
        "severity": "block",
    },
}

# Keywords that indicate Brooklyn/NYC local content
LOCAL_MARKERS = [
    "brooklyn", "bk", "bushwick", "williamsburg", "ridgewood", "bed-stuy",
    "crown heights", "prospect", "l train", "g train", "jmz", "mta",
    "metro", "subway", "myrtle", "maria hernandez", "mccarren",
]

# Protected group indicators (for punch-up check)
PROTECTED_INDICATORS = [
    "homeless", "poor", "disabled", "immigrant", "undocumented",
    "refugee", "trans", "queer", "gay", "lesbian", "bi",
]


class ConstitutionViolation:
    """A violation of the content constitution."""

    def __init__(self, rule: str, reason: str, severity: Literal["block", "warn"]):
        self.rule = rule
        self.reason = reason
        self.severity = severity

    def __repr__(self) -> str:
        return f"<Violation: {self.rule} ({self.severity}): {self.reason}>"


def check_constitution(candidate: MemeCandidate) -> list[ConstitutionViolation]:
    """
    Check a meme candidate against constitutional rules.

    Returns:
        List of violations (empty if all checks pass)
    """
    violations = []

    # Combine all text for checking
    full_text = f"{candidate.caption} {candidate.local_hook} {candidate.rationale}"
    full_text_lower = full_text.lower()

    # Check regex patterns
    for rule_name, rule_def in RULES.items():
        for pattern in rule_def["patterns"]:
            if re.search(pattern, full_text_lower, re.IGNORECASE):
                violations.append(ConstitutionViolation(
                    rule=rule_name,
                    reason=f"Matched pattern: {pattern}",
                    severity=rule_def["severity"]
                ))

    # Semantic checks
    # 1. Require local hook
    has_local_marker = any(marker in full_text_lower for marker in LOCAL_MARKERS)
    if not has_local_marker:
        violations.append(ConstitutionViolation(
            rule="require_local_hook",
            reason="No Brooklyn/NYC/transit reference found",
            severity="block"
        ))

    # 2. Punch-up check (heuristic: avoid targeting protected groups)
    if _targets_protected_group(full_text_lower):
        violations.append(ConstitutionViolation(
            rule="punch_up",
            reason="May be punching down at a vulnerable group",
            severity="block"
        ))

    return violations


def _targets_protected_group(text: str) -> bool:
    """
    Heuristic check: does text seem to mock a protected group?

    This is imperfect but catches obvious cases.
    """
    for indicator in PROTECTED_INDICATORS:
        if indicator in text:
            # Check for negative sentiment words nearby
            negative_words = [
                "stupid", "dumb", "lazy", "dirty", "disgusting", "gross",
                "pathetic", "loser", "trash", "scum"
            ]
            for neg in negative_words:
                if neg in text:
                    return True
    return False


def is_safe(candidate: MemeCandidate) -> tuple[bool, list[ConstitutionViolation]]:
    """
    Check if a candidate is safe to publish.

    Returns:
        (is_safe, violations)
    """
    violations = check_constitution(candidate)

    # Block if any "block"-severity violations
    has_blocking_violation = any(v.severity == "block" for v in violations)

    return (not has_blocking_violation, violations)


def format_violations(violations: list[ConstitutionViolation]) -> str:
    """Format violations for human-readable output."""
    if not violations:
        return "No violations"

    lines = []
    for v in violations:
        lines.append(f"  [{v.severity.upper()}] {v.rule}: {v.reason}")

    return "\n".join(lines)

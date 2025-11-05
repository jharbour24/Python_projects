"""
Content filtering with constitutional checks and retry logic.

Filters out candidates that violate safety rules or quality thresholds.
"""

from typing import Optional

from .constitution import check_constitution, punch_up_check
from .generator import validate_candidate
from .io_schemas import MemeCandidate


class FilterResult:
    """Result of filtering a candidate."""

    def __init__(
        self,
        passed: bool,
        candidate: Optional[MemeCandidate] = None,
        reason: Optional[str] = None,
        rule: Optional[str] = None
    ):
        self.passed = passed
        self.candidate = candidate
        self.reason = reason
        self.rule = rule


def filter_candidate(candidate: MemeCandidate) -> FilterResult:
    """
    Filter a single candidate through all checks.

    Returns:
        FilterResult with passed=True if candidate is acceptable
    """
    # Step 1: Validate hard constraints (format, length, etc.)
    is_valid, error = validate_candidate(candidate)
    if not is_valid:
        return FilterResult(
            passed=False,
            candidate=candidate,
            reason=error,
            rule="format_validation"
        )

    # Step 2: Constitutional checks
    passes_constitution, violation = check_constitution(candidate)
    if not passes_constitution:
        return FilterResult(
            passed=False,
            candidate=candidate,
            reason=violation,
            rule="constitution"
        )

    # Step 3: Punch-up check (warning only, doesn't block)
    passes_punch_up, warning = punch_up_check(candidate)
    if not passes_punch_up:
        # Log warning but don't block
        print(f"Warning for {candidate.visual_template}: {warning}")

    # All checks passed
    return FilterResult(
        passed=True,
        candidate=candidate,
        reason=None,
        rule=None
    )


def filter_candidates(
    candidates: list[MemeCandidate],
    verbose: bool = False
) -> tuple[list[MemeCandidate], list[FilterResult]]:
    """
    Filter a batch of candidates.

    Args:
        candidates: List of candidates to filter
        verbose: If True, print filter results

    Returns:
        (keepers, rejections) tuple of lists
    """
    keepers = []
    rejections = []

    for candidate in candidates:
        result = filter_candidate(candidate)

        if result.passed:
            keepers.append(candidate)
        else:
            rejections.append(result)
            if verbose:
                print(
                    f"REJECTED [{result.rule}]: "
                    f"{candidate.visual_template} - {result.reason}"
                )

    return keepers, rejections


def compute_violation_rate(results: list[FilterResult]) -> float:
    """
    Compute rate of constitutional violations.

    Args:
        results: List of FilterResult objects

    Returns:
        Violation rate as float between 0 and 1
    """
    if not results:
        return 0.0

    violations = sum(1 for r in results if not r.passed)
    return violations / len(results)


def get_violation_summary(rejections: list[FilterResult]) -> dict[str, int]:
    """
    Get summary of rejection reasons.

    Args:
        rejections: List of rejected FilterResult objects

    Returns:
        Dict mapping rule names to violation counts
    """
    summary = {}
    for rejection in rejections:
        rule = rejection.rule or "unknown"
        summary[rule] = summary.get(rule, 0) + 1

    return summary

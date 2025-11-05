"""
Filter layer: applies constitution checks and retry logic.
"""

from typing import Callable

from .constitution import is_safe, format_violations
from .io_schemas import LocalSnippet, MemeCandidate


def filter_candidates(
    candidates: list[MemeCandidate],
    verbose: bool = True
) -> tuple[list[MemeCandidate], list[MemeCandidate]]:
    """
    Filter candidates through constitutional safety checks.

    Returns:
        (safe_candidates, rejected_candidates)
    """
    safe = []
    rejected = []

    for candidate in candidates:
        is_safe_flag, violations = is_safe(candidate)

        if is_safe_flag:
            safe.append(candidate)
        else:
            rejected.append(candidate)
            if verbose:
                print(f"\nL Rejected candidate:")
                print(f"   Caption: {candidate.caption}")
                print(f"   Violations:\n{format_violations(violations)}")

    if verbose:
        print(f"\n {len(safe)}/{len(candidates)} candidates passed safety checks")

    return safe, rejected


def filter_with_retry(
    generator_fn: Callable[[list[LocalSnippet], int], list[MemeCandidate]],
    snippets: list[LocalSnippet],
    target_count: int = 8,
    max_retries: int = 2,
    verbose: bool = True
) -> list[MemeCandidate]:
    """
    Generate and filter candidates with retry logic.

    If initial generation doesn't yield enough safe candidates,
    retry up to max_retries times.

    Args:
        generator_fn: Function that generates candidates
        snippets: Snippets to generate from
        target_count: Desired number of safe candidates
        max_retries: Maximum retry attempts
        verbose: Print progress

    Returns:
        List of safe candidates (may be less than target_count)
    """
    all_safe = []
    attempts = 0

    while len(all_safe) < target_count and attempts <= max_retries:
        attempts += 1

        if verbose and attempts > 1:
            print(f"\n= Retry {attempts - 1}: Generating more candidates...")

        # Generate candidates
        batch_size = target_count if attempts == 1 else (target_count - len(all_safe)) * 2
        candidates = generator_fn(snippets, batch_size)

        if not candidates:
            if verbose:
                print("Warning: Generator returned no candidates")
            break

        # Filter
        safe, rejected = filter_candidates(candidates, verbose=verbose)
        all_safe.extend(safe)

        if len(all_safe) >= target_count:
            break

    # Trim to target count if we over-generated
    return all_safe[:target_count] if len(all_safe) > target_count else all_safe


def apply_additional_filters(
    candidates: list[MemeCandidate],
    min_caption_words: int = 3,
    max_caption_words: int = 14
) -> list[MemeCandidate]:
    """
    Apply additional heuristic filters beyond constitution.

    Filters:
    - Caption length (words)
    - Duplicate detection
    """
    filtered = []
    seen_captions = set()

    for candidate in candidates:
        caption = candidate.caption
        word_count = len(caption.split())

        # Length check
        if word_count < min_caption_words or word_count > max_caption_words:
            continue

        # Duplicate check
        if caption.lower() in seen_captions:
            continue

        seen_captions.add(caption.lower())
        filtered.append(candidate)

    return filtered

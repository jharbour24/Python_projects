"""
Show title normalization and fuzzy matching.

The central challenge: the same show appears under slightly different names
across BroadwayWorld, DTLI, NYT, and Tony records. Revivals add the extra
wrinkle that "Cabaret" in 2014 and "Cabaret" in 2024 are different shows
and must NOT be merged.

Matching logic:
  1. Normalize both titles (lowercase, strip punctuation/articles)
  2. rapidfuzz token_set_ratio >= threshold → candidate match
  3. If multiple candidates: prefer the one whose opening_date year is
     closest to the target year (within REVIVAL_YEAR_WINDOW)
  4. If still ambiguous: log and return None (manual review needed)
"""
import re
from datetime import date
from typing import Optional

from rapidfuzz import fuzz, process

from config import FUZZY_MATCH_THRESHOLD, REVIVAL_YEAR_WINDOW

# Common alternate title forms to collapse before matching
_SUBSTITUTIONS = [
    (r"\band\b", "&"),
    (r"\bthe\b", ""),
    (r"[''`]", "'"),
    (r'[""]', '"'),
    (r"\s+", " "),
]

# Suffixes added by DTLI slug generation that pollute title matching
_SLUG_SUFFIXES = ["-review", "-reviews", "-2", "-3", "-4"]


def normalize(title: str) -> str:
    """Canonical normalized form for fuzzy matching."""
    t = title.lower().strip()
    t = re.sub(r"[^a-z0-9\s&']", " ", t)
    for pattern, repl in _SUBSTITUTIONS:
        t = re.sub(pattern, repl, t)
    # Strip leading article
    for article in ("the ", "a ", "an "):
        if t.startswith(article):
            t = t[len(article):]
            break
    return t.strip()


def slug_to_title(slug: str) -> str:
    """Best-effort title from a URL slug (used before we scrape the show page)."""
    s = slug
    for suffix in _SLUG_SUFFIXES:
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s.replace("-", " ").title()


def find_best_match(
    query_title: str,
    candidates: dict[int, tuple[str, Optional[str]]],  # show_id → (normalized_title, opening_date_str)
    target_year: Optional[int] = None,
    threshold: int = FUZZY_MATCH_THRESHOLD,
) -> Optional[int]:
    """
    Find the best matching show_id for query_title.

    candidates: {show_id: (normalized_title, opening_date_iso)}
    target_year: publication year of the review (used to disambiguate revivals)

    Returns show_id or None.
    """
    if not candidates:
        return None

    norm_query = normalize(query_title)
    choices = {sid: info[0] for sid, info in candidates.items()}

    results = process.extract(
        norm_query,
        choices,
        scorer=fuzz.token_set_ratio,
        limit=5,
        score_cutoff=threshold,
    )

    if not results:
        return None

    if len(results) == 1:
        return results[0][2]  # (match, score, key)

    # Multiple candidates — disambiguate by opening year
    if target_year is None:
        return results[0][2]

    best_id = None
    best_year_diff = float("inf")
    best_score = 0

    for _, score, show_id in results:
        opening_date_str = candidates[show_id][1]
        if opening_date_str:
            try:
                opening_year = int(opening_date_str[:4])
                year_diff = abs(opening_year - target_year)
            except (ValueError, TypeError):
                year_diff = float("inf")
        else:
            year_diff = float("inf")

        if year_diff < best_year_diff or (year_diff == best_year_diff and score > best_score):
            best_year_diff = year_diff
            best_score = score
            best_id = show_id

    # If best match is too far in time, reject
    if best_year_diff > REVIVAL_YEAR_WINDOW:
        return None

    return best_id


def build_candidate_map(conn) -> dict[int, tuple[str, Optional[str]]]:
    """Load all shows from DB into a {show_id: (normalized_title, opening_date)} map."""
    rows = conn.execute(
        "SELECT show_id, normalized_title, opening_date FROM shows"
    ).fetchall()
    return {r["show_id"]: (r["normalized_title"], r["opening_date"]) for r in rows}

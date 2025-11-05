"""
Tests for meme generator module.
"""

from src.generator import draft_candidates, validate_candidate
from src.io_schemas import LocalSnippet


def test_draft_candidates_enforces_caption_length():
    """Test that generated candidates have d14 word captions."""
    snippets = [
        LocalSnippet(
            id="s1",
            date="2025-11-05",
            source="manual",
            text="The L train is absolutely packed at rush hour",
            tags=["L-train", "transit"]
        ),
        LocalSnippet(
            id="s2",
            date="2025-11-05",
            source="manual",
            text="Bushwick venue has a huge line outside",
            tags=["bushwick", "venue"]
        ),
    ]

    candidates = draft_candidates(snippets, n=5)

    assert len(candidates) > 0, "Should generate candidates"

    for candidate in candidates:
        word_count = len(candidate.caption.split())
        assert word_count <= 14, f"Caption has {word_count} words, exceeds limit: {candidate.caption}"


def test_draft_candidates_uses_template_whitelist():
    """Test that only allowed templates are used."""
    snippets = [
        LocalSnippet(
            id="s1",
            date="2025-11-05",
            source="manual",
            text="Brooklyn nightlife is chaotic",
            tags=["brooklyn"]
        )
    ]

    candidates = draft_candidates(snippets, n=10)

    allowed_templates = {
        "drake",
        "distracted_boyfriend",
        "tweet_screenshot",
        "two_panel",
        "top_text_bottom_text"
    }

    for candidate in candidates:
        assert candidate.visual_template in allowed_templates, \
            f"Template {candidate.visual_template} not in whitelist"


def test_validate_candidate():
    """Test candidate validation."""
    valid = {
        "visual_template": "drake",
        "local_hook": "L train delays",
        "tone": "dry",
        "caption": "when the train says 2 minutes but you know",
        "rationale": "relatable transit frustration",
        "evidence_refs": ["s1"]
    }

    candidate = validate_candidate(valid)
    assert candidate is not None, "Valid candidate should pass"

    # Invalid: too many words
    invalid = {
        "visual_template": "drake",
        "local_hook": "L train",
        "tone": "dry",
        "caption": "this is a very long caption that definitely exceeds the fourteen word limit we have set",
        "rationale": "test",
        "evidence_refs": []
    }

    candidate = validate_candidate(invalid)
    assert candidate is None, "Should reject caption >14 words"


def test_generator_requires_snippets():
    """Test that generator handles empty snippets gracefully."""
    candidates = draft_candidates([], n=5)
    assert len(candidates) == 0, "Should return empty list when no snippets"

"""Tests for generator module."""

import pytest

from src.generator import draft_candidates, validate_candidate
from src.io_schemas import LocalSnippet, MemeCandidate


@pytest.fixture
def sample_snippets():
    """Sample snippets for generation."""
    return [
        LocalSnippet(
            id="gen_001",
            date="2025-11-05",
            source="manual",
            text="L train packed at midnight on Saturday",
            tags=["transit", "L train"]
        ),
        LocalSnippet(
            id="gen_002",
            date="2025-11-05",
            source="manual",
            text="Bushwick venue with $15 cover charge",
            tags=["venue", "bushwick"]
        ),
    ]


def test_draft_candidates_count(sample_snippets):
    """Test generating n candidates."""
    n = 5
    candidates = draft_candidates(sample_snippets, n=n)

    assert len(candidates) <= n  # May be fewer if some fail validation
    assert all(isinstance(c, MemeCandidate) for c in candidates)


def test_draft_candidates_caption_length(sample_snippets):
    """Test that captions are ≤ 14 words."""
    candidates = draft_candidates(sample_snippets, n=10)

    for cand in candidates:
        word_count = len(cand.caption.split())
        assert word_count <= 14, f"Caption too long: {word_count} words"


def test_draft_candidates_template_whitelist(sample_snippets):
    """Test that templates are from allowed list."""
    candidates = draft_candidates(sample_snippets, n=10)

    valid_templates = ["drake", "distracted_boyfriend", "tweet_screenshot", "two_panel", "top_text_bottom_text"]

    for cand in candidates:
        assert cand.visual_template in valid_templates


def test_validate_candidate_valid():
    """Test validating a valid candidate."""
    candidate = MemeCandidate(
        visual_template="drake",
        local_hook="L train delays",
        tone="dry",
        caption="taking the train on time",
        rationale="test",
        evidence_refs=["test_001"]
    )

    is_valid, error = validate_candidate(candidate)

    assert is_valid is True
    assert error is None


def test_validate_candidate_caption_too_long():
    """Test rejecting caption that's too long."""
    with pytest.raises(ValueError, match="Caption must be"):
        MemeCandidate(
            visual_template="drake",
            local_hook="test",
            tone="dry",
            caption="this is a very long caption with way more than fourteen words in it for sure definitely",
            rationale="test",
            evidence_refs=[]
        )


def test_validate_candidate_invalid_template():
    """Test rejecting invalid template."""
    candidate = MemeCandidate(
        visual_template="drake",  # Valid, but we'll test validation logic
        local_hook="test",
        tone="dry",
        caption="short caption",
        rationale="test",
        evidence_refs=[]
    )

    # Manually set invalid template to test validation
    candidate.visual_template = "invalid_template"

    is_valid, error = validate_candidate(candidate)

    assert is_valid is False
    assert "Invalid template" in error


def test_draft_candidates_with_empty_snippets():
    """Test handling empty snippets list."""
    candidates = draft_candidates([], n=5)

    # Should still generate something (using fallback)
    assert len(candidates) > 0

"""Tests for filter module."""

import pytest

from src.filter import filter_candidate, filter_candidates, compute_violation_rate
from src.io_schemas import MemeCandidate


def test_filter_valid_candidate():
    """Test filtering a valid candidate."""
    candidate = MemeCandidate(
        visual_template="drake",
        local_hook="L train in Brooklyn",
        tone="dry",
        caption="taking the L train on time",
        rationale="test",
        evidence_refs=[]
    )

    result = filter_candidate(candidate)

    assert result.passed is True
    assert result.candidate == candidate


def test_filter_blocks_profanity():
    """Test that profanity is blocked."""
    candidate = MemeCandidate(
        visual_template="drake",
        local_hook="Brooklyn venue",
        tone="dry",
        caption="this fucking sucks",
        rationale="test",
        evidence_refs=[]
    )

    result = filter_candidate(candidate)

    assert result.passed is False
    assert "profanity" in result.reason.lower()


def test_filter_blocks_missing_local_reference():
    """Test that missing local reference is blocked."""
    candidate = MemeCandidate(
        visual_template="drake",
        local_hook="generic thing",
        tone="dry",
        caption="something generic",
        rationale="test",
        evidence_refs=[]
    )

    result = filter_candidate(candidate)

    assert result.passed is False
    assert "local" in result.reason.lower()


def test_filter_blocks_hashtags():
    """Test that hashtags are blocked."""
    candidate = MemeCandidate(
        visual_template="drake",
        local_hook="Brooklyn L train",
        tone="dry",
        caption="taking the train #brooklyn",
        rationale="test",
        evidence_refs=[]
    )

    result = filter_candidate(candidate)

    assert result.passed is False
    assert "Hashtag" in result.reason


def test_filter_candidates_batch():
    """Test filtering a batch of candidates."""
    candidates = [
        MemeCandidate(
            visual_template="drake",
            local_hook="Brooklyn L train",
            tone="dry",
            caption="taking the L train",
            rationale="test",
            evidence_refs=[]
        ),
        MemeCandidate(
            visual_template="drake",
            local_hook="Brooklyn venue",
            tone="dry",
            caption="bad words fuck",
            rationale="test",
            evidence_refs=[]
        ),
    ]

    keepers, rejections = filter_candidates(candidates)

    assert len(keepers) == 1
    assert len(rejections) == 1


def test_compute_violation_rate():
    """Test computing violation rate."""
    from src.filter import FilterResult

    results = [
        FilterResult(passed=True),
        FilterResult(passed=False),
        FilterResult(passed=False),
        FilterResult(passed=True),
    ]

    rate = compute_violation_rate(results)

    assert rate == 0.5  # 2 out of 4 failed


def test_filter_all_caps_wrong_tone():
    """Test that ALL CAPS is blocked for wrong tone."""
    candidate = MemeCandidate(
        visual_template="drake",
        local_hook="Brooklyn L train",
        tone="dry",  # Not "slightly unhinged"
        caption="TAKING THE L TRAIN",
        rationale="test",
        evidence_refs=[]
    )

    result = filter_candidate(candidate)

    assert result.passed is False
    assert "CAPS" in result.reason

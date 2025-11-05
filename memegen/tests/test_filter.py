"""
Tests for filter and constitution modules.
"""

from src.constitution import check_constitution, is_safe
from src.filter import filter_candidates
from src.io_schemas import MemeCandidate


def test_constitution_blocks_slurs():
    """Test that constitution blocks obvious violations."""
    bad_candidate = MemeCandidate(
        visual_template="drake",
        local_hook="Brooklyn venue",
        tone="dry",
        caption="this is retarded",
        rationale="test",
        evidence_refs=[]
    )

    violations = check_constitution(bad_candidate)
    assert len(violations) > 0, "Should detect violation"
    assert any(v.rule == "no_slurs" for v in violations)


def test_constitution_requires_local_hook():
    """Test that constitution requires Brooklyn/NYC reference."""
    # No local reference
    bad_candidate = MemeCandidate(
        visual_template="drake",
        local_hook="Some generic place",
        tone="dry",
        caption="when you do the thing",
        rationale="generic meme",
        evidence_refs=[]
    )

    safe, violations = is_safe(bad_candidate)
    assert not safe, "Should fail without local hook"
    assert any(v.rule == "require_local_hook" for v in violations)

    # Has local reference
    good_candidate = MemeCandidate(
        visual_template="drake",
        local_hook="L train at Bedford",
        tone="dry",
        caption="when the L train says arriving",
        rationale="transit humor",
        evidence_refs=[]
    )

    safe, violations = is_safe(good_candidate)
    assert safe, "Should pass with local hook"


def test_filter_candidates_separates_safe_and_rejected():
    """Test that filter correctly separates candidates."""
    candidates = [
        MemeCandidate(
            visual_template="drake",
            local_hook="Brooklyn scene",
            tone="dry",
            caption="when you get to Bushwick at 1am",
            rationale="late night vibes",
            evidence_refs=[]
        ),
        MemeCandidate(
            visual_template="tweet_screenshot",
            local_hook="generic place",
            tone="coy",
            caption="generic meme with no local content",
            rationale="test",
            evidence_refs=[]
        ),
    ]

    safe, rejected = filter_candidates(candidates, verbose=False)

    assert len(safe) >= 1, "Should have at least one safe candidate"
    assert len(rejected) >= 1, "Should reject at least one"


def test_constitution_allows_good_content():
    """Test that good content passes all checks."""
    good_candidate = MemeCandidate(
        visual_template="tweet_screenshot",
        local_hook="L train delays at Bedford",
        tone="dry",
        caption="POV: you're waiting for the L train",
        rationale="relatable transit moment",
        evidence_refs=["s1"]
    )

    safe, violations = is_safe(good_candidate)
    assert safe, f"Good candidate should pass, but got: {violations}"

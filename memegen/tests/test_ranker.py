"""
Tests for preference ranker module.
"""

import tempfile
from pathlib import Path

from src.io_schemas import MemeCandidate, MemeMetadata, PairwiseLabel, save_jsonl
from src.ranker import PreferenceRanker


def test_ranker_deterministic_top3():
    """Test that ranker returns deterministic top-3 for a fixed seed."""
    candidates = [
        MemeCandidate(
            visual_template="drake",
            local_hook="L train",
            tone="dry",
            caption="when the L says two minutes",
            rationale="transit",
            evidence_refs=[]
        ),
        MemeCandidate(
            visual_template="tweet_screenshot",
            local_hook="Bushwick venue",
            tone="coy",
            caption="Brooklyn nightlife hits different",
            rationale="scene",
            evidence_refs=[]
        ),
        MemeCandidate(
            visual_template="two_panel",
            local_hook="Maria Hernandez",
            tone="slightly unhinged",
            caption="me at the park pretending I'm chill",
            rationale="park vibes",
            evidence_refs=[]
        ),
    ]

    ranker = PreferenceRanker()

    # Train on dummy data
    with tempfile.TemporaryDirectory() as tmpdir:
        pairs_path = Path(tmpdir) / "pairs.jsonl"
        save_jsonl([], pairs_path)  # Empty file
        ranker.train(pairs_path)

    # Rank twice
    ranked1 = ranker.rank(candidates, top_k=3)
    ranked2 = ranker.rank(candidates, top_k=3)

    assert len(ranked1) == 3, "Should return 3 candidates"
    assert len(ranked2) == 3, "Should return 3 candidates"

    # Check determinism
    for i in range(3):
        assert ranked1[i][0].caption == ranked2[i][0].caption, "Rankings should be deterministic"


def test_ranker_trains_on_pairwise_labels():
    """Test that ranker can train on pairwise labels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pairs_path = Path(tmpdir) / "pairs.jsonl"

        pairs = [
            PairwiseLabel(
                pair_id="p1",
                a=MemeMetadata(text="good meme", visual_template="drake", tone="dry"),
                b=MemeMetadata(text="bad meme", visual_template="drake", tone="dry"),
                winner="a",
                panel="test",
                timestamp="2025-11-05T12:00:00"
            )
        ]

        save_jsonl(pairs, pairs_path)

        ranker = PreferenceRanker()
        stats = ranker.train(pairs_path)

        assert stats["n_pairs"] == 1, "Should train on 1 pair"
        assert ranker.is_trained, "Should be marked as trained"


def test_ranker_handles_empty_candidates():
    """Test that ranker handles empty candidate list."""
    ranker = PreferenceRanker()

    ranked = ranker.rank([], top_k=3)
    assert len(ranked) == 0, "Should return empty list"

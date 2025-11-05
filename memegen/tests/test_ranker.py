"""Tests for ranker module."""

import tempfile
from pathlib import Path

import pytest

from src.io_schemas import (
    MemeCandidate,
    PairwiseCandidate,
    PairwiseLabel,
    PairwiseMeta,
    save_jsonl,
)
from src.ranker import PreferenceRanker, extract_features


@pytest.fixture
def sample_pairs():
    """Sample pairwise labels for training."""
    return [
        PairwiseLabel(
            pair_id="p_001",
            a=PairwiseCandidate(
                text="L train delays again",
                meta=PairwiseMeta(template="tweet_screenshot", tone="dry")
            ),
            b=PairwiseCandidate(
                text="another venue closure",
                meta=PairwiseMeta(template="drake", tone="coy")
            ),
            winner="a",
            timestamp="2025-11-05T12:00:00"
        ),
        PairwiseLabel(
            pair_id="p_002",
            a=PairwiseCandidate(
                text="Bushwick cover charge",
                meta=PairwiseMeta(template="two_panel", tone="dry")
            ),
            b=PairwiseCandidate(
                text="taking the G train",
                meta=PairwiseMeta(template="drake", tone="slightly unhinged")
            ),
            winner="b",
            timestamp="2025-11-04T12:00:00"
        ),
    ]


def test_extract_features():
    """Test feature extraction."""
    candidate = MemeCandidate(
        visual_template="drake",
        local_hook="Brooklyn L train",
        tone="dry",
        caption="taking the L train",
        rationale="test",
        evidence_refs=["ref1", "ref2"]
    )

    features = extract_features(candidate)

    # Should have 11 features
    assert len(features) == 11
    assert all(isinstance(f, (int, float)) for f in features)


def test_ranker_train(sample_pairs):
    """Test training ranker on pairwise labels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pairs_path = Path(tmpdir) / "pairs.jsonl"
        save_jsonl(pairs_path, sample_pairs)

        ranker = PreferenceRanker()
        metrics = ranker.train(pairs_path)

        assert ranker.is_trained is True
        assert metrics["n_pairs"] == 2
        assert "accuracy" in metrics


def test_ranker_score():
    """Test scoring a candidate."""
    ranker = PreferenceRanker()
    ranker._train_dummy()

    candidate = MemeCandidate(
        visual_template="drake",
        local_hook="Brooklyn venue",
        tone="dry",
        caption="test caption",
        rationale="test",
        evidence_refs=[]
    )

    score = ranker.score(candidate)

    assert 0.0 <= score <= 1.0


def test_ranker_rank_deterministic():
    """Test that ranking is deterministic for fixed seed."""
    ranker = PreferenceRanker()
    ranker._train_dummy()

    candidates = [
        MemeCandidate(
            visual_template="drake",
            local_hook="L train",
            tone="dry",
            caption=f"test caption {i}",
            rationale="test",
            evidence_refs=[]
        )
        for i in range(5)
    ]

    # Rank twice
    result1 = ranker.rank(candidates, top_k=3)
    result2 = ranker.rank(candidates, top_k=3)

    # Should get same top-3 (same order)
    assert len(result1) == 3
    assert len(result2) == 3
    assert [c.caption for c in result1] == [c.caption for c in result2]


def test_ranker_returns_top_k():
    """Test that ranker returns exactly top-k results."""
    ranker = PreferenceRanker()
    ranker._train_dummy()

    candidates = [
        MemeCandidate(
            visual_template="drake",
            local_hook="Brooklyn",
            tone="dry",
            caption=f"caption {i}",
            rationale="test",
            evidence_refs=[]
        )
        for i in range(10)
    ]

    top3 = ranker.rank(candidates, top_k=3)

    assert len(top3) == 3


def test_ranker_save_and_load():
    """Test saving and loading ranker."""
    ranker = PreferenceRanker()
    ranker._train_dummy()

    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "model.pkl"
        ranker.save(model_path)

        loaded_ranker = PreferenceRanker.load(model_path)

        assert loaded_ranker.is_trained == ranker.is_trained
        assert loaded_ranker.time_decay_days == ranker.time_decay_days

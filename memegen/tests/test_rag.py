"""Tests for RAG module."""

import tempfile
from pathlib import Path

import pytest

from src.io_schemas import LocalSnippet, save_jsonl
from src.rag import RAGIndex


@pytest.fixture
def sample_snippets():
    """Sample local snippets for testing."""
    return [
        LocalSnippet(
            id="test_001",
            date="2025-11-05",
            source="manual",
            text="L train delays on Saturday night",
            tags=["transit", "L train", "brooklyn"]
        ),
        LocalSnippet(
            id="test_002",
            date="2025-11-05",
            source="manual",
            text="New venue opening in Bushwick with no cover",
            tags=["venue", "bushwick", "brooklyn"]
        ),
        LocalSnippet(
            id="test_003",
            date="2025-11-05",
            source="manual",
            text="Drag brunch at a Bed-Stuy spot this Sunday",
            tags=["drag", "bed-stuy", "brooklyn"]
        ),
    ]


@pytest.fixture
def sources_dir(sample_snippets):
    """Create temporary sources directory with test snippets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sources_path = Path(tmpdir) / "sources"
        sources_path.mkdir()

        # Save snippets
        save_jsonl(sources_path / "test.jsonl", sample_snippets)

        yield sources_path


def test_rag_index_build(sources_dir):
    """Test building RAG index."""
    index = RAGIndex(backend="tfidf")
    n_snippets = index.build_index(sources_dir)

    assert n_snippets == 3
    assert len(index.snippets) == 3
    assert index.vectorizer is not None


def test_rag_retrieve_k_results(sources_dir):
    """Test retrieving k snippets."""
    index = RAGIndex(backend="tfidf")
    index.build_index(sources_dir)

    results = index.retrieve(["L train"], k=2)

    assert len(results) <= 2
    assert all(isinstance(r, LocalSnippet) for r in results)


def test_rag_retrieve_with_tags(sources_dir):
    """Test tag filtering."""
    index = RAGIndex(backend="tfidf")
    index.build_index(sources_dir)

    results = index.retrieve(["brooklyn"], k=10, tag_filter=["drag"])

    assert len(results) <= 10
    # All results should have 'drag' tag
    for r in results:
        assert "drag" in r.tags


def test_rag_empty_query(sources_dir):
    """Test handling empty query."""
    index = RAGIndex(backend="tfidf")
    index.build_index(sources_dir)

    results = index.retrieve([], k=5)

    # Should still return results (using empty query)
    assert isinstance(results, list)


def test_rag_save_and_load(sources_dir):
    """Test saving and loading index."""
    index = RAGIndex(backend="tfidf")
    index.build_index(sources_dir)

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "test_index.pkl"
        index.save(index_path)

        loaded_index = RAGIndex.load(index_path)

        assert len(loaded_index.snippets) == len(index.snippets)
        assert loaded_index.backend == index.backend

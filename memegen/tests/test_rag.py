"""
Tests for RAG retrieval module.
"""

import tempfile
from pathlib import Path

from src.io_schemas import LocalSnippet, save_jsonl
from src.rag import RAGIndex


def test_rag_index_and_retrieve():
    """Test that RAG indexes snippets and retrieves top-k."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sources_dir = Path(tmpdir) / "sources"
        sources_dir.mkdir()

        # Create test snippets
        snippets = [
            LocalSnippet(
                id="s1",
                date="2025-11-05",
                source="manual",
                text="The L train is delayed again at Bedford",
                tags=["L-train", "transit"]
            ),
            LocalSnippet(
                id="s2",
                date="2025-11-05",
                source="manual",
                text="New drag show at House of Yes in Bushwick",
                tags=["bushwick", "drag", "venue"]
            ),
            LocalSnippet(
                id="s3",
                date="2025-11-05",
                source="manual",
                text="Maria Hernandez Park is packed with picnics",
                tags=["park", "bushwick"]
            ),
        ]

        save_jsonl(snippets, sources_dir / "test.jsonl")

        # Index
        rag = RAGIndex(backend="tfidf")
        count = rag.index(sources_dir)

        assert count == 3, "Should index 3 snippets"

        # Retrieve
        results = rag.retrieve(["L train", "transit"], k=2)

        assert len(results) <= 2, "Should return at most k results"
        assert len(results) > 0, "Should return at least one result"
        assert any("L train" in r.text for r in results), "Should retrieve relevant snippet"


def test_rag_tag_filtering():
    """Test that RAG respects tag filters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sources_dir = Path(tmpdir) / "sources"
        sources_dir.mkdir()

        snippets = [
            LocalSnippet(
                id="s1",
                date="2025-11-05",
                source="manual",
                text="Bushwick venue with great vibes",
                tags=["bushwick", "venue"]
            ),
            LocalSnippet(
                id="s2",
                date="2025-11-05",
                source="manual",
                text="Williamsburg bar is overpriced",
                tags=["williamsburg", "bar"]
            ),
        ]

        save_jsonl(snippets, sources_dir / "test.jsonl")

        rag = RAGIndex(backend="tfidf")
        rag.index(sources_dir)

        # Filter by tags
        results = rag.retrieve(["venue", "bar"], k=10, tags=["bushwick"])

        assert len(results) == 1, "Should only return Bushwick snippet"
        assert results[0].id == "s1"


def test_rag_empty_sources():
    """Test that RAG handles empty sources gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sources_dir = Path(tmpdir) / "sources"
        sources_dir.mkdir()

        rag = RAGIndex()
        count = rag.index(sources_dir)

        assert count == 0, "Should index 0 snippets"

        results = rag.retrieve(["test"], k=5)
        assert len(results) == 0, "Should return empty list"

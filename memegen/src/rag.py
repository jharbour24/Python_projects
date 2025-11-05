"""
Retrieval-Augmented Generation (RAG) layer for local snippet retrieval.

Uses TF-IDF by default, with optional sentence-transformers for semantic search.
"""

import pickle
from pathlib import Path
from typing import Literal, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .io_schemas import LocalSnippet, load_jsonl

# Try to import sentence-transformers; fall back gracefully
try:
    from sentence_transformers import SentenceTransformer
    SBERT_AVAILABLE = True
except ImportError:
    SBERT_AVAILABLE = False


class RAGIndex:
    """
    Lightweight retrieval index for local snippets.

    Supports two backends:
    - 'tfidf': sklearn TF-IDF (default, no dependencies)
    - 'sbert': sentence-transformers (requires installation)
    """

    def __init__(
        self,
        backend: Literal["tfidf", "sbert"] = "tfidf",
        model_name: str = "all-MiniLM-L6-v2"
    ):
        self.backend = backend
        self.model_name = model_name
        self.snippets: list[LocalSnippet] = []
        self.corpus: list[str] = []

        # Backend-specific components
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix: Optional[np.ndarray] = None
        self.sbert_model: Optional[SentenceTransformer] = None
        self.embeddings: Optional[np.ndarray] = None

        if backend == "sbert" and not SBERT_AVAILABLE:
            print("Warning: sentence-transformers not available, falling back to TF-IDF")
            self.backend = "tfidf"

    def build_index(self, sources_dir: Path) -> int:
        """
        Build index from all JSONL files in sources directory.
        Returns number of snippets indexed.
        """
        self.snippets = []

        # Load all snippet files
        for jsonl_file in sorted(sources_dir.glob("*.jsonl")):
            snippets = load_jsonl(jsonl_file, LocalSnippet)
            self.snippets.extend(snippets)

        if not self.snippets:
            print(f"Warning: No snippets found in {sources_dir}")
            return 0

        # Build corpus
        self.corpus = [
            f"{s.text} {' '.join(s.tags)}"
            for s in self.snippets
        ]

        # Build backend-specific index
        if self.backend == "tfidf":
            self._build_tfidf_index()
        elif self.backend == "sbert":
            self._build_sbert_index()

        return len(self.snippets)

    def _build_tfidf_index(self) -> None:
        """Build TF-IDF index."""
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            ngram_range=(1, 2),
            stop_words="english",
            lowercase=True
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)

    def _build_sbert_index(self) -> None:
        """Build sentence-transformer embeddings."""
        if not SBERT_AVAILABLE:
            raise RuntimeError("sentence-transformers not available")

        self.sbert_model = SentenceTransformer(self.model_name)
        self.embeddings = self.sbert_model.encode(
            self.corpus,
            show_progress_bar=False,
            convert_to_numpy=True
        )

    def retrieve(
        self,
        query_terms: list[str],
        k: int = 15,
        tag_filter: Optional[list[str]] = None
    ) -> list[LocalSnippet]:
        """
        Retrieve top-k most relevant snippets for query terms.

        Args:
            query_terms: List of search terms/phrases
            k: Number of results to return
            tag_filter: Optional list of tags; only return snippets with these tags

        Returns:
            List of LocalSnippet objects, sorted by relevance
        """
        if not self.snippets:
            return []

        # Combine query terms
        query = " ".join(query_terms)

        # Get scores
        if self.backend == "tfidf":
            scores = self._score_tfidf(query)
        elif self.backend == "sbert":
            scores = self._score_sbert(query)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

        # Apply tag filter if specified
        if tag_filter:
            tag_set = set(tag_filter)
            for i, snippet in enumerate(self.snippets):
                if not any(tag in tag_set for tag in snippet.tags):
                    scores[i] = -np.inf

        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:k]

        # Return snippets
        results = [self.snippets[i] for i in top_indices if scores[i] > -np.inf]
        return results

    def _score_tfidf(self, query: str) -> np.ndarray:
        """Score snippets using TF-IDF cosine similarity."""
        if self.vectorizer is None or self.tfidf_matrix is None:
            return np.zeros(len(self.snippets))

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        return similarities

    def _score_sbert(self, query: str) -> np.ndarray:
        """Score snippets using sentence-transformer embeddings."""
        if self.sbert_model is None or self.embeddings is None:
            return np.zeros(len(self.snippets))

        query_emb = self.sbert_model.encode(
            [query],
            show_progress_bar=False,
            convert_to_numpy=True
        )
        similarities = cosine_similarity(query_emb, self.embeddings).flatten()
        return similarities

    def save(self, path: Path) -> None:
        """Save index to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "backend": self.backend,
            "model_name": self.model_name,
            "snippets": [s.model_dump() for s in self.snippets],
            "corpus": self.corpus,
        }

        if self.backend == "tfidf":
            state["vectorizer"] = self.vectorizer
            state["tfidf_matrix"] = self.tfidf_matrix

        with open(path, "wb") as f:
            pickle.dump(state, f)

    @classmethod
    def load(cls, path: Path) -> "RAGIndex":
        """Load index from disk."""
        with open(path, "rb") as f:
            state = pickle.load(f)

        index = cls(backend=state["backend"], model_name=state["model_name"])
        index.snippets = [LocalSnippet.model_validate(s) for s in state["snippets"]]
        index.corpus = state["corpus"]

        if state["backend"] == "tfidf":
            index.vectorizer = state["vectorizer"]
            index.tfidf_matrix = state["tfidf_matrix"]
        elif state["backend"] == "sbert":
            # Rebuild embeddings (can't pickle SBERT model easily)
            index._build_sbert_index()

        return index


# ============================================================================
# Common Query Templates
# ============================================================================

RAG_QUERY_TEMPLATES = [
    "L train",
    "JMZ",
    "Bushwick",
    "Ridgewood",
    "Bed-Stuy",
    "drag brunch",
    "cover",
    "line outside",
    "Maria Hernandez",
    "scaffolding",
    "bike locks",
    "pop-up",
    "venue closure",
    "cash only",
    "2 drink minimum",
]

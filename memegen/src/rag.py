"""
Retrieval-Augmented Generation layer for local Brooklyn/NYC snippets.
"""

import pickle
from pathlib import Path
from typing import Literal

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .io_schemas import LocalSnippet, load_jsonl

# Try to import sentence-transformers; fall back to TF-IDF if not available
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class RAGIndex:
    """
    Retrieval index over local snippets.
    Supports TF-IDF (default) or sentence-transformers embeddings.
    """

    def __init__(
        self,
        backend: Literal["tfidf", "sentence-transformers"] = "tfidf",
        model_name: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize RAG index.

        Args:
            backend: Which embedding backend to use
            model_name: Sentence-transformer model (ignored if backend is tfidf)
        """
        self.backend = backend
        self.snippets: list[LocalSnippet] = []
        self.corpus: list[str] = []

        if backend == "sentence-transformers":
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                print("Warning: sentence-transformers not available, falling back to TF-IDF")
                self.backend = "tfidf"
            else:
                self.model = SentenceTransformer(model_name)
                self.embeddings = None

        if self.backend == "tfidf":
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words="english",
                ngram_range=(1, 2)
            )
            self.tfidf_matrix = None

    def index(self, sources_dir: Path | str) -> int:
        """
        Index all JSONL files in sources directory.

        Returns:
            Number of snippets indexed
        """
        sources_dir = Path(sources_dir)
        self.snippets = []
        self.corpus = []

        if not sources_dir.exists():
            print(f"Warning: Sources directory {sources_dir} does not exist")
            return 0

        # Load all JSONL files
        for jsonl_file in sorted(sources_dir.glob("*.jsonl")):
            snippets = load_jsonl(jsonl_file, LocalSnippet)
            self.snippets.extend(snippets)

        if not self.snippets:
            print("Warning: No snippets found to index")
            return 0

        # Build corpus for embedding/vectorization
        for snippet in self.snippets:
            # Combine text and tags for richer retrieval
            tags_str = " ".join(snippet.tags)
            self.corpus.append(f"{snippet.text} {tags_str}")

        # Build index
        if self.backend == "tfidf":
            self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)
        else:
            self.embeddings = self.model.encode(self.corpus, show_progress_bar=False)

        print(f"Indexed {len(self.snippets)} snippets using {self.backend}")
        return len(self.snippets)

    def retrieve(
        self,
        query_terms: list[str],
        k: int = 15,
        tags: list[str] | None = None
    ) -> list[LocalSnippet]:
        """
        Retrieve top-k most relevant snippets.

        Args:
            query_terms: List of query terms
            k: Number of results to return
            tags: Optional tag filter (snippets must have at least one matching tag)

        Returns:
            List of LocalSnippet objects, ranked by relevance
        """
        if not self.snippets:
            return []

        # Build query string
        query = " ".join(query_terms)

        # Compute similarities
        if self.backend == "tfidf":
            query_vec = self.vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        else:
            query_emb = self.model.encode([query], show_progress_bar=False)
            similarities = cosine_similarity(query_emb, self.embeddings).flatten()

        # Apply tag filter if provided
        if tags:
            tag_set = set(tags)
            for i, snippet in enumerate(self.snippets):
                if not tag_set.intersection(snippet.tags):
                    similarities[i] = -1  # Exclude from results

        # Get top-k indices
        top_k_indices = np.argsort(similarities)[::-1][:k]

        # Return snippets
        results = [self.snippets[i] for i in top_k_indices if similarities[i] > -1]
        return results

    def save(self, cache_path: Path | str) -> None:
        """Save index to disk for fast loading."""
        cache_path = Path(cache_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "backend": self.backend,
            "snippets": [s.model_dump() for s in self.snippets],
            "corpus": self.corpus,
        }

        if self.backend == "tfidf":
            state["vectorizer"] = self.vectorizer
            state["tfidf_matrix"] = self.tfidf_matrix
        else:
            state["model_name"] = self.model.get_sentence_embedding_dimension()
            state["embeddings"] = self.embeddings

        with open(cache_path, "wb") as f:
            pickle.dump(state, f)

    def load(self, cache_path: Path | str) -> bool:
        """Load index from disk. Returns True if successful."""
        cache_path = Path(cache_path)
        if not cache_path.exists():
            return False

        with open(cache_path, "rb") as f:
            state = pickle.load(f)

        self.backend = state["backend"]
        self.snippets = [LocalSnippet(**s) for s in state["snippets"]]
        self.corpus = state["corpus"]

        if self.backend == "tfidf":
            self.vectorizer = state["vectorizer"]
            self.tfidf_matrix = state["tfidf_matrix"]
        else:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                print("Warning: sentence-transformers not available")
                return False
            self.embeddings = state["embeddings"]

        print(f"Loaded index with {len(self.snippets)} snippets")
        return True


# Query templates for common Brooklyn nightlife concepts
RAG_QUERY_TEMPLATES = [
    "L train",
    "JMZ",
    "Bushwick",
    "Ridgewood",
    "Bed-Stuy",
    "drag brunch",
    "cover",
    "Line outside",
    "Maria Hernandez",
    "scaffolding",
    "bike locks",
    "pop-up",
    "venue closure",
    "cash only",
    "2 drink minimum",
]

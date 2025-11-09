"""NLP analysis engine for discourse clustering and embedding."""
import numpy as np
from typing import List, Dict, Any, Tuple
from collections import Counter
import warnings
warnings.filterwarnings('ignore')


class NLPEngine:
    """Advanced NLP analysis using embeddings and clustering."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize NLP engine.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.embedding_model = None
        self.sentiment_analyzer = None

        # Initialize models (lazy loading)
        self._models_loaded = False

    def _load_models(self):
        """Lazy load heavy NLP models."""
        if self._models_loaded:
            return

        print("Loading NLP models...")
        try:
            from sentence_transformers import SentenceTransformer
            from textblob import TextBlob

            # Load embedding model
            model_name = self.config.get('nlp', {}).get(
                'embedding_model',
                'sentence-transformers/all-MiniLM-L6-v2'
            )
            self.embedding_model = SentenceTransformer(model_name)
            self.sentiment_analyzer = TextBlob
            self._models_loaded = True
            print("✓ NLP models loaded")

        except ImportError as e:
            print(f"⚠ NLP models not available: {e}")
            print("Install with: pip install sentence-transformers textblob")
            self._models_loaded = False

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for texts.

        Args:
            texts: List of text strings

        Returns:
            Numpy array of embeddings
        """
        self._load_models()

        if not self._models_loaded or not self.embedding_model:
            # Return random embeddings as fallback
            print("⚠ Using random embeddings (models not loaded)")
            return np.random.rand(len(texts), 384)

        # Filter out empty texts
        valid_texts = [t if t and len(t) > 0 else "empty" for t in texts]

        embeddings = self.embedding_model.encode(
            valid_texts,
            show_progress_bar=True,
            batch_size=32
        )

        return embeddings

    def cluster_discourse(
        self,
        embeddings: np.ndarray,
        n_clusters: int = 5
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Cluster discourse using embeddings.

        Args:
            embeddings: Embedding vectors
            n_clusters: Number of clusters

        Returns:
            Tuple of (cluster labels, cluster info)
        """
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score

        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)

        # Calculate cluster quality
        silhouette = silhouette_score(embeddings, labels)

        cluster_info = {
            'n_clusters': n_clusters,
            'silhouette_score': silhouette,
            'cluster_sizes': dict(Counter(labels)),
            'centroids': kmeans.cluster_centers_
        }

        print(f"✓ Clustered into {n_clusters} groups (silhouette: {silhouette:.3f})")

        return labels, cluster_info

    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of text.

        Args:
            text: Input text

        Returns:
            Dictionary with sentiment scores
        """
        self._load_models()

        if not self._models_loaded or not self.sentiment_analyzer:
            return {'polarity': 0.0, 'subjectivity': 0.0}

        try:
            blob = self.sentiment_analyzer(text)
            return {
                'polarity': blob.sentiment.polarity,  # -1 to 1
                'subjectivity': blob.sentiment.subjectivity  # 0 to 1
            }
        except Exception:
            return {'polarity': 0.0, 'subjectivity': 0.0}

    def extract_key_phrases(
        self,
        texts: List[str],
        top_n: int = 20
    ) -> List[Tuple[str, int]]:
        """
        Extract most common phrases from texts.

        Args:
            texts: List of texts
            top_n: Number of top phrases to return

        Returns:
            List of (phrase, count) tuples
        """
        # Simple n-gram extraction
        from collections import Counter
        import re

        # Combine all texts
        combined = ' '.join(texts).lower()

        # Extract 2-3 word phrases
        bigrams = re.findall(r'\b\w+\s+\w+\b', combined)
        trigrams = re.findall(r'\b\w+\s+\w+\s+\w+\b', combined)

        # Count and filter
        all_phrases = bigrams + trigrams
        phrase_counts = Counter(all_phrases)

        # Filter out common stop phrases
        stop_phrases = {
            'oh mary', 'the show', 'on broadway', 'of the',
            'in the', 'to the', 'and the', 'for the'
        }

        filtered = [
            (phrase, count) for phrase, count in phrase_counts.most_common(top_n * 2)
            if phrase not in stop_phrases
        ]

        return filtered[:top_n]

    def calculate_pronoun_shift(self, texts: List[str]) -> Dict[str, float]:
        """
        Calculate I→we pronoun shift ratios.

        Args:
            texts: List of texts

        Returns:
            Dictionary with pronoun statistics
        """
        import re

        i_count = 0
        we_count = 0
        total_words = 0

        for text in texts:
            if not text:
                continue

            text_lower = text.lower()
            words = text_lower.split()
            total_words += len(words)

            # Count pronouns
            i_count += len(re.findall(r'\b(i|me|my|mine)\b', text_lower))
            we_count += len(re.findall(r'\b(we|us|our|ours)\b', text_lower))

        total_pronouns = i_count + we_count

        if total_pronouns == 0:
            return {
                'i_count': 0,
                'we_count': 0,
                'we_ratio': 0.0,
                'shift_index': 0.0
            }

        we_ratio = we_count / total_pronouns
        # Shift index: ranges from -1 (all I) to +1 (all we)
        shift_index = (we_count - i_count) / total_pronouns

        return {
            'i_count': i_count,
            'we_count': we_count,
            'we_ratio': we_ratio,
            'shift_index': shift_index,
            'avg_pronouns_per_text': total_pronouns / len(texts) if texts else 0
        }

    def detect_mimetic_motifs(
        self,
        texts: List[str],
        min_frequency: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Detect repeated memes/motifs in discourse.

        Args:
            texts: List of texts
            min_frequency: Minimum frequency to count as motif

        Returns:
            List of motif dictionaries
        """
        from collections import Counter
        import re

        # Look for repeated patterns
        patterns = []

        # Exact phrase repetition
        phrase_counts = Counter()
        for text in texts:
            # Extract phrases in quotes
            quotes = re.findall(r'"([^"]+)"', text)
            quotes += re.findall(r"'([^']+)'", text)

            for quote in quotes:
                if len(quote.split()) >= 2:  # At least 2 words
                    phrase_counts[quote.lower()] += 1

        motifs = []
        for phrase, count in phrase_counts.items():
            if count >= min_frequency:
                motifs.append({
                    'motif': phrase,
                    'frequency': count,
                    'type': 'quoted_phrase'
                })

        # Common hashtags (if present in texts)
        hashtag_counts = Counter()
        for text in texts:
            hashtags = re.findall(r'#\w+', text)
            for tag in hashtags:
                hashtag_counts[tag.lower()] += 1

        for hashtag, count in hashtag_counts.items():
            if count >= min_frequency and hashtag.lower() not in ['#ohmary', '#broadway']:
                motifs.append({
                    'motif': hashtag,
                    'frequency': count,
                    'type': 'hashtag'
                })

        return sorted(motifs, key=lambda x: x['frequency'], reverse=True)

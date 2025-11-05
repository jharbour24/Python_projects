"""
Preference ranker: trains on pairwise labels and scores candidates.
"""

import pickle
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from .io_schemas import MemeCandidate, PairwiseLabel, load_jsonl


class PreferenceRanker:
    """
    A simple preference ranker trained on pairwise comparisons.

    Uses logistic regression over TF-IDF + template/tone features.
    TODO: Replace with DPO or LLM-based preference model for better results.
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=200, ngram_range=(1, 2))
        self.model = LogisticRegression(random_state=42, max_iter=500)
        self.is_trained = False

        # Template and tone encodings
        self.template_to_idx = {
            "drake": 0,
            "distracted_boyfriend": 1,
            "tweet_screenshot": 2,
            "two_panel": 3,
            "top_text_bottom_text": 4,
        }
        self.tone_to_idx = {
            "dry": 0,
            "slightly unhinged": 1,
            "coy": 2,
        }

    def _featurize(self, candidate: MemeCandidate | dict) -> np.ndarray:
        """
        Extract features from a candidate.

        Features:
        - TF-IDF of caption
        - Template one-hot
        - Tone one-hot
        - Caption length
        """
        if isinstance(candidate, dict):
            caption = candidate.get("text", "")
            template = candidate.get("visual_template", "tweet_screenshot")
            tone = candidate.get("tone", "dry")
        else:
            caption = candidate.caption
            template = candidate.visual_template
            tone = candidate.tone

        # TF-IDF features
        tfidf_vec = self.vectorizer.transform([caption]).toarray()[0]

        # Template one-hot
        template_vec = np.zeros(len(self.template_to_idx))
        template_vec[self.template_to_idx.get(template, 2)] = 1

        # Tone one-hot
        tone_vec = np.zeros(len(self.tone_to_idx))
        tone_vec[self.tone_to_idx.get(tone, 0)] = 1

        # Caption length
        length_feature = np.array([len(caption.split())])

        # Concatenate all
        features = np.concatenate([tfidf_vec, template_vec, tone_vec, length_feature])
        return features

    def train(
        self,
        pairs_path: Path | str,
        time_decay_days: int = 90
    ) -> dict:
        """
        Train the ranker on pairwise labels.

        Args:
            pairs_path: Path to pairwise_labels.jsonl
            time_decay_days: Labels older than this get down-weighted

        Returns:
            Training statistics dict
        """
        pairs = load_jsonl(pairs_path, PairwiseLabel)

        if not pairs:
            print("Warning: No pairwise labels found, training dummy model")
            return self._train_dummy()

        # Extract texts for vectorizer fitting
        all_texts = []
        for pair in pairs:
            all_texts.append(pair.a.text)
            all_texts.append(pair.b.text)

        self.vectorizer.fit(all_texts)

        # Build training data: for each pair, winner gets label 1, loser gets 0
        X = []
        y = []
        weights = []

        for pair in pairs:
            # Featurize both
            feat_a = self._featurize(pair.a.model_dump())
            feat_b = self._featurize(pair.b.model_dump())

            # Add to training set based on winner
            if pair.winner == "a":
                X.append(feat_a)
                y.append(1)
                X.append(feat_b)
                y.append(0)
            else:
                X.append(feat_b)
                y.append(1)
                X.append(feat_a)
                y.append(0)

            # Calculate weight based on age
            weight = self._calculate_weight(pair.timestamp, time_decay_days)
            weights.extend([weight, weight])

        X = np.array(X)
        y = np.array(y)
        weights = np.array(weights)

        # Train logistic regression
        self.model.fit(X, y, sample_weight=weights)
        self.is_trained = True

        train_score = self.model.score(X, y, sample_weight=weights)

        return {
            "n_pairs": len(pairs),
            "n_samples": len(X),
            "train_accuracy": train_score,
        }

    def _train_dummy(self) -> dict:
        """Train a dummy model when no labels are available."""
        # Fit vectorizer on dummy data
        self.vectorizer.fit(["dummy text for vectorizer"])

        # Create dummy training data
        dummy_features = self._featurize({"text": "test", "visual_template": "drake", "tone": "dry"})
        X = np.array([dummy_features, dummy_features])
        y = np.array([1, 0])

        self.model.fit(X, y)
        self.is_trained = True

        return {
            "n_pairs": 0,
            "n_samples": 0,
            "train_accuracy": 0.5,
            "note": "Trained on dummy data; predictions will be random"
        }

    def _calculate_weight(self, timestamp: str, decay_days: int) -> float:
        """Calculate sample weight based on age (exponential decay)."""
        try:
            label_date = datetime.fromisoformat(timestamp)
            age_days = (datetime.now() - label_date).days

            if age_days <= 0:
                return 1.0

            # Exponential decay: weight = exp(-age / decay_days)
            weight = np.exp(-age_days / decay_days)
            return max(weight, 0.1)  # Floor at 0.1
        except Exception:
            return 1.0  # Default weight if parsing fails

    def score(self, candidate: MemeCandidate) -> float:
        """
        Score a single candidate.

        Returns:
            Preference score (higher = better)
        """
        if not self.is_trained:
            return 0.5  # Random score if not trained

        features = self._featurize(candidate).reshape(1, -1)
        # Return probability of being preferred
        return self.model.predict_proba(features)[0][1]

    def rank(self, candidates: list[MemeCandidate], top_k: int = 3) -> list[tuple[MemeCandidate, float]]:
        """
        Rank candidates by preference score.

        Returns:
            List of (candidate, score) tuples, sorted by score (descending)
        """
        if not candidates:
            return []

        scored = [(c, self.score(c)) for c in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored[:top_k]

    def save(self, model_path: Path | str) -> None:
        """Save trained model to disk."""
        model_path = Path(model_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "vectorizer": self.vectorizer,
            "model": self.model,
            "is_trained": self.is_trained,
            "template_to_idx": self.template_to_idx,
            "tone_to_idx": self.tone_to_idx,
        }

        with open(model_path, "wb") as f:
            pickle.dump(state, f)

    def load(self, model_path: Path | str) -> bool:
        """Load trained model from disk. Returns True if successful."""
        model_path = Path(model_path)
        if not model_path.exists():
            return False

        with open(model_path, "rb") as f:
            state = pickle.load(f)

        self.vectorizer = state["vectorizer"]
        self.model = state["model"]
        self.is_trained = state["is_trained"]
        self.template_to_idx = state["template_to_idx"]
        self.tone_to_idx = state["tone_to_idx"]

        return True


def train_dpo(pairs_path: Path | str, output_path: Path | str | None = None) -> PreferenceRanker:
    """
    Train a preference ranker using DPO-style pairwise labels.

    This is a simplified version using logistic regression.
    TODO: Implement true DPO with language model fine-tuning.

    Args:
        pairs_path: Path to pairwise_labels.jsonl
        output_path: Optional path to save trained model

    Returns:
        Trained PreferenceRanker
    """
    ranker = PreferenceRanker()
    stats = ranker.train(pairs_path)

    print(f"Training complete:")
    for key, val in stats.items():
        print(f"  {key}: {val}")

    if output_path:
        ranker.save(output_path)
        print(f"Model saved to {output_path}")

    return ranker

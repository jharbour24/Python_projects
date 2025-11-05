"""
Preference-based ranking model for meme candidates.

Trains on pairwise labels using logistic regression with custom features.
In future, could integrate DPO or LLM-based preference scoring.
"""

import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.linear_model import LogisticRegression

from .io_schemas import MemeCandidate, PairwiseLabel, load_jsonl


# ============================================================================
# Feature Engineering
# ============================================================================

def extract_features(candidate: MemeCandidate) -> np.ndarray:
    """
    Extract feature vector from a candidate.

    Features:
    - Caption length (normalized)
    - Template one-hot (5 dims)
    - Tone one-hot (3 dims)
    - Has local reference (binary)
    - Evidence count (normalized)

    Total: 11 features
    """
    features = []

    # Caption length (0-14 words, normalized to 0-1)
    word_count = len(candidate.caption.split())
    features.append(word_count / 14.0)

    # Template one-hot
    templates = ["drake", "distracted_boyfriend", "tweet_screenshot", "two_panel", "top_text_bottom_text"]
    template_vec = [1 if candidate.visual_template == t else 0 for t in templates]
    features.extend(template_vec)

    # Tone one-hot
    tones = ["dry", "slightly unhinged", "coy"]
    tone_vec = [1 if candidate.tone == t else 0 for t in tones]
    features.extend(tone_vec)

    # Has local reference (binary)
    local_keywords = ["brooklyn", "bushwick", "train", "mta", "l train", "venue"]
    has_local = any(kw in candidate.caption.lower() for kw in local_keywords)
    features.append(1 if has_local else 0)

    # Evidence count (normalized, cap at 5)
    evidence_count = min(len(candidate.evidence_refs), 5) / 5.0
    features.append(evidence_count)

    return np.array(features)


def compute_time_weight(timestamp: str, decay_days: int = 30) -> float:
    """
    Compute time-based weight for training sample.

    Recent samples get higher weight. Exponential decay.

    Args:
        timestamp: ISO8601 timestamp string
        decay_days: Number of days for weight to decay to ~0.5

    Returns:
        Weight between 0 and 1
    """
    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return 1.0  # Default weight if parse fails

    now = datetime.utcnow()
    age_days = (now - ts).days

    # Exponential decay: weight = exp(-age / decay_constant)
    decay_constant = decay_days / 0.693  # ln(2) ≈ 0.693
    weight = np.exp(-age_days / decay_constant)

    return weight


# ============================================================================
# Preference Ranker
# ============================================================================

class PreferenceRanker:
    """
    Logistic regression ranker trained on pairwise preferences.

    Features are extracted from candidate metadata (template, tone, length, etc.)
    Training uses pairwise labels with optional time-based weighting.
    """

    def __init__(self, time_decay_days: int = 30):
        self.model = LogisticRegression(
            random_state=42,
            max_iter=1000,
            class_weight="balanced"
        )
        self.time_decay_days = time_decay_days
        self.is_trained = False

    def train(self, pairs_path: Path) -> dict[str, float]:
        """
        Train on pairwise labels.

        Args:
            pairs_path: Path to pairwise_labels.jsonl

        Returns:
            Training metrics dict
        """
        pairs = load_jsonl(pairs_path, PairwiseLabel)

        if not pairs:
            print("Warning: No training pairs found, using dummy model")
            self._train_dummy()
            return {"n_pairs": 0, "accuracy": 0.0}

        # Build training data
        X_list = []
        y_list = []
        weights_list = []

        for pair in pairs:
            # Convert pair candidates to MemeCandidate-like objects
            cand_a = self._pair_to_candidate(pair.a)
            cand_b = self._pair_to_candidate(pair.b)

            # Extract features
            feat_a = extract_features(cand_a)
            feat_b = extract_features(cand_b)

            # Compute time weight
            weight = compute_time_weight(pair.timestamp, self.time_decay_days)

            # Create two training examples: winner vs loser and loser vs winner
            # This gives us both positive (1) and negative (0) examples
            if pair.winner == "a":
                # A beats B: positive example
                X_list.append(feat_a - feat_b)
                y_list.append(1)
                weights_list.append(weight)
                # B loses to A: negative example
                X_list.append(feat_b - feat_a)
                y_list.append(0)
                weights_list.append(weight)
            else:
                # B beats A: positive example
                X_list.append(feat_b - feat_a)
                y_list.append(1)
                weights_list.append(weight)
                # A loses to B: negative example
                X_list.append(feat_a - feat_b)
                y_list.append(0)
                weights_list.append(weight)

        X = np.array(X_list)
        y = np.array(y_list)
        weights = np.array(weights_list)

        # Train model
        self.model.fit(X, y, sample_weight=weights)
        self.is_trained = True

        # Compute training accuracy
        y_pred = self.model.predict(X)
        accuracy = np.mean(y_pred == y)

        return {
            "n_pairs": len(pairs),
            "accuracy": accuracy,
            "feature_dim": X.shape[1],
        }

    def _train_dummy(self) -> None:
        """Train a dummy model when no data is available."""
        # Create synthetic data with both classes
        np.random.seed(42)
        X = np.random.randn(10, 11)
        y = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1])  # Ensure both classes
        self.model.fit(X, y)
        self.is_trained = True

    def _pair_to_candidate(self, pair_cand) -> MemeCandidate:
        """Convert PairwiseCandidate to MemeCandidate for feature extraction."""
        # Extract metadata
        template = pair_cand.meta.template or "tweet_screenshot"
        tone = pair_cand.meta.tone or "dry"
        topic = pair_cand.meta.topic or ""

        return MemeCandidate(
            visual_template=template,
            local_hook=topic,
            tone=tone,
            caption=pair_cand.text,
            rationale="",
            evidence_refs=[]
        )

    def score(self, candidate: MemeCandidate) -> float:
        """
        Score a single candidate.

        Returns:
            Score between 0 and 1 (higher is better)
        """
        if not self.is_trained:
            return 0.5  # Neutral score

        features = extract_features(candidate)
        # Predict probability of being preferred
        # (We trained on feature diffs, so this is approximate)
        score = self.model.predict_proba(features.reshape(1, -1))[0, 1]
        return score

    def rank(self, candidates: list[MemeCandidate], top_k: int = 3) -> list[MemeCandidate]:
        """
        Rank candidates and return top-k.

        Args:
            candidates: List of candidates to rank
            top_k: Number of top candidates to return

        Returns:
            Sorted list of top-k candidates with scores attached
        """
        if not candidates:
            return []

        # Score all candidates
        scored = []
        for cand in candidates:
            score = self.score(cand)
            cand.score = score
            scored.append(cand)

        # Sort by score descending
        scored.sort(key=lambda c: c.score or 0.0, reverse=True)

        return scored[:top_k]

    def save(self, path: Path) -> None:
        """Save model to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "model": self.model,
            "time_decay_days": self.time_decay_days,
            "is_trained": self.is_trained,
        }
        with open(path, "wb") as f:
            pickle.dump(state, f)

    @classmethod
    def load(cls, path: Path) -> "PreferenceRanker":
        """Load model from disk."""
        with open(path, "rb") as f:
            state = pickle.load(f)

        ranker = cls(time_decay_days=state["time_decay_days"])
        ranker.model = state["model"]
        ranker.is_trained = state["is_trained"]
        return ranker


# ============================================================================
# TODO: DPO-style training
# ============================================================================

def train_dpo(pairs_path: Path, model_path: Optional[Path] = None):
    """
    Train using Direct Preference Optimization.

    TODO: Implement DPO-style training with language model.
    For now, falls back to logistic regression.
    """
    print("Note: DPO training not yet implemented, using logistic regression")

    ranker = PreferenceRanker()
    metrics = ranker.train(pairs_path)

    if model_path:
        ranker.save(model_path)

    return ranker, metrics

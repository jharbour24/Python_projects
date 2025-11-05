"""
Evaluation harness for weekly re-tuning and metrics reporting.

Computes diversity, violation rate, and share-score proxies.
"""

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .filter import compute_violation_rate, get_violation_summary, filter_candidates
from .io_schemas import MemeCandidate, PairwiseLabel, load_jsonl
from .ranker import PreferenceRanker


# ============================================================================
# Evaluation Metrics
# ============================================================================

def compute_diversity(candidates: list[MemeCandidate]) -> dict[str, float]:
    """
    Compute diversity metrics for a set of candidates.

    Measures:
    - Template entropy
    - Tone entropy
    - Topic diversity (based on local_hook terms)

    Returns:
        Dict of metric names to values
    """
    if not candidates:
        return {
            "template_entropy": 0.0,
            "tone_entropy": 0.0,
            "topic_diversity": 0.0,
        }

    # Template distribution
    templates = [c.visual_template for c in candidates]
    template_entropy = _compute_entropy(templates)

    # Tone distribution
    tones = [c.tone for c in candidates]
    tone_entropy = _compute_entropy(tones)

    # Topic diversity (unique terms in local_hooks)
    all_terms = []
    for c in candidates:
        terms = c.local_hook.lower().split()
        all_terms.extend(terms)

    unique_terms = len(set(all_terms))
    total_terms = len(all_terms)
    topic_diversity = unique_terms / total_terms if total_terms > 0 else 0.0

    return {
        "template_entropy": template_entropy,
        "tone_entropy": tone_entropy,
        "topic_diversity": topic_diversity,
    }


def _compute_entropy(items: list[str]) -> float:
    """Compute Shannon entropy of a list of categorical items."""
    if not items:
        return 0.0

    counts = Counter(items)
    total = len(items)
    probs = [count / total for count in counts.values()]

    entropy = -sum(p * np.log2(p) for p in probs if p > 0)
    return entropy


def compute_share_score(
    candidates: list[MemeCandidate],
    top_k: int = 3
) -> dict[str, float]:
    """
    Compute share-score proxy metrics.

    Proxies for shareability:
    - Caption brevity (shorter = more shareable)
    - Has personal pronoun (relatability)
    - Local specificity (in-group appeal)

    Returns:
        Dict of metric names to average scores
    """
    if not candidates:
        return {
            "avg_brevity": 0.0,
            "has_personal_pronoun": 0.0,
            "local_specificity": 0.0,
        }

    top_candidates = candidates[:top_k]

    # Brevity score (inverse of word count, normalized)
    word_counts = [len(c.caption.split()) for c in top_candidates]
    avg_word_count = np.mean(word_counts)
    brevity = 1.0 - (avg_word_count / 14.0)  # Max 14 words

    # Has personal pronoun
    personal_pronouns = ["i", "me", "my", "we", "us", "our"]
    has_pronoun = [
        any(p in c.caption.lower() for p in personal_pronouns)
        for c in top_candidates
    ]
    pronoun_rate = np.mean(has_pronoun)

    # Local specificity (has Brooklyn/transit terms)
    local_terms = ["brooklyn", "bushwick", "train", "mta", "l train", "venue", "bed-stuy"]
    has_local = [
        any(term in c.caption.lower() or term in c.local_hook.lower() for term in local_terms)
        for c in top_candidates
    ]
    local_rate = np.mean(has_local)

    return {
        "avg_brevity": brevity,
        "has_personal_pronoun": pronoun_rate,
        "local_specificity": local_rate,
    }


def evaluate_generation(
    candidates: list[MemeCandidate],
    data_dir: Path
) -> dict[str, any]:
    """
    Run full evaluation on a generation batch.

    Args:
        candidates: All candidates before filtering
        data_dir: Path to data directory (for loading pairs)

    Returns:
        Dict of all metrics
    """
    # Filter candidates
    keepers, rejections = filter_candidates(candidates)

    # Compute metrics
    diversity = compute_diversity(keepers)
    share_scores = compute_share_score(keepers)
    violation_rate = len(rejections) / len(candidates) if candidates else 0.0
    violation_summary = get_violation_summary(rejections)

    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "n_candidates": len(candidates),
        "n_keepers": len(keepers),
        "n_rejected": len(rejections),
        "violation_rate": violation_rate,
        "violation_summary": violation_summary,
        **diversity,
        **share_scores,
    }

    return metrics


# ============================================================================
# Weekly Retraining
# ============================================================================

def weekly_retrain(
    data_dir: Path,
    model_path: Path,
    report_path: Optional[Path] = None
) -> dict[str, any]:
    """
    Weekly retraining workflow.

    Steps:
    1. Load new pairwise labels
    2. Retrain ranker with time decay
    3. Compute metrics on held-out pairs
    4. Save model and report

    Args:
        data_dir: Path to data directory
        model_path: Path to save model
        report_path: Optional path to save markdown report

    Returns:
        Metrics dict
    """
    pairs_path = data_dir / "pairwise_labels.jsonl"

    # Train model
    ranker = PreferenceRanker(time_decay_days=30)
    train_metrics = ranker.train(pairs_path)

    # Save model
    ranker.save(model_path)

    # Generate report
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "training": train_metrics,
    }

    if report_path:
        _write_report(report, report_path)

    return report


def _write_report(report: dict, path: Path) -> None:
    """Write evaluation report as markdown."""
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Weekly Evaluation Report",
        f"\n**Generated:** {report['timestamp']}\n",
        "## Training Metrics",
    ]

    for key, value in report.get("training", {}).items():
        lines.append(f"- **{key}**: {value}")

    if "evaluation" in report:
        lines.append("\n## Evaluation Metrics")
        for key, value in report["evaluation"].items():
            if isinstance(value, dict):
                lines.append(f"\n### {key}")
                for k, v in value.items():
                    lines.append(f"- **{k}**: {v}")
            else:
                lines.append(f"- **{key}**: {value}")

    with open(path, "w") as f:
        f.write("\n".join(lines))


def print_metrics_table(metrics: dict) -> None:
    """Print metrics as a formatted table."""
    print("\n" + "=" * 60)
    print("EVALUATION METRICS")
    print("=" * 60)

    # Generation stats
    print(f"\nGeneration:")
    print(f"  Candidates:     {metrics.get('n_candidates', 0)}")
    print(f"  Keepers:        {metrics.get('n_keepers', 0)}")
    print(f"  Rejected:       {metrics.get('n_rejected', 0)}")
    print(f"  Violation Rate: {metrics.get('violation_rate', 0):.2%}")

    # Diversity
    print(f"\nDiversity:")
    print(f"  Template Entropy: {metrics.get('template_entropy', 0):.3f}")
    print(f"  Tone Entropy:     {metrics.get('tone_entropy', 0):.3f}")
    print(f"  Topic Diversity:  {metrics.get('topic_diversity', 0):.3f}")

    # Share scores
    print(f"\nShare Score Proxies:")
    print(f"  Brevity:          {metrics.get('avg_brevity', 0):.3f}")
    print(f"  Has Pronoun:      {metrics.get('has_personal_pronoun', 0):.3f}")
    print(f"  Local Specific:   {metrics.get('local_specificity', 0):.3f}")

    # Violations
    if "violation_summary" in metrics:
        print(f"\nViolation Summary:")
        for rule, count in metrics["violation_summary"].items():
            print(f"  {rule}: {count}")

    print("=" * 60 + "\n")

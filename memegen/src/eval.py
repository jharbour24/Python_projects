"""
Evaluation harness for measuring meme quality and diversity.
"""

from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

from .constitution import check_constitution
from .io_schemas import MemeCandidate, load_jsonl
from .ranker import PreferenceRanker, train_dpo


class MemeEvaluator:
    """Evaluates meme candidate quality and diversity."""

    def __init__(self):
        self.metrics = {}

    def evaluate(
        self,
        candidates: list[MemeCandidate],
        verbose: bool = True
    ) -> dict:
        """
        Compute evaluation metrics for a set of candidates.

        Metrics:
        - diversity_score: Template and topic entropy
        - avg_caption_length: Average words per caption
        - violation_rate: % that fail constitution checks
        - template_distribution: Counter of templates used

        Returns:
            Dict of metrics
        """
        if not candidates:
            return {
                "n_candidates": 0,
                "error": "No candidates to evaluate"
            }

        # Template diversity (entropy)
        templates = [c.visual_template for c in candidates]
        template_entropy = self._calculate_entropy(templates)

        # Tone diversity
        tones = [c.tone for c in candidates]
        tone_entropy = self._calculate_entropy(tones)

        # Caption length stats
        caption_lengths = [len(c.caption.split()) for c in candidates]
        avg_length = np.mean(caption_lengths)
        std_length = np.std(caption_lengths)

        # Violation rate
        violations_count = 0
        for candidate in candidates:
            violations = check_constitution(candidate)
            if any(v.severity == "block" for v in violations):
                violations_count += 1
        violation_rate = violations_count / len(candidates)

        # Template distribution
        template_counts = Counter(templates)

        metrics = {
            "n_candidates": len(candidates),
            "diversity_score": (template_entropy + tone_entropy) / 2,
            "template_entropy": template_entropy,
            "tone_entropy": tone_entropy,
            "avg_caption_length": avg_length,
            "std_caption_length": std_length,
            "violation_rate": violation_rate,
            "template_distribution": dict(template_counts),
        }

        self.metrics = metrics

        if verbose:
            self.print_metrics()

        return metrics

    def _calculate_entropy(self, items: list) -> float:
        """Calculate Shannon entropy for a list of items."""
        if not items:
            return 0.0

        counts = Counter(items)
        total = len(items)
        probs = [count / total for count in counts.values()]

        entropy = -sum(p * np.log2(p) for p in probs if p > 0)
        return entropy

    def print_metrics(self) -> None:
        """Pretty-print evaluation metrics."""
        if not self.metrics:
            print("No metrics to display")
            return

        print("\n" + "=" * 50)
        print("EVALUATION METRICS")
        print("=" * 50)

        print(f"Candidates: {self.metrics['n_candidates']}")
        print(f"Diversity Score: {self.metrics['diversity_score']:.2f}")
        print(f"  Template Entropy: {self.metrics['template_entropy']:.2f}")
        print(f"  Tone Entropy: {self.metrics['tone_entropy']:.2f}")
        print(f"Caption Length: {self.metrics['avg_caption_length']:.1f} +/- {self.metrics['std_caption_length']:.1f} words")
        print(f"Violation Rate: {self.metrics['violation_rate']:.1%}")

        print("\nTemplate Distribution:")
        for template, count in sorted(
            self.metrics['template_distribution'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            pct = count / self.metrics['n_candidates'] * 100
            print(f"  {template:25s}: {count:2d} ({pct:4.1f}%)")

        print("=" * 50 + "\n")


def weekly_retrain(
    data_dir: Path | str,
    output_dir: Path | str,
    verbose: bool = True
) -> dict:
    """
    Weekly retraining routine:
    1. Load new pairwise labels
    2. Retrain preference ranker
    3. Evaluate on recent candidates
    4. Save report

    Args:
        data_dir: Directory containing pairwise_labels.jsonl
        output_dir: Directory to save model and report
        verbose: Print progress

    Returns:
        Dict with retraining stats
    """
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        print("\n= Starting weekly retraining...")

    # 1. Train ranker
    pairs_path = data_dir / "pairwise_labels.jsonl"
    model_path = output_dir / "ranker_model.pkl"

    ranker = train_dpo(pairs_path, model_path)

    # 2. Evaluate if we have recent candidates
    recent_candidates_path = output_dir / f"{datetime.now().strftime('%Y-%m-%d')}_top.jsonl"

    eval_metrics = {}
    if recent_candidates_path.exists():
        candidates = load_jsonl(recent_candidates_path, MemeCandidate)
        evaluator = MemeEvaluator()
        eval_metrics = evaluator.evaluate(candidates, verbose=verbose)

    # 3. Save report
    report_path = output_dir / f"retrain_report_{datetime.now().strftime('%Y%m%d')}.txt"

    with open(report_path, "w") as f:
        f.write(f"WEEKLY RETRAIN REPORT\n")
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write(f"\n{'=' * 50}\n\n")

        f.write(f"RANKER TRAINING\n")
        f.write(f"  Pairs file: {pairs_path}\n")
        f.write(f"  Model saved: {model_path}\n")

        if eval_metrics:
            f.write(f"\nEVALUATION\n")
            for key, val in eval_metrics.items():
                f.write(f"  {key}: {val}\n")

    if verbose:
        print(f"\n Retraining complete. Report saved to {report_path}")

    return {
        "report_path": str(report_path),
        "model_path": str(model_path),
        "eval_metrics": eval_metrics,
    }

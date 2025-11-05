"""
Data schemas for the meme generation pipeline.
Defines Pydantic models for all data structures and JSONL I/O helpers.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Core Data Models
# ============================================================================

class SeedExample(BaseModel):
    """A seed meme example for training and style reference."""

    id: str
    text: str
    topic: Literal["venue", "borough", "transit", "party"]
    trope: Literal["queue", "cover", "L-train", "after-hours", "DIY"]
    device: Literal["exaggeration", "misdirection", "deadpan", "code-switch"]
    lol_score: int = Field(ge=1, le=5)


class PairwiseMeta(BaseModel):
    """Metadata for a meme candidate in a pairwise comparison."""

    template: Optional[str] = None
    topic: Optional[str] = None
    tone: Optional[str] = None


class PairwiseCandidate(BaseModel):
    """A candidate in a pairwise comparison."""

    text: str
    meta: PairwiseMeta = Field(default_factory=PairwiseMeta)


class PairwiseLabel(BaseModel):
    """A pairwise preference label for training the ranker."""

    pair_id: str
    a: PairwiseCandidate
    b: PairwiseCandidate
    winner: Literal["a", "b"]
    panel: str = "seed_panel_v1"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Ensure timestamp is valid ISO8601."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError(f"Invalid ISO8601 timestamp: {v}")


class LocalSnippet(BaseModel):
    """A local snippet of current Brooklyn/NYC cultural context."""

    id: str
    date: str
    source: Literal["manual", "newsletter", "rss", "notes"]
    text: str
    tags: list[str] = Field(default_factory=list)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Ensure date is YYYY-MM-DD format."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError(f"Date must be YYYY-MM-DD format, got: {v}")


class MemeCandidate(BaseModel):
    """A generated meme concept candidate."""

    visual_template: Literal[
        "drake",
        "distracted_boyfriend",
        "tweet_screenshot",
        "two_panel",
        "top_text_bottom_text"
    ]
    local_hook: str
    tone: Literal["dry", "slightly unhinged", "coy"]
    caption: str
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)
    score: Optional[float] = None

    @field_validator("caption")
    @classmethod
    def validate_caption_length(cls, v: str) -> str:
        """Ensure caption is ≤ 14 words."""
        word_count = len(v.split())
        if word_count > 14:
            raise ValueError(
                f"Caption must be ≤ 14 words, got {word_count}: {v}"
            )
        return v


# ============================================================================
# JSONL I/O Helpers
# ============================================================================

def load_jsonl(path: Path, model_class: type[BaseModel]) -> list[BaseModel]:
    """Load and validate JSONL file into Pydantic models."""
    if not path.exists():
        return []

    results = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                obj = model_class.model_validate(data)
                results.append(obj)
            except Exception as e:
                print(f"Warning: Skipping invalid line {line_num} in {path}: {e}")

    return results


def save_jsonl(path: Path, items: list[BaseModel]) -> None:
    """Save Pydantic models to JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            json_str = item.model_dump_json()
            f.write(json_str + "\n")


def append_jsonl(path: Path, item: BaseModel) -> None:
    """Append a single item to JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a", encoding="utf-8") as f:
        json_str = item.model_dump_json()
        f.write(json_str + "\n")


def load_raw_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL as raw dicts without validation."""
    if not path.exists():
        return []

    results = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))

    return results

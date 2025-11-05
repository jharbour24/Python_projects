"""
Data schemas and I/O utilities for the meme generation pipeline.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class SeedExample(BaseModel):
    """A seed meme example for training."""
    id: str
    text: str
    topic: Literal["venue", "borough", "transit", "party"]
    trope: Literal["queue", "cover", "L-train", "after-hours", "DIY"]
    device: Literal["exaggeration", "misdirection", "deadpan", "code-switch"]
    lol_score: int = Field(ge=1, le=5)


class MemeMetadata(BaseModel):
    """Metadata for a meme in pairwise comparison."""
    text: str
    visual_template: Optional[str] = None
    tone: Optional[str] = None


class PairwiseLabel(BaseModel):
    """A pairwise preference label between two meme candidates."""
    pair_id: str
    a: MemeMetadata
    b: MemeMetadata
    winner: Literal["a", "b"]
    panel: str
    timestamp: str


class LocalSnippet(BaseModel):
    """A snippet of local/current information from NYC/Brooklyn."""
    id: str
    date: str
    source: Literal["manual", "newsletter", "rss", "notes"]
    text: str
    tags: list[str] = Field(default_factory=list)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Ensure date is in YYYY-MM-DD format."""
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"Date must be in YYYY-MM-DD format, got: {v}")


class MemeCandidate(BaseModel):
    """A generated meme candidate."""
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

    @field_validator("caption")
    @classmethod
    def validate_caption_length(cls, v: str) -> str:
        """Ensure caption is 14 words or fewer."""
        word_count = len(v.split())
        if word_count > 14:
            raise ValueError(f"Caption must be d14 words, got {word_count}: {v}")
        return v


# JSONL I/O utilities

def load_jsonl(file_path: Path | str, model_class: type[BaseModel]) -> list[BaseModel]:
    """Load and validate JSONL file into a list of Pydantic models."""
    file_path = Path(file_path)
    if not file_path.exists():
        return []

    items = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                items.append(model_class(**data))
            except Exception as e:
                print(f"Warning: Skipping line {line_num} in {file_path}: {e}")

    return items


def save_jsonl(
    items: list[BaseModel | dict],
    file_path: Path | str,
    append: bool = False
) -> None:
    """Save a list of Pydantic models or dicts to a JSONL file."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    mode = "a" if append else "w"
    with open(file_path, mode, encoding="utf-8") as f:
        for item in items:
            if isinstance(item, BaseModel):
                line = item.model_dump_json()
            else:
                line = json.dumps(item)
            f.write(line + "\n")


def validate_jsonl(file_path: Path | str, model_class: type[BaseModel]) -> tuple[int, int]:
    """
    Validate a JSONL file against a schema.

    Returns:
        (valid_count, error_count)
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return (0, 0)

    valid = 0
    errors = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                model_class(**data)
                valid += 1
            except Exception as e:
                errors += 1
                print(f"Line {line_num}: {e}")

    return (valid, errors)

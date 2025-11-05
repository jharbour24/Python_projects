"""
Constrained meme concept generator for queer Brooklyn nightlife.
"""

import json
import random
from typing import Any

from .io_schemas import LocalSnippet, MemeCandidate

# Generator prompt template
GENERATOR_PROMPT = """
You are a culturally-tuned meme writer for queer Brooklyn nightlife (ages 20-40).

AUDIENCE: Queer folks who go out in Brooklyn - know the venues, the vibes, the chaos.

TONE: Witty, self-aware, lightly chaotic; slang-literate; NO punching down.

CONSTRAINTS:
- Must reference a current/recent local hook from provided snippets
- Output ONLY valid JSON with these exact fields:
  * visual_template: one of [drake, distracted_boyfriend, tweet_screenshot, two_panel, top_text_bottom_text]
  * local_hook: specific venue/event/MTA moment (1 sentence)
  * tone: one of [dry, slightly unhinged, coy]
  * caption: d 14 words, no hashtags
  * rationale: why this hits now (1 sentence)
  * evidence_refs: list of snippet IDs used
- No venue doxxing; only reference places publicly promoting events
- No profanity stronger than PG-13
- Favor self-deprecation and affectionate in-jokes over meanness

SNIPPETS:
{snippets}

Generate {n} meme concepts as a JSON array.
"""

# Template choices with weights for variety
TEMPLATE_WEIGHTS = {
    "drake": 0.25,
    "distracted_boyfriend": 0.15,
    "tweet_screenshot": 0.35,  # Most versatile
    "two_panel": 0.15,
    "top_text_bottom_text": 0.10,
}

# Borough/transit terms that should appear
REQUIRED_LOCAL_TERMS = [
    "L train", "G train", "JMZ", "Bushwick", "Ridgewood", "Bed-Stuy",
    "Williamsburg", "Crown Heights", "Prospect Park", "Maria Hernandez",
    "Metropolitan", "Myrtle-Wyckoff", "Brooklyn", "BK", "MTA"
]


def draft_candidates(
    snippets: list[LocalSnippet],
    n: int = 12,
    use_llm: bool = False
) -> list[MemeCandidate]:
    """
    Generate n meme candidates based on provided snippets.

    Args:
        snippets: Recent local snippets to draw from
        n: Number of candidates to generate
        use_llm: If True, attempt LLM generation (stub); else use templates

    Returns:
        List of MemeCandidate objects
    """
    if not snippets:
        print("Warning: No snippets provided for generation")
        return []

    if use_llm:
        # Stub for LLM-based generation
        # In production: call OpenAI/Anthropic API with GENERATOR_PROMPT
        print("LLM generation not implemented; using template-based fallback")
        return _template_based_generation(snippets, n)
    else:
        return _template_based_generation(snippets, n)


def _template_based_generation(
    snippets: list[LocalSnippet],
    n: int
) -> list[MemeCandidate]:
    """
    Template-based fallback generator.

    Creates semi-random but valid meme candidates by mixing templates with snippets.
    """
    candidates = []
    templates = list(TEMPLATE_WEIGHTS.keys())
    tones = ["dry", "slightly unhinged", "coy"]

    # Sample snippet templates for variety
    caption_templates = [
        "when the {term} is {adjective} but you already paid cover",
        "{term}: a love story in {number} acts",
        "me explaining {term} to someone who just moved here",
        "POV: you're waiting for the {term}",
        "{term} hit different at 2am",
        "telling myself I'll leave by midnight knowing the {term}",
        "the {term} to {term} pipeline is real",
        "{term} apologists when you ask them literally anything",
        "my bank account vs my {term} plans",
        "nobody: / me: time to check the {term}",
    ]

    used_snippets = random.sample(snippets, min(len(snippets), n))

    for i, snippet in enumerate(used_snippets):
        if i >= n:
            break

        # Pick random template
        template = random.choice(templates)
        tone = random.choice(tones)

        # Extract a local term from snippet or use a generic one
        local_term = _extract_local_term(snippet.text)

        # Generate caption
        caption_template = random.choice(caption_templates)
        caption = _fill_caption_template(caption_template, snippet, local_term)

        # Ensure caption is d14 words
        caption = _truncate_caption(caption, 14)

        try:
            candidate = MemeCandidate(
                visual_template=template,
                local_hook=snippet.text[:100],  # Use snippet as hook
                tone=tone,
                caption=caption,
                rationale=f"References current {', '.join(snippet.tags[:2])} moment",
                evidence_refs=[snippet.id]
            )
            candidates.append(candidate)
        except Exception as e:
            print(f"Warning: Failed to create candidate: {e}")
            continue

    return candidates


def _extract_local_term(text: str) -> str:
    """Extract a Brooklyn/NYC term from text, or return a default."""
    text_lower = text.lower()
    for term in REQUIRED_LOCAL_TERMS:
        if term.lower() in text_lower:
            return term

    # Fallback to common terms
    fallbacks = ["the train", "the venue", "the line", "Brooklyn", "the party"]
    return random.choice(fallbacks)


def _fill_caption_template(
    template: str,
    snippet: LocalSnippet,
    local_term: str
) -> str:
    """Fill in a caption template with context."""
    adjectives = ["chaotic", "packed", "sketchy", "iconic", "unhinged", "perfect"]
    numbers = ["two", "three", "four", "five"]

    # Extract another term if needed
    terms = snippet.tags if snippet.tags else ["the scene", "the vibe"]
    secondary_term = random.choice(terms) if terms else "everything"

    caption = template.format(
        term=local_term,
        adjective=random.choice(adjectives),
        number=random.choice(numbers)
    )

    # Handle multiple {term} replacements
    if caption.count("{term}") > 0:
        caption = caption.replace("{term}", secondary_term, 1)

    return caption


def _truncate_caption(caption: str, max_words: int) -> str:
    """Truncate caption to max_words."""
    words = caption.split()
    if len(words) <= max_words:
        return caption

    return " ".join(words[:max_words])


def validate_candidate(candidate: dict[str, Any]) -> MemeCandidate | None:
    """
    Validate and parse a candidate dict into a MemeCandidate.

    Returns None if validation fails.
    """
    try:
        return MemeCandidate(**candidate)
    except Exception as e:
        print(f"Validation error: {e}")
        return None


def parse_llm_output(llm_response: str) -> list[MemeCandidate]:
    """
    Parse LLM JSON output into MemeCandidate objects.

    Handles both array and single-object responses.
    """
    try:
        data = json.loads(llm_response)

        if isinstance(data, list):
            candidates = [validate_candidate(c) for c in data]
            return [c for c in candidates if c is not None]
        elif isinstance(data, dict):
            candidate = validate_candidate(data)
            return [candidate] if candidate else []
        else:
            print(f"Unexpected LLM output format: {type(data)}")
            return []

    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM output as JSON: {e}")
        return []

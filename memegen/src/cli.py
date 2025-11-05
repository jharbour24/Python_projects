"""
Command-line interface for the meme generation pipeline.
"""

from datetime import datetime
from pathlib import Path

import click
from PIL import Image, ImageDraw, ImageFont

from .eval import MemeEvaluator, weekly_retrain
from .filter import filter_with_retry
from .generator import draft_candidates
from .io_schemas import MemeCandidate, save_jsonl
from .rag import RAGIndex
from .ranker import PreferenceRanker, train_dpo

# Default paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SOURCES_DIR = DATA_DIR / "sources"
OUT_DIR = PROJECT_ROOT / "out"
TEMPLATES_DIR = PROJECT_ROOT / "memes" / "templates"


@click.group()
def cli():
    """Meme generation pipeline for queer Brooklyn nightlife."""
    pass


@cli.command()
@click.option("--sources-dir", default=SOURCES_DIR, type=click.Path(), help="Directory with source JSONL files")
@click.option("--cache", default=DATA_DIR / "rag_cache.pkl", type=click.Path(), help="Cache file for RAG index")
@click.option("--backend", default="tfidf", type=click.Choice(["tfidf", "sentence-transformers"]), help="Embedding backend")
def ingest(sources_dir, cache, backend):
    """Index local snippets for RAG retrieval."""
    click.echo(f"Indexing snippets from {sources_dir}...")

    rag = RAGIndex(backend=backend)
    count = rag.index(sources_dir)

    if count > 0:
        rag.save(cache)
        click.echo(f"Indexed {count} snippets, saved to {cache}")
    else:
        click.echo("No snippets found. Add JSONL files to data/sources/")


@cli.command()
@click.option("--n", default=12, help="Number of candidates to generate")
@click.option("--top-k", default=3, help="Number of top candidates to select")
@click.option("--cache", default=DATA_DIR / "rag_cache.pkl", type=click.Path(), help="RAG index cache")
@click.option("--model", default=DATA_DIR / "ranker_model.pkl", type=click.Path(), help="Ranker model path")
@click.option("--out-dir", default=OUT_DIR, type=click.Path(), help="Output directory")
@click.option("--render/--no-render", default=True, help="Render PNG images")
def generate(n, top_k, cache, model, out_dir, render):
    """Run full pipeline: RAG -> generate -> filter -> rank."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    click.echo("Starting meme generation pipeline...\n")

    # 1. Load RAG index
    click.echo("1. Loading RAG index...")
    rag = RAGIndex()
    if not rag.load(cache):
        click.echo(f"No RAG cache found at {cache}. Run 'ingest' first.")
        return

    # 2. Retrieve relevant snippets
    click.echo("2. Retrieving relevant snippets...")
    query_terms = ["Brooklyn", "nightlife", "L train", "venue", "party"]
    snippets = rag.retrieve(query_terms, k=15)
    click.echo(f"   Retrieved {len(snippets)} snippets")

    if not snippets:
        click.echo("No snippets available. Add data to sources/")
        return

    # 3. Generate candidates with filtering
    click.echo(f"3. Generating {n} candidates with safety filters...")
    safe_candidates = filter_with_retry(
        draft_candidates,
        snippets,
        target_count=n,
        max_retries=2,
        verbose=True
    )

    if not safe_candidates:
        click.echo("No safe candidates generated")
        return

    # 4. Rank candidates
    click.echo(f"\n4. Ranking candidates...")
    ranker = PreferenceRanker()

    if Path(model).exists():
        ranker.load(model)
        click.echo(f"   Loaded ranker model from {model}")
    else:
        click.echo(f"   No trained model found, using random ranking")

    ranked = ranker.rank(safe_candidates, top_k=top_k)

    # 5. Save outputs
    click.echo(f"\n5. Saving outputs to {out_dir}...")

    today = datetime.now().strftime("%Y-%m-%d")

    # Save all candidates
    all_path = out_dir / f"{today}_top.jsonl"
    save_jsonl(safe_candidates, all_path)
    click.echo(f"   Saved all candidates: {all_path}")

    # Save top-k
    top_candidates = [c for c, score in ranked]
    top_path = out_dir / f"{today}_top3.jsonl"
    save_jsonl(top_candidates, top_path)
    click.echo(f"   Saved top {top_k}: {top_path}")

    # 6. Render images
    if render:
        click.echo(f"\n6. Rendering images...")
        for i, (candidate, score) in enumerate(ranked, 1):
            img_path = out_dir / f"{today}_meme_{i}.png"
            _render_tweet_screenshot(candidate, img_path, score)
            click.echo(f"   Rendered: {img_path}")

    # 7. Display results
    click.echo("\n" + "=" * 60)
    click.echo("TOP MEME CONCEPTS")
    click.echo("=" * 60)

    for i, (candidate, score) in enumerate(ranked, 1):
        click.echo(f"\n#{i} (score: {score:.3f})")
        click.echo(f"Template: {candidate.visual_template}")
        click.echo(f"Tone: {candidate.tone}")
        click.echo(f"Caption: {candidate.caption}")
        click.echo(f"Hook: {candidate.local_hook[:80]}...")

    click.echo("\nGeneration complete!")


@cli.command()
@click.option("--pairs", default=DATA_DIR / "pairwise_labels.jsonl", type=click.Path(), help="Pairwise labels file")
@click.option("--output", default=DATA_DIR / "ranker_model.pkl", type=click.Path(), help="Output model path")
def retrain(pairs, output):
    """Train preference ranker on pairwise labels."""
    click.echo(f"Training ranker on {pairs}...")

    ranker = train_dpo(pairs, output)

    click.echo(f"Ranker trained and saved to {output}")


@cli.command()
@click.option("--candidates", default=OUT_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_top.jsonl", type=click.Path(), help="Candidates file")
def eval(candidates):
    """Evaluate candidate quality and diversity."""
    from .io_schemas import load_jsonl

    candidates_path = Path(candidates)

    if not candidates_path.exists():
        click.echo(f"Candidates file not found: {candidates_path}")
        return

    click.echo(f"Evaluating candidates from {candidates_path}...")

    candidates_list = load_jsonl(candidates_path, MemeCandidate)

    evaluator = MemeEvaluator()
    evaluator.evaluate(candidates_list, verbose=True)


@cli.command()
@click.option("--data-dir", default=DATA_DIR, type=click.Path(), help="Data directory")
@click.option("--out-dir", default=OUT_DIR, type=click.Path(), help="Output directory")
def weekly(data_dir, out_dir):
    """Run weekly retraining routine."""
    click.echo("Running weekly retraining...")

    results = weekly_retrain(data_dir, out_dir, verbose=True)

    click.echo(f"\nWeekly retrain complete!")
    click.echo(f"   Report: {results['report_path']}")


def _render_tweet_screenshot(
    candidate: MemeCandidate,
    output_path: Path,
    score: float
) -> None:
    """
    Render a simple tweet-screenshot style meme.

    Creates a white background with black text to simulate a tweet.
    """
    # Image settings
    width, height = 600, 400
    bg_color = (255, 255, 255)
    text_color = (20, 23, 26)

    # Create image
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Try to use a nicer font, fall back to default
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_tiny = ImageFont.load_default()

    # Draw header
    draw.text((30, 30), "@bkNightlifeMemes", fill=text_color, font=font_small)

    # Draw caption (wrapped)
    caption_lines = _wrap_text(candidate.caption, 40)
    y_pos = 80
    for line in caption_lines:
        draw.text((30, y_pos), line, fill=text_color, font=font_large)
        y_pos += 40

    # Draw metadata
    y_pos = height - 100
    draw.text((30, y_pos), f"Tone: {candidate.tone}", fill=(100, 100, 100), font=font_tiny)
    draw.text((30, y_pos + 20), f"Template: {candidate.visual_template}", fill=(100, 100, 100), font=font_tiny)
    draw.text((30, y_pos + 40), f"Score: {score:.3f}", fill=(100, 100, 100), font=font_tiny)

    # Save
    img.save(output_path)


def _wrap_text(text: str, max_width: int) -> list[str]:
    """Simple text wrapping by word boundaries."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        if len(test_line) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    return lines


if __name__ == "__main__":
    cli()

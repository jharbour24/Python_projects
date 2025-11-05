"""
Command-line interface for the meme generation pipeline.

Commands:
- ingest: Index local snippets
- generate: Run full pipeline (RAG → generate → filter → rank)
- retrain: Train preference model on pairwise labels
- eval: Run evaluation and print metrics
"""

import json
from datetime import datetime
from pathlib import Path

import click
from PIL import Image, ImageDraw, ImageFont

from . import eval as eval_module
from .filter import filter_candidates
from .generator import draft_candidates
from .io_schemas import save_jsonl
from .rag import RAG_QUERY_TEMPLATES, RAGIndex
from .ranker import PreferenceRanker


# ============================================================================
# CLI Setup
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SOURCES_DIR = DATA_DIR / "sources"
OUT_DIR = PROJECT_ROOT / "out"
TEMPLATES_DIR = PROJECT_ROOT / "memes" / "templates"

INDEX_PATH = DATA_DIR / "rag_index.pkl"
MODEL_PATH = DATA_DIR / "ranker_model.pkl"


@click.group()
def cli():
    """Queer Brooklyn Memegen Pipeline"""
    pass


# ============================================================================
# Commands
# ============================================================================

@cli.command()
@click.option("--backend", default="tfidf", type=click.Choice(["tfidf", "sbert"]))
def ingest(backend):
    """Index local snippets from data/sources/*.jsonl"""
    click.echo(f"Building RAG index with {backend} backend...")

    index = RAGIndex(backend=backend)
    n_snippets = index.build_index(SOURCES_DIR)

    if n_snippets == 0:
        click.echo("⚠️  No snippets found. Add .jsonl files to data/sources/")
        return

    index.save(INDEX_PATH)
    click.echo(f"✓ Indexed {n_snippets} snippets → {INDEX_PATH}")


@cli.command()
@click.option("--n-candidates", "-n", default=12, help="Number of candidates to generate")
@click.option("--top-k", "-k", default=3, help="Number of top candidates to return")
@click.option("--query", "-q", multiple=True, help="Additional query terms")
def generate(n_candidates, top_k, query):
    """Run full generation pipeline"""
    click.echo("🎨 Running meme generation pipeline...\n")

    # Load RAG index
    if not INDEX_PATH.exists():
        click.echo("⚠️  No index found. Run 'ingest' first.")
        return

    click.echo("Loading RAG index...")
    index = RAGIndex.load(INDEX_PATH)

    # Build query
    query_terms = list(RAG_QUERY_TEMPLATES[:5])  # Use first 5 default templates
    if query:
        query_terms.extend(query)

    click.echo(f"Retrieving snippets for: {', '.join(query_terms[:3])}...")
    snippets = index.retrieve(query_terms, k=15)
    click.echo(f"✓ Retrieved {len(snippets)} snippets\n")

    # Generate candidates
    click.echo(f"Generating {n_candidates} candidates...")
    candidates = draft_candidates(snippets, n=n_candidates)
    click.echo(f"✓ Generated {len(candidates)} candidates\n")

    # Filter
    click.echo("Filtering candidates...")
    keepers, rejections = filter_candidates(candidates, verbose=True)
    click.echo(f"✓ {len(keepers)} passed filters, {len(rejections)} rejected\n")

    if not keepers:
        click.echo("⚠️  No candidates passed filters. Try generating more.")
        return

    # Rank
    click.echo("Ranking candidates...")
    if MODEL_PATH.exists():
        ranker = PreferenceRanker.load(MODEL_PATH)
        click.echo("✓ Loaded trained ranker")
    else:
        ranker = PreferenceRanker()
        ranker._train_dummy()
        click.echo("⚠️  No trained model, using dummy ranker")

    top_candidates = ranker.rank(keepers, top_k=top_k)
    click.echo(f"✓ Ranked top {len(top_candidates)} candidates\n")

    # Save results
    today = datetime.now().strftime("%Y-%m-%d")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_output_path = OUT_DIR / f"{today}_top.jsonl"
    save_jsonl(all_output_path, keepers)
    click.echo(f"📁 All keepers → {all_output_path}")

    top_output_path = OUT_DIR / f"{today}_top3.jsonl"
    save_jsonl(top_output_path, top_candidates)
    click.echo(f"📁 Top {top_k} → {top_output_path}")

    # Generate images
    click.echo("\nGenerating images...")
    for i, cand in enumerate(top_candidates, start=1):
        img_path = OUT_DIR / f"{today}_top{i}.png"
        _generate_image(cand, img_path)
        click.echo(f"🖼️  {img_path.name}")

    # Print top candidates
    click.echo("\n" + "=" * 60)
    click.echo("TOP CANDIDATES")
    click.echo("=" * 60)
    for i, cand in enumerate(top_candidates, start=1):
        click.echo(f"\n#{i} [{cand.visual_template}] (score: {cand.score:.3f})")
        click.echo(f"  {cand.caption}")
        click.echo(f"  tone: {cand.tone}")

    click.echo("\n✓ Generation complete!")


@cli.command()
@click.option("--decay-days", default=30, help="Time decay for training samples")
def retrain(decay_days):
    """Retrain preference model on pairwise labels"""
    pairs_path = DATA_DIR / "pairwise_labels.jsonl"

    if not pairs_path.exists():
        click.echo("⚠️  No pairwise labels found at data/pairwise_labels.jsonl")
        return

    click.echo("Training preference model...")

    ranker = PreferenceRanker(time_decay_days=decay_days)
    metrics = ranker.train(pairs_path)

    ranker.save(MODEL_PATH)

    click.echo(f"\n✓ Model trained on {metrics['n_pairs']} pairs")
    click.echo(f"  Accuracy: {metrics['accuracy']:.2%}")
    click.echo(f"  Saved → {MODEL_PATH}")


@cli.command()
@click.option("--input-file", "-i", help="JSONL file of candidates to evaluate")
def eval(input_file):
    """Run evaluation and print metrics"""
    if input_file:
        candidates_path = Path(input_file)
    else:
        # Find most recent output
        candidates_path = sorted(OUT_DIR.glob("*_top.jsonl"))[-1] if OUT_DIR.exists() else None

    if not candidates_path or not candidates_path.exists():
        click.echo("⚠️  No candidates found. Run 'generate' first or specify --input-file")
        return

    click.echo(f"Loading candidates from {candidates_path}...")

    from .io_schemas import load_jsonl, MemeCandidate
    candidates = load_jsonl(candidates_path, MemeCandidate)

    click.echo(f"✓ Loaded {len(candidates)} candidates\n")

    metrics = eval_module.evaluate_generation(candidates, DATA_DIR)
    eval_module.print_metrics_table(metrics)

    # Save metrics
    metrics_path = OUT_DIR / f"metrics_{datetime.now().strftime('%Y-%m-%d')}.json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    click.echo(f"📁 Metrics saved → {metrics_path}")


# ============================================================================
# Image Generation Helper
# ============================================================================

def _generate_image(candidate, output_path: Path):
    """
    Generate simple PNG with caption text.

    For tweet_screenshot template only (others would need different layouts).
    """
    # Create blank tweet-style image
    width, height = 600, 400
    bg_color = (255, 255, 255)
    text_color = (20, 23, 26)

    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Try to use a nice font, fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        font = ImageFont.load_default()

    # Word wrap caption
    caption = candidate.caption
    words = caption.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] < width - 80:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    # Draw text
    y_offset = (height - len(lines) * 35) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        draw.text((x, y_offset), line, fill=text_color, font=font)
        y_offset += 35

    # Draw template label
    try:
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        label_font = ImageFont.load_default()

    draw.text((10, height - 30), f"[{candidate.visual_template}]", fill=(128, 128, 128), font=label_font)

    img.save(output_path)


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    cli()

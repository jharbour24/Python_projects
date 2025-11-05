# Queer Brooklyn Memegen Pipeline

A daily-runnable system that generates culturally current meme concepts for queer Brooklyn nightlife (ages ~20–40), then ranks them with a taste model trained on pairwise preferences.

## Features

- **RAG-based generation**: Retrieves recent local NYC snippets to ground memes in current culture
- **Constrained output**: Strict format (≤14 words, valid templates, proper tone)
- **Constitutional filters**: Safety checks for slurs, doxxing, profanity, and community guidelines
- **Preference ranking**: Logistic model trained on pairwise labels (DPO-ready)
- **Evaluation harness**: Weekly re-tuning with diversity and violation metrics
- **Simple PNG export**: Auto-generates tweet screenshots with captions

## Quick Start

```bash
# Install dependencies
make setup

# Add local snippets (manual or from permitted sources)
# Create data/sources/YYYY-MM-DD.jsonl with LocalSnippet records

# Index snippets
make refresh

# Generate memes
make generate

# View results in out/YYYY-MM-DD_top3.jsonl and *.png files
```

## Daily Workflow

1. **Drop sources**: Add new `data/sources/YYYY-MM-DD.jsonl` with current Brooklyn/NYC snippets
2. **Refresh index**: `make refresh` to rebuild RAG index
3. **Generate**: `make generate` to create candidates
4. **Pick one**: Review `out/YYYY-MM-DD_top3.jsonl` and pick best for posting
5. **(Optional)** Add pairwise labels for training: append to `data/pairwise_labels.jsonl`
6. **Weekly retrain**: `make retrain` to update preference model

## Project Structure

```
memegen/
├── data/
│   ├── sources/           # Drop dated JSONL files here
│   ├── seed_examples.jsonl
│   ├── pairwise_labels.jsonl
│   ├── rag_index.pkl      # Auto-generated
│   └── ranker_model.pkl   # Auto-generated
├── memes/
│   └── templates/         # PNG/SVG base images
├── src/
│   ├── io_schemas.py      # Pydantic models
│   ├── rag.py             # Retrieval (TF-IDF or sentence-transformers)
│   ├── generator.py       # Constrained meme generation
│   ├── constitution.py    # Content rules
│   ├── filter.py          # Safety filters
│   ├── ranker.py          # Preference model
│   ├── eval.py            # Metrics and reporting
│   └── cli.py             # Command-line interface
├── tests/
├── out/                   # Generated memes and metrics
├── Makefile
├── README.md
├── STYLE_GUIDE.md
├── CONSTITUTION.md
└── requirements.txt
```

## Commands

### CLI Commands

```bash
# Index local snippets
python -m src.cli ingest [--backend tfidf|sbert]

# Generate memes
python -m src.cli generate [-n 12] [-k 3] [-q "extra query terms"]

# Retrain preference model
python -m src.cli retrain [--decay-days 30]

# Run evaluation
python -m src.cli eval [-i path/to/candidates.jsonl]
```

### Makefile Targets

```bash
make setup      # Install dependencies
make refresh    # Re-index sources
make generate   # Run full pipeline
make retrain    # Retrain preference model
make eval       # Print weekly metrics
make test       # Run pytest
```

## Data Schemas

### LocalSnippet (data/sources/*.jsonl)

```json
{
  "id": "src_2025-11-05_001",
  "date": "2025-11-05",
  "source": "manual|newsletter|rss|notes",
  "text": "L train delays causing 30-minute waits in Williamsburg",
  "tags": ["transit", "L train", "williamsburg"]
}
```

### PairwiseLabel (data/pairwise_labels.jsonl)

```json
{
  "pair_id": "p_0001",
  "a": {"text": "caption A", "meta": {"template": "drake", "tone": "dry"}},
  "b": {"text": "caption B", "meta": {"template": "tweet_screenshot", "tone": "coy"}},
  "winner": "a",
  "panel": "seed_panel_v1",
  "timestamp": "2025-11-05T12:00:00Z"
}
```

### MemeCandidate (output)

```json
{
  "visual_template": "drake|distracted_boyfriend|tweet_screenshot|two_panel|top_text_bottom_text",
  "local_hook": "L train at 2 AM on Saturday",
  "tone": "dry|slightly unhinged|coy",
  "caption": "≤ 14 words",
  "rationale": "why this hits now",
  "evidence_refs": ["src_2025-11-05_001"],
  "score": 0.85
}
```

## Constitutional Rules

See [CONSTITUTION.md](CONSTITUTION.md) for full details.

**Hard blocks:**
1. No slurs or hate speech
2. No explicit sexual content
3. No doxxing or private info
4. No violence or threats
5. Profanity ≤ PG-13
6. Must have local Brooklyn/NYC reference
7. ALL CAPS only for "slightly unhinged" tone
8. No hashtags

**Soft warnings:**
9. No venue doxxing
10. Punch up (systems), not down (people)

## Style Guide

See [STYLE_GUIDE.md](STYLE_GUIDE.md) for examples.

**Key principles:**
- **Punch up**: Target MTA, cover charges, rent—not individuals
- **Local specificity**: Must reference Brooklyn, transit, or venue culture
- **Affectionate**: In-group jokes that feel like shared laughs
- **Tone options**: Dry (deadpan), slightly unhinged (chaotic), coy (playful)

## Testing

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_rag.py -v

# Run with coverage
pytest --cov=src tests/
```

## Training the Ranker

The preference model is trained on pairwise labels. To collect labels:

1. **IG Story polls**: Post two candidates, track which gets more engagement
2. **Close Friends A/B**: Show different candidates to close friends groups
3. **Manual labels**: Record your own preferences in `data/pairwise_labels.jsonl`

Then retrain weekly:

```bash
make retrain
```

## Evaluation Metrics

- **Diversity**: Template/tone entropy, topic diversity
- **Share score proxies**: Brevity, personal pronouns, local specificity
- **Violation rate**: % of candidates blocked by filters

Run evaluation:

```bash
make eval
```

## Extending the System

### Swap TF-IDF for Sentence-Transformers

```bash
pip install sentence-transformers
python -m src.cli ingest --backend sbert
```

### Add Time Decay to Ranker

Already implemented! Recent pairwise labels get higher weight (default 30-day decay).

### Connect to LLM API

Edit `src/generator.py` and implement `_draft_with_llm()` to call OpenAI/Anthropic/etc.

### Add Annotation UI

Build a simple web UI for pairwise comparisons:
- Load two candidates
- Click to pick winner
- Append to `data/pairwise_labels.jsonl`

## Legal & Ethics

- **No scraping**: Assume user provides snippets manually or via permitted APIs
- **No faces**: Only text-based memes
- **Borough-level only**: No street addresses or geolocation
- **Venue allowlist**: Only reference venues that publicly promote events
- **No targeting individuals**: Punch up at systems, not down at people

## Automation (Optional)

Add to crontab for weekly automation:

```bash
# Every Sunday at 2 AM: refresh, retrain, eval
0 2 * * 0 cd /path/to/memegen && make refresh && make retrain && make eval
```

## Troubleshooting

### "No snippets found"
- Check that `data/sources/*.jsonl` files exist
- Verify JSONL format is valid (one object per line)
- Run `python -m src.cli ingest` to rebuild index

### "No trained model"
- Run `make retrain` to train a model
- If no pairwise labels, a dummy model will be used
- Add labels to `data/pairwise_labels.jsonl`

### Tests failing
- Ensure dependencies installed: `make setup`
- Check Python version: requires Python 3.11+
- Run `pytest -v` for detailed error messages

## Contributing

1. Fork the repo
2. Create a feature branch
3. Add tests for new features
4. Ensure `make test` passes
5. Update documentation
6. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built for the queer Brooklyn nightlife community. With love and chaos.

---

**Version:** 0.1.0
**Last Updated:** 2025-11-05

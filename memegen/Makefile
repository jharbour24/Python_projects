.PHONY: setup refresh generate retrain eval test clean help

# Default target
help:
	@echo "Queer Brooklyn Memegen Pipeline"
	@echo ""
	@echo "Available targets:"
	@echo "  make setup      - Install dependencies"
	@echo "  make refresh    - Re-index local snippets"
	@echo "  make generate   - Run full pipeline (RAG -> generate -> filter -> rank)"
	@echo "  make retrain    - Retrain preference model"
	@echo "  make eval       - Run evaluation and print metrics"
	@echo "  make test       - Run test suite"
	@echo "  make clean      - Remove generated files"
	@echo ""
	@echo "Daily workflow:"
	@echo "  1. Add data/sources/YYYY-MM-DD.jsonl"
	@echo "  2. make refresh"
	@echo "  3. make generate"
	@echo "  4. Check out/*.png and out/*_top3.jsonl"

# Install dependencies
setup:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "✓ Setup complete"

# Re-index local snippets
refresh:
	@echo "Re-indexing local snippets..."
	python -m src.cli ingest
	@echo "✓ Index refreshed"

# Run full generation pipeline
generate:
	@echo "Running meme generation pipeline..."
	python -m src.cli generate -n 12 -k 3
	@echo "✓ Generation complete"

# Retrain preference model
retrain:
	@echo "Retraining preference model..."
	python -m src.cli retrain
	@echo "✓ Model retrained"

# Run evaluation
eval:
	@echo "Running evaluation..."
	python -m src.cli eval
	@echo "✓ Evaluation complete"

# Run tests
test:
	@echo "Running test suite..."
	pytest tests/ -v
	@echo "✓ All tests passed"

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	rm -rf out/*.jsonl out/*.png out/*.json
	rm -rf data/rag_index.pkl data/ranker_model.pkl
	rm -rf __pycache__ src/__pycache__ tests/__pycache__
	rm -rf .pytest_cache
	rm -rf *.egg-info
	@echo "✓ Cleaned"

# Full pipeline (setup -> refresh -> generate)
all: setup refresh generate
	@echo "✓ Full pipeline complete"

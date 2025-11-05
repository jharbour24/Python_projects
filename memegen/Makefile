.PHONY: setup refresh generate retrain eval test clean help

help:
	@echo "Meme Generation Pipeline"
	@echo ""
	@echo "Commands:"
	@echo "  make setup      - Install dependencies"
	@echo "  make refresh    - Re-index source snippets"
	@echo "  make generate   - Run full generation pipeline"
	@echo "  make retrain    - Retrain preference model"
	@echo "  make eval       - Print evaluation metrics"
	@echo "  make test       - Run test suite"
	@echo "  make clean      - Remove generated files"

setup:
	pip install -r requirements.txt

refresh:
	python -m src.cli ingest --sources-dir data/sources --cache data/rag_cache.pkl

generate:
	python -m src.cli generate --n 12 --top-k 3 --out-dir out

retrain:
	python -m src.cli retrain --pairs data/pairwise_labels.jsonl --output data/ranker_model.pkl

eval:
	python -m src.cli eval

test:
	pytest tests/ -v

clean:
	rm -rf out/*.jsonl out/*.png
	rm -f data/rag_cache.pkl data/ranker_model.pkl
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

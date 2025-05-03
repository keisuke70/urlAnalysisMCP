# Makefile for Company Analyzer Script

.PHONY: help install update-deps lint test analyze clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies from requirements.txt"
	@echo "  make update-deps   - Update dependencies to latest compatible versions"
	@echo "  make lint          - Run linting tools (flake8, mypy)"
	@echo "  make test          - Run tests using pytest"
	@echo "  make analyze       - Run the analysis script (requires INPUT and OUTPUT args)"
	@echo "                     Example: make analyze INPUT=input.csv OUTPUT=results.csv"
	@echo "  make clean         - Clean up temporary files"

# Install dependencies
install:
	pip install -r mcp_server/requirements.txt

# Update dependencies
update-deps:
	pip install --upgrade -r mcp_server/requirements.txt

# Run linting (include the new script, adjust paths if needed)
lint:
	python -m flake8 mcp_server company_analyzer.py
	python -m mypy mcp_server company_analyzer.py

# Run tests (point to the updated test file)
test:
	python test_japanese_prompts.py

# Run the analysis script
# Expects INPUT and OUTPUT variables to be passed, e.g., make analyze INPUT=companies.csv OUTPUT=analysis.csv
analyze:
ifndef INPUT
	$(error INPUT variable is not set. Example: make analyze INPUT=input.csv)
endif
ifndef OUTPUT
	$(error OUTPUT variable is not set. Example: make analyze OUTPUT=output.csv)
endif
	python company_analyzer.py --input $(INPUT) --output $(OUTPUT)

# Clean up temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage*" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage*" -delete
	find . -type f -name "coverage.xml" -delete
	find . -type f -name "*.log" -delete
	find . -type f -name "*.csv" -delete # Remove generated CSVs during clean
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

# Makefile for URL Analysis MCP Server

.PHONY: update-deps lint test run clean

# Update dependencies
update-deps:
	pip install --upgrade -r mcp_server/requirements.txt

# Run linting
lint:
	python -m flake8 mcp_server
	python -m mypy mcp_server

# Run tests
test:
	python -m pytest mcp_server/tests

# Run the application
run:
	python -m mcp_server.server

# Clean up temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type f -name "coverage.xml" -delete
	find . -type f -name "*.log" -delete

# Help command
help:
	@echo "Available commands:"
	@echo "  make update-deps  - Update dependencies"
	@echo "  make lint         - Run linting tools"
	@echo "  make test         - Run tests"
	@echo "  make run          - Run the application"
	@echo "  make clean        - Clean up temporary files"

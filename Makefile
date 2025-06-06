.PHONY: help install test lint format coverage clean docker-build docker-test docker-run docker-test-image env-create env-activate

# Default target
help:
	@echo "Available targets:"
	@echo "  env-create      - Create conda environment"
	@echo "  env-activate    - Show command to activate environment"
	@echo "  install         - Install the package with development dependencies"
	@echo "  test            - Run tests with pytest"
	@echo "  lint            - Run ruff linter and check formatting"
	@echo "  format          - Format code with ruff"
	@echo "  coverage        - Run tests with coverage report"
	@echo "  clean           - Remove build artifacts and cache files"
	@echo "  docker-build    - Build production Docker image"
	@echo "  docker-test     - Run tests in Docker container"
	@echo "  docker-run      - Run the Docker container"
	@echo "  docker-test-image - Test the built Docker image"

# Create conda environment
env-create:
	@echo "Creating conda environment..."
	conda create -n integran python=3.12 -y
	@echo "Environment created. Activate with: conda activate integran"

# Show activation command
env-activate:
	@echo "To activate the environment, run:"
	@echo "conda activate integran"

# Install dependencies with uv
install:
	@echo "Installing dependencies with uv..."
	@if ! command -v uv &> /dev/null; then \
		echo "Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi
	uv pip install -e ".[dev]"
	@echo "Installation complete!"

# Run tests
test:
	@echo "Running tests..."
	pytest -v --tb=short

# Run linter and check formatting
lint:
	@echo "Running ruff linter..."
	ruff check src/ tests/
	@echo "Checking formatting..."
	ruff format --check src/ tests/

# Format code
format:
	@echo "Formatting code with ruff..."
	ruff format src/ tests/
	@echo "Fixing linting issues..."
	ruff check --fix src/ tests/

# Run tests with coverage
coverage:
	@echo "Running tests with coverage..."
	pytest --cov=src --cov-report=term-missing --cov-report=html

# Type checking
typecheck:
	@echo "Running type checking..."
	mypy src/

# Run all checks (lint, format, typecheck, test)
check-all: lint typecheck test
	@echo "All checks passed!"

# Clean up build artifacts
clean:
	@echo "Cleaning up build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf data/*.db
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete!"

# Build production Docker image
docker-build:
	@echo "Building production Docker image..."
	docker build -t integran:latest .
	@echo "Image built successfully: integran:latest"

# Run tests in Docker container (for CI)
docker-test:
	@echo "Running tests in Docker container..."
	docker run --rm -v "$(PWD)":/app -w /app python:3.12-slim sh -c "\
		apt-get update && apt-get install -y curl && \
		echo 'Setting up test environment...' && \
		if [ -f .env.test ]; then cp .env.test .env; fi && \
		echo 'Installing uv...' && \
		curl -LsSf https://astral.sh/uv/install.sh | sh && \
		export PATH=\"/root/.local/bin:\$$PATH\" && \
		echo 'Installing dependencies...' && \
		uv pip install --system -e '.[dev]' && \
		echo 'Running linter...' && \
		ruff check src/ tests/ && \
		echo 'Running tests...' && \
		pytest -v --tb=short && \
		echo 'All tests passed!' \
	"

# Run the Docker container
docker-run:
	@echo "Running Integran in Docker..."
	docker run -it --rm -v "$(PWD)/data":/app/data integran:latest

# Test the built Docker image
docker-test-image:
	@echo "Testing the built Docker image..."
	docker run --rm integran:latest integran --help
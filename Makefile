.PHONY: build
build:
	@echo "Build Docker image..."
	docker compose build

.PHONY: run
run:
	@echo "Running container..."
	docker compose up

.PHONY: shell
shell:
	@echo "Opening Python shell in Poetry environment..."
	docker compose run --rm bot poetry run python

.PHONY: test
test:
	@echo "Running tests in Docker container..."
	docker compose run --rm bot poetry run pytest

.PHONY: test-cov
test-cov:
	@echo "Running tests with coverage in Docker container..."
	docker compose run --rm bot poetry run pytest --cov=. --cov-report=term

.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make build          - Build the Docker image"
	@echo "  make run            - Run the container"
	@echo "  make shell          - Run a python shell in the container"
	@echo "  make test           - Run the test suite"
	@echo "  make test-cov       - Run the test suite with coverage report"

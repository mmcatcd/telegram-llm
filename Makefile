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

.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make build    - Build the Docker image"
	@echo "  make run      - Run the container"
	@echo "  make shell    - Run a python shell in the container"

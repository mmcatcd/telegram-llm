# Telegram LLM Project Guide

## Commands
- Install dependencies: `poetry install`
- Run service: `poetry run service-run`
- Build Docker: `make build`
- Run container: `make run`
- Run all tests: `make test` or `poetry run pytest`
- Run specific test: `poetry run pytest tests/test_filename.py::TestClass::test_function`
- Test with coverage: `make test-cov` or `poetry run pytest --cov=. --cov-report=term`
- Python shell: `make shell`

## Code Style
- **Imports**: Standard library → Third-party → Local modules
- **Type hints**: Required for function parameters and return values
- **Async**: Use async/await for Telegram handlers
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Error handling**: Use try/except with `logfire` for logging
- **Testing**: pytest with pytest-asyncio for async tests
- **Documentation**: Docstrings for classes and test functions
- **Module organization**: Keep related functionality in appropriate modules

## Architecture
- `app.py`: Main entry point
- `config.py`: Configuration settings
- `handlers.py`: Telegram command handlers
- `telegram_utils.py`: Telegram API utilities
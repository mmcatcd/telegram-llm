# Unit Tests for Telegram LLM Bot

This directory contains unit tests for the Telegram LLM Bot application.

## Test Structure

- `test_telegram_utils.py`: Tests for utility functions in `telegram_utils.py`
- `test_handlers.py`: Tests for command and message handlers in `handlers.py`
- `test_app.py`: Tests for the main application in `app.py`
- `test_config.py`: Tests for configuration settings in `config.py`
- `conftest.py`: Common fixtures for tests

## Running Tests

To run all tests:

```bash
# Using make (from project root)
make test

# Using pytest directly
pytest
```

To run tests with coverage:

```bash
# Using make (from project root)
make test-cov

# Using pytest directly
pytest --cov=.
```

To run tests in Docker:

```bash
# Using make (from project root)
make docker-test
make docker-test-cov
```

To run a specific test file:

```bash
pytest tests/test_telegram_utils.py
```

## Test Dependencies

The tests require the following packages:
- pytest
- pytest-asyncio
- pytest-cov
- unittest.mock (part of the Python standard library)

You can install them with:

```bash
# Using poetry
poetry install --with dev

# Using pip
pip install pytest pytest-asyncio pytest-cov
```

## Notes

- The tests use mocking extensively to avoid making actual API calls or database operations.
- Async functions are tested using the `pytest-asyncio` plugin.
- The `@restricted` decorator is mocked to allow testing protected functions without authentication. 
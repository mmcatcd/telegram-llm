# telegram-llm

A Telegram bot that integrates with various LLM models to provide AI-powered chat capabilities.

## Features

- Supports multiple LLM models (Claude, Gemini, etc.)
- Custom system prompts
- Message history tracking
- Support for text, photo, and audio attachments
- User authentication via admin list

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/telegram-llm.git
cd telegram-llm
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Set up environment variables in a `.env` file:
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ADMINS=["your_telegram_user_id"]
LOGFIRE_API_KEY=your_logfire_api_key
FIRECRAWL_API_KEY=your_firecrawl_api_key
BRAVE_SEARCH_API_KEY=your_brave_search_api_key
```

## Usage

Run the bot:
```bash
poetry run service-run
```

Or using Docker:
```bash
docker-compose up -d
```

## Commands

- `/help` - Show available commands
- `/model` - Show current model
- `/set_model <model_id>` - Set the model to use
- `/models` - List available models
- `/system_prompt` - Show current system prompt
- `/set_system_prompt <prompt>` - Set system prompt
- `/attachment_types` - Show supported attachment types
- `/_user_id` - Get your user ID
- `/_chat_id` - Get the current chat ID (admin only)
- `/private` - Process a message privately (admin only)

## Special Syntax

- `@think` - Make the model show its thinking and reasoning process before answering
- `@web your search query` - Search the web for information related to your query
- `@https://example.com` or `@example.com/page` - Scrape a webpage and include its content in the LLM context

## Testing

The project includes a comprehensive test suite. To run the tests:

```bash
# Run tests using make
make test

# Run tests with coverage
make test-cov
```

Alternatively, you can run tests directly with pytest:

```bash
poetry run pytest
poetry run pytest --cov=.
```

See the [tests/README.md](tests/README.md) file for more details on testing.

## Development

This project uses Poetry for dependency management and pytest for testing.

To add a new dependency:
```bash
poetry add package-name
```

To add a development dependency:
```bash
poetry add --group dev package-name
```

import json
import os

from dotenv import load_dotenv

# Load the environment variables from the .env file.
load_dotenv()

list_of_admins = json.loads(os.getenv("ADMINS", "[]"))
telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
logfire_api_key = os.getenv("LOGFIRE_API_KEY")
firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
brave_search_api_key = os.getenv("BRAVE_SEARCH_API_KEY")

default_model_id = "anthropic/claude-3-7-sonnet-latest"

import unittest
from unittest.mock import patch

import config


class TestConfig(unittest.TestCase):
    """Tests for the configuration module."""

    @patch("config.os")
    @patch("config.load_dotenv")
    def test_load_dotenv_called(self, mock_load_dotenv, mock_os):
        """Test that load_dotenv is called during module import."""
        # Re-import the module to trigger the load_dotenv call
        import importlib

        importlib.reload(config)

        # Assert load_dotenv was called
        mock_load_dotenv.assert_called_once()

    @patch("config.os")
    @patch("config.json.loads")
    def test_list_of_admins_from_env(self, mock_json_loads, mock_os):
        """Test that list_of_admins is loaded from environment variable."""
        # Setup mock environment
        mock_os.getenv.return_value = '["123", "456"]'
        mock_json_loads.return_value = ["123", "456"]

        # Re-import the module to use the mocked environment
        import importlib

        importlib.reload(config)

        # Assert getenv was called with the correct key
        mock_os.getenv.assert_any_call("ADMINS", "[]")

        # Assert json.loads was called with the env value
        mock_json_loads.assert_called_once_with('["123", "456"]')

        # Assert list_of_admins has the expected value
        self.assertEqual(config.list_of_admins, ["123", "456"])

    @patch("config.os")
    def test_telegram_bot_token_from_env(self, mock_os):
        """Test that telegram_bot_token is loaded from environment variable."""
        # Setup mock environment
        mock_os.getenv.return_value = "test_bot_token"

        # Re-import the module to use the mocked environment
        import importlib

        importlib.reload(config)

        # Assert getenv was called with the correct key
        mock_os.getenv.assert_any_call("TELEGRAM_BOT_TOKEN")

        # Assert telegram_bot_token has the expected value
        self.assertEqual(config.telegram_bot_token, "test_bot_token")

    @patch("config.os")
    def test_logfire_api_key_from_env(self, mock_os):
        """Test that logfire_api_key is loaded from environment variable."""
        # Setup mock environment
        mock_os.getenv.return_value = "test_logfire_key"

        # Re-import the module to use the mocked environment
        import importlib

        importlib.reload(config)

        # Assert getenv was called with the correct key
        mock_os.getenv.assert_any_call("LOGFIRE_API_KEY")

        # Assert logfire_api_key has the expected value
        self.assertEqual(config.logfire_api_key, "test_logfire_key")

    def test_default_model_id(self):
        """Test that default_model_id has the expected value."""
        self.assertEqual(config.default_model_id, "anthropic/claude-3-7-sonnet-latest")


if __name__ == "__main__":
    unittest.main()

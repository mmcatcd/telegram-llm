import unittest
from unittest.mock import MagicMock, patch

import app


class TestApp(unittest.TestCase):
    """Tests for the main application module."""

    @patch("app.ApplicationBuilder")
    @patch("app.CommandHandler")
    @patch("app.MessageHandler")
    @patch("app.filters")
    @patch("app.BOT_TOKEN", "test_token")
    def test_main_initializes_app(
        self, mock_filters, mock_message_handler, mock_command_handler, mock_app_builder
    ):
        """Test that the main function initializes the application correctly."""
        # Setup mock application
        mock_app = MagicMock()
        mock_app_builder.return_value.token.return_value.build.return_value = mock_app

        # Call the main function
        app.main()

        # Assert ApplicationBuilder was called with the correct token
        mock_app_builder.return_value.token.assert_called_once_with("test_token")
        mock_app_builder.return_value.token.return_value.build.assert_called_once()

        # Assert that all command handlers were added
        self.assertEqual(
            mock_app.add_handler.call_count, 11
        )  # 10 commands + 1 message handler

        # Verify specific handlers were added
        mock_command_handler.assert_any_call("_user_id", app.user_id)
        mock_command_handler.assert_any_call("_chat_id", app.chat_id)
        mock_command_handler.assert_any_call("private", app.process_private_message)
        mock_command_handler.assert_any_call("system_prompt", app.system_prompt)
        mock_command_handler.assert_any_call("set_system_prompt", app.set_system_prompt)
        mock_command_handler.assert_any_call("models", app.list_models)
        mock_command_handler.assert_any_call("model", app.model)
        mock_command_handler.assert_any_call("set_model", app.set_model)
        mock_command_handler.assert_any_call("attachment_types", app.attachment_types)
        mock_command_handler.assert_any_call("help", app.help)

        # Verify message handler was added with correct filters
        mock_message_handler.assert_called_once()

        # Instead of checking the string representation, verify the filter construction
        mock_filters.TEXT.__or__.assert_called_once()
        mock_filters.TEXT.__or__.return_value.__or__.assert_called_once()
        mock_filters.TEXT.__or__.return_value.__or__.return_value.__and__.assert_called_once()

        # Verify app.run_polling was called
        mock_app.run_polling.assert_called_once()


if __name__ == "__main__":
    unittest.main()

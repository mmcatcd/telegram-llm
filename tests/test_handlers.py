import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from handlers import (
    _get_user_conversation_id,
    _get_user_conversations_table,
    _set_user_conversation_id,
    attachment_types,
    chat_id,
    help,
    list_models,
    model,
    set_model,
    set_system_prompt,
    system_prompt,
    user_id,
)


class TestUserCommands(unittest.TestCase):
    """Tests for user-related command handlers."""

    @pytest.mark.asyncio
    async def test_user_id(self):
        """Test the user_id command handler."""
        # Create mock update and context
        mock_update = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()

        # Call the handler
        await user_id(mock_update, mock_context)

        # Assert reply_text was called with the correct message
        mock_update.message.reply_text.assert_called_once_with(
            "Your user id is: 123456"
        )

    @pytest.mark.asyncio
    @patch("handlers.restricted")
    async def test_chat_id(self, mock_restricted):
        """Test the chat_id command handler."""
        # Setup the mock decorator to call the function directly
        mock_restricted.side_effect = lambda f: f

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.effective_chat.id = 789012
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()

        # Call the handler
        await chat_id(mock_update, mock_context)

        # Assert reply_text was called with the correct message
        mock_update.message.reply_text.assert_called_once_with(
            "Your chat id is: 789012"
        )


class TestModelCommands(unittest.TestCase):
    """Tests for model-related command handlers."""

    @pytest.mark.asyncio
    @patch("handlers.restricted")
    async def test_model_with_default(self, mock_restricted):
        """Test the model command handler with default model."""
        # Setup the mock decorator to call the function directly
        mock_restricted.side_effect = lambda f: f

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        mock_context.user_data = {}  # No model_id set

        # Call the handler
        with patch("handlers.default_model_id", "default-model"):
            await model(mock_update, mock_context)

        # Assert reply_text was called with the correct message
        mock_update.message.reply_text.assert_called_once_with(
            "Your current model id is: `default-model`",
            parse_mode="MARKDOWN",
        )

    @pytest.mark.asyncio
    @patch("handlers.restricted")
    async def test_model_with_custom(self, mock_restricted):
        """Test the model command handler with custom model."""
        # Setup the mock decorator to call the function directly
        mock_restricted.side_effect = lambda f: f

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        mock_context.user_data = {"model_id": "custom-model"}

        # Call the handler
        await model(mock_update, mock_context)

        # Assert reply_text was called with the correct message
        mock_update.message.reply_text.assert_called_once_with(
            "Your current model id is: `custom-model`",
            parse_mode="MARKDOWN",
        )

    @pytest.mark.asyncio
    @patch("handlers.restricted")
    async def test_set_model_no_args(self, mock_restricted):
        """Test the set_model command handler with no arguments."""
        # Setup the mock decorator to call the function directly
        mock_restricted.side_effect = lambda f: f

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        mock_context.args = []

        # Call the handler
        await set_model(mock_update, mock_context)

        # Assert reply_text was called with the correct message
        mock_update.message.reply_text.assert_called_once_with(
            "You must provide a valid model id like: `/set_model gpt-4o`",
            parse_mode="MARKDOWN",
        )

    @pytest.mark.asyncio
    @patch("handlers.restricted")
    @patch("handlers.model_ids", ["valid-model", "another-model"])
    async def test_set_model_valid(self, mock_restricted):
        """Test the set_model command handler with a valid model."""
        # Setup the mock decorator to call the function directly
        mock_restricted.side_effect = lambda f: f

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        mock_context.args = ["valid-model"]
        mock_context.user_data = {}

        # Call the handler
        await set_model(mock_update, mock_context)

        # Assert reply_text was called with the correct message
        mock_update.message.reply_text.assert_called_once_with(
            "Model set to: `valid-model`",
            parse_mode="MARKDOWN",
        )
        # Assert model_id was set in user_data
        self.assertEqual(mock_context.user_data["model_id"], "valid-model")

    @pytest.mark.asyncio
    @patch("handlers.restricted")
    @patch("handlers.model_ids", ["valid-model", "another-model"])
    async def test_set_model_invalid(self, mock_restricted):
        """Test the set_model command handler with an invalid model."""
        # Setup the mock decorator to call the function directly
        mock_restricted.side_effect = lambda f: f

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        mock_context.args = ["invalid-model"]

        # Call the handler
        await set_model(mock_update, mock_context)

        # Assert reply_text was called with the correct message
        mock_update.message.reply_text.assert_called_once_with(
            "Invalid model id. Available models: `valid-model`, `another-model`",
            parse_mode="MARKDOWN",
        )


class TestSystemPromptCommands(unittest.TestCase):
    """Tests for system prompt-related command handlers."""

    @pytest.mark.asyncio
    @patch("handlers.restricted")
    async def test_system_prompt_not_set(self, mock_restricted):
        """Test the system_prompt command handler when no prompt is set."""
        # Setup the mock decorator to call the function directly
        mock_restricted.side_effect = lambda f: f

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        mock_context.user_data = {}  # No system_prompt set

        # Call the handler
        await system_prompt(mock_update, mock_context)

        # Assert reply_text was called with the correct message
        mock_update.message.reply_text.assert_called_once_with(
            "You don't have a system prompt set.",
            parse_mode="MARKDOWN",
        )

    @pytest.mark.asyncio
    @patch("handlers.restricted")
    async def test_system_prompt_set(self, mock_restricted):
        """Test the system_prompt command handler when a prompt is set."""
        # Setup the mock decorator to call the function directly
        mock_restricted.side_effect = lambda f: f

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        mock_context.user_data = {"system_prompt": "You are a helpful assistant."}

        # Call the handler
        await system_prompt(mock_update, mock_context)

        # Assert reply_text was called with the correct message
        mock_update.message.reply_text.assert_called_once_with(
            "Your current system prompt is:\n\n`You are a helpful assistant.`",
            parse_mode="MARKDOWN",
        )

    @pytest.mark.asyncio
    @patch("handlers.restricted")
    async def test_set_system_prompt_no_args(self, mock_restricted):
        """Test the set_system_prompt command handler with no arguments."""
        # Setup the mock decorator to call the function directly
        mock_restricted.side_effect = lambda f: f

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        mock_context.args = []

        # Call the handler
        await set_system_prompt(mock_update, mock_context)

        # Assert reply_text was called with the correct message
        mock_update.message.reply_text.assert_called_once_with(
            "You must provide a system prompt like: `/set_system_prompt You are a helpful assistant.`",
            parse_mode="MARKDOWN",
        )

    @pytest.mark.asyncio
    @patch("handlers.restricted")
    async def test_set_system_prompt_valid(self, mock_restricted):
        """Test the set_system_prompt command handler with a valid prompt."""
        # Setup the mock decorator to call the function directly
        mock_restricted.side_effect = lambda f: f

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        mock_context.args = ["You", "are", "a", "helpful", "assistant."]
        mock_context.user_data = {}

        # Call the handler
        await set_system_prompt(mock_update, mock_context)

        # Assert reply_text was called with the correct message
        mock_update.message.reply_text.assert_called_once_with(
            "System prompt set to:\n\n`You are a helpful assistant.`",
            parse_mode="MARKDOWN",
        )
        # Assert system_prompt was set in user_data
        self.assertEqual(
            mock_context.user_data["system_prompt"], "You are a helpful assistant."
        )


class TestOtherCommands(unittest.TestCase):
    """Tests for other command handlers."""

    @pytest.mark.asyncio
    @patch("handlers.restricted")
    @patch("handlers.model_ids", ["model1", "model2"])
    async def test_list_models(self, mock_restricted):
        """Test the list_models command handler."""
        # Setup the mock decorator to call the function directly
        mock_restricted.side_effect = lambda f: f

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()

        # Call the handler
        await list_models(mock_update, mock_context)

        # Assert reply_text was called with the correct message
        mock_update.message.reply_text.assert_called_once_with(
            "Available models:\n\n`model1`\n`model2`",
            parse_mode="MARKDOWN",
        )

    @pytest.mark.asyncio
    @patch("handlers.restricted")
    async def test_attachment_types(self, mock_restricted):
        """Test the attachment_types command handler."""
        # Setup the mock decorator to call the function directly
        mock_restricted.side_effect = lambda f: f

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()

        # Call the handler
        await attachment_types(mock_update, mock_context)

        # Assert reply_text was called with a message containing supported types
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        self.assertIn("Supported attachment types", call_args)

    @pytest.mark.asyncio
    async def test_help(self):
        """Test the help command handler."""
        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()

        # Call the handler
        await help(mock_update, mock_context)

        # Assert reply_text was called with a message containing help information
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        self.assertIn("Commands:", call_args)


class TestMessageProcessing(unittest.TestCase):
    """Tests for message processing functions."""

    @patch("handlers.sqlite_utils")
    def test_get_user_conversations_table(self, mock_sqlite_utils):
        """Test the _get_user_conversations_table function."""
        # Create a mock database and table
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.table.return_value = mock_table
        mock_table.exists.return_value = False

        # Call the function
        result = _get_user_conversations_table(mock_db)

        # Assert the correct table was requested
        mock_db.table.assert_called_once_with("user_conversations", pk=("user_id",))
        # Assert the table was created if it didn't exist
        mock_table.create.assert_called_once()
        # Assert the function returned the table
        self.assertEqual(result, mock_table)

    def test_get_user_conversation_id_exists(self):
        """Test the _get_user_conversation_id function when a conversation exists."""
        # Create a mock table with a conversation for the user
        mock_table = MagicMock()
        mock_table.rows_where.return_value = [{"conversation_id": "conv123"}]

        # Call the function
        result = _get_user_conversation_id(mock_table, 123)

        # Assert the correct query was made
        mock_table.rows_where.assert_called_once_with("user_id = ?", [123], limit=1)
        # Assert the correct conversation ID was returned
        self.assertEqual(result, "conv123")

    def test_get_user_conversation_id_not_exists(self):
        """Test the _get_user_conversation_id function when no conversation exists."""
        # Create a mock table with no conversation for the user
        mock_table = MagicMock()
        mock_table.rows_where.return_value = []

        # Call the function
        result = _get_user_conversation_id(mock_table, 123)

        # Assert the correct query was made
        mock_table.rows_where.assert_called_once_with("user_id = ?", [123], limit=1)
        # Assert None was returned
        self.assertIsNone(result)

    @patch("handlers.datetime")
    def test_set_user_conversation_id(self, mock_datetime):
        """Test the _set_user_conversation_id function."""
        # Create a mock table and datetime
        mock_table = MagicMock()
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T12:00:00"

        # Call the function
        _set_user_conversation_id(mock_table, "conv123", 123)

        # Assert the conversation ID was set correctly
        mock_table.upsert.assert_called_once_with(
            {
                "user_id": 123,
                "conversation_id": "conv123",
                "last_used": "2023-01-01T12:00:00",
            },
            pk="user_id",
        )


if __name__ == "__main__":
    unittest.main()

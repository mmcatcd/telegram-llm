import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from telegram_utils import (
    code_block_start_at,
    escape_markdown_v2,
    format_symbol_at,
    has_closing_symbol_in_line,
    inline_code_at,
    inline_code_has_closing_in_line,
    restricted,
    send_long_message,
    special_symbol_at,
)


class TestRestricted(unittest.TestCase):
    """Tests for the restricted decorator function."""

    @pytest.mark.asyncio
    async def test_restricted_allowed_user(self):
        """Test that allowed users can access restricted functions."""
        # Mock function to be decorated
        mock_func = AsyncMock(return_value="function_result")

        # Mock update and context
        mock_update = MagicMock()
        mock_update.effective_user.id = "123"  # This ID is in list_of_admins
        mock_context = MagicMock()

        # Patch list_of_admins to include our test user ID
        with patch("telegram_utils.list_of_admins", ["123"]):
            # Apply decorator to mock function
            decorated_func = restricted(mock_func)

            # Call decorated function
            result = await decorated_func(mock_update, mock_context)

            # Assert function was called and returned expected result
            mock_func.assert_called_once_with(mock_update, mock_context)
            self.assertEqual(result, "function_result")

    @pytest.mark.asyncio
    async def test_restricted_unauthorized_user(self):
        """Test that unauthorized users cannot access restricted functions."""
        # Mock function to be decorated
        mock_func = AsyncMock(return_value="function_result")

        # Mock update and context
        mock_update = MagicMock()
        mock_update.effective_user.id = "456"  # This ID is not in list_of_admins
        mock_context = MagicMock()

        # Patch list_of_admins to exclude our test user ID
        with patch("telegram_utils.list_of_admins", ["123"]):
            # Apply decorator to mock function
            decorated_func = restricted(mock_func)

            # Call decorated function
            result = await decorated_func(mock_update, mock_context)

            # Assert function was not called and returned None
            mock_func.assert_not_called()
            self.assertIsNone(result)


class TestMarkdownEscaping(unittest.TestCase):
    """Tests for Markdown escaping functions."""

    def test_escape_markdown_v2_simple_text(self):
        """Test escaping simple text without special characters."""
        text = "Hello world"
        result = escape_markdown_v2(text, add_closing_code_block=False)
        self.assertEqual(result, "Hello world")

    def test_escape_markdown_v2_special_characters(self):
        """Test escaping text with special characters."""
        text = "Hello! This is a (test) with [brackets] and other symbols: +-=."
        result = escape_markdown_v2(text, add_closing_code_block=False)
        # Special characters should be escaped with backslashes
        self.assertIn("Hello\\!", result)
        self.assertIn("\\(test\\)", result)
        self.assertIn("\\[brackets\\]", result)

    def test_escape_markdown_v2_code_blocks(self):
        """Test escaping text with code blocks."""
        text = "Some text\n```\ncode block\n```"
        result = escape_markdown_v2(text, add_closing_code_block=False)
        # Code blocks should be preserved without escaping their content
        self.assertIn("```\ncode block\n```", result)

    def test_escape_markdown_v2_inline_code(self):
        """Test escaping text with inline code."""
        text = "Some text with `inline code`"
        result = escape_markdown_v2(text, add_closing_code_block=False)
        # Inline code should be preserved without escaping its content
        self.assertIn("`inline code`", result)

    def test_escape_markdown_v2_add_closing_code_block(self):
        """Test adding closing code block when needed."""
        text = "Some text\n```\ncode block"
        result = escape_markdown_v2(text, add_closing_code_block=True)
        # Should add closing code block
        self.assertTrue(result.endswith("\n```"))

    def test_code_block_start_at(self):
        """Test detection of code block start."""
        text = "Some text ```code block```"
        self.assertTrue(code_block_start_at(text, 10))
        self.assertFalse(code_block_start_at(text, 0))

    def test_inline_code_at(self):
        """Test detection of inline code."""
        text = "Some text `inline code`"
        self.assertTrue(inline_code_at(text, 10))
        self.assertFalse(inline_code_at(text, 0))

    def test_special_symbol_at(self):
        """Test detection of special symbols."""
        text = "Hello! This is a (test)"
        self.assertTrue(special_symbol_at(text, 5))  # !
        self.assertTrue(special_symbol_at(text, 16))  # (
        self.assertFalse(special_symbol_at(text, 0))  # H

    def test_format_symbol_at(self):
        """Test detection of format symbols."""
        text = "Some *bold* and _italic_ text"
        self.assertTrue(format_symbol_at(text, 5))  # *
        self.assertTrue(format_symbol_at(text, 16))  # _
        self.assertFalse(format_symbol_at(text, 0))  # S

    def test_inline_code_has_closing_in_line(self):
        """Test detection of closing inline code in the same line."""
        text = "Some `inline code` text"
        self.assertTrue(inline_code_has_closing_in_line(text, 5, "`"))
        text = "Some `inline code without closing"
        self.assertFalse(inline_code_has_closing_in_line(text, 5, "`"))

    def test_has_closing_symbol_in_line(self):
        """Test detection of closing symbol in the same line."""
        text = "Some *bold* text"
        self.assertTrue(has_closing_symbol_in_line(text, 5, "*"))
        text = "Some *bold text without closing"
        self.assertFalse(has_closing_symbol_in_line(text, 5, "*"))


class TestSendLongMessage(unittest.TestCase):
    """Tests for the send_long_message function."""

    @pytest.mark.asyncio
    async def test_send_short_message(self):
        """Test sending a message shorter than the maximum length."""
        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()

        # Call function with short message
        short_text = "This is a short message"
        await send_long_message(mock_update, mock_context, short_text)

        # Assert reply_text was called once with the full message
        mock_update.message.reply_text.assert_called_once_with(
            short_text, parse_mode="MarkdownV2"
        )

    @pytest.mark.asyncio
    async def test_send_long_message(self):
        """Test sending a message longer than the maximum length."""
        # Create mock update and context
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()

        # Create a message longer than MAX_MESSAGE_LENGTH
        from telegram_utils import MAX_MESSAGE_LENGTH

        long_text = "A" * (MAX_MESSAGE_LENGTH + 1000)

        # Call function with long message
        await send_long_message(mock_update, mock_context, long_text)

        # Assert reply_text was called multiple times
        self.assertGreater(mock_update.message.reply_text.call_count, 1)


if __name__ == "__main__":
    unittest.main()

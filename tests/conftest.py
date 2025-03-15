from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_update():
    """Create a mock Update object for testing."""
    mock = MagicMock()
    mock.effective_user = MagicMock()
    mock.effective_user.id = 123456
    mock.effective_chat = MagicMock()
    mock.effective_chat.id = 789012
    mock.message = MagicMock()
    mock.message.reply_text = AsyncMock()
    mock.message.text = "Test message"
    return mock


@pytest.fixture
def mock_context():
    """Create a mock CallbackContext object for testing."""
    mock = MagicMock()
    mock.args = []
    mock.user_data = {}
    return mock


@pytest.fixture
def mock_restricted():
    """Create a mock for the restricted decorator."""
    with patch("handlers.restricted") as mock:
        # Make the decorator pass through the function
        mock.side_effect = lambda f: f
        yield mock


@pytest.fixture
def mock_db():
    """Create a mock database for testing."""
    mock = MagicMock()
    mock_table = MagicMock()
    mock.table.return_value = mock_table
    return mock


@pytest.fixture
def mock_conversation_table():
    """Create a mock conversation table for testing."""
    mock = MagicMock()
    return mock

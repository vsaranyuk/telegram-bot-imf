"""Unit tests for admin authorization decorator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes

from src.decorators.authorization import admin_only
from src.config.settings import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings with admin user ID."""
    settings = Settings(
        telegram_bot_token="test_token",
        admin_user_id=123456789,
        anthropic_api_key="test_key"
    )
    return settings


@pytest.fixture
def mock_update():
    """Create mock Telegram update object."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context(mock_settings):
    """Create mock context with settings in bot_data."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot_data = {"settings": mock_settings}
    return context


@pytest.mark.asyncio
async def test_admin_only_authorized_user(mock_update, mock_context, mock_settings):
    """Test that admin_only decorator allows authorized admin user."""
    # Set user_id to match admin_user_id
    mock_update.effective_user.id = mock_settings.admin_user_id

    # Create a test command handler
    @admin_only
    async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test command handler."""
        return "success"

    # Execute decorated function
    result = await test_command(mock_update, mock_context)

    # Assert function was executed successfully
    assert result == "success"

    # Assert no error message was sent
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_admin_only_unauthorized_user(mock_update, mock_context, mock_settings):
    """Test that admin_only decorator blocks unauthorized user."""
    # Set user_id to NOT match admin_user_id
    mock_update.effective_user.id = 987654321  # Different from admin_user_id

    # Create a test command handler
    @admin_only
    async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test command handler."""
        return "success"

    # Execute decorated function
    result = await test_command(mock_update, mock_context)

    # Assert function did not execute (returned None)
    assert result is None

    # Assert error message was sent
    mock_update.message.reply_text.assert_called_once_with(
        "⛔️ Access denied. Admin only command."
    )


@pytest.mark.asyncio
async def test_admin_only_missing_effective_user(mock_update, mock_context):
    """Test that decorator handles missing effective_user gracefully."""
    # Remove effective_user
    mock_update.effective_user = None

    @admin_only
    async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test command handler."""
        return "success"

    # Execute decorated function
    result = await test_command(mock_update, mock_context)

    # Assert function did not execute
    assert result is None

    # Assert no error message was sent (user doesn't exist)
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_admin_only_missing_settings(mock_update, mock_context):
    """Test that decorator handles missing settings in bot_data."""
    # Remove settings from bot_data
    mock_update.effective_user.id = 123456789
    mock_context.bot_data = {}  # No settings

    @admin_only
    async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test command handler."""
        return "success"

    # Execute decorated function
    result = await test_command(mock_update, mock_context)

    # Assert function did not execute
    assert result is None

    # Assert configuration error message was sent
    mock_update.message.reply_text.assert_called_once_with(
        "⚠️ Bot configuration error. Please contact administrator."
    )


@pytest.mark.asyncio
async def test_admin_only_preserves_function_metadata():
    """Test that decorator preserves function metadata using functools.wraps."""
    @admin_only
    async def test_command_with_docstring(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """This is a test command with documentation."""
        return "success"

    # Assert function metadata is preserved
    assert test_command_with_docstring.__name__ == "test_command_with_docstring"
    assert test_command_with_docstring.__doc__ == "This is a test command with documentation."


@pytest.mark.asyncio
async def test_admin_only_works_with_function_args(mock_update, mock_context, mock_settings):
    """Test that decorator works with functions that have additional arguments."""
    mock_update.effective_user.id = mock_settings.admin_user_id

    @admin_only
    async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        """Test command with extra args."""
        return {"args": args, "kwargs": kwargs}

    # Execute with extra arguments
    result = await test_command(mock_update, mock_context, "arg1", "arg2", key="value")

    # Assert function received the arguments
    assert result == {"args": ("arg1", "arg2"), "kwargs": {"key": "value"}}


@pytest.mark.asyncio
async def test_admin_only_logging_on_unauthorized_access(mock_update, mock_context, mock_settings):
    """Test that unauthorized access attempts are logged."""
    mock_update.effective_user.id = 987654321  # Unauthorized user

    @admin_only
    async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test command handler."""
        return "success"

    # Patch logger to verify logging
    with patch('src.decorators.authorization.logger') as mock_logger:
        await test_command(mock_update, mock_context)

        # Assert warning was logged
        assert mock_logger.warning.called
        warning_message = mock_logger.warning.call_args[0][0]
        assert "Unauthorized command access attempt" in warning_message
        assert "user_id=987654321" in warning_message


@pytest.mark.asyncio
async def test_admin_only_logging_on_authorized_access(mock_update, mock_context, mock_settings):
    """Test that authorized access is logged."""
    mock_update.effective_user.id = mock_settings.admin_user_id

    @admin_only
    async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test command handler."""
        return "success"

    # Patch logger to verify logging
    with patch('src.decorators.authorization.logger') as mock_logger:
        await test_command(mock_update, mock_context)

        # Assert info log was created
        assert mock_logger.info.called
        info_message = mock_logger.info.call_args[0][0]
        assert "Admin command authorized" in info_message
        assert f"user_id={mock_settings.admin_user_id}" in info_message

"""Unit tests for admin command handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes
from datetime import datetime

from src.handlers.admin_commands import (
    add_chat_command,
    list_chats_command,
    remove_chat_command,
    get_chat_id_command,
    admin_help_command
)
from src.models.chat import Chat as ChatModel
from src.repositories.chat_repository import ChatRepository


# Fixtures

@pytest.fixture
def mock_update():
    """Create mock Telegram update object."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456789
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = -1001234567890
    update.effective_chat.title = "Test Channel"
    update.effective_chat.type = "channel"
    return update


@pytest.fixture
def mock_context():
    """Create mock context with admin settings."""
    from src.config.settings import Settings
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    # Add settings with admin_user_id matching the mock_update fixture
    context.bot_data = {
        "settings": Settings(
            telegram_bot_token="test_token",
            admin_user_id=123456789,  # Matches mock_update.effective_user.id
            anthropic_api_key="test_key"
        )
    }
    return context


# Tests for add_chat_command

@pytest.mark.asyncio
@patch('src.handlers.admin_commands.get_db_session')
async def test_add_chat_success_new_chat(mock_get_db, mock_update, mock_context, db_session):
    """Test successfully adding a new chat to whitelist."""
    # Setup
    mock_context.args = ["-1001234567890", "Test", "Channel"]
    mock_get_db.return_value.__enter__.return_value = db_session

    # Execute
    await add_chat_command(mock_update, mock_context)

    # Verify
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "✅ Chat added to whitelist" in call_args[0][0]
    assert "-1001234567890" in call_args[0][0]
    assert "Test Channel" in call_args[0][0]


@pytest.mark.asyncio
@patch('src.handlers.admin_commands.get_db_session')
async def test_add_chat_success_update_existing(mock_get_db, mock_update, mock_context, db_session):
    """Test successfully updating an existing chat."""
    # Setup - add existing chat first with NEGATIVE chat_id
    existing_chat = ChatModel(chat_id=-1001234, chat_name="Old Name", enabled=False)
    repo = ChatRepository(db_session)
    repo.save_chat(existing_chat)

    mock_context.args = ["-1001234", "Updated", "Name"]
    mock_get_db.return_value.__enter__.return_value = db_session

    # Execute
    await add_chat_command(mock_update, mock_context)

    # Verify
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "✅ Chat updated in whitelist" in call_args[0][0]
    assert "Updated Name" in call_args[0][0]


@pytest.mark.asyncio
async def test_add_chat_missing_arguments(mock_update, mock_context):
    """Test add_chat with missing arguments shows usage help."""
    # Setup - no arguments
    mock_context.args = []

    # Execute
    await add_chat_command(mock_update, mock_context)

    # Verify
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "❌ Usage:" in call_args[0][0]
    assert "/add_chat <chat_id> <chat_name>" in call_args[0][0]


@pytest.mark.asyncio
async def test_add_chat_invalid_chat_id(mock_update, mock_context):
    """Test add_chat with invalid (non-numeric) chat_id."""
    # Setup
    mock_context.args = ["invalid_id", "Test", "Channel"]

    # Execute
    await add_chat_command(mock_update, mock_context)

    # Verify
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "❌ Invalid chat_id" in call_args[0][0]


@pytest.mark.asyncio
@patch('src.handlers.admin_commands.get_db_session')
async def test_add_chat_positive_id_warning(mock_get_db, mock_update, mock_context, db_session):
    """Test add_chat with positive chat_id shows warning AND adds chat."""
    # Setup
    mock_context.args = ["12345", "Test", "User"]
    mock_get_db.return_value.__enter__.return_value = db_session

    # Execute
    await add_chat_command(mock_update, mock_context)

    # Verify - should show warning about positive chat_id (first call) AND success message (second call)
    assert mock_update.message.reply_text.call_count == 2
    first_call_args = mock_update.message.reply_text.call_args_list[0]
    second_call_args = mock_update.message.reply_text.call_args_list[1]

    assert "⚠️ Warning" in first_call_args[0][0]
    assert "should typically be negative" in first_call_args[0][0]
    assert "✅ Chat added to whitelist" in second_call_args[0][0]


# Tests for list_chats_command

@pytest.mark.asyncio
@patch('src.handlers.admin_commands.get_db_session')
async def test_list_chats_with_chats(mock_get_db, mock_update, mock_context, db_session):
    """Test listing chats when chats exist."""
    # Setup - add some chats
    repo = ChatRepository(db_session)
    chat1 = ChatModel(chat_id=-1001, chat_name="Chat 1", enabled=True)
    chat2 = ChatModel(chat_id=-1002, chat_name="Chat 2", enabled=True)
    repo.save_chat(chat1)
    repo.save_chat(chat2)

    mock_get_db.return_value.__enter__.return_value = db_session

    # Execute
    await list_chats_command(mock_update, mock_context)

    # Verify
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    message = call_args[0][0]
    assert "📋 *Whitelisted Chats:*" in message
    assert "Chat 1" in message
    assert "Chat 2" in message
    assert "-1001" in message
    assert "-1002" in message


@pytest.mark.asyncio
@patch('src.handlers.admin_commands.get_db_session')
async def test_list_chats_empty(mock_get_db, mock_update, mock_context, db_session):
    """Test listing chats when no chats exist."""
    # Setup - empty database
    mock_get_db.return_value.__enter__.return_value = db_session

    # Execute
    await list_chats_command(mock_update, mock_context)

    # Verify
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "📭 No whitelisted chats found" in call_args[0][0]


# Tests for remove_chat_command

@pytest.mark.asyncio
@patch('src.handlers.admin_commands.get_db_session')
async def test_remove_chat_success(mock_get_db, mock_update, mock_context, db_session, sample_chat):
    """Test successfully removing a chat."""
    # Setup - add chat first
    repo = ChatRepository(db_session)
    repo.save_chat(sample_chat)

    mock_context.args = [str(sample_chat.chat_id)]
    mock_get_db.return_value.__enter__.return_value = db_session

    # Execute
    await remove_chat_command(mock_update, mock_context)

    # Verify
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "✅ Chat removed from whitelist" in call_args[0][0]
    assert sample_chat.chat_name in call_args[0][0]

    # Verify chat is soft deleted (enabled=False)
    chat = repo.get_chat_by_id(sample_chat.chat_id)
    assert chat is not None
    assert chat.enabled is False


@pytest.mark.asyncio
@patch('src.handlers.admin_commands.get_db_session')
async def test_remove_chat_not_found(mock_get_db, mock_update, mock_context, db_session):
    """Test removing non-existent chat."""
    # Setup
    mock_context.args = ["-999999"]
    mock_get_db.return_value.__enter__.return_value = db_session

    # Execute
    await remove_chat_command(mock_update, mock_context)

    # Verify
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "❌ Chat not found" in call_args[0][0]


@pytest.mark.asyncio
async def test_remove_chat_missing_arguments(mock_update, mock_context):
    """Test remove_chat with missing arguments shows usage help."""
    # Setup - no arguments
    mock_context.args = []

    # Execute
    await remove_chat_command(mock_update, mock_context)

    # Verify
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "❌ Usage:" in call_args[0][0]
    assert "/remove_chat <chat_id>" in call_args[0][0]


@pytest.mark.asyncio
async def test_remove_chat_invalid_chat_id(mock_update, mock_context):
    """Test remove_chat with invalid chat_id."""
    # Setup
    mock_context.args = ["invalid"]

    # Execute
    await remove_chat_command(mock_update, mock_context)

    # Verify
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "❌ Invalid chat_id" in call_args[0][0]


# Tests for get_chat_id_command

@pytest.mark.asyncio
async def test_get_chat_id_in_channel(mock_update, mock_context):
    """Test get_chat_id in a channel."""
    # Setup
    mock_update.effective_chat.id = -1001234567890
    mock_update.effective_chat.title = "Test Channel"
    mock_update.effective_chat.type = "channel"

    # Execute
    await get_chat_id_command(mock_update, mock_context)

    # Verify
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    message = call_args[0][0]
    assert "🆔 *Chat Information:*" in message
    assert "-1001234567890" in message
    assert "Test Channel" in message
    assert "channel" in message
    assert "/add_chat -1001234567890" in message


@pytest.mark.asyncio
async def test_get_chat_id_in_private_chat(mock_update, mock_context):
    """Test get_chat_id in a private chat."""
    # Setup
    mock_update.effective_chat.id = 123456789
    mock_update.effective_chat.title = None
    mock_update.effective_chat.first_name = "John"
    mock_update.effective_chat.type = "private"

    # Execute
    await get_chat_id_command(mock_update, mock_context)

    # Verify
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    message = call_args[0][0]
    assert "123456789" in message
    assert "John" in message
    assert "private" in message


# Tests for admin_help_command

@pytest.mark.asyncio
async def test_admin_help_command(mock_update, mock_context):
    """Test admin help command shows all commands."""
    # Execute
    await admin_help_command(mock_update, mock_context)

    # Verify
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    message = call_args[0][0]

    # Check all commands are documented
    assert "🔧 *Admin Commands*" in message
    assert "/add_chat" in message
    assert "/remove_chat" in message
    assert "/list_chats" in message
    assert "/get_chat_id" in message


# Integration-style tests with real database operations

@pytest.mark.asyncio
@patch('src.handlers.admin_commands.get_db_session')
async def test_admin_workflow_add_list_remove(mock_get_db, mock_update, mock_context, db_session):
    """Test complete admin workflow: add chat -> list -> remove."""
    mock_get_db.return_value.__enter__.return_value = db_session

    # Step 1: Add chat
    mock_context.args = ["-1001234", "Test", "Channel"]
    await add_chat_command(mock_update, mock_context)
    assert mock_update.message.reply_text.call_count == 1
    assert "✅ Chat added" in mock_update.message.reply_text.call_args[0][0]

    # Step 2: List chats
    mock_update.message.reply_text.reset_mock()
    await list_chats_command(mock_update, mock_context)
    assert mock_update.message.reply_text.call_count == 1
    message = mock_update.message.reply_text.call_args[0][0]
    assert "Test Channel" in message
    assert "-1001234" in message

    # Step 3: Remove chat
    mock_update.message.reply_text.reset_mock()
    mock_context.args = ["-1001234"]
    await remove_chat_command(mock_update, mock_context)
    assert mock_update.message.reply_text.call_count == 1
    assert "✅ Chat removed" in mock_update.message.reply_text.call_args[0][0]

    # Step 4: Verify chat is disabled
    repo = ChatRepository(db_session)
    chat = repo.get_chat_by_id(-1001234)
    assert chat is not None
    assert chat.enabled is False


# Error handling tests

@pytest.mark.asyncio
@patch('src.handlers.admin_commands.get_db_session')
async def test_add_chat_database_error(mock_get_db, mock_update, mock_context):
    """Test add_chat handles database errors gracefully."""
    # Setup - simulate database error
    mock_session = MagicMock()
    mock_session.commit.side_effect = Exception("Database error")
    mock_get_db.return_value.__enter__.return_value = mock_session

    mock_context.args = ["-1001234", "Test"]

    # Execute
    await add_chat_command(mock_update, mock_context)

    # Verify error message shown
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "❌ Error adding chat" in call_args[0][0]


@pytest.mark.asyncio
@patch('src.handlers.admin_commands.get_db_session')
async def test_list_chats_database_error(mock_get_db, mock_update, mock_context):
    """Test list_chats handles database errors gracefully."""
    # Setup - simulate database error
    mock_get_db.return_value.__enter__.side_effect = Exception("Database connection failed")

    # Execute
    await list_chats_command(mock_update, mock_context)

    # Verify error message shown
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "❌ Error listing chats" in call_args[0][0]


# Logging tests

@pytest.mark.asyncio
@patch('src.handlers.admin_commands.logger')
@patch('src.handlers.admin_commands.get_db_session')
async def test_add_chat_logs_admin_action(mock_get_db, mock_logger, mock_update, mock_context, db_session):
    """Test that add_chat logs admin actions."""
    mock_get_db.return_value.__enter__.return_value = db_session
    mock_context.args = ["-1001234", "Test"]

    await add_chat_command(mock_update, mock_context)

    # Verify logging occurred
    assert mock_logger.info.called
    log_message = mock_logger.info.call_args[0][0]
    assert "Admin added chat" in log_message
    assert "admin_id" in log_message

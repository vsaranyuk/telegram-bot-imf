"""Integration tests for admin chat whitelist management E2E workflows.

These tests verify complete end-to-end scenarios:
1. Admin adds chat → Messages from that chat are collected
2. Admin removes chat → Messages from that chat are ignored
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.handlers.admin_commands import add_chat_command, remove_chat_command
from src.services.message_collector_service import MessageCollectorService
from src.repositories.message_repository import MessageRepository
from src.repositories.chat_repository import ChatRepository
from src.config.settings import Settings


@pytest.mark.asyncio
class TestAdminChatWorkflow:
    """E2E integration tests for admin chat management workflows."""

    async def test_admin_adds_chat_then_messages_collected(self, db_session):
        """Test E2E: Admin adds chat to whitelist → Bot collects messages from it.

        Workflow:
        1. Admin executes /add_chat command with chat_id and name
        2. Chat is added to whitelist (enabled=True)
        3. Message arrives from that chat
        4. Bot collects and stores the message

        Args:
            db_session: Database session fixture
        """
        # Step 1: Setup admin context and mock update
        admin_user_id = 123456789
        test_chat_id = -1001234567890
        test_chat_name = "Partner Channel"

        settings = Settings(
            telegram_bot_token="test_token",
            admin_user_id=admin_user_id,
            anthropic_api_key="test_key"
        )

        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = admin_user_id
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()

        mock_context = MagicMock()
        mock_context.args = [str(test_chat_id), test_chat_name]
        mock_context.bot_data = {"settings": settings}

        # Step 2: Admin executes /add_chat command
        with pytest.MonkeyPatch.context() as mp:
            def mock_get_session():
                class SessionContext:
                    def __enter__(self):
                        return db_session
                    def __exit__(self, *args):
                        pass
                return SessionContext()

            mp.setattr(
                'src.handlers.admin_commands.get_db_session',
                mock_get_session
            )

            await add_chat_command(mock_update, mock_context)

        # Verify: Chat was added to whitelist
        chat_repo = ChatRepository(db_session)
        added_chat = chat_repo.get_chat_by_id(test_chat_id)

        assert added_chat is not None, "Chat should be added to whitelist"
        assert added_chat.chat_id == test_chat_id
        assert added_chat.chat_name == test_chat_name
        assert added_chat.enabled is True, "Chat should be enabled"

        # Verify: Admin received success message
        mock_update.message.reply_text.assert_called()
        success_message = mock_update.message.reply_text.call_args[0][0]
        assert "✅ Chat added to whitelist" in success_message

        # Step 3: Simulate message arriving from the whitelisted chat
        mock_message_update = MagicMock()
        mock_message = MagicMock()
        mock_message.chat_id = test_chat_id
        mock_message.message_id = 100
        mock_message.text = "Test message from partner channel"
        mock_message.date = datetime.now()

        mock_user = MagicMock()
        mock_user.id = 999888777
        mock_user.full_name = "Partner User"
        mock_message.from_user = mock_user

        mock_message_update.message = mock_message

        # Step 4: Bot handles the message
        collector = MessageCollectorService()

        with pytest.MonkeyPatch.context() as mp:
            def mock_get_session():
                class SessionContext:
                    def __enter__(self):
                        return db_session
                    def __exit__(self, *args):
                        pass
                return SessionContext()

            mp.setattr(
                'src.services.message_collector_service.get_db_session',
                mock_get_session
            )

            await collector.handle_message(mock_message_update, None)

        # Verify: Message was collected and stored
        message_repo = MessageRepository(db_session)
        saved_message = message_repo.get_message_by_id(test_chat_id, 100)

        assert saved_message is not None, "Message should be collected from whitelisted chat"
        assert saved_message.chat_id == test_chat_id
        assert saved_message.message_id == 100
        assert saved_message.text == "Test message from partner channel"
        assert saved_message.user_id == 999888777
        assert saved_message.user_name == "Partner User"

    async def test_admin_removes_chat_then_messages_ignored(self, db_session):
        """Test E2E: Admin removes chat from whitelist → Bot ignores messages from it.

        Workflow:
        1. Chat exists in whitelist (enabled=True)
        2. Message from chat is collected (verify baseline behavior)
        3. Admin executes /remove_chat command
        4. Chat is disabled (enabled=False)
        5. New message arrives from same chat
        6. Bot ignores the message (does not store it)

        Args:
            db_session: Database session fixture
        """
        # Step 1: Setup - Chat already exists in whitelist
        admin_user_id = 123456789
        test_chat_id = -1001234567890
        test_chat_name = "Partner Channel"

        settings = Settings(
            telegram_bot_token="test_token",
            admin_user_id=admin_user_id,
            anthropic_api_key="test_key"
        )

        chat_repo = ChatRepository(db_session)
        from src.models.chat import Chat
        existing_chat = Chat(
            chat_id=test_chat_id,
            chat_name=test_chat_name,
            enabled=True
        )
        chat_repo.save_chat(existing_chat)

        # Step 2: Verify baseline - Messages from enabled chat are collected
        mock_message_update = MagicMock()
        mock_message = MagicMock()
        mock_message.chat_id = test_chat_id
        mock_message.message_id = 100
        mock_message.text = "Message before removal"
        mock_message.date = datetime.now()

        mock_user = MagicMock()
        mock_user.id = 999888777
        mock_user.full_name = "Partner User"
        mock_message.from_user = mock_user

        mock_message_update.message = mock_message

        collector = MessageCollectorService()

        with pytest.MonkeyPatch.context() as mp:
            def mock_get_session():
                class SessionContext:
                    def __enter__(self):
                        return db_session
                    def __exit__(self, *args):
                        pass
                return SessionContext()

            mp.setattr(
                'src.services.message_collector_service.get_db_session',
                mock_get_session
            )

            await collector.handle_message(mock_message_update, None)

        # Verify: Message was collected (baseline)
        message_repo = MessageRepository(db_session)
        baseline_message = message_repo.get_message_by_id(test_chat_id, 100)
        assert baseline_message is not None, "Baseline: Message should be collected from enabled chat"

        # Step 3: Admin executes /remove_chat command
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = admin_user_id
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()

        mock_context = MagicMock()
        mock_context.args = [str(test_chat_id)]
        mock_context.bot_data = {"settings": settings}

        with pytest.MonkeyPatch.context() as mp:
            def mock_get_session():
                class SessionContext:
                    def __enter__(self):
                        return db_session
                    def __exit__(self, *args):
                        pass
                return SessionContext()

            mp.setattr(
                'src.handlers.admin_commands.get_db_session',
                mock_get_session
            )

            await remove_chat_command(mock_update, mock_context)

        # Step 4: Verify chat was disabled
        db_session.expire_all()  # Refresh from database
        removed_chat = chat_repo.get_chat_by_id(test_chat_id)

        assert removed_chat is not None, "Chat should still exist (soft delete)"
        assert removed_chat.enabled is False, "Chat should be disabled after removal"

        # Verify: Admin received success message
        mock_update.message.reply_text.assert_called()
        success_message = mock_update.message.reply_text.call_args[0][0]
        assert "✅ Chat removed from whitelist" in success_message

        # Step 5: Simulate new message arriving from the disabled chat
        mock_new_message_update = MagicMock()
        mock_new_message = MagicMock()
        mock_new_message.chat_id = test_chat_id
        mock_new_message.message_id = 200  # Different message ID
        mock_new_message.text = "Message after removal - should be ignored"
        mock_new_message.date = datetime.now()

        mock_new_message.from_user = mock_user
        mock_new_message_update.message = mock_new_message

        # Step 6: Bot handles the new message
        with pytest.MonkeyPatch.context() as mp:
            def mock_get_session():
                class SessionContext:
                    def __enter__(self):
                        return db_session
                    def __exit__(self, *args):
                        pass
                return SessionContext()

            mp.setattr(
                'src.services.message_collector_service.get_db_session',
                mock_get_session
            )

            await collector.handle_message(mock_new_message_update, None)

        # Verify: New message was NOT collected (ignored)
        ignored_message = message_repo.get_message_by_id(test_chat_id, 200)

        assert ignored_message is None, "Message should be ignored from disabled chat"

        # Verify: Only the baseline message exists, not the new one
        all_messages = message_repo.get_messages_last_24h(test_chat_id)
        assert len(all_messages) == 1, "Only baseline message should exist"
        assert all_messages[0].message_id == 100, "Should be the baseline message"

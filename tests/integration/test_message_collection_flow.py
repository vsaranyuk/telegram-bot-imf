"""Integration tests for message collection flow."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.services.message_collector_service import MessageCollectorService
from src.repositories.message_repository import MessageRepository
from src.repositories.chat_repository import ChatRepository
from src.models.chat import Chat
from src.models.message import Message


@pytest.mark.asyncio
class TestMessageCollectionFlow:
    """Integration tests for bot receiving and storing messages."""

    async def test_handle_message_saves_to_database(self, db_session):
        """Test message flow: receive → validate chat → save to DB.

        Args:
            db_session: Database session fixture
        """
        # Setup chat whitelist
        chat_repo = ChatRepository(db_session)
        test_chat = Chat(
            chat_id=12345678,
            chat_name="Test Chat",
            enabled=True
        )
        chat_repo.save_chat(test_chat)

        # Create mock Telegram update
        mock_update = MagicMock()
        mock_message = MagicMock()
        mock_message.chat_id = 12345678
        mock_message.message_id = 100
        mock_message.text = "Test message"
        mock_message.date = datetime.now()

        mock_user = MagicMock()
        mock_user.id = 999
        mock_user.full_name = "Test User"
        mock_message.from_user = mock_user

        mock_update.message = mock_message

        # Handle message
        collector = MessageCollectorService()

        with pytest.MonkeyPatch.context() as mp:
            # Patch get_db_session to use our test session
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

            await collector.handle_message(mock_update, None)

        # Verify message was saved
        message_repo = MessageRepository(db_session)
        saved_message = message_repo.get_message_by_id(12345678, 100)

        assert saved_message is not None
        assert saved_message.text == "Test message"
        assert saved_message.user_name == "Test User"

    async def test_handle_message_ignores_non_whitelisted_chat(self, db_session):
        """Test message from non-whitelisted chat is ignored.

        Args:
            db_session: Database session fixture
        """
        # DO NOT add chat to whitelist

        # Create mock Telegram update
        mock_update = MagicMock()
        mock_message = MagicMock()
        mock_message.chat_id = 99999999  # Not whitelisted
        mock_message.message_id = 100
        mock_message.text = "Should be ignored"
        mock_message.date = datetime.now()

        mock_user = MagicMock()
        mock_user.id = 999
        mock_user.full_name = "Test User"
        mock_message.from_user = mock_user

        mock_update.message = mock_message

        # Handle message
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

            await collector.handle_message(mock_update, None)

        # Verify no message was saved
        message_repo = MessageRepository(db_session)
        saved_message = message_repo.get_message_by_id(99999999, 100)

        assert saved_message is None

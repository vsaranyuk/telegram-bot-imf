"""Unit tests for ChatRepository."""

import pytest

from src.repositories.chat_repository import ChatRepository
from src.models.chat import Chat


class TestChatRepository:
    """Test suite for ChatRepository."""

    def test_save_chat(self, db_session, sample_chat):
        """Test saving a chat to database.

        Args:
            db_session: Database session fixture
            sample_chat: Sample chat fixture
        """
        repo = ChatRepository(db_session)

        # Save chat
        saved = repo.save_chat(sample_chat)

        # Verify
        assert saved.id is not None
        assert saved.chat_id == sample_chat.chat_id
        assert saved.chat_name == sample_chat.chat_name
        assert saved.enabled is True

    def test_get_chat_by_id(self, db_session, sample_chat):
        """Test retrieving chat by chat_id.

        Args:
            db_session: Database session fixture
            sample_chat: Sample chat fixture
        """
        repo = ChatRepository(db_session)

        # Save and retrieve
        repo.save_chat(sample_chat)
        found = repo.get_chat_by_id(sample_chat.chat_id)

        assert found is not None
        assert found.chat_id == sample_chat.chat_id
        assert found.chat_name == sample_chat.chat_name

    def test_get_chat_by_id_not_found(self, db_session):
        """Test retrieving non-existent chat returns None.

        Args:
            db_session: Database session fixture
        """
        repo = ChatRepository(db_session)

        found = repo.get_chat_by_id(99999)

        assert found is None

    def test_get_all_enabled_chats(self, db_session):
        """Test retrieving only enabled chats.

        Args:
            db_session: Database session fixture
        """
        repo = ChatRepository(db_session)

        # Create mix of enabled and disabled chats
        chats = [
            Chat(chat_id=111, chat_name="Enabled 1", enabled=True),
            Chat(chat_id=222, chat_name="Disabled", enabled=False),
            Chat(chat_id=333, chat_name="Enabled 2", enabled=True),
        ]

        for chat in chats:
            repo.save_chat(chat)

        # Get enabled chats
        enabled = repo.get_all_enabled_chats()

        assert len(enabled) == 2
        assert all(chat.enabled for chat in enabled)

    def test_get_all_chats(self, db_session):
        """Test retrieving all chats regardless of status.

        Args:
            db_session: Database session fixture
        """
        repo = ChatRepository(db_session)

        # Create chats
        chats = [
            Chat(chat_id=111, chat_name="Chat 1", enabled=True),
            Chat(chat_id=222, chat_name="Chat 2", enabled=False),
        ]

        for chat in chats:
            repo.save_chat(chat)

        # Get all chats
        all_chats = repo.get_all_chats()

        assert len(all_chats) == 2

    def test_update_chat_enabled_status(self, db_session, sample_chat):
        """Test updating chat enabled status.

        Args:
            db_session: Database session fixture
            sample_chat: Sample chat fixture
        """
        repo = ChatRepository(db_session)

        # Save chat
        repo.save_chat(sample_chat)

        # Update to disabled
        updated = repo.update_chat_enabled_status(sample_chat.chat_id, False)

        assert updated is not None
        assert updated.enabled is False

        # Verify in database
        found = repo.get_chat_by_id(sample_chat.chat_id)
        assert found.enabled is False

    def test_is_chat_enabled(self, db_session):
        """Test checking if chat is enabled.

        Args:
            db_session: Database session fixture
        """
        repo = ChatRepository(db_session)

        # Create enabled and disabled chats
        enabled_chat = Chat(chat_id=111, chat_name="Enabled", enabled=True)
        disabled_chat = Chat(chat_id=222, chat_name="Disabled", enabled=False)

        repo.save_chat(enabled_chat)
        repo.save_chat(disabled_chat)

        # Check enabled status
        assert repo.is_chat_enabled(111) is True
        assert repo.is_chat_enabled(222) is False
        assert repo.is_chat_enabled(999) is False  # Non-existent chat

    def test_delete_chat(self, db_session, sample_chat):
        """Test deleting a chat.

        Args:
            db_session: Database session fixture
            sample_chat: Sample chat fixture
        """
        repo = ChatRepository(db_session)

        # Save chat
        repo.save_chat(sample_chat)

        # Delete
        result = repo.delete_chat(sample_chat.chat_id)

        assert result is True

        # Verify deleted
        found = repo.get_chat_by_id(sample_chat.chat_id)
        assert found is None

    def test_delete_chat_not_found(self, db_session):
        """Test deleting non-existent chat returns False.

        Args:
            db_session: Database session fixture
        """
        repo = ChatRepository(db_session)

        result = repo.delete_chat(99999)

        assert result is False

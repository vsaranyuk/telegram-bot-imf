"""Unit tests for MessageRepository."""

import pytest
from datetime import datetime, timedelta

from src.repositories.message_repository import MessageRepository
from src.models.message import Message


class TestMessageRepository:
    """Test suite for MessageRepository."""

    def test_save_message(self, db_session, sample_message):
        """Test saving a message to database.

        Args:
            db_session: Database session fixture
            sample_message: Sample message fixture
        """
        repo = MessageRepository(db_session)

        # Save message
        saved = repo.save_message(sample_message)

        # Verify
        assert saved.id is not None
        assert saved.chat_id == sample_message.chat_id
        assert saved.message_id == sample_message.message_id
        assert saved.text == sample_message.text

    def test_get_messages_last_24h(self, db_session):
        """Test retrieving messages from last 24 hours.

        Args:
            db_session: Database session fixture
        """
        repo = MessageRepository(db_session)
        chat_id = 12345678

        # Create messages at different times
        now = datetime.now()
        messages = [
            Message(
                chat_id=chat_id,
                message_id=1,
                user_id=1,
                user_name="User 1",
                text="Recent message",
                timestamp=now - timedelta(hours=2)
            ),
            Message(
                chat_id=chat_id,
                message_id=2,
                user_id=1,
                user_name="User 1",
                text="Old message",
                timestamp=now - timedelta(hours=30)
            ),
            Message(
                chat_id=chat_id,
                message_id=3,
                user_id=1,
                user_name="User 1",
                text="Very recent",
                timestamp=now - timedelta(minutes=5)
            )
        ]

        for msg in messages:
            repo.save_message(msg)

        # Get messages from last 24h
        recent = repo.get_messages_last_24h(chat_id)

        # Should only include messages 1 and 3
        assert len(recent) == 2
        assert all(msg.timestamp >= now - timedelta(hours=24) for msg in recent)

    def test_get_message_by_id(self, db_session, sample_message):
        """Test retrieving message by chat_id and message_id.

        Args:
            db_session: Database session fixture
            sample_message: Sample message fixture
        """
        repo = MessageRepository(db_session)

        # Save message
        repo.save_message(sample_message)

        # Retrieve by ID
        found = repo.get_message_by_id(
            sample_message.chat_id,
            sample_message.message_id
        )

        assert found is not None
        assert found.message_id == sample_message.message_id
        assert found.text == sample_message.text

    def test_get_message_by_id_not_found(self, db_session):
        """Test retrieving non-existent message returns None.

        Args:
            db_session: Database session fixture
        """
        repo = MessageRepository(db_session)

        found = repo.get_message_by_id(99999, 99999)

        assert found is None

    def test_delete_old_messages(self, db_session):
        """Test deleting messages older than cutoff date.

        Args:
            db_session: Database session fixture
        """
        repo = MessageRepository(db_session)
        chat_id = 12345678
        now = datetime.now()

        # Create messages at different ages
        messages = [
            Message(
                chat_id=chat_id,
                message_id=1,
                user_id=1,
                user_name="User 1",
                text="10 hours old",
                timestamp=now - timedelta(hours=10)
            ),
            Message(
                chat_id=chat_id,
                message_id=2,
                user_id=1,
                user_name="User 1",
                text="30 hours old",
                timestamp=now - timedelta(hours=30)
            ),
            Message(
                chat_id=chat_id,
                message_id=3,
                user_id=1,
                user_name="User 1",
                text="50 hours old",
                timestamp=now - timedelta(hours=50)
            )
        ]

        for msg in messages:
            repo.save_message(msg)

        # Delete messages older than 48 hours
        cutoff = now - timedelta(hours=48)
        deleted_count = repo.delete_old_messages(cutoff)

        # Should delete 1 message (50 hours old)
        assert deleted_count == 1

        # Verify remaining messages
        remaining = db_session.query(Message).count()
        assert remaining == 2

    def test_count_messages(self, db_session):
        """Test counting messages with optional chat filter.

        Args:
            db_session: Database session fixture
        """
        repo = MessageRepository(db_session)

        # Create messages in different chats
        messages = [
            Message(
                chat_id=111,
                message_id=1,
                user_id=1,
                user_name="User 1",
                text="Chat 111",
                timestamp=datetime.now()
            ),
            Message(
                chat_id=111,
                message_id=2,
                user_id=1,
                user_name="User 1",
                text="Chat 111 again",
                timestamp=datetime.now()
            ),
            Message(
                chat_id=222,
                message_id=1,
                user_id=1,
                user_name="User 1",
                text="Chat 222",
                timestamp=datetime.now()
            )
        ]

        for msg in messages:
            repo.save_message(msg)

        # Count all messages
        total = repo.count_messages()
        assert total == 3

        # Count messages in specific chat
        chat_111_count = repo.count_messages(chat_id=111)
        assert chat_111_count == 2

    def test_message_reactions(self, db_session, sample_message_with_reactions):
        """Test storing and retrieving message reactions.

        Args:
            db_session: Database session fixture
            sample_message_with_reactions: Message with reactions fixture
        """
        repo = MessageRepository(db_session)

        # Save message with reactions
        saved = repo.save_message(sample_message_with_reactions)

        # Retrieve and check reactions
        found = repo.get_message_by_id(saved.chat_id, saved.message_id)
        reactions = found.get_reactions()

        assert reactions == {"❤️": 5, "👍": 3, "💩": 1}

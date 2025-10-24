"""Message repository for database operations."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from src.models.message import Message

logger = logging.getLogger(__name__)


class MessageRepository:
    """Repository for Message entity operations.

    Provides data access layer for messages with common query patterns.
    """

    def __init__(self, session: Session):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def save_message(self, message: Message) -> Message:
        """Save a new message to the database.

        Args:
            message: Message entity to save

        Returns:
            Saved message with ID assigned

        Example:
            message = Message(
                chat_id=12345,
                message_id=67890,
                user_id=111,
                user_name="John",
                text="Hello",
                timestamp=datetime.now()
            )
            saved = repo.save_message(message)
        """
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)

        logger.debug(
            f"Message saved: chat_id={message.chat_id}, "
            f"message_id={message.message_id}"
        )

        return message

    def get_messages_last_24h(self, chat_id: int) -> List[Message]:
        """Get all messages from the last 24 hours for a chat.

        Uses index idx_chat_timestamp for efficient querying.

        Args:
            chat_id: Telegram chat ID

        Returns:
            List of messages ordered by timestamp descending
        """
        cutoff_time = datetime.now() - timedelta(hours=24)

        messages = (
            self.session.query(Message)
            .filter(
                and_(
                    Message.chat_id == chat_id,
                    Message.timestamp >= cutoff_time
                )
            )
            .order_by(desc(Message.timestamp))
            .all()
        )

        logger.debug(
            f"Retrieved {len(messages)} messages from last 24h "
            f"for chat_id={chat_id}"
        )

        return messages

    def get_message_by_id(
        self, chat_id: int, message_id: int
    ) -> Optional[Message]:
        """Get a specific message by chat_id and message_id.

        Uses index idx_message_lookup for efficient querying.

        Args:
            chat_id: Telegram chat ID
            message_id: Telegram message ID

        Returns:
            Message if found, None otherwise
        """
        message = (
            self.session.query(Message)
            .filter(
                and_(
                    Message.chat_id == chat_id,
                    Message.message_id == message_id
                )
            )
            .first()
        )

        return message

    def delete_old_messages(self, before_date: datetime) -> int:
        """Delete messages older than the specified date.

        Args:
            before_date: Delete messages with timestamp before this date

        Returns:
            Number of messages deleted

        Example:
            # Delete messages older than 48 hours
            cutoff = datetime.now() - timedelta(hours=48)
            deleted_count = repo.delete_old_messages(cutoff)
        """
        result = (
            self.session.query(Message)
            .filter(Message.timestamp < before_date)
            .delete()
        )

        self.session.commit()

        logger.info(f"Deleted {result} old messages (before {before_date})")

        return result

    def count_messages(self, chat_id: Optional[int] = None) -> int:
        """Count messages, optionally filtered by chat_id.

        Args:
            chat_id: Optional chat ID to filter by

        Returns:
            Count of messages
        """
        query = self.session.query(Message)

        if chat_id is not None:
            query = query.filter(Message.chat_id == chat_id)

        return query.count()

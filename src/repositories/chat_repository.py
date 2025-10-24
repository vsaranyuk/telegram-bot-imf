"""Chat repository for database operations."""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.chat import Chat

logger = logging.getLogger(__name__)


class ChatRepository:
    """Repository for Chat entity operations.

    Provides data access layer for chat configuration management.
    """

    def __init__(self, session: Session):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def save_chat(self, chat: Chat) -> Chat:
        """Save a new chat configuration.

        Args:
            chat: Chat entity to save

        Returns:
            Saved chat with ID assigned

        Example:
            chat = Chat(
                chat_id=12345,
                chat_name="Partner Chat",
                enabled=True
            )
            saved = repo.save_chat(chat)
        """
        self.session.add(chat)
        self.session.commit()
        self.session.refresh(chat)

        logger.info(
            f"Chat saved: chat_id={chat.chat_id}, name={chat.chat_name}"
        )

        return chat

    def get_chat_by_id(self, chat_id: int) -> Optional[Chat]:
        """Get chat by Telegram chat ID.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Chat if found, None otherwise
        """
        chat = (
            self.session.query(Chat)
            .filter(Chat.chat_id == chat_id)
            .first()
        )

        return chat

    def get_all_enabled_chats(self) -> List[Chat]:
        """Get all enabled chats.

        Returns:
            List of enabled Chat entities
        """
        chats = (
            self.session.query(Chat)
            .filter(Chat.enabled == True)
            .all()
        )

        logger.debug(f"Retrieved {len(chats)} enabled chats")

        return chats

    def get_all_chats(self) -> List[Chat]:
        """Get all chats regardless of enabled status.

        Returns:
            List of all Chat entities
        """
        chats = self.session.query(Chat).all()

        return chats

    def update_chat_enabled_status(
        self, chat_id: int, enabled: bool
    ) -> Optional[Chat]:
        """Update the enabled status of a chat.

        Args:
            chat_id: Telegram chat ID
            enabled: New enabled status

        Returns:
            Updated Chat if found, None otherwise
        """
        chat = self.get_chat_by_id(chat_id)

        if chat:
            chat.enabled = enabled
            self.session.commit()
            self.session.refresh(chat)

            logger.info(
                f"Chat {chat_id} enabled status updated to {enabled}"
            )

        return chat

    def is_chat_enabled(self, chat_id: int) -> bool:
        """Check if a chat is enabled for monitoring.

        Args:
            chat_id: Telegram chat ID

        Returns:
            True if chat is enabled, False otherwise
        """
        chat = self.get_chat_by_id(chat_id)

        return chat is not None and chat.enabled

    def delete_chat(self, chat_id: int) -> bool:
        """Delete a chat configuration.

        Args:
            chat_id: Telegram chat ID

        Returns:
            True if deleted, False if not found
        """
        chat = self.get_chat_by_id(chat_id)

        if chat:
            self.session.delete(chat)
            self.session.commit()

            logger.info(f"Chat deleted: chat_id={chat_id}")
            return True

        return False

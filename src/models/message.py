"""Message database model."""

from datetime import datetime
from typing import Optional
import json
from sqlalchemy import Integer, String, Text, DateTime, Index, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class Message(Base, TimestampMixin):
    """Message entity representing a Telegram message.

    Stores messages collected from monitored Telegram chats.

    Attributes:
        id: Primary key (auto-increment)
        chat_id: Telegram chat ID
        message_id: Telegram message ID
        user_id: Telegram user ID of sender
        user_name: Display name of sender
        text: Message content
        timestamp: When message was sent
        reactions: JSON dictionary of reactions (emoji: count)
    """

    __tablename__ = "messages"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Telegram Identifiers
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Message Content
    user_name: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Reactions (stored as JSON)
    reactions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Indexes for performance
    __table_args__ = (
        # Index for 24-hour message queries
        Index('idx_chat_timestamp', 'chat_id', 'timestamp'),
        # Index for message lookup
        Index('idx_message_lookup', 'chat_id', 'message_id'),
    )

    def set_reactions(self, reactions_dict: dict) -> None:
        """Set reactions from dictionary.

        Args:
            reactions_dict: Dictionary of emoji reactions {emoji: count}
        """
        self.reactions = json.dumps(reactions_dict) if reactions_dict else None

    def get_reactions(self) -> dict:
        """Get reactions as dictionary.

        Returns:
            Dictionary of emoji reactions or empty dict
        """
        if not self.reactions:
            return {}
        try:
            return json.loads(self.reactions)
        except json.JSONDecodeError:
            return {}

    def __repr__(self) -> str:
        """String representation of Message."""
        return (
            f"<Message(id={self.id}, chat_id={self.chat_id}, "
            f"message_id={self.message_id}, user={self.user_name}, "
            f"timestamp={self.timestamp})>"
        )

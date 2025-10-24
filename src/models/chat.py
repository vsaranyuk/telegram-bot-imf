"""Chat database model."""

from typing import Optional, List
from sqlalchemy import Integer, String, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class Chat(Base, TimestampMixin):
    """Chat entity representing a monitored Telegram chat.

    Stores configuration for chats that the bot monitors.

    Attributes:
        id: Primary key (auto-increment)
        chat_id: Telegram chat ID (unique)
        chat_name: Human-readable chat name
        enabled: Whether this chat is actively monitored
    """

    __tablename__ = "chats"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Telegram Identifier
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)

    # Chat Configuration
    chat_name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    reports: Mapped[List["Report"]] = relationship(
        "Report",
        back_populates="chat",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of Chat."""
        status = "enabled" if self.enabled else "disabled"
        return f"<Chat(id={self.id}, chat_id={self.chat_id}, name={self.chat_name}, {status})>"

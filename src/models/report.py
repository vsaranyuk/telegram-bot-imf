"""Report model for storing analysis results."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class Report(Base, TimestampMixin):
    """Report entity for storing AI analysis results.

    Stores daily analysis reports for chats including:
    - Question/answer statistics
    - Response time metrics
    - Full report content in Markdown
    """

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Statistics
    questions_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    answered_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    unanswered_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_response_time_minutes: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )

    # Report content
    report_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Delivery tracking
    sent_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="reports")

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_chat_date", "chat_id", "report_date", unique=False),
    )

    def __repr__(self) -> str:
        return (
            f"<Report(id={self.id}, chat_id={self.chat_id}, "
            f"date={self.report_date}, questions={self.questions_count})>"
        )

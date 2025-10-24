"""Base model for all database entities."""

from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all database models.

    Provides common fields and functionality for all models.
    """

    pass


class TimestampMixin:
    """Mixin for created_at timestamp field."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

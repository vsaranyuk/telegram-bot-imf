"""Pytest configuration and fixtures."""

import pytest
import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.models.base import Base
from src.models.message import Message
from src.models.chat import Chat

# Load environment variables for integration tests
load_dotenv()


@pytest.fixture(scope="function")
def db_engine():
    """Create in-memory SQLite engine for testing.

    Yields:
        SQLAlchemy engine instance
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create database session for testing.

    Args:
        db_engine: Database engine fixture

    Yields:
        SQLAlchemy session
    """
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()

    yield session

    session.rollback()
    session.close()


@pytest.fixture
def sample_chat():
    """Create a sample chat for testing.

    Returns:
        Chat instance
    """
    return Chat(
        chat_id=12345678,
        chat_name="Test Chat",
        enabled=True
    )


@pytest.fixture
def sample_message():
    """Create a sample message for testing.

    Returns:
        Message instance
    """
    return Message(
        chat_id=12345678,
        message_id=100,
        user_id=999,
        user_name="Test User",
        text="Hello, this is a test message!",
        timestamp=datetime.now()
    )


@pytest.fixture
def sample_message_with_reactions():
    """Create a sample message with reactions.

    Returns:
        Message instance with reactions
    """
    message = Message(
        chat_id=12345678,
        message_id=101,
        user_id=999,
        user_name="Test User",
        text="Message with reactions",
        timestamp=datetime.now()
    )
    message.set_reactions({"❤️": 5, "👍": 3, "💩": 1})
    return message

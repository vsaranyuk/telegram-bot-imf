"""Database configuration and session management."""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from src.config.settings import get_settings
from src.models.base import Base

logger = logging.getLogger(__name__)


# SQLite optimization: Enable WAL mode for better concurrency
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for better performance and concurrency.

    Args:
        dbapi_conn: Database API connection
        connection_record: Connection record
    """
    if "sqlite" in str(dbapi_conn):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_engine():
    """Create and configure database engine.

    Returns:
        Configured SQLAlchemy engine
    """
    settings = get_settings()

    engine = create_engine(
        settings.database_url,
        echo=False,  # Set to True for SQL query logging
        pool_pre_ping=True,  # Verify connections before using
    )

    return engine


def init_db(engine: Engine = None) -> None:
    """Initialize database by creating all tables.

    Args:
        engine: SQLAlchemy engine (creates new one if None)
    """
    if engine is None:
        engine = get_engine()

    logger.info("Initializing database...")

    # Import all models to ensure they're registered
    from src.models import Message, Chat

    # Create all tables
    Base.metadata.create_all(bind=engine)

    logger.info("Database initialized successfully")


def get_session_factory():
    """Get session factory for creating database sessions.

    Returns:
        SQLAlchemy session factory
    """
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions.

    Provides automatic session cleanup and transaction management.

    Yields:
        Database session

    Example:
        with get_db_session() as session:
            message = session.query(Message).first()
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()

    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()

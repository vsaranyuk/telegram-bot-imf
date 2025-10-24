"""Cleanup service for removing old messages."""

import logging
from datetime import datetime, timedelta

from src.repositories.message_repository import MessageRepository
from src.config.database import get_db_session
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class CleanupService:
    """Service for cleaning up old messages.

    Implements data retention policy by deleting messages
    older than configured retention period.
    """

    def __init__(self):
        """Initialize cleanup service."""
        self.settings = get_settings()

    def cleanup_old_messages(self) -> int:
        """Delete messages older than retention period.

        Returns:
            Number of messages deleted

        Example:
            service = CleanupService()
            deleted_count = service.cleanup_old_messages()
            print(f"Deleted {deleted_count} old messages")
        """
        try:
            # Calculate cutoff time based on retention policy
            retention_hours = self.settings.message_retention_hours
            cutoff_time = datetime.now() - timedelta(hours=retention_hours)

            logger.info(
                f"Starting cleanup: deleting messages older than {cutoff_time} "
                f"(retention: {retention_hours} hours)"
            )

            # Delete old messages
            with get_db_session() as session:
                message_repo = MessageRepository(session)
                deleted_count = message_repo.delete_old_messages(cutoff_time)

            logger.info(
                f"Cleanup completed: {deleted_count} messages deleted"
            )

            return deleted_count

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            return 0

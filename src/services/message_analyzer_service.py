"""Message analyzer service - orchestrates AI analysis workflow."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from src.config.settings import Settings
from src.models.message import Message
from src.repositories.message_repository import MessageRepository
from src.services.claude_api_service import AnalysisResult, ClaudeAPIService


logger = logging.getLogger(__name__)


class MessageAnalyzerService:
    """Orchestrates message analysis using Claude API.

    Coordinates:
    - Fetching messages from database
    - Sending to Claude API for analysis
    - Returning structured analysis results
    """

    def __init__(
        self, session: Session, settings: Settings
    ):
        """Initialize message analyzer service.

        Args:
            session: Database session
            settings: Application settings
        """
        self.session = session
        self.settings = settings
        self.message_repo = MessageRepository(session)
        self.claude_service = ClaudeAPIService(settings)

    async def analyze_chat_last_24h(self, chat_id: int) -> Optional[AnalysisResult]:
        """Analyze messages from the last 24 hours for a chat.

        Args:
            chat_id: Internal database chat ID

        Returns:
            AnalysisResult with questions, answers, and summary, or None if no messages

        Raises:
            Exception: If analysis fails
        """
        logger.info(f"Starting 24h analysis for chat_id={chat_id}")

        # Fetch messages from last 24 hours
        since = datetime.utcnow() - timedelta(hours=24)
        messages = self.message_repo.get_messages_since(chat_id, since)

        if not messages:
            logger.info(f"No messages found for chat_id={chat_id} in last 24h")
            return None

        logger.info(
            f"Fetched {len(messages)} messages from {since} for chat_id={chat_id}"
        )

        # Analyze messages with Claude API
        try:
            result = await self.claude_service.analyze_messages(messages)
            logger.info(
                f"Analysis successful: {result.summary.total_questions} questions detected"
            )
            return result
        except Exception as e:
            logger.error(f"Analysis failed for chat_id={chat_id}: {e}")
            raise

    async def analyze_custom_period(
        self, chat_id: int, start_time: datetime, end_time: datetime
    ) -> Optional[AnalysisResult]:
        """Analyze messages for a custom time period.

        Args:
            chat_id: Internal database chat ID
            start_time: Start of analysis period
            end_time: End of analysis period

        Returns:
            AnalysisResult with questions, answers, and summary, or None if no messages

        Raises:
            Exception: If analysis fails
        """
        logger.info(
            f"Starting custom period analysis for chat_id={chat_id} "
            f"from {start_time} to {end_time}"
        )

        # Fetch messages for period
        messages = self.message_repo.get_messages_between(
            chat_id, start_time, end_time
        )

        if not messages:
            logger.info(
                f"No messages found for chat_id={chat_id} "
                f"between {start_time} and {end_time}"
            )
            return None

        logger.info(f"Fetched {len(messages)} messages for analysis")

        # Analyze messages with Claude API
        try:
            result = await self.claude_service.analyze_messages(messages)
            logger.info(
                f"Analysis successful: {result.summary.total_questions} questions detected"
            )
            return result
        except Exception as e:
            logger.error(
                f"Analysis failed for chat_id={chat_id} "
                f"({start_time} to {end_time}): {e}"
            )
            raise

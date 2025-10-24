"""Unit tests for MessageAnalyzerService."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.message_analyzer_service import MessageAnalyzerService
from src.services.claude_api_service import AnalysisResult, AnalysisSummary, QuestionAnalysis
from src.models.message import Message


@pytest.fixture
def mock_session():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.anthropic_api_key = "test-key"
    return settings


@pytest.fixture
def analyzer_service(mock_session, mock_settings):
    """Create MessageAnalyzerService with mocked dependencies."""
    return MessageAnalyzerService(mock_session, mock_settings)


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    now = datetime.now(timezone.utc)
    return [
        Message(
            chat_id=1,
            message_id=1,
            user_id=100,
            user_name="Alice",
            text="When will the report be ready?",
            timestamp=now - timedelta(hours=2),
        ),
        Message(
            chat_id=1,
            message_id=2,
            user_id=101,
            user_name="Bob",
            text="The report will be ready tomorrow morning",
            timestamp=now - timedelta(hours=1),
        ),
    ]


@pytest.fixture
def sample_analysis_result():
    """Create sample analysis result."""
    return AnalysisResult(
        questions=[
            QuestionAnalysis(
                message_id=1,
                text="When will the report be ready?",
                category="business",
                is_answered=True,
                answer_message_id=2,
                response_time_minutes=60.0,
            )
        ],
        answers=[],
        summary=AnalysisSummary(
            total_questions=1,
            answered=1,
            unanswered=0,
            avg_response_time_minutes=60.0,
        ),
    )


class TestMessageAnalyzerService:
    """Tests for MessageAnalyzerService."""

    @pytest.mark.asyncio
    async def test_analyze_chat_last_24h_success(
        self, analyzer_service, sample_messages, sample_analysis_result
    ):
        """Test successful analysis of last 24h messages."""
        # Mock message repository
        analyzer_service.message_repo.get_messages_since = MagicMock(
            return_value=sample_messages
        )

        # Mock Claude service
        analyzer_service.claude_service.analyze_messages = AsyncMock(
            return_value=sample_analysis_result
        )

        # Execute analysis
        result = await analyzer_service.analyze_chat_last_24h(chat_id=1)

        # Verify
        assert result is not None
        assert result.summary.total_questions == 1
        assert result.summary.answered == 1
        assert result.summary.unanswered == 0

        # Verify message_repo called with correct time window
        analyzer_service.message_repo.get_messages_since.assert_called_once()
        call_args = analyzer_service.message_repo.get_messages_since.call_args
        assert call_args[0][0] == 1  # chat_id

        # Verify Claude service called
        analyzer_service.claude_service.analyze_messages.assert_awaited_once_with(
            sample_messages
        )

    @pytest.mark.asyncio
    async def test_analyze_chat_last_24h_no_messages(self, analyzer_service):
        """Test analysis when no messages found."""
        # Mock empty message list
        analyzer_service.message_repo.get_messages_since = MagicMock(return_value=[])

        # Mock Claude service (should not be called)
        analyzer_service.claude_service.analyze_messages = AsyncMock()

        # Execute analysis
        result = await analyzer_service.analyze_chat_last_24h(chat_id=1)

        # Verify returns None
        assert result is None

        # Verify Claude service not called
        analyzer_service.claude_service.analyze_messages.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_chat_last_24h_api_error(
        self, analyzer_service, sample_messages
    ):
        """Test handling of Claude API errors."""
        # Mock message repository
        analyzer_service.message_repo.get_messages_since = MagicMock(
            return_value=sample_messages
        )

        # Mock Claude service to raise error
        analyzer_service.claude_service.analyze_messages = AsyncMock(
            side_effect=Exception("API Error")
        )

        # Execute and verify exception propagates
        with pytest.raises(Exception, match="API Error"):
            await analyzer_service.analyze_chat_last_24h(chat_id=1)

    @pytest.mark.asyncio
    async def test_analyze_custom_period_success(
        self, analyzer_service, sample_messages, sample_analysis_result
    ):
        """Test successful analysis for custom time period."""
        start_time = datetime(2025, 10, 24, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 10, 24, 23, 59, tzinfo=timezone.utc)

        # Mock message repository
        analyzer_service.message_repo.get_messages_between = MagicMock(
            return_value=sample_messages
        )

        # Mock Claude service
        analyzer_service.claude_service.analyze_messages = AsyncMock(
            return_value=sample_analysis_result
        )

        # Execute analysis
        result = await analyzer_service.analyze_custom_period(
            chat_id=1, start_time=start_time, end_time=end_time
        )

        # Verify
        assert result is not None
        assert result.summary.total_questions == 1

        # Verify repository called with correct parameters
        analyzer_service.message_repo.get_messages_between.assert_called_once_with(
            1, start_time, end_time
        )

        # Verify Claude service called
        analyzer_service.claude_service.analyze_messages.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_analyze_custom_period_no_messages(self, analyzer_service):
        """Test custom period analysis when no messages found."""
        start_time = datetime(2025, 10, 24, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 10, 24, 23, 59, tzinfo=timezone.utc)

        # Mock empty message list
        analyzer_service.message_repo.get_messages_between = MagicMock(return_value=[])

        # Mock Claude service (should not be called)
        analyzer_service.claude_service.analyze_messages = AsyncMock()

        # Execute analysis
        result = await analyzer_service.analyze_custom_period(
            chat_id=1, start_time=start_time, end_time=end_time
        )

        # Verify returns None
        assert result is None

        # Verify Claude service not called
        analyzer_service.claude_service.analyze_messages.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_custom_period_api_error(
        self, analyzer_service, sample_messages
    ):
        """Test handling of API errors in custom period analysis."""
        start_time = datetime(2025, 10, 24, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 10, 24, 23, 59, tzinfo=timezone.utc)

        # Mock message repository
        analyzer_service.message_repo.get_messages_between = MagicMock(
            return_value=sample_messages
        )

        # Mock Claude service to raise error
        analyzer_service.claude_service.analyze_messages = AsyncMock(
            side_effect=Exception("API Error")
        )

        # Execute and verify exception propagates
        with pytest.raises(Exception, match="API Error"):
            await analyzer_service.analyze_custom_period(
                chat_id=1, start_time=start_time, end_time=end_time
            )

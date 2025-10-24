"""Tests for ReportDeliveryService - focusing on formatting and business logic."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.services.report_delivery_service import ReportDeliveryService
from src.services.claude_api_service import AnalysisResult, AnalysisSummary, QuestionAnalysis


class TestReportFormatting:
    """Test suite for report formatting logic."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.telegram_bot_token = "test_token"
        settings.anthropic_api_key = "test_key"
        return settings

    @pytest.fixture
    def service(self, mock_settings):
        """Create ReportDeliveryService instance with mocks."""
        with patch('src.services.report_delivery_service.Bot'):
            service = ReportDeliveryService(settings=mock_settings)
            return service

    @pytest.fixture
    def sample_analysis(self):
        """Create sample analysis result."""
        return AnalysisResult(
            questions=[
                QuestionAnalysis(
                    message_id=123,
                    text="What is the status?",
                    category="business",
                    is_answered=True,
                    answer_message_id=124,
                    response_time_minutes=15.5
                ),
                QuestionAnalysis(
                    message_id=125,
                    text="Can you help?",
                    category="other",
                    is_answered=False
                )
            ],
            answers=[],
            summary=AnalysisSummary(
                total_questions=2,
                answered=1,
                unanswered=1,
                avg_response_time_minutes=15.5
            )
        )

    def test_format_report_contains_required_elements(self, service, sample_analysis):
        """Test that formatted report contains all required elements."""
        report = service._format_report(sample_analysis, "Test Chat")

        # Check header elements
        assert "#IMFReport" in report
        assert "Test Chat" in report
        assert "Daily Communication Report" in report

        # Check summary statistics
        assert "Total Questions: 2" in report
        assert "Answered: 1" in report
        assert "Unanswered: 1" in report
        assert "15.5 minutes" in report

        # Check questions are included
        assert "What is the status?" in report
        assert "Can you help?" in report

        # Check status indicators
        assert "✅ Answered" in report
        assert "⏳ Pending" in report

    def test_format_report_truncates_long_content(self, service, sample_analysis):
        """Test that long reports are truncated to Telegram limit."""
        # Create a very long question text
        long_text = "x" * 5000
        sample_analysis.questions[0].text = long_text

        report = service._format_report(sample_analysis, "Test Chat")

        # Check that report doesn't exceed Telegram limit
        assert len(report) <= service.MAX_MESSAGE_LENGTH
        assert "[Report truncated due to length limit]" in report

    def test_format_report_without_avg_response_time(self, service):
        """Test report formatting when average response time is None."""
        analysis = AnalysisResult(
            questions=[],
            answers=[],
            summary=AnalysisSummary(
                total_questions=0,
                answered=0,
                unanswered=0,
                avg_response_time_minutes=None
            )
        )

        report = service._format_report(analysis, "Test Chat")

        # Should not contain response time line
        assert "Avg Response Time" not in report

    @pytest.mark.asyncio
    async def test_send_telegram_report_success(self, service):
        """Test successful Telegram message sending."""
        service.bot.send_message = AsyncMock()

        result = await service._send_telegram_report(12345, "Test report")

        assert result is True
        service.bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_telegram_report_rate_limit_retry(self, service):
        """Test retry logic on rate limit."""
        from telegram.error import RetryAfter

        # First call raises RetryAfter, second succeeds
        service.bot.send_message = AsyncMock(
            side_effect=[RetryAfter(retry_after=1), None]
        )

        result = await service._send_telegram_report(12345, "Test report")

        assert result is True
        assert service.bot.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_send_telegram_report_failure_after_retries(self, service):
        """Test failure after exhausting retries."""
        from telegram.error import TelegramError

        service.bot.send_message = AsyncMock(
            side_effect=TelegramError("Network error")
        )

        result = await service._send_telegram_report(12345, "Test report")

        assert result is False
        assert service.bot.send_message.call_count == service.MAX_RETRIES

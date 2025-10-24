"""Unit tests for ReportGeneratorService."""

from datetime import date
import pytest

from src.services.claude_api_service import (
    AnalysisResult,
    AnalysisSummary,
    QuestionAnalysis,
    AnswerAnalysis,
)
from src.services.report_generator_service import ReportGeneratorService


class TestReportGeneratorService:
    """Test cases for ReportGeneratorService."""

    @pytest.fixture
    def service(self):
        """Create ReportGeneratorService instance."""
        return ReportGeneratorService()

    @pytest.fixture
    def sample_analysis(self):
        """Create sample analysis result for testing."""
        return AnalysisResult(
            questions=[
                QuestionAnalysis(
                    message_id=1,
                    text="What is the deadline?",
                    category="business",
                    is_answered=True,
                    answer_message_id=2,
                    response_time_minutes=30.0,
                ),
                QuestionAnalysis(
                    message_id=3,
                    text="How do I configure this?",
                    category="technical",
                    is_answered=True,
                    answer_message_id=4,
                    response_time_minutes=120.0,
                ),
                QuestionAnalysis(
                    message_id=5,
                    text="Can someone help?",
                    category="other",
                    is_answered=False,
                    answer_message_id=None,
                    response_time_minutes=None,
                ),
            ],
            answers=[
                AnswerAnalysis(
                    message_id=2, text="Friday at 5pm", answers_to_message_id=1
                ),
                AnswerAnalysis(
                    message_id=4,
                    text="You need to edit the config file",
                    answers_to_message_id=3,
                ),
            ],
            summary=AnalysisSummary(
                total_questions=3,
                answered=2,
                unanswered=1,
                avg_response_time_minutes=75.0,
            ),
        )

    def test_categorize_response_time_fast(self, service):
        """Test response time categorization - fast (<1h)."""
        assert service._categorize_response_time(30) == "Fast response (<1h)"
        assert service._categorize_response_time(59) == "Fast response (<1h)"

    def test_categorize_response_time_medium(self, service):
        """Test response time categorization - medium (1-4h)."""
        assert service._categorize_response_time(60) == "Medium response (1-4h)"
        assert service._categorize_response_time(120) == "Medium response (1-4h)"
        assert service._categorize_response_time(239) == "Medium response (1-4h)"

    def test_categorize_response_time_slow(self, service):
        """Test response time categorization - slow (4-24h)."""
        assert service._categorize_response_time(240) == "Slow response (4-24h)"
        assert service._categorize_response_time(720) == "Slow response (4-24h)"
        assert service._categorize_response_time(1439) == "Slow response (4-24h)"

    def test_categorize_response_time_very_slow(self, service):
        """Test response time categorization - very slow (>24h)."""
        assert service._categorize_response_time(1440) == "Very slow response (>24h)"
        assert service._categorize_response_time(2000) == "Very slow response (>24h)"

    def test_categorize_response_time_unanswered(self, service):
        """Test response time categorization - unanswered."""
        assert service._categorize_response_time(None) == "Unanswered"

    def test_format_duration_minutes(self, service):
        """Test duration formatting - minutes only."""
        assert service._format_duration(30) == "30m"
        assert service._format_duration(59) == "59m"

    def test_format_duration_hours(self, service):
        """Test duration formatting - hours."""
        assert service._format_duration(60) == "1h"
        assert service._format_duration(120) == "2h"

    def test_format_duration_hours_minutes(self, service):
        """Test duration formatting - hours and minutes."""
        assert service._format_duration(90) == "1h 30m"
        assert service._format_duration(135) == "2h 15m"

    def test_format_report_structure(self, service, sample_analysis):
        """Test that generated report has all required sections."""
        report = service.format_report(
            sample_analysis, "Test Chat", date(2025, 10, 24)
        )

        # Check all required sections are present
        assert "# Daily Communication Report #IMFReport" in report
        assert "**Chat:** Test Chat" in report
        assert "**Date:** 2025-10-24" in report
        assert "## Summary" in report
        assert "## Response Time Breakdown" in report
        assert "## Unanswered Questions" in report
        assert "## Top Reactions" in report

    def test_format_report_summary_stats(self, service, sample_analysis):
        """Test that summary section contains correct statistics."""
        report = service.format_report(
            sample_analysis, "Test Chat", date(2025, 10, 24)
        )

        assert "**Total Questions:** 3" in report
        assert "**Answered:** 2" in report
        assert "**Unanswered:** 1" in report
        assert "1h 15m" in report  # avg response time

    def test_format_report_response_time_breakdown(self, service, sample_analysis):
        """Test response time breakdown section."""
        report = service.format_report(
            sample_analysis, "Test Chat", date(2025, 10, 24)
        )

        assert "**Fast (<1h):** 1" in report  # 30 min question
        assert "**Medium (1-4h):** 1" in report  # 120 min question
        assert "**Slow (4-24h):** 0" in report
        assert "**Very Slow (>24h):** 0" in report

    def test_format_report_unanswered_questions(self, service, sample_analysis):
        """Test unanswered questions section."""
        report = service.format_report(
            sample_analysis, "Test Chat", date(2025, 10, 24)
        )

        assert "## Unanswered Questions" in report
        assert "Can someone help?" in report
        assert "❓ Other" in report  # category badge

    def test_format_report_all_answered(self, service):
        """Test report when all questions are answered."""
        analysis = AnalysisResult(
            questions=[
                QuestionAnalysis(
                    message_id=1,
                    text="Test question?",
                    category="technical",
                    is_answered=True,
                    answer_message_id=2,
                    response_time_minutes=30.0,
                )
            ],
            answers=[
                AnswerAnalysis(
                    message_id=2, text="Test answer", answers_to_message_id=1
                )
            ],
            summary=AnalysisSummary(
                total_questions=1,
                answered=1,
                unanswered=0,
                avg_response_time_minutes=30.0,
            ),
        )

        report = service.format_report(analysis, "Test Chat", date(2025, 10, 24))

        assert "All questions have been answered!" in report

    def test_format_report_no_questions(self, service):
        """Test report when there are no questions."""
        analysis = AnalysisResult(
            questions=[],
            answers=[],
            summary=AnalysisSummary(
                total_questions=0,
                answered=0,
                unanswered=0,
                avg_response_time_minutes=None,
            ),
        )

        report = service.format_report(analysis, "Test Chat", date(2025, 10, 24))

        assert "**Total Questions:** 0" in report
        assert "All questions have been answered!" in report

    def test_format_report_markdown_escaping(self, service):
        """Test that special Markdown characters are escaped in questions."""
        analysis = AnalysisResult(
            questions=[
                QuestionAnalysis(
                    message_id=1,
                    text="What is *this* _thing_?",
                    category="technical",
                    is_answered=False,
                    answer_message_id=None,
                    response_time_minutes=None,
                )
            ],
            answers=[],
            summary=AnalysisSummary(
                total_questions=1, answered=0, unanswered=1, avg_response_time_minutes=None
            ),
        )

        report = service.format_report(analysis, "Test Chat", date(2025, 10, 24))

        # Check that special characters are escaped
        assert "\\*this\\*" in report or "*this*" not in report
        assert "\\_thing\\_" in report or "_thing_" not in report

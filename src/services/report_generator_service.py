"""Report generator service - formats analysis results into Markdown reports."""

import logging
from datetime import date, datetime
from typing import List, Optional

from src.services.claude_api_service import (
    AnalysisResult,
    QuestionAnalysis,
)


logger = logging.getLogger(__name__)


class ReportGeneratorService:
    """Generates formatted Markdown reports from analysis results.

    Creates structured reports with:
    - Header with date and chat name
    - Summary statistics
    - Response time breakdown
    - Unanswered questions list
    - Top reactions (if available)
    """

    @staticmethod
    def _categorize_response_time(minutes: Optional[float]) -> str:
        """Categorize response time into fast/medium/slow/very slow.

        Args:
            minutes: Response time in minutes

        Returns:
            Category string
        """
        if minutes is None:
            return "Unanswered"
        elif minutes < 60:  # < 1 hour
            return "Fast response (<1h)"
        elif minutes < 240:  # 1-4 hours
            return "Medium response (1-4h)"
        elif minutes < 1440:  # 4-24 hours
            return "Slow response (4-24h)"
        else:  # > 24 hours
            return "Very slow response (>24h)"

    @staticmethod
    def _format_duration(minutes: float) -> str:
        """Format duration in minutes to human-readable string.

        Args:
            minutes: Duration in minutes

        Returns:
            Formatted duration string (e.g., "2h 30m", "45m")
        """
        if minutes < 60:
            return f"{int(minutes)}m"

        hours = int(minutes // 60)
        mins = int(minutes % 60)

        if mins == 0:
            return f"{hours}h"
        return f"{hours}h {mins}m"

    def format_report(
        self,
        analysis: AnalysisResult,
        chat_name: str,
        report_date: date,
    ) -> str:
        """Generate formatted Markdown report from analysis results.

        Args:
            analysis: Analysis results from Claude API
            chat_name: Name of the chat
            report_date: Date of the report

        Returns:
            Formatted Markdown report string
        """
        logger.info(f"Generating report for {chat_name} on {report_date}")

        # Build report sections
        sections = []

        # Header
        sections.append(self._format_header(chat_name, report_date))

        # Summary
        sections.append(self._format_summary(analysis))

        # Response Time Stats
        sections.append(self._format_response_time_stats(analysis))

        # Unanswered Questions
        sections.append(self._format_unanswered_questions(analysis))

        # Top Reactions (placeholder for future implementation)
        sections.append(self._format_top_reactions())

        # Join all sections
        report = "\n\n".join(sections)

        logger.info(f"Report generated: {len(report)} characters")
        return report

    def _format_header(self, chat_name: str, report_date: date) -> str:
        """Format report header.

        Args:
            chat_name: Chat name
            report_date: Report date

        Returns:
            Formatted header section
        """
        return f"""# Daily Communication Report #IMFReport

**Chat:** {chat_name}
**Date:** {report_date.strftime('%Y-%m-%d')}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

    def _format_summary(self, analysis: AnalysisResult) -> str:
        """Format summary statistics section.

        Args:
            analysis: Analysis results

        Returns:
            Formatted summary section
        """
        summary = analysis.summary
        answer_rate = (
            f"{(summary.answered / summary.total_questions * 100):.1f}%"
            if summary.total_questions > 0
            else "N/A"
        )

        avg_time = (
            self._format_duration(summary.avg_response_time_minutes)
            if summary.avg_response_time_minutes
            else "N/A"
        )

        return f"""## Summary

📊 **Total Questions:** {summary.total_questions}
✅ **Answered:** {summary.answered} ({answer_rate})
❌ **Unanswered:** {summary.unanswered}
⏱️ **Avg Response Time:** {avg_time}"""

    def _format_response_time_stats(self, analysis: AnalysisResult) -> str:
        """Format response time breakdown section.

        Args:
            analysis: Analysis results

        Returns:
            Formatted response time stats section
        """
        # Categorize all answered questions by response time
        fast = []
        medium = []
        slow = []
        very_slow = []

        for question in analysis.questions:
            if question.is_answered and question.response_time_minutes is not None:
                category = self._categorize_response_time(
                    question.response_time_minutes
                )
                if "Fast" in category:
                    fast.append(question)
                elif "Medium" in category:
                    medium.append(question)
                elif "Slow" in category and "Very" not in category:
                    slow.append(question)
                elif "Very slow" in category:
                    very_slow.append(question)

        total_answered = len(fast) + len(medium) + len(slow) + len(very_slow)

        return f"""## Response Time Breakdown

⚡ **Fast (<1h):** {len(fast)} questions
🕐 **Medium (1-4h):** {len(medium)} questions
🐌 **Slow (4-24h):** {len(slow)} questions
🦥 **Very Slow (>24h):** {len(very_slow)} questions"""

    def _format_unanswered_questions(self, analysis: AnalysisResult) -> str:
        """Format unanswered questions section.

        Args:
            analysis: Analysis results

        Returns:
            Formatted unanswered questions section
        """
        unanswered = [q for q in analysis.questions if not q.is_answered]

        if not unanswered:
            return "## Unanswered Questions\n\n✨ All questions have been answered!"

        lines = ["## Unanswered Questions\n"]

        for i, question in enumerate(unanswered, 1):
            # Escape Markdown special characters in question text
            text = question.text.replace("_", "\\_").replace("*", "\\*")
            category_badge = {
                "technical": "🔧 Technical",
                "business": "💼 Business",
                "other": "❓ Other",
            }.get(question.category.lower(), "❓ Other")

            lines.append(f"{i}. [{category_badge}] {text}")

        return "\n".join(lines)

    def _format_top_reactions(self) -> str:
        """Format top reactions section.

        Returns:
            Formatted top reactions section (placeholder for future)
        """
        # TODO: Implement reaction tracking
        return """## Top Reactions

_Reaction tracking coming soon_"""

"""Repository for Report entity operations."""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.report import Report


class ReportRepository:
    """Repository for managing Report entities.

    Provides CRUD operations and queries for analysis reports.
    """

    def __init__(self, session: Session):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def create(
        self,
        chat_id: int,
        report_date: date,
        questions_count: Optional[int] = None,
        answered_count: Optional[int] = None,
        unanswered_count: Optional[int] = None,
        avg_response_time_minutes: Optional[float] = None,
        report_content: Optional[str] = None,
    ) -> Report:
        """Create a new report.

        Args:
            chat_id: ID of the chat this report belongs to
            report_date: Date of the report
            questions_count: Total number of questions identified
            answered_count: Number of answered questions
            unanswered_count: Number of unanswered questions
            avg_response_time_minutes: Average response time in minutes
            report_content: Full report content in Markdown

        Returns:
            Created Report entity
        """
        report = Report(
            chat_id=chat_id,
            report_date=report_date,
            questions_count=questions_count,
            answered_count=answered_count,
            unanswered_count=unanswered_count,
            avg_response_time_minutes=avg_response_time_minutes,
            report_content=report_content,
        )
        self.session.add(report)
        self.session.commit()
        self.session.refresh(report)
        return report

    def get_by_id(self, report_id: int) -> Optional[Report]:
        """Get report by ID.

        Args:
            report_id: Report ID to retrieve

        Returns:
            Report if found, None otherwise
        """
        stmt = select(Report).where(Report.id == report_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_chat_and_date(
        self, chat_id: int, report_date: date
    ) -> Optional[Report]:
        """Get report for a specific chat and date.

        Args:
            chat_id: Chat ID
            report_date: Report date

        Returns:
            Report if found, None otherwise
        """
        stmt = (
            select(Report)
            .where(Report.chat_id == chat_id)
            .where(Report.report_date == report_date)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_recent_by_chat(
        self, chat_id: int, limit: int = 10
    ) -> List[Report]:
        """Get recent reports for a chat.

        Args:
            chat_id: Chat ID
            limit: Maximum number of reports to return

        Returns:
            List of recent reports, ordered by date descending
        """
        stmt = (
            select(Report)
            .where(Report.chat_id == chat_id)
            .order_by(Report.report_date.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def update_sent_at(self, report_id: int, sent_at: datetime) -> Optional[Report]:
        """Mark report as sent.

        Args:
            report_id: Report ID
            sent_at: Timestamp when report was sent

        Returns:
            Updated Report if found, None otherwise
        """
        report = self.get_by_id(report_id)
        if report:
            report.sent_at = sent_at
            self.session.commit()
            self.session.refresh(report)
        return report

    def delete(self, report_id: int) -> bool:
        """Delete a report.

        Args:
            report_id: Report ID to delete

        Returns:
            True if deleted, False if not found
        """
        report = self.get_by_id(report_id)
        if report:
            self.session.delete(report)
            self.session.commit()
            return True
        return False

    def delete_old_reports(
        self, chat_id: int, before_date: date
    ) -> int:
        """Delete reports older than specified date for a chat.

        Args:
            chat_id: Chat ID
            before_date: Delete reports before this date

        Returns:
            Number of reports deleted
        """
        stmt = (
            select(Report)
            .where(Report.chat_id == chat_id)
            .where(Report.report_date < before_date)
        )
        reports = self.session.execute(stmt).scalars().all()
        count = len(reports)

        for report in reports:
            self.session.delete(report)

        self.session.commit()
        return count

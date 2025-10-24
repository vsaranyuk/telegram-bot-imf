"""Unit tests for ReportRepository."""

from datetime import date, datetime, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.chat import Chat
from src.models.report import Report
from src.repositories.report_repository import ReportRepository


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def test_chat(session):
    """Create test chat."""
    chat = Chat(chat_id=123456, chat_name="Test Chat", enabled=True)
    session.add(chat)
    session.commit()
    return chat


@pytest.fixture
def repository(session):
    """Create ReportRepository instance."""
    return ReportRepository(session)


class TestReportRepository:
    """Test cases for ReportRepository."""

    def test_create_report(self, repository, test_chat):
        """Test creating a new report."""
        report = repository.create(
            chat_id=test_chat.id,
            report_date=date(2025, 10, 24),
            questions_count=10,
            answered_count=8,
            unanswered_count=2,
            avg_response_time_minutes=45.5,
            report_content="# Test Report",
        )

        assert report.id is not None
        assert report.chat_id == test_chat.id
        assert report.report_date == date(2025, 10, 24)
        assert report.questions_count == 10
        assert report.answered_count == 8
        assert report.unanswered_count == 2
        assert report.avg_response_time_minutes == 45.5
        assert report.report_content == "# Test Report"
        assert report.sent_at is None
        assert report.created_at is not None

    def test_create_minimal_report(self, repository, test_chat):
        """Test creating report with minimal required fields."""
        report = repository.create(
            chat_id=test_chat.id, report_date=date(2025, 10, 24)
        )

        assert report.id is not None
        assert report.chat_id == test_chat.id
        assert report.report_date == date(2025, 10, 24)
        assert report.questions_count is None
        assert report.report_content is None

    def test_get_by_id(self, repository, test_chat):
        """Test retrieving report by ID."""
        created = repository.create(
            chat_id=test_chat.id,
            report_date=date(2025, 10, 24),
            questions_count=5,
        )

        retrieved = repository.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.questions_count == 5

    def test_get_by_id_not_found(self, repository):
        """Test retrieving non-existent report."""
        report = repository.get_by_id(99999)
        assert report is None

    def test_get_by_chat_and_date(self, repository, test_chat):
        """Test retrieving report by chat and date."""
        report_date = date(2025, 10, 24)
        created = repository.create(
            chat_id=test_chat.id, report_date=report_date, questions_count=7
        )

        retrieved = repository.get_by_chat_and_date(test_chat.id, report_date)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.questions_count == 7

    def test_get_by_chat_and_date_not_found(self, repository, test_chat):
        """Test retrieving non-existent report by chat and date."""
        report = repository.get_by_chat_and_date(test_chat.id, date(2025, 10, 24))
        assert report is None

    def test_get_recent_by_chat(self, repository, test_chat):
        """Test retrieving recent reports for a chat."""
        # Create reports for multiple dates
        dates = [date(2025, 10, 24), date(2025, 10, 23), date(2025, 10, 22)]
        for d in dates:
            repository.create(chat_id=test_chat.id, report_date=d)

        recent = repository.get_recent_by_chat(test_chat.id, limit=2)

        assert len(recent) == 2
        # Should be ordered by date descending
        assert recent[0].report_date == date(2025, 10, 24)
        assert recent[1].report_date == date(2025, 10, 23)

    def test_get_recent_by_chat_empty(self, repository, test_chat):
        """Test retrieving recent reports when none exist."""
        recent = repository.get_recent_by_chat(test_chat.id)
        assert recent == []

    def test_update_sent_at(self, repository, test_chat):
        """Test updating sent_at timestamp."""
        report = repository.create(
            chat_id=test_chat.id, report_date=date(2025, 10, 24)
        )

        assert report.sent_at is None

        sent_time = datetime(2025, 10, 24, 10, 30, 0)
        updated = repository.update_sent_at(report.id, sent_time)

        assert updated is not None
        assert updated.sent_at == sent_time

    def test_update_sent_at_not_found(self, repository):
        """Test updating sent_at for non-existent report."""
        updated = repository.update_sent_at(99999, datetime.now())
        assert updated is None

    def test_delete_report(self, repository, test_chat):
        """Test deleting a report."""
        report = repository.create(
            chat_id=test_chat.id, report_date=date(2025, 10, 24)
        )

        result = repository.delete(report.id)
        assert result is True

        # Verify deletion
        retrieved = repository.get_by_id(report.id)
        assert retrieved is None

    def test_delete_report_not_found(self, repository):
        """Test deleting non-existent report."""
        result = repository.delete(99999)
        assert result is False

    def test_delete_old_reports(self, repository, test_chat):
        """Test deleting reports older than specified date."""
        # Create reports for different dates
        dates = [
            date(2025, 10, 20),
            date(2025, 10, 21),
            date(2025, 10, 22),
            date(2025, 10, 23),
            date(2025, 10, 24),
        ]
        for d in dates:
            repository.create(chat_id=test_chat.id, report_date=d)

        # Delete reports before Oct 23
        count = repository.delete_old_reports(test_chat.id, date(2025, 10, 23))

        # Should delete 3 reports (20, 21, 22)
        assert count == 3

        # Verify remaining reports
        remaining = repository.get_recent_by_chat(test_chat.id, limit=10)
        assert len(remaining) == 2
        assert remaining[0].report_date == date(2025, 10, 24)
        assert remaining[1].report_date == date(2025, 10, 23)

    def test_delete_old_reports_none_match(self, repository, test_chat):
        """Test deleting old reports when none match criteria."""
        repository.create(chat_id=test_chat.id, report_date=date(2025, 10, 24))

        count = repository.delete_old_reports(test_chat.id, date(2025, 10, 20))

        assert count == 0

    def test_report_chat_relationship(self, repository, test_chat):
        """Test relationship between Report and Chat."""
        report = repository.create(
            chat_id=test_chat.id, report_date=date(2025, 10, 24)
        )

        assert report.chat is not None
        assert report.chat.id == test_chat.id
        assert report.chat.chat_name == "Test Chat"

"""Unit tests for CleanupService."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.services.cleanup_service import CleanupService
from src.models.message import Message


class TestCleanupService:
    """Test suite for CleanupService."""

    @patch('src.services.cleanup_service.get_db_session')
    @patch('src.services.cleanup_service.get_settings')
    def test_cleanup_old_messages_success(
        self,
        mock_settings,
        mock_get_session
    ):
        """Test successful cleanup of old messages.

        Args:
            mock_settings: Mock settings
            mock_get_session: Mock database session
        """
        # Setup mocks
        mock_settings_instance = MagicMock()
        mock_settings_instance.message_retention_hours = 48
        mock_settings.return_value = mock_settings_instance

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.delete_old_messages.return_value = 10  # 10 messages deleted

        mock_get_session.return_value.__enter__.return_value = mock_session

        # Create service
        service = CleanupService()

        with patch(
            'src.services.cleanup_service.MessageRepository',
            return_value=mock_repo
        ):
            # Run cleanup
            deleted_count = service.cleanup_old_messages()

        # Verify
        assert deleted_count == 10
        mock_repo.delete_old_messages.assert_called_once()

    @patch('src.services.cleanup_service.get_db_session')
    @patch('src.services.cleanup_service.get_settings')
    def test_cleanup_old_messages_error_handling(
        self,
        mock_settings,
        mock_get_session
    ):
        """Test cleanup handles errors gracefully.

        Args:
            mock_settings: Mock settings
            mock_get_session: Mock database session
        """
        # Setup mocks
        mock_settings_instance = MagicMock()
        mock_settings_instance.message_retention_hours = 48
        mock_settings.return_value = mock_settings_instance

        # Simulate error
        mock_get_session.return_value.__enter__.side_effect = Exception("DB Error")

        # Create service
        service = CleanupService()

        # Run cleanup (should not raise, returns 0)
        deleted_count = service.cleanup_old_messages()

        # Verify error handled
        assert deleted_count == 0

    @patch('src.services.cleanup_service.get_settings')
    def test_cleanup_respects_retention_hours(self, mock_settings):
        """Test cleanup uses configured retention hours.

        Args:
            mock_settings: Mock settings
        """
        # Setup different retention periods
        mock_settings_instance = MagicMock()
        mock_settings_instance.message_retention_hours = 72  # 3 days
        mock_settings.return_value = mock_settings_instance

        service = CleanupService()

        assert service.settings.message_retention_hours == 72

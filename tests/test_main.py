"""Tests for main.py - BotApplication conditional startup logic."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from src.main import BotApplication
from src.config.settings import Settings


@pytest.fixture
def mock_settings_polling():
    """Create mock settings for polling mode."""
    return Settings(
        telegram_bot_token="test_token",
        anthropic_api_key="test_api_key",
        environment="development",
        webhook_enabled=False,
        webhook_url="",
        webhook_secret_token="",
        webhook_port=8080
    )


@pytest.fixture
def mock_settings_webhook():
    """Create mock settings for webhook mode."""
    return Settings(
        telegram_bot_token="test_token",
        anthropic_api_key="test_api_key",
        environment="production",
        webhook_enabled=True,
        webhook_url="https://example.com/webhook",
        webhook_secret_token="test_secret_token",
        webhook_port=8080
    )


@pytest.fixture
def mock_settings_production_polling():
    """Create mock settings for production polling mode."""
    return Settings(
        telegram_bot_token="test_token",
        anthropic_api_key="test_api_key",
        environment="production",
        webhook_enabled=False,
        webhook_url="",
        webhook_secret_token="",
        webhook_port=8080
    )


class TestBotApplicationInit:
    """Tests for BotApplication initialization."""

    @patch('src.main.get_settings')
    @patch('src.main.TelegramBotService')
    @patch('src.main.MessageCollectorService')
    @patch('src.main.CleanupService')
    @patch('src.main.ReportDeliveryService')
    @patch('src.main.AsyncIOScheduler')
    @patch('src.main.HealthCheckServer')
    def test_init_initializes_webhook_server_none(
        self,
        mock_health_server,
        mock_scheduler,
        mock_report_delivery,
        mock_cleanup,
        mock_message_collector,
        mock_bot_service,
        mock_get_settings,
        mock_settings_polling
    ):
        """Test that webhook_server is initialized as None."""
        mock_get_settings.return_value = mock_settings_polling

        app = BotApplication()

        assert app.webhook_server is None
        assert app.application is None
        assert app.running is False


class TestBotApplicationStartWebhookMode:
    """Tests for BotApplication start in webhook mode."""

    @pytest.mark.asyncio
    @patch('src.main.init_db')
    @patch('src.main.get_settings')
    async def test_start_webhook_mode_initializes_webhook_server(
        self,
        mock_get_settings,
        mock_init_db,
        mock_settings_webhook
    ):
        """Test that webhook mode initializes WebhookServer and registers webhook."""
        mock_get_settings.return_value = mock_settings_webhook

        with patch('src.main.TelegramBotService') as mock_bot_service_class, \
             patch('src.main.MessageCollectorService'), \
             patch('src.main.CleanupService'), \
             patch('src.main.ReportDeliveryService'), \
             patch('src.main.AsyncIOScheduler') as mock_scheduler_class, \
             patch('src.main.HealthCheckServer') as mock_health_server_class, \
             patch('src.main.WebhookServer') as mock_webhook_server_class:

            # Setup mocks
            mock_application = MagicMock()
            mock_application.start = AsyncMock()
            mock_application.stop = AsyncMock()
            mock_application.__aenter__ = AsyncMock(return_value=mock_application)
            mock_application.__aexit__ = AsyncMock()

            mock_bot_service = Mock()
            mock_bot_service.setup = Mock(return_value=mock_application)
            mock_bot_service.setup_webhook = AsyncMock()
            mock_bot_service.remove_webhook = AsyncMock()
            mock_bot_service_class.return_value = mock_bot_service

            mock_scheduler = Mock()
            mock_scheduler.start = Mock()
            mock_scheduler.running = False
            mock_scheduler_class.return_value = mock_scheduler

            mock_health_server = Mock()
            mock_health_server.start = AsyncMock()
            mock_health_server.stop = AsyncMock()
            mock_health_server_class.return_value = mock_health_server

            mock_webhook_server = Mock()
            mock_webhook_server.start = AsyncMock()
            mock_webhook_server.stop = AsyncMock()
            mock_webhook_server_class.return_value = mock_webhook_server

            app = BotApplication()

            # Simulate running briefly then stopping
            async def simulate_running():
                app.running = False  # Stop immediately for test

            with patch.object(app, '_keep_running', side_effect=simulate_running):
                await app.start()

            # Verify webhook server was created and started
            mock_webhook_server_class.assert_called_once_with(
                application=mock_application,
                settings=mock_settings_webhook
            )
            mock_webhook_server.start.assert_called_once()

            # Verify webhook was registered with Telegram
            mock_bot_service.setup_webhook.assert_called_once_with(
                webhook_url=mock_settings_webhook.webhook_url,
                secret_token=mock_settings_webhook.webhook_secret_token
            )


    @pytest.mark.asyncio
    @patch('src.main.init_db')
    @patch('src.main.get_settings')
    async def test_start_webhook_mode_no_startup_delay(
        self,
        mock_get_settings,
        mock_init_db,
        mock_settings_webhook
    ):
        """Test that webhook mode doesn't apply production startup delay."""
        mock_get_settings.return_value = mock_settings_webhook

        with patch('src.main.TelegramBotService') as mock_bot_service_class, \
             patch('src.main.MessageCollectorService'), \
             patch('src.main.CleanupService'), \
             patch('src.main.ReportDeliveryService'), \
             patch('src.main.AsyncIOScheduler') as mock_scheduler_class, \
             patch('src.main.HealthCheckServer') as mock_health_server_class, \
             patch('src.main.WebhookServer') as mock_webhook_server_class, \
             patch('src.main.asyncio.sleep') as mock_sleep:

            # Setup mocks
            mock_application = MagicMock()
            mock_application.start = AsyncMock()
            mock_application.stop = AsyncMock()
            mock_application.__aenter__ = AsyncMock(return_value=mock_application)
            mock_application.__aexit__ = AsyncMock()

            mock_bot_service = Mock()
            mock_bot_service.setup = Mock(return_value=mock_application)
            mock_bot_service.setup_webhook = AsyncMock()
            mock_bot_service.remove_webhook = AsyncMock()
            mock_bot_service_class.return_value = mock_bot_service

            mock_scheduler = Mock()
            mock_scheduler.start = Mock()
            mock_scheduler.running = False
            mock_scheduler_class.return_value = mock_scheduler

            mock_health_server = Mock()
            mock_health_server.start = AsyncMock()
            mock_health_server.stop = AsyncMock()
            mock_health_server_class.return_value = mock_health_server

            mock_webhook_server = Mock()
            mock_webhook_server.start = AsyncMock()
            mock_webhook_server.stop = AsyncMock()
            mock_webhook_server_class.return_value = mock_webhook_server

            app = BotApplication()

            async def simulate_running():
                app.running = False

            with patch.object(app, '_keep_running', side_effect=simulate_running):
                await app.start()

            # Verify NO 60-second sleep was called (webhook mode in production)
            mock_sleep.assert_not_called()


class TestBotApplicationStartPollingMode:
    """Tests for BotApplication start in polling mode."""

    @pytest.mark.asyncio
    @patch('src.main.init_db')
    @patch('src.main.get_settings')
    async def test_start_polling_mode_starts_polling(
        self,
        mock_get_settings,
        mock_init_db,
        mock_settings_polling
    ):
        """Test that polling mode starts the updater with polling."""
        mock_get_settings.return_value = mock_settings_polling

        with patch('src.main.TelegramBotService') as mock_bot_service_class, \
             patch('src.main.MessageCollectorService'), \
             patch('src.main.CleanupService'), \
             patch('src.main.ReportDeliveryService'), \
             patch('src.main.AsyncIOScheduler') as mock_scheduler_class, \
             patch('src.main.HealthCheckServer') as mock_health_server_class:

            # Setup mocks
            mock_updater = Mock()
            mock_updater.start_polling = AsyncMock()
            mock_updater.stop = AsyncMock()

            mock_application = MagicMock()
            mock_application.start = AsyncMock()
            mock_application.stop = AsyncMock()
            mock_application.updater = mock_updater
            mock_application.__aenter__ = AsyncMock(return_value=mock_application)
            mock_application.__aexit__ = AsyncMock()

            mock_bot_service = Mock()
            mock_bot_service.setup = Mock(return_value=mock_application)
            mock_bot_service_class.return_value = mock_bot_service

            mock_scheduler = Mock()
            mock_scheduler.start = Mock()
            mock_scheduler.running = False
            mock_scheduler_class.return_value = mock_scheduler

            mock_health_server = Mock()
            mock_health_server.start = AsyncMock()
            mock_health_server.stop = AsyncMock()
            mock_health_server_class.return_value = mock_health_server

            app = BotApplication()

            async def simulate_running():
                app.running = False

            with patch.object(app, '_keep_running', side_effect=simulate_running):
                await app.start()

            # Verify polling was started
            from telegram import Update
            mock_updater.start_polling.assert_called_once_with(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )


    @pytest.mark.asyncio
    @patch('src.main.init_db')
    @patch('src.main.get_settings')
    async def test_start_production_polling_applies_startup_delay(
        self,
        mock_get_settings,
        mock_init_db,
        mock_settings_production_polling
    ):
        """Test that production polling mode applies 60s startup delay."""
        mock_get_settings.return_value = mock_settings_production_polling

        with patch('src.main.TelegramBotService') as mock_bot_service_class, \
             patch('src.main.MessageCollectorService'), \
             patch('src.main.CleanupService'), \
             patch('src.main.ReportDeliveryService'), \
             patch('src.main.AsyncIOScheduler') as mock_scheduler_class, \
             patch('src.main.HealthCheckServer') as mock_health_server_class, \
             patch('src.main.asyncio.sleep') as mock_sleep:

            mock_sleep.return_value = AsyncMock()

            # Setup mocks
            mock_updater = Mock()
            mock_updater.start_polling = AsyncMock()
            mock_updater.stop = AsyncMock()

            mock_application = MagicMock()
            mock_application.start = AsyncMock()
            mock_application.stop = AsyncMock()
            mock_application.updater = mock_updater
            mock_application.__aenter__ = AsyncMock(return_value=mock_application)
            mock_application.__aexit__ = AsyncMock()

            mock_bot_service = Mock()
            mock_bot_service.setup = Mock(return_value=mock_application)
            mock_bot_service_class.return_value = mock_bot_service

            mock_scheduler = Mock()
            mock_scheduler.start = Mock()
            mock_scheduler.running = False
            mock_scheduler_class.return_value = mock_scheduler

            mock_health_server = Mock()
            mock_health_server.start = AsyncMock()
            mock_health_server.stop = AsyncMock()
            mock_health_server_class.return_value = mock_health_server

            app = BotApplication()

            async def simulate_running():
                app.running = False

            with patch.object(app, '_keep_running', side_effect=simulate_running):
                await app.start()

            # Verify 60-second sleep was called (production polling mode)
            mock_sleep.assert_called_once_with(60)


class TestBotApplicationStop:
    """Tests for BotApplication graceful shutdown."""

    @pytest.mark.asyncio
    @patch('src.main.get_settings')
    async def test_stop_webhook_mode_removes_webhook(
        self,
        mock_get_settings,
        mock_settings_webhook
    ):
        """Test that stopping in webhook mode removes webhook and stops server."""
        mock_get_settings.return_value = mock_settings_webhook

        with patch('src.main.TelegramBotService') as mock_bot_service_class, \
             patch('src.main.MessageCollectorService'), \
             patch('src.main.CleanupService'), \
             patch('src.main.ReportDeliveryService'), \
             patch('src.main.AsyncIOScheduler') as mock_scheduler_class, \
             patch('src.main.HealthCheckServer') as mock_health_server_class:

            mock_bot_service = Mock()
            mock_bot_service.remove_webhook = AsyncMock()
            mock_bot_service_class.return_value = mock_bot_service

            mock_scheduler = Mock()
            mock_scheduler.running = False
            mock_scheduler_class.return_value = mock_scheduler

            mock_health_server = Mock()
            mock_health_server.stop = AsyncMock()
            mock_health_server_class.return_value = mock_health_server

            app = BotApplication()

            # Simulate webhook server exists
            mock_webhook_server = Mock()
            mock_webhook_server.stop = AsyncMock()
            app.webhook_server = mock_webhook_server

            await app.stop()

            # Verify webhook was removed and server stopped
            mock_bot_service.remove_webhook.assert_called_once()
            mock_webhook_server.stop.assert_called_once()


    @pytest.mark.asyncio
    @patch('src.main.get_settings')
    async def test_stop_polling_mode_no_webhook_cleanup(
        self,
        mock_get_settings,
        mock_settings_polling
    ):
        """Test that stopping in polling mode doesn't try to clean up webhook."""
        mock_get_settings.return_value = mock_settings_polling

        with patch('src.main.TelegramBotService') as mock_bot_service_class, \
             patch('src.main.MessageCollectorService'), \
             patch('src.main.CleanupService'), \
             patch('src.main.ReportDeliveryService'), \
             patch('src.main.AsyncIOScheduler') as mock_scheduler_class, \
             patch('src.main.HealthCheckServer') as mock_health_server_class:

            mock_bot_service = Mock()
            mock_bot_service.remove_webhook = AsyncMock()
            mock_bot_service_class.return_value = mock_bot_service

            mock_scheduler = Mock()
            mock_scheduler.running = False
            mock_scheduler_class.return_value = mock_scheduler

            mock_health_server = Mock()
            mock_health_server.stop = AsyncMock()
            mock_health_server_class.return_value = mock_health_server

            app = BotApplication()
            # webhook_server should be None in polling mode
            assert app.webhook_server is None

            await app.stop()

            # Verify webhook cleanup was NOT called
            mock_bot_service.remove_webhook.assert_not_called()

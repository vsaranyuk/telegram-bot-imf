"""Main application entry point.

This module initializes and runs the Telegram bot with scheduled tasks.
"""

import asyncio
import logging
import signal
import sys
from datetime import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from telegram import Update
from telegram.ext import CommandHandler

from src.config.settings import get_settings, configure_logging
from src.config.database import init_db
from src.services.telegram_bot_service import TelegramBotService
from src.services.message_collector_service import MessageCollectorService
from src.services.cleanup_service import CleanupService
from src.services.report_delivery_service import ReportDeliveryService
from src.services.webhook_server import WebhookServer
from src.health_check import HealthCheckServer
from src.handlers.admin_commands import (
    add_chat_command,
    list_chats_command,
    remove_chat_command,
    get_chat_id_command,
    admin_help_command,
)

logger = logging.getLogger(__name__)


class BotApplication:
    """Main bot application with scheduler.

    Manages bot lifecycle, message collection, and scheduled tasks.
    """

    def __init__(self):
        """Initialize bot application."""
        self.settings = get_settings()
        self.bot_service = TelegramBotService()
        self.message_collector = MessageCollectorService()
        self.cleanup_service = CleanupService()
        self.report_delivery_service = ReportDeliveryService()

        # Configure scheduler with in-memory job store
        # Note: Jobs are not persisted across restarts, but this avoids
        # serialization issues with Bot objects in python-telegram-bot 22.x
        self.scheduler = AsyncIOScheduler()
        self.health_server = HealthCheckServer(port=8080, scheduler=self.scheduler)
        self.application = None
        self.webhook_server = None  # Will be initialized after application setup if webhook_enabled
        self.running = False

    def setup_scheduler(self) -> None:
        """Set up scheduled jobs for cleanup and daily reports.

        Schedules:
        - Daily reports at configured hour (default 10:00 AM)
        - Daily cleanup at configured hour (default 02:00 AM)
        """
        # Schedule daily reports job
        self.scheduler.add_job(
            self.report_delivery_service.generate_daily_reports,
            trigger=CronTrigger(hour=self.settings.report_time_hour, minute=0),
            id='daily_reports',
            name='Generate and deliver daily reports',
            replace_existing=True
        )

        # Schedule cleanup job
        self.scheduler.add_job(
            self.cleanup_service.cleanup_old_messages,
            trigger=CronTrigger(hour=self.settings.cleanup_time_hour, minute=0),
            id='cleanup_old_messages',
            name='Delete messages older than 48 hours',
            replace_existing=True
        )

        logger.info("Scheduled jobs configured:")
        logger.info(f"  - Daily reports: Daily at {self.settings.report_time_hour:02d}:00")
        logger.info(f"  - Cleanup job: Daily at {self.settings.cleanup_time_hour:02d}:00")
        logger.info(f"  - Timezone: {self.settings.timezone}")
        logger.info(f"  - Job store: In-memory (jobs reset on restart)")

    async def start(self) -> None:
        """Start the bot application.

        Initializes database, sets up bot, starts scheduler and polling.
        """
        try:
            logger.info("="*60)
            logger.info("Starting Telegram Bot for IMF")
            logger.info("="*60)

            # Add startup delay in production polling mode to avoid conflicts during rolling deployment
            # This gives the old instance time to disconnect from Telegram API
            # 60 seconds ensures old instance has fully shut down (45s shutdown + 15s buffer)
            # Note: Webhook mode doesn't need this delay as it uses different connection pattern
            if self.settings.environment == "production" and not self.settings.webhook_enabled:
                startup_delay = 60  # seconds
                logger.info(f"⏳ Production startup (polling mode): waiting {startup_delay}s for clean deployment...")
                await asyncio.sleep(startup_delay)
                logger.info("✅ Startup delay complete, proceeding with initialization")

            # Initialize database
            logger.info("Initializing database...")
            init_db()

            # Set up bot with message handler
            logger.info("Setting up Telegram bot...")
            self.application = self.bot_service.setup(
                self.message_collector.handle_message
            )

            # Store settings in bot_data for admin decorators
            self.application.bot_data['settings'] = self.settings

            # Register admin command handlers
            logger.info("Registering admin commands...")
            self.application.add_handler(CommandHandler("add_chat", add_chat_command))
            self.application.add_handler(CommandHandler("list_chats", list_chats_command))
            self.application.add_handler(CommandHandler("remove_chat", remove_chat_command))
            self.application.add_handler(CommandHandler("get_chat_id", get_chat_id_command))
            self.application.add_handler(CommandHandler("admin", admin_help_command))
            logger.info("Admin commands registered")

            # Set up scheduler
            logger.info("Setting up scheduled tasks...")
            self.setup_scheduler()
            self.scheduler.start()

            # Start health check server only in polling mode
            # In webhook mode, WebhookServer provides the /health endpoint
            if not self.settings.webhook_enabled:
                logger.info("Starting health check server...")
                await self.health_server.start()

            self.running = True

            # Use the async context manager pattern from python-telegram-bot 20.x docs
            async with self.application:
                await self.application.start()

                # Initialize webhook server if webhook mode is enabled
                if self.settings.webhook_enabled:
                    logger.info("="*60)
                    logger.info("Starting in WEBHOOK mode")
                    logger.info("="*60)

                    # Create webhook server with the application instance
                    self.webhook_server = WebhookServer(
                        application=self.application,
                        settings=self.settings
                    )

                    # Start webhook HTTP server
                    await self.webhook_server.start()

                    # Register webhook with Telegram
                    await self.bot_service.setup_webhook(
                        webhook_url=self.settings.webhook_url,
                        secret_token=self.settings.webhook_secret_token
                    )

                    logger.info("="*60)
                    logger.info("Bot is now running in WEBHOOK mode!")
                    logger.info("Press Ctrl+C to stop")
                    logger.info("="*60)

                else:
                    logger.info("="*60)
                    logger.info("Starting in POLLING mode (development)")
                    logger.info("="*60)

                    # Retry polling start to handle temporary conflicts during deployment
                    max_retries = 5
                    retry_delay = 10  # seconds

                    for attempt in range(max_retries):
                        try:
                            await self.application.updater.start_polling(
                                allowed_updates=Update.ALL_TYPES,
                                drop_pending_updates=True
                            )
                            logger.info("✅ Bot polling started successfully")
                            break
                        except Exception as e:
                            if "Conflict" in str(e) and attempt < max_retries - 1:
                                logger.warning(
                                    f"⚠️ Conflict detected during polling start (attempt {attempt + 1}/{max_retries}). "
                                    f"Previous bot instance still active. Retrying in {retry_delay}s..."
                                )
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 1.5  # Exponential backoff
                            else:
                                raise

                    logger.info("="*60)
                    logger.info("Bot is now running in POLLING mode!")
                    logger.info("Press Ctrl+C to stop")
                    logger.info("="*60)

                # Keep the bot running
                await self._keep_running()

                # Clean stop based on mode
                if self.settings.webhook_enabled:
                    # Remove webhook from Telegram
                    await self.bot_service.remove_webhook()
                    # Stop webhook server
                    if self.webhook_server:
                        await self.webhook_server.stop()
                else:
                    # Stop polling
                    await self.application.updater.stop()

                await self.application.stop()

        except Exception as e:
            logger.error(f"Failed to start bot: {e}", exc_info=True)
            await self.stop()
            sys.exit(1)

    async def _keep_running(self) -> None:
        """Keep the bot running until stopped."""
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Bot received cancellation signal")

    async def stop(self) -> None:
        """Stop the bot gracefully."""
        logger.info("Shutting down bot...")

        self.running = False

        # Stop health check server (only runs in polling mode)
        if not self.settings.webhook_enabled:
            await self.health_server.stop()

        # Stop scheduler
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

        # Stop webhook server if running in webhook mode
        if self.webhook_server:
            await self.bot_service.remove_webhook()
            await self.webhook_server.stop()
            logger.info("Webhook server stopped")

        # Stop bot - run_polling() handles cleanup automatically
        # but we can stop it explicitly if needed
        if self.application and self.application.running:
            await self.application.stop()
            await self.application.shutdown()

        logger.info("Bot shut down complete")

    def handle_signal(self, signum, frame):
        """Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False


async def main():
    """Main entry point."""
    # Configure logging
    settings = get_settings()
    configure_logging(settings)

    # Create and run application
    app = BotApplication()

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, lambda s, f: app.handle_signal(s, f))
    signal.signal(signal.SIGTERM, lambda s, f: app.handle_signal(s, f))

    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

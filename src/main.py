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
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from src.config.settings import get_settings, configure_logging
from src.config.database import init_db
from src.services.telegram_bot_service import TelegramBotService
from src.services.message_collector_service import MessageCollectorService
from src.services.cleanup_service import CleanupService
from src.services.report_delivery_service import ReportDeliveryService
from src.health_check import HealthCheckServer

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

        # Configure scheduler with SQLite job store for persistence
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///jobs.db')
        }
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)
        self.health_server = HealthCheckServer(port=8080, scheduler=self.scheduler)
        self.application = None
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
        logger.info(f"  - Job store: SQLite (jobs.db) for persistence")

    async def start(self) -> None:
        """Start the bot application.

        Initializes database, sets up bot, starts scheduler and polling.
        """
        try:
            logger.info("="*60)
            logger.info("Starting Telegram Bot for IMF")
            logger.info("="*60)

            # Initialize database
            logger.info("Initializing database...")
            init_db()

            # Set up bot with message handler
            logger.info("Setting up Telegram bot...")
            self.application = self.bot_service.setup(
                self.message_collector.handle_message
            )

            # Set up scheduler
            logger.info("Setting up scheduled tasks...")
            self.setup_scheduler()
            self.scheduler.start()

            # Start health check server
            logger.info("Starting health check server...")
            await self.health_server.start()

            # Start bot polling
            await self.bot_service.start_polling(self.application)

            self.running = True

            logger.info("="*60)
            logger.info("Bot is now running!")
            logger.info("Press Ctrl+C to stop")
            logger.info("="*60)

            # Keep the bot running
            await self._keep_running()

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

        # Stop health check server
        await self.health_server.stop()

        # Stop scheduler
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

        # Stop bot
        if self.application:
            await self.bot_service.stop_polling(self.application)

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

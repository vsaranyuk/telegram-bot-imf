"""Telegram bot service for lifecycle management."""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
)

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class TelegramBotService:
    """Service for managing Telegram bot lifecycle.

    Handles bot initialization, connection, and lifecycle management.
    Delegates message processing to MessageCollectorService.

    Attributes:
        application: Telegram bot application instance
        settings: Application settings
    """

    def __init__(self):
        """Initialize Telegram bot service."""
        self.settings = get_settings()
        self.application: Optional[Application] = None

    def create_application(self) -> Application:
        """Create and configure Telegram bot application.

        Returns:
            Configured Telegram Application instance
        """
        logger.info("Creating Telegram bot application...")

        application = (
            ApplicationBuilder()
            .token(self.settings.telegram_bot_token)
            .build()
        )

        logger.info("Telegram bot application created successfully")

        return application

    def register_handlers(
        self,
        application: Application,
        message_handler_callback
    ) -> None:
        """Register bot handlers for processing updates.

        Args:
            application: Telegram Application instance
            message_handler_callback: Async callback function for messages
        """
        # Handler for all text messages in groups
        message_handler = MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler_callback
        )

        application.add_handler(message_handler)

        logger.info("Message handlers registered")

    async def start_command(self, update: Update, context) -> None:
        """Handle /start command.

        Args:
            update: Telegram update object
            context: Bot context
        """
        await update.message.reply_text(
            "Bot is running and monitoring configured chats."
        )

    def setup(self, message_handler_callback) -> Application:
        """Set up bot with all handlers.

        Args:
            message_handler_callback: Async callback for message processing

        Returns:
            Configured Application instance
        """
        self.application = self.create_application()
        self.register_handlers(self.application, message_handler_callback)

        # Add start command handler
        start_handler = CommandHandler("start", self.start_command)
        self.application.add_handler(start_handler)

        return self.application

    async def start_polling(self, application: Application) -> None:
        """Start bot in polling mode.

        Args:
            application: Telegram Application instance
        """
        logger.info("Starting bot in polling mode...")

        # Initialize bot
        await application.initialize()
        await application.start()

        # Start polling
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES
        )

        logger.info("Bot is now polling for updates")

    async def stop_polling(self, application: Application) -> None:
        """Stop bot polling gracefully.

        Args:
            application: Telegram Application instance
        """
        logger.info("Stopping bot...")

        await application.updater.stop()
        await application.stop()
        await application.shutdown()

        logger.info("Bot stopped successfully")

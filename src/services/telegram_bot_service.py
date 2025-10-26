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

        # In python-telegram-bot 20.x, we need to initialize and start separately
        # But NOT call updater.start_polling directly
        await application.initialize()
        await application.start()

        # Start polling using the updater
        # The updater should already be initialized by Application
        if application.updater:
            await application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )

        logger.info("Bot is now polling for updates")

    async def stop_polling(self, application: Application) -> None:
        """Stop bot polling gracefully.

        Args:
            application: Telegram Application instance
        """
        logger.info("Stopping bot...")

        if application.updater and application.updater.running:
            await application.updater.stop()

        if application.running:
            await application.stop()

        await application.shutdown()

        logger.info("Bot stopped successfully")

    async def setup_webhook(self, webhook_url: str, secret_token: str) -> None:
        """Register webhook with Telegram API.

        Args:
            webhook_url: Full HTTPS URL for webhook endpoint
            secret_token: Secret token for request validation

        Raises:
            Exception: If webhook registration fails
        """
        logger.info(f"🌐 Registering webhook: {webhook_url}")

        try:
            await self.application.bot.set_webhook(
                url=webhook_url,
                secret_token=secret_token,
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                max_connections=40  # Telegram default
            )

            # Verify webhook was set
            webhook_info = await self.application.bot.get_webhook_info()

            logger.info(f"✅ Webhook registered successfully")
            logger.info(f"   URL: {webhook_info.url}")
            logger.info(f"   Pending updates: {webhook_info.pending_update_count}")
            logger.info(f"   Max connections: {webhook_info.max_connections}")

        except Exception as e:
            logger.error(f"Failed to set webhook: {e}", exc_info=True)
            raise

    async def remove_webhook(self) -> None:
        """Remove webhook and return to polling mode.

        This deletes the webhook from Telegram, allowing the bot
        to fall back to long polling for updates.
        """
        logger.info("Removing webhook...")

        try:
            await self.application.bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook removed successfully")
        except Exception as e:
            logger.error(f"Failed to remove webhook: {e}", exc_info=True)
            raise

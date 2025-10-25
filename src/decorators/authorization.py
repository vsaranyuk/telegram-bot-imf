"""Authorization decorators for Telegram bot commands.

This module provides decorators to restrict command access to authorized users.
"""

import logging
from functools import wraps
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def admin_only(func: Callable) -> Callable:
    """Decorator to restrict command to admin users only.

    Checks if the user executing the command matches ADMIN_USER_ID from settings.
    If not authorized, sends an error message and returns without executing the command.

    Args:
        func: Async command handler function to wrap

    Returns:
        Wrapped function with authorization check

    Example:
        @admin_only
        async def add_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # Only admin can execute this
            ...
    """

    @wraps(func)
    async def wrapped(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        """Authorization wrapper for command handlers."""
        if not update.effective_user:
            logger.warning("Command received without effective_user")
            return

        user_id = update.effective_user.id
        settings = context.bot_data.get("settings")

        if not settings:
            logger.error("Settings not found in bot_data")
            await update.message.reply_text(
                "⚠️ Bot configuration error. Please contact administrator."
            )
            return

        if user_id != settings.admin_user_id:
            logger.warning(
                f"Unauthorized command access attempt: user_id={user_id}, "
                f"command={func.__name__}"
            )
            await update.message.reply_text(
                "⛔️ Access denied. Admin only command."
            )
            return

        logger.info(f"Admin command authorized: user_id={user_id}, command={func.__name__}")
        return await func(update, context, *args, **kwargs)

    return wrapped

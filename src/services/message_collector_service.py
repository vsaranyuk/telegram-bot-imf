"""Message collector service for handling incoming messages."""

import logging
from datetime import datetime
from typing import Optional, Dict

from telegram import Update
from telegram.ext import ContextTypes

from src.models.message import Message
from src.repositories.message_repository import MessageRepository
from src.repositories.chat_repository import ChatRepository
from src.config.database import get_db_session

logger = logging.getLogger(__name__)


class MessageCollectorService:
    """Service for collecting and storing Telegram messages.

    Listens for new messages, validates against whitelist,
    and persists to database with all metadata.
    """

    async def handle_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle incoming Telegram message.

        Args:
            update: Telegram update containing message
            context: Bot context
        """
        if not update.message or not update.message.text:
            return

        telegram_message = update.message
        chat_id = telegram_message.chat_id
        message_id = telegram_message.message_id

        try:
            # Check if chat is whitelisted
            with get_db_session() as session:
                chat_repo = ChatRepository(session)

                if not chat_repo.is_chat_enabled(chat_id):
                    logger.debug(
                        f"Ignoring message from non-whitelisted chat: {chat_id}"
                    )
                    return

                # Extract message data
                user = telegram_message.from_user
                user_id = user.id if user else 0
                user_name = user.full_name if user else "Unknown"
                text = telegram_message.text
                timestamp = telegram_message.date

                # Create Message entity
                message = Message(
                    chat_id=chat_id,
                    message_id=message_id,
                    user_id=user_id,
                    user_name=user_name,
                    text=text,
                    timestamp=timestamp
                )

                # Store reactions if available (initially empty)
                reactions = self._extract_reactions(telegram_message)
                if reactions:
                    message.set_reactions(reactions)

                # Save to database
                message_repo = MessageRepository(session)
                saved_message = message_repo.save_message(message)

                logger.info(
                    f"Message collected: chat_id={chat_id}, "
                    f"message_id={message_id}, user={user_name}"
                )

        except Exception as e:
            logger.error(
                f"Error handling message {message_id} from chat {chat_id}: {e}",
                exc_info=True
            )

    def _extract_reactions(self, telegram_message) -> Optional[Dict[str, int]]:
        """Extract reactions from Telegram message.

        Args:
            telegram_message: Telegram Message object

        Returns:
            Dictionary of reactions {emoji: count} or None

        Note:
            Telegram Bot API provides reactions through MessageReactionUpdated,
            not directly on Message. This method handles initial message creation.
            Reactions will be updated separately when reaction events occur.
        """
        # Initial messages don't have reactions
        # Reactions are added later via MessageReactionUpdated events
        return None

    async def handle_reaction_update(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle message reaction updates.

        Args:
            update: Telegram update containing reaction change
            context: Bot context

        Note:
            This is a placeholder for future implementation.
            Telegram Bot API provides reactions through message_reaction updates,
            which require additional setup.
        """
        # Placeholder for future implementation
        pass

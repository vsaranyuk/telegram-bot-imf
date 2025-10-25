"""Admin commands for managing chat whitelist.

This module provides Telegram commands for administrators to manage
the whitelist of monitored chats without direct database access.
"""

import logging
from datetime import datetime
from typing import List

from telegram import Update
from telegram.ext import ContextTypes

from src.decorators.authorization import admin_only
from src.models.chat import Chat
from src.repositories.chat_repository import ChatRepository
from src.config.database import get_db_session

logger = logging.getLogger(__name__)


@admin_only
async def add_chat_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Add a chat to the whitelist.

    Usage: /add_chat <chat_id> <chat_name>

    Args:
        update: Telegram update object
        context: Bot context with args

    Example:
        /add_chat -1001234567890 "Partner Channel"
    """
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: /add_chat <chat_id> <chat_name>\n\n"
            "Example: /add_chat -1001234567890 \"Partner Channel\"\n\n"
            "Use /get_chat_id to find chat IDs"
        )
        return

    try:
        chat_id = int(context.args[0])
        chat_name = " ".join(context.args[1:])

        # Validate chat_id format (should be negative for groups/channels)
        if chat_id > 0:
            await update.message.reply_text(
                "⚠️ Warning: chat_id should typically be negative for groups/channels.\n"
                f"Received: {chat_id}\n\n"
                "Continue anyway? Use /get_chat_id to verify."
            )

        with get_db_session() as session:
            chat_repo = ChatRepository(session)

            # Check if chat already exists
            existing_chat = chat_repo.get_chat_by_id(chat_id)

            if existing_chat:
                # Update existing chat
                existing_chat.chat_name = chat_name
                existing_chat.enabled = True
                session.commit()
                session.refresh(existing_chat)

                logger.info(
                    f"Admin updated chat: chat_id={chat_id}, name='{chat_name}', "
                    f"admin_id={update.effective_user.id}"
                )

                await update.message.reply_text(
                    f"✅ Chat updated in whitelist:\n\n"
                    f"Chat ID: `{chat_id}`\n"
                    f"Name: {chat_name}\n"
                    f"Status: Enabled",
                    parse_mode="Markdown"
                )
            else:
                # Create new chat
                new_chat = Chat(
                    chat_id=chat_id,
                    chat_name=chat_name,
                    enabled=True
                )
                created_chat = chat_repo.save_chat(new_chat)

                logger.info(
                    f"Admin added chat: chat_id={chat_id}, name='{chat_name}', "
                    f"admin_id={update.effective_user.id}"
                )

                await update.message.reply_text(
                    f"✅ Chat added to whitelist:\n\n"
                    f"Chat ID: `{chat_id}`\n"
                    f"Name: {chat_name}\n"
                    f"Status: Enabled\n\n"
                    f"Bot will now collect messages from this chat.",
                    parse_mode="Markdown"
                )

    except ValueError:
        await update.message.reply_text(
            f"❌ Invalid chat_id: '{context.args[0]}'\n\n"
            "Chat ID must be a number (usually negative for groups/channels)"
        )
    except Exception as e:
        logger.error(f"Error adding chat: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error adding chat: {str(e)}\n\n"
            "Please contact the administrator."
        )


@admin_only
async def list_chats_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """List all enabled chats in the whitelist.

    Usage: /list_chats

    Args:
        update: Telegram update object
        context: Bot context
    """
    try:
        with get_db_session() as session:
            chat_repo = ChatRepository(session)
            chats = chat_repo.get_all_enabled_chats()

            if not chats:
                await update.message.reply_text(
                    "📭 No whitelisted chats found.\n\n"
                    "Use /add_chat to add a chat to the whitelist."
                )
                return

            message_lines = ["📋 *Whitelisted Chats:*\n"]

            for chat in chats:
                created_at = chat.created_at.strftime("%Y-%m-%d %H:%M")
                message_lines.append(
                    f"• *{chat.chat_name}*\n"
                    f"  ID: `{chat.chat_id}`\n"
                    f"  Added: {created_at}\n"
                )

            message = "\n".join(message_lines)
            await update.message.reply_text(message, parse_mode="Markdown")

            logger.info(
                f"Admin listed chats: count={len(chats)}, admin_id={update.effective_user.id}"
            )

    except Exception as e:
        logger.error(f"Error listing chats: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error listing chats: {str(e)}\n\n"
            "Please contact the administrator."
        )


@admin_only
async def remove_chat_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Remove a chat from the whitelist (soft delete).

    Usage: /remove_chat <chat_id>

    Args:
        update: Telegram update object
        context: Bot context with args

    Example:
        /remove_chat -1001234567890
    """
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ Usage: /remove_chat <chat_id>\n\n"
            "Example: /remove_chat -1001234567890\n\n"
            "Use /list_chats to see chat IDs"
        )
        return

    try:
        chat_id = int(context.args[0])

        with get_db_session() as session:
            chat_repo = ChatRepository(session)
            chat = chat_repo.get_chat_by_id(chat_id)

            if not chat:
                await update.message.reply_text(
                    f"❌ Chat not found: `{chat_id}`\n\n"
                    "Use /list_chats to see available chats.",
                    parse_mode="Markdown"
                )
                return

            # Soft delete by setting enabled=False
            chat.enabled = False
            session.commit()
            session.refresh(chat)

            logger.info(
                f"Admin removed chat: chat_id={chat_id}, name='{chat.chat_name}', "
                f"admin_id={update.effective_user.id}"
            )

            await update.message.reply_text(
                f"✅ Chat removed from whitelist:\n\n"
                f"Chat ID: `{chat_id}`\n"
                f"Name: {chat.chat_name}\n"
                f"Status: Disabled\n\n"
                f"Bot will no longer collect messages from this chat.",
                parse_mode="Markdown"
            )

    except ValueError:
        await update.message.reply_text(
            f"❌ Invalid chat_id: '{context.args[0]}'\n\n"
            "Chat ID must be a number"
        )
    except Exception as e:
        logger.error(f"Error removing chat: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error removing chat: {str(e)}\n\n"
            "Please contact the administrator."
        )


async def get_chat_id_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show the current chat ID and provide example /add_chat command.

    This command works in both private and group chats.
    No admin authorization required - any user can check chat ID.

    Usage: /get_chat_id

    Args:
        update: Telegram update object
        context: Bot context
    """
    if not update.message or not update.effective_chat:
        return

    chat = update.effective_chat
    chat_id = chat.id
    chat_title = chat.title or chat.first_name or "Unknown"
    chat_type = chat.type

    # Build response message
    message_lines = [
        "🆔 *Chat Information:*\n",
        f"Chat ID: `{chat_id}`",
        f"Chat Name: {chat_title}",
        f"Chat Type: {chat_type}\n",
    ]

    # Add usage example for admin
    message_lines.append("📝 *Admin Command Example:*")
    message_lines.append(f"`/add_chat {chat_id} \"{chat_title}\"`")

    message = "\n".join(message_lines)

    await update.message.reply_text(message, parse_mode="Markdown")

    logger.info(
        f"Chat ID requested: chat_id={chat_id}, chat_type={chat_type}, "
        f"user_id={update.effective_user.id if update.effective_user else 'unknown'}"
    )


@admin_only
async def admin_help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show admin commands help.

    Usage: /admin

    Args:
        update: Telegram update object
        context: Bot context
    """
    help_text = """
🔧 *Admin Commands*

*Whitelist Management:*
• `/add_chat <chat_id> <name>` - Add chat to whitelist
• `/remove_chat <chat_id>` - Remove chat from whitelist
• `/list_chats` - Show all whitelisted chats
• `/get_chat_id` - Show current chat ID

*Examples:*
```
/get_chat_id
/add_chat -1001234567890 "Partner Channel"
/list_chats
/remove_chat -1001234567890
```

*How to add a channel:*
1. Go to the channel you want to monitor
2. Send `/get_chat_id` in the channel
3. Copy the chat ID from the response
4. Use `/add_chat` with the chat ID and a name

*Note:* Only authorized admin users can use these commands.
"""

    await update.message.reply_text(help_text, parse_mode="Markdown")

    logger.info(f"Admin help requested: admin_id={update.effective_user.id}")

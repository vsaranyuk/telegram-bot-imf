"""Helper script to add a chat to the whitelist.

Usage:
    python add_chat.py <chat_id> <chat_name>

Example:
    python add_chat.py -123456789 "My Test Group"
"""

import sys
from src.config.database import get_db_session
from src.repositories.chat_repository import ChatRepository
from src.models.chat import Chat


def add_chat(chat_id: int, chat_name: str) -> None:
    """Add a chat to the whitelist.

    Args:
        chat_id: Telegram chat ID (negative for groups)
        chat_name: Human-readable chat name
    """
    with get_db_session() as session:
        chat_repo = ChatRepository(session)

        # Check if chat already exists
        existing = chat_repo.get_chat_by_id(chat_id)
        if existing:
            print(f"⚠️  Chat {chat_id} already exists: {existing.chat_name}")
            print(f"   Enabled: {existing.enabled}")
            return

        # Create new chat
        chat = Chat(
            chat_id=chat_id,
            chat_name=chat_name,
            enabled=True
        )

        saved = chat_repo.save_chat(chat)
        print(f"✅ Chat added successfully!")
        print(f"   Chat ID: {saved.chat_id}")
        print(f"   Name: {saved.chat_name}")
        print(f"   Enabled: {saved.enabled}")


def list_chats() -> None:
    """List all chats in the whitelist."""
    with get_db_session() as session:
        chat_repo = ChatRepository(session)
        chats = chat_repo.get_all_chats()

        if not chats:
            print("📋 No chats in whitelist yet.")
            return

        print(f"📋 Whitelist has {len(chats)} chat(s):")
        print()
        for chat in chats:
            status = "✓ Enabled" if chat.enabled else "✗ Disabled"
            print(f"  {status}")
            print(f"    Chat ID: {chat.chat_id}")
            print(f"    Name: {chat.chat_name}")
            print()


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] == "list":
        # List all chats
        list_chats()
    elif len(sys.argv) == 3:
        # Add a chat
        try:
            chat_id = int(sys.argv[1])
            chat_name = sys.argv[2]
            add_chat(chat_id, chat_name)
        except ValueError:
            print("❌ Error: chat_id must be a number")
            print(f"Usage: python {sys.argv[0]} <chat_id> <chat_name>")
            sys.exit(1)
    else:
        print(f"Usage: python {sys.argv[0]} <chat_id> <chat_name>")
        print(f"   or: python {sys.argv[0]} list")
        print()
        print("Example:")
        print(f"   python {sys.argv[0]} -123456789 'My Test Group'")
        sys.exit(1)

# Telegram Bot for IMF - Message Collection & Storage

A Telegram bot that automatically collects and stores messages from monitored group chats for daily analysis.

## Features

- ✅ Automatic message collection from configured Telegram group chats
- ✅ Stores messages with metadata (user, timestamp, reactions)
- ✅ SQLite database with indexed storage for performance
- ✅ Automatic cleanup of messages older than 48 hours
- ✅ Chat whitelist configuration for security
- ✅ Repository pattern for data access

## Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Telegram_bot_IMF
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file from template:
```bash
cp .env.example .env
```

5. Configure your bot token in `.env`:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

6. Initialize database:
```bash
python -c "from src.config.database import init_db; init_db()"
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Telegram Bot Token (required)
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Admin User ID for command access (get from @userinfobot)
ADMIN_USER_ID=0

# Database URL (default: SQLite)
DATABASE_URL=sqlite:///./bot_data.db

# Logging Level (INFO, DEBUG, ERROR)
LOG_LEVEL=INFO

# Message Retention (hours)
MESSAGE_RETENTION_HOURS=48
```

### Admin Commands

**New!** You can now manage monitored chats directly through Telegram commands (no code required).

#### Getting Your Telegram User ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. The bot will reply with your user ID
3. Set this ID as `ADMIN_USER_ID` in your `.env` file or Render dashboard

#### Setting Admin User ID

In your `.env` file:
```env
ADMIN_USER_ID=123456789  # Your Telegram user ID from @userinfobot
```

**Security Note:** Keep your `ADMIN_USER_ID` private. Never commit it to git.

#### Available Admin Commands

Once configured, you can manage chats via Telegram:

- `/get_chat_id` - Show current chat ID (works in any chat)
- `/add_chat <chat_id> <chat_name>` - Add chat to whitelist (admin only)
- `/list_chats` - Show all whitelisted chats (admin only)
- `/remove_chat <chat_id>` - Remove chat from whitelist (admin only)
- `/admin` - Show admin commands help (admin only)

#### Example Workflow

1. Go to the channel you want to monitor
2. Send `/get_chat_id` to get the channel ID
3. Copy the chat ID from the response
4. Send `/add_chat -1001234567890 "Partner Channel"`
5. The bot will now collect messages from that channel
6. Use `/list_chats` to verify the chat was added

#### Setting Up BotFather Commands

To enable command autocomplete in Telegram:

1. Message [@BotFather](https://t.me/botfather)
2. Send `/mybots` → Select your bot → **Edit Bot** → **Edit Commands**
3. Paste this command list:
```
add_chat - Add chat to whitelist (admin only)
list_chats - Show whitelisted chats (admin only)
remove_chat - Remove chat from whitelist (admin only)
get_chat_id - Show current chat ID
admin - Show admin commands help (admin only)
```
4. Commands will now appear in autocomplete for all users (but only admin can execute them)

### Chat Whitelist (Legacy Method)

**Note:** The legacy Python script method still works but admin commands are recommended for easier management.

<details>
<summary>Click to expand legacy Python method</summary>

Add monitored chats to the database using Python:

```python
from src.config.database import get_db_session
from src.repositories.chat_repository import ChatRepository
from src.models.chat import Chat

with get_db_session() as session:
    chat_repo = ChatRepository(session)

    # Add a chat
    chat = Chat(
        chat_id=-1001234567890,  # Your Telegram chat ID (negative for groups/channels)
        chat_name="Partner Chat",
        enabled=True
    )
    chat_repo.save_chat(chat)
```

</details>

## Usage

### Running the Bot

```bash
python -m src.main
```

The bot will:
- Connect to Telegram API
- Monitor configured group chats
- Collect and store messages within 2 seconds
- Run cleanup job daily at 02:00 AM

### Stopping the Bot

Press `Ctrl+C` to gracefully shutdown the bot.

## Database Schema

### Messages Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| chat_id | BIGINT | Telegram chat ID (indexed) |
| message_id | BIGINT | Telegram message ID |
| user_id | BIGINT | Sender's Telegram user ID |
| user_name | VARCHAR(255) | Sender's display name |
| text | TEXT | Message content |
| timestamp | DATETIME | When message was sent (indexed) |
| reactions | JSON | Message reactions {emoji: count} |
| created_at | DATETIME | When record was created |

**Indexes:**
- `idx_chat_timestamp`: (chat_id, timestamp) - For 24h queries
- `idx_message_lookup`: (chat_id, message_id) - For message lookup

### Chats Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| chat_id | BIGINT | Telegram chat ID (unique, indexed) |
| chat_name | VARCHAR(255) | Chat display name |
| enabled | BOOLEAN | Whether chat is monitored |
| created_at | DATETIME | When record was created |

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_message_repository.py
```

### Code Formatting

```bash
# Format code with black
black src/ tests/

# Type checking with mypy
mypy src/
```

### Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

## Architecture

```
src/
├── config/          # Configuration and settings
│   ├── settings.py  # Pydantic settings
│   └── database.py  # Database setup
├── models/          # SQLAlchemy models
│   ├── message.py   # Message entity
│   └── chat.py      # Chat entity
├── repositories/    # Data access layer
│   ├── message_repository.py
│   └── chat_repository.py
├── services/        # Business logic
│   ├── telegram_bot_service.py      # Bot lifecycle
│   ├── message_collector_service.py # Message handling
│   └── cleanup_service.py           # Data cleanup
└── main.py         # Application entry point
```

## Troubleshooting

### Bot doesn't receive messages

1. Ensure bot token is correct in `.env`
2. Verify bot is added to the group chat as admin
3. Check that chat_id is whitelisted in database
4. Check logs for errors: `LOG_LEVEL=DEBUG python -m src.main`

### Database errors

1. Ensure database file is writable
2. Check database URL in `.env`
3. Reinitialize database: `rm bot_data.db && python -c "from src.config.database import init_db; init_db()"`

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub.

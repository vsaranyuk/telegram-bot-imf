"""Application configuration settings.

This module provides configuration management.
All settings are loaded from environment variables.
"""

import logging
import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Settings:
    """Application settings loaded from environment variables.

    Attributes:
        telegram_bot_token: Telegram Bot API token
        database_url: SQLAlchemy database URL (default: SQLite)
        log_level: Logging level (INFO, DEBUG, ERROR)
        message_retention_hours: Hours to keep messages before deletion
        anthropic_api_key: Claude API key for message analysis
        report_time_hour: Hour (0-23) when daily reports are sent
        cleanup_time_hour: Hour (0-23) when old messages are deleted
        timezone: Timezone for scheduler (e.g., 'UTC+3')
    """

    # Telegram Configuration
    telegram_bot_token: str

    # Database Configuration
    database_url: str = "sqlite:///./bot_data.db"

    # Logging Configuration
    log_level: str = "INFO"

    # Data Retention Configuration
    message_retention_hours: int = 48

    # Claude API Configuration
    anthropic_api_key: str = ""

    # Scheduler Configuration
    report_time_hour: int = 10  # 10:00 AM
    cleanup_time_hour: int = 2  # 02:00 AM
    timezone: str = "UTC"

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables.

        Returns:
            Settings instance loaded from environment

        Raises:
            ValueError: If required environment variables are missing
        """
        # Load .env file if it exists (for local development)
        load_dotenv()

        # Get required variables
        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")

        # Validate required variables
        if not telegram_bot_token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN environment variable is required but not set. "
                "Please configure it in Render dashboard under Environment."
            )

        if not anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required but not set. "
                "Please configure it in Render dashboard under Environment."
            )

        return cls(
            telegram_bot_token=telegram_bot_token,
            database_url=os.getenv("DATABASE_URL", "sqlite:///./bot_data.db"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            message_retention_hours=int(os.getenv("MESSAGE_RETENTION_HOURS", "48")),
            anthropic_api_key=anthropic_api_key,
            report_time_hour=int(os.getenv("REPORT_TIME_HOUR", "10")),
            cleanup_time_hour=int(os.getenv("CLEANUP_TIME_HOUR", "2")),
            timezone=os.getenv("TIMEZONE", "UTC")
        )


def get_settings() -> Settings:
    """Get application settings instance.

    Returns:
        Settings instance loaded from environment
    """
    return Settings.from_env()


def configure_logging(settings: Settings) -> None:
    """Configure application logging.

    Args:
        settings: Application settings with log level
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Set specific log levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)

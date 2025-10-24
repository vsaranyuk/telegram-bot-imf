"""Report delivery service for automated daily reports."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError, RetryAfter

from src.config.database import get_db_session
from src.config.settings import Settings, get_settings
from src.models.chat import Chat
from src.models.report import Report
from src.repositories.chat_repository import ChatRepository
from src.repositories.report_repository import ReportRepository
from src.services.message_analyzer_service import MessageAnalyzerService
from src.services.claude_api_service import AnalysisResult


logger = logging.getLogger(__name__)


class ReportDeliveryService:
    """Service for automated daily report generation and delivery.

    Orchestrates:
    - Fetching enabled chats
    - Generating reports using MessageAnalyzerService
    - Formatting reports for Telegram
    - Delivering reports with rate limiting and error handling
    - Tracking delivery status
    """

    # Rate limiting configuration
    STAGGER_DELAY_SECONDS = 5  # Delay between chat processing
    MAX_MESSAGE_LENGTH = 4096  # Telegram message limit
    RETRY_DELAY_SECONDS = 60  # Delay before retry on error
    MAX_RETRIES = 3

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize report delivery service.

        Args:
            settings: Application settings (optional, will load if not provided)

        Note: This service creates its own database sessions as needed.
        """
        self.settings = settings or get_settings()

        # Initialize Telegram bot for sending
        self.bot = Bot(token=self.settings.telegram_bot_token)

    async def generate_daily_reports(self) -> dict:
        """Generate and deliver daily reports to all enabled chats.

        Main entry point called by scheduler at 10:00 AM daily.

        Returns:
            dict: Summary of delivery results
                - total_chats: Number of chats processed
                - reports_sent: Number of reports successfully sent
                - reports_skipped: Number skipped (no questions)
                - errors: Number of failed deliveries
                - failed_chat_ids: List of chat IDs that failed

        This method:
        1. Fetches all enabled chats
        2. For each chat, generates report (if questions exist)
        3. Sends report to Telegram with rate limiting
        4. Handles errors gracefully (continues with other chats)
        5. Returns summary statistics
        """
        logger.info("="*60)
        logger.info("Starting daily report generation and delivery")
        logger.info("="*60)

        start_time = datetime.now(timezone.utc)

        # Use database session context
        with get_db_session() as session:
            chat_repo = ChatRepository(session)

            # Get all enabled chats
            logger.debug("📊 Fetching enabled chats from database...")
            enabled_chats = chat_repo.get_all_enabled_chats()
            logger.info(f"Found {len(enabled_chats)} enabled chats")

            if enabled_chats:
                logger.debug(f"Chat list: {[(c.chat_id, c.chat_name) for c in enabled_chats]}")

            if not enabled_chats:
                logger.warning("No enabled chats found - skipping report delivery")
                return {
                    "total_chats": 0,
                    "reports_sent": 0,
                    "reports_skipped": 0,
                    "errors": 0,
                    "failed_chat_ids": []
                }

            # Delivery tracking
            results = {
                "total_chats": len(enabled_chats),
                "reports_sent": 0,
                "reports_skipped": 0,
                "errors": 0,
                "failed_chat_ids": []
            }

            # Process each chat with rate limiting
            for i, chat in enumerate(enabled_chats):
                logger.info(f"📋 Processing chat {i+1}/{len(enabled_chats)}: {chat.chat_name} (ID: {chat.chat_id})")

                try:
                    # Generate and deliver report for this chat
                    logger.debug(f"Generating report for chat {chat.chat_id}...")
                    report_sent = await self._process_chat_report(chat)

                    if report_sent:
                        results["reports_sent"] += 1
                    else:
                        results["reports_skipped"] += 1

                except Exception as e:
                    logger.error(
                        f"Failed to process chat {chat.chat_id} ({chat.chat_name}): {e}",
                        exc_info=True
                    )
                    results["errors"] += 1
                    results["failed_chat_ids"].append(chat.chat_id)

                # Rate limiting: stagger requests
                if i < len(enabled_chats) - 1:  # Don't delay after last chat
                    logger.debug(f"Waiting {self.STAGGER_DELAY_SECONDS}s before next chat")
                    await asyncio.sleep(self.STAGGER_DELAY_SECONDS)

        # Log summary
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info("="*60)
        logger.info("Daily report delivery complete")
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info(f"Total chats: {results['total_chats']}")
        logger.info(f"Reports sent: {results['reports_sent']}")
        logger.info(f"Reports skipped: {results['reports_skipped']} (no questions)")
        logger.info(f"Errors: {results['errors']}")
        if results['failed_chat_ids']:
            logger.warning(f"Failed chat IDs: {results['failed_chat_ids']}")
        logger.info("="*60)

        # Check if admin notification needed (>50% failure rate)
        if results['total_chats'] > 0:
            failure_rate = results['errors'] / results['total_chats']
            if failure_rate > 0.5:
                logger.critical(
                    f"HIGH FAILURE RATE: {failure_rate*100:.1f}% of chats failed "
                    f"({results['errors']}/{results['total_chats']})"
                )
                # Send admin notification
                await self._send_admin_notification(
                    failure_rate=failure_rate,
                    failed_count=results['errors'],
                    total_count=results['total_chats'],
                    failed_chat_ids=results['failed_chat_ids']
                )

        return results

    async def _process_chat_report(self, chat: Chat) -> bool:
        """Generate and send report for a single chat.

        Args:
            chat: Chat entity to process

        Returns:
            bool: True if report was sent, False if skipped (no questions)

        Raises:
            Exception: If report generation or delivery fails
        """
        logger.info(f"Generating report for chat {chat.chat_id}")

        # Use database session for this operation
        with get_db_session() as session:
            message_analyzer = MessageAnalyzerService(session, self.settings)
            report_repo = ReportRepository(session)

            # Analyze last 24 hours of messages
            analysis = await message_analyzer.analyze_chat_last_24h(chat.id)

            if not analysis or analysis.summary.total_questions == 0:
                logger.info(f"No questions found for chat {chat.chat_id} - skipping report")
                return False

            logger.info(
                f"Analysis complete for chat {chat.chat_id}: "
                f"{analysis.summary.total_questions} questions, "
                f"{analysis.summary.answered} answered"
            )

            # Format report
            report_text = self._format_report(analysis, chat.chat_name)

            # Send to Telegram with retry logic
            sent = await self._send_telegram_report(chat.chat_id, report_text)

            if sent:
                # Save report to database
                report = Report(
                    chat_id=chat.id,
                    generated_at=datetime.now(timezone.utc),
                    questions_count=analysis.summary.total_questions,
                    answered_count=analysis.summary.answered,
                    unanswered_count=analysis.summary.unanswered,
                    avg_response_time_minutes=analysis.summary.avg_response_time_minutes,
                    report_data=analysis.model_dump()
                )
                report_repo.save_report(report)
                logger.info(f"Report sent and saved for chat {chat.chat_id}")
                return True
            else:
                logger.error(f"Failed to send report for chat {chat.chat_id}")
                raise Exception(f"Report delivery failed for chat {chat.chat_id}")

    def _format_report(self, analysis: AnalysisResult, chat_name: str) -> str:
        """Format analysis result as Telegram message.

        Args:
            analysis: Analysis result from Claude API
            chat_name: Name of the chat for header

        Returns:
            str: Formatted Telegram message with Markdown
        """
        # Build header
        report_lines = [
            "📊 *Daily Communication Report* #IMFReport",
            f"Chat: {chat_name}",
            f"Period: Last 24 hours",
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        # Summary section
        report_lines.extend([
            "📈 *Summary*",
            f"• Total Questions: {analysis.summary.total_questions}",
            f"• Answered: {analysis.summary.answered}",
            f"• Unanswered: {analysis.summary.unanswered}",
        ])

        if analysis.summary.avg_response_time_minutes:
            report_lines.append(
                f"• Avg Response Time: {analysis.summary.avg_response_time_minutes:.1f} minutes"
            )

        report_lines.extend(["", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━", ""])

        # Questions section
        if analysis.questions:
            report_lines.append("❓ *Questions Identified*")
            report_lines.append("")

            for i, q in enumerate(analysis.questions, 1):
                status = "✅ Answered" if q.is_answered else "⏳ Pending"
                report_lines.append(f"{i}. {status} | {q.category.upper()}")
                report_lines.append(f"   _{q.text}_")

                if q.is_answered and q.response_time_minutes:
                    report_lines.append(
                        f"   Response time: {q.response_time_minutes:.1f} min"
                    )

                report_lines.append("")

        # Footer
        report_lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "_This report was generated automatically by IMF Bot_",
        ])

        report_text = "\n".join(report_lines)

        # Handle message length limit
        if len(report_text) > self.MAX_MESSAGE_LENGTH:
            logger.warning(
                f"Report exceeds Telegram limit ({len(report_text)} > {self.MAX_MESSAGE_LENGTH}). "
                "Truncating..."
            )
            truncate_marker = "\n\n_[Report truncated due to length limit]_"
            max_len = self.MAX_MESSAGE_LENGTH - len(truncate_marker)
            report_text = report_text[:max_len] + truncate_marker

        return report_text

    async def _send_telegram_report(
        self,
        chat_id: int,
        report_text: str
    ) -> bool:
        """Send report to Telegram with retry logic.

        Args:
            chat_id: Telegram chat ID
            report_text: Formatted report text

        Returns:
            bool: True if sent successfully, False otherwise
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=report_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"Report sent to chat {chat_id}")
                return True

            except RetryAfter as e:
                # Rate limit hit - wait and retry
                wait_seconds = e.retry_after
                logger.warning(
                    f"Rate limit hit for chat {chat_id}. "
                    f"Waiting {wait_seconds}s (attempt {attempt+1}/{self.MAX_RETRIES})"
                )
                await asyncio.sleep(wait_seconds)

            except TelegramError as e:
                logger.error(
                    f"Telegram error sending to chat {chat_id}: {e} "
                    f"(attempt {attempt+1}/{self.MAX_RETRIES})"
                )

                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY_SECONDS)

            except Exception as e:
                logger.error(
                    f"Unexpected error sending to chat {chat_id}: {e}",
                    exc_info=True
                )
                break

        return False

    async def _send_admin_notification(
        self,
        failure_rate: float,
        failed_count: int,
        total_count: int,
        failed_chat_ids: List[int]
    ) -> None:
        """Send critical failure notification to admin.

        Args:
            failure_rate: Percentage of failed chats (0.0 to 1.0)
            failed_count: Number of failed chats
            total_count: Total number of chats processed
            failed_chat_ids: List of chat IDs that failed
        """
        if self.settings.admin_chat_id == 0:
            logger.warning(
                "Admin notification needed but ADMIN_CHAT_ID not configured. "
                "Set ADMIN_CHAT_ID environment variable to receive critical alerts."
            )
            return

        # Build admin notification message
        message = (
            "🚨 *CRITICAL: High Report Delivery Failure Rate*\n\n"
            f"⚠️ Failure Rate: *{failure_rate*100:.1f}%*\n"
            f"📊 Failed: {failed_count}/{total_count} chats\n"
            f"🕐 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            "Failed Chat IDs:\n"
        )

        if failed_chat_ids:
            message += "\n".join([f"• Chat ID: `{chat_id}`" for chat_id in failed_chat_ids[:10]])
            if len(failed_chat_ids) > 10:
                message += f"\n... and {len(failed_chat_ids) - 10} more"
        else:
            message += "No specific chat IDs available"

        message += "\n\n💡 Check logs for detailed error information."

        try:
            await self.bot.send_message(
                chat_id=self.settings.admin_chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Admin notification sent to chat_id={self.settings.admin_chat_id}")
        except TelegramError as e:
            logger.error(
                f"Failed to send admin notification to chat_id={self.settings.admin_chat_id}: {e}",
                exc_info=True
            )

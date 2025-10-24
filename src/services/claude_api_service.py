"""Claude API service for AI-powered message analysis."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from anthropic import Anthropic
from pydantic import BaseModel, Field

from src.config.settings import Settings
from src.models.message import Message


logger = logging.getLogger(__name__)


# Pydantic models for Claude API response validation
class QuestionAnalysis(BaseModel):
    """Analysis result for a single question."""

    message_id: int = Field(description="Telegram message ID")
    text: str = Field(description="Question text")
    category: str = Field(description="Question category: technical/business/other")
    is_answered: bool = Field(description="Whether question has been answered")
    answer_message_id: Optional[int] = Field(
        default=None, description="Message ID of the answer"
    )
    response_time_minutes: Optional[float] = Field(
        default=None, description="Time to answer in minutes"
    )


class AnswerAnalysis(BaseModel):
    """Analysis result for an answer."""

    message_id: int = Field(description="Telegram message ID")
    text: str = Field(description="Answer text")
    answers_to_message_id: Optional[int] = Field(
        default=None, description="Message ID this answers"
    )


class AnalysisSummary(BaseModel):
    """Summary statistics from analysis."""

    total_questions: int = Field(description="Total questions identified")
    answered: int = Field(description="Number of answered questions")
    unanswered: int = Field(description="Number of unanswered questions")
    avg_response_time_minutes: Optional[float] = Field(
        default=None, description="Average response time"
    )


class AnalysisResult(BaseModel):
    """Complete analysis result from Claude API."""

    questions: List[QuestionAnalysis] = Field(description="List of questions found")
    answers: List[AnswerAnalysis] = Field(description="List of answers found")
    summary: AnalysisSummary = Field(description="Summary statistics")


class ClaudeAPIService:
    """Service for interacting with Claude API for message analysis.

    Uses Message Batches API for 50% cost savings.
    Analyzes Telegram messages to identify questions, answers, and response patterns.
    """

    # Model configuration
    MODEL = "claude-sonnet-4-20250514"  # Latest Claude Sonnet 4 model
    MAX_TOKENS = 4096
    BATCH_POLL_INTERVAL = 10  # seconds
    BATCH_MAX_WAIT = 300  # 5 minutes

    def __init__(self, settings: Settings):
        """Initialize Claude API service.

        Args:
            settings: Application settings with API key

        Raises:
            ValueError: If ANTHROPIC_API_KEY is not configured
        """
        if not settings.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not configured. "
                "Please set the ANTHROPIC_API_KEY environment variable."
            )
        self.settings = settings
        self.client = Anthropic(api_key=settings.anthropic_api_key)

    def _build_analysis_prompt(self, messages: List[Message]) -> str:
        """Build prompt for Claude API analysis.

        Args:
            messages: List of Telegram messages to analyze

        Returns:
            Formatted prompt string
        """
        # Format messages for the prompt
        messages_text = []
        for msg in messages:
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            user = msg.user_name or f"User {msg.user_id}"
            messages_text.append(
                f"[{timestamp}] {user} (ID: {msg.message_id}): {msg.text}"
            )

        messages_block = "\n".join(messages_text)

        prompt = f"""Analyze the following Telegram messages and identify:

1. **Questions**: Messages that ask for information or clarification
   - Categorize each as: technical, business, or other
   - Track message ID and text
   - Note: Exclude rhetorical questions and pleasantries

2. **Answers**: Messages that respond to questions
   - Map each answer to the question it addresses (by message_id)
   - Calculate response time from question to answer

3. **Summary Statistics**:
   - Total questions found
   - Number answered vs unanswered
   - Average response time

**Messages:**
{messages_block}

**Important Guidelines:**
- Be precise in identifying genuine questions (exclude rhetorical or casual remarks)
- Map answers to questions based on context and timing
- For multi-part questions, treat as single question unless clearly separate
- Response time should be calculated from question timestamp to answer timestamp
- If a question has multiple answers, use the first substantive answer

**CRITICAL**: You MUST respond with ONLY valid JSON. Do not include any explanations, markdown formatting, or code blocks.

Return your analysis in this exact JSON format:
{{
  "questions": [
    {{
      "message_id": 123,
      "text": "question text",
      "category": "technical|business|other",
      "is_answered": true|false,
      "answer_message_id": 124,
      "response_time_minutes": 15.5
    }}
  ],
  "answers": [
    {{
      "message_id": 124,
      "text": "answer text",
      "answers_to_message_id": 123
    }}
  ],
  "summary": {{
    "total_questions": 10,
    "answered": 8,
    "unanswered": 2,
    "avg_response_time_minutes": 45.2
  }}
}}"""
        return prompt

    async def analyze_messages(self, messages: List[Message]) -> AnalysisResult:
        """Analyze messages using Claude API (async).

        Currently uses standard Messages API.
        TODO: Implement Message Batches for 50% cost savings.

        Args:
            messages: List of messages to analyze

        Returns:
            AnalysisResult with questions, answers, and summary

        Raises:
            Exception: If API call fails
        """
        if not messages:
            # Return empty result for no messages
            return AnalysisResult(
                questions=[],
                answers=[],
                summary=AnalysisSummary(
                    total_questions=0,
                    answered=0,
                    unanswered=0,
                    avg_response_time_minutes=None,
                ),
            )

        logger.info(f"Analyzing {len(messages)} messages with Claude API")

        try:
            # Build prompt
            prompt = self._build_analysis_prompt(messages)

            # Call Claude API in thread pool (SDK client is sync)
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract JSON from response
            response_text = response.content[0].text

            logger.debug(f"Claude API raw response: {response_text[:500]}...")

            # Parse and validate response
            # Handle case where response might be wrapped in markdown code blocks
            if response_text.strip().startswith("```"):
                # Extract JSON from markdown code block
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)

            result_data = json.loads(response_text)
            result = AnalysisResult(**result_data)

            logger.info(
                f"Analysis complete: {result.summary.total_questions} questions, "
                f"{result.summary.answered} answered, "
                f"{result.summary.unanswered} unanswered"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude API response: {e}")
            logger.error(f"Response text: {response_text}")
            raise Exception(f"Invalid JSON response from Claude API: {e}")
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise

    async def analyze_messages_batch(
        self, messages: List[Message]
    ) -> AnalysisResult:
        """Analyze messages using Message Batches API for 50% cost savings.

        Creates a batch job, polls for completion, and retrieves results.

        Args:
            messages: List of messages to analyze

        Returns:
            AnalysisResult with questions, answers, and summary

        Raises:
            ValueError: If API key is not configured
            Exception: If batch processing fails or times out
        """
        # TODO: Implement Message Batches API
        # For MVP, use standard API
        return await self.analyze_messages(messages)

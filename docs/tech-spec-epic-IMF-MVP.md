# Technical Specification: Telegram Bot MVP - Daily Report Generation

Date: 2025-10-23
Author: Vladimir
Epic ID: IMF-MVP
Status: Draft

---

## Overview

This Technical Specification defines the MVP implementation of a Telegram bot for monitoring partner communication across 15 chats. The bot collects messages over 24-hour periods, analyzes question-answer patterns using AI (Claude API), and delivers daily reports at 10:00 AM. The primary goal is to create transparency in partner communication, track response times, and identify unanswered questions to improve partner service quality.

The system implements a scheduled batch processing pattern: collect → analyze → report. It leverages Telegram Bot API for message access, APScheduler for daily scheduling, SQLite for temporary storage, and Anthropic's Claude API with batch processing for cost-effective AI analysis.

## Objectives and Scope

**In Scope (MVP v1.0):**
- ✅ Daily message collection from 15 Telegram group chats (last 24 hours)
- ✅ AI-powered analysis: identify questions, answers, and question→answer mapping
- ✅ Track response times by category (<1h, 1-4h, 4-24h, >24h)
- ✅ Track message reactions (❤️ 👍 💩) as sentiment indicators
- ✅ Generate structured daily report at 10:00 AM
- ✅ Send report to each chat (only if questions were detected)
- ✅ Include #IMFReport tag for searchability
- ✅ Docker containerization for easy deployment
- ✅ CI/CD pipeline with GitHub Actions
- ✅ Deployment to Render platform

**Out of Scope (Future versions):**
- ❌ Proactive bot clarification of unclear questions (v2.0)
- ❌ Monthly strategic reports for leadership (v2.0)
- ❌ Feedback collection mechanism (v2.0)
- ❌ Integration with knowledge base / AI assistant (v2.0+)
- ❌ Geotargetification and awards system (v3.0+)
- ❌ Admin panel for mass broadcasts (v3.0+)
- ❌ Multi-language support (not required)

## System Architecture Alignment

**Architecture Pattern:** Event-Driven Scheduled Bot (Single-Process)

**Technology Stack Alignment:**
- **Bot Framework:** python-telegram-bot v20+ (asyncio-based)
- **Task Scheduler:** APScheduler 3.11+ (in-process, cron triggers)
- **Database:** SQLite 3 (file-based, zero-config)
- **AI/LLM:** Anthropic Claude API with Message Batches (50% cost savings)
- **Hosting:** Render platform (Free tier → Hobby $7/mo)
- **CI/CD:** GitHub Actions (automated Docker builds and deployment)

**Key Architectural Decisions (from ADR-001):**
- Single Docker container deployment (avoids APScheduler multi-worker issues)
- Repository pattern for database abstraction (enables future PostgreSQL migration)
- Service layer separation (business logic independent of bot handlers)
- Batch processing pattern (collect 24h → single Claude API call → report)
- Environment-based configuration (12-factor app principles)

**Constraints:**
- Single-server deployment (sufficient for 15-50 chats)
- Low write volume (15 reports/day at 10:00 AM)
- Beginner-friendly stack (excellent documentation required)
- Budget: < $50/month total ($0-7 hosting + <$30 Claude API)

## Detailed Design

### Services and Modules

| Module | Responsibility | Inputs | Outputs | Owner/Layer |
|--------|---------------|--------|---------|-------------|
| **TelegramBotService** | Manages bot lifecycle, handles incoming messages and commands | Telegram Bot API events | Message objects to MessageRepository | Infrastructure |
| **MessageCollectorService** | Listens for new messages, stores them with metadata | Message events from bot | Stored messages in DB | Application |
| **SchedulerService** | Manages APScheduler, triggers daily report generation at 10:00 AM | Cron schedule config | Trigger events to ReportGeneratorService | Infrastructure |
| **MessageRepository** | Abstracts database access for messages (CRUD operations) | Message objects | Persisted/retrieved messages | Data Access |
| **ChatRepository** | Manages chat configurations and settings | Chat IDs, configs | Chat metadata | Data Access |
| **ReportRepository** | Stores generated reports for audit trail | Report objects | Historical reports | Data Access |
| **ClaudeAPIService** | Handles Claude API batch requests for message analysis | Batch of messages | Analysis results (questions, answers, mappings) | External Integration |
| **MessageAnalyzerService** | Orchestrates AI analysis via Claude API | Messages from last 24h | Structured analysis data | Application |
| **ReportGeneratorService** | Formats analysis into readable Telegram report | Analysis data | Formatted markdown report | Application |
| **ReportDeliveryService** | Sends reports to appropriate chats via Telegram | Report + chat_id | Sent message confirmation | Application |
| **ConfigService** | Loads and validates environment configuration | .env file | Config objects | Infrastructure |

**Module Interaction Flow:**
```
TelegramBotService ──> MessageCollectorService ──> MessageRepository ──> SQLite DB
                                                                              ↓
SchedulerService (10:00 AM) ──> ReportGeneratorService ──> MessageRepository (fetch 24h)
                                        ↓
                              MessageAnalyzerService ──> ClaudeAPIService ──> Claude API
                                        ↓
                              ReportGeneratorService (format)
                                        ↓
                              ReportDeliveryService ──> TelegramBotService ──> Telegram API
```

### Data Models and Contracts

**Message Entity:**
```python
class Message:
    id: int (PK, auto-increment)
    chat_id: int (indexed)
    message_id: int (Telegram message ID)
    user_id: int (sender Telegram user ID)
    user_name: str (sender display name)
    text: str (message content)
    timestamp: datetime (indexed for 24h queries)
    reactions: JSON (dict: {emoji: count})
    is_question: bool (nullable, set after analysis)
    is_answer: bool (nullable, set after analysis)
    answered_message_id: int (FK to Message.id, nullable)
    created_at: datetime

    # Indexes
    INDEX idx_chat_timestamp ON (chat_id, timestamp DESC)
    INDEX idx_message_lookup ON (chat_id, message_id)
```

**Chat Entity:**
```python
class Chat:
    id: int (PK, auto-increment)
    chat_id: int (Telegram chat ID, unique)
    chat_name: str
    enabled: bool (default: true)
    last_report_sent: datetime (nullable)
    created_at: datetime
```

**Report Entity:**
```python
class Report:
    id: int (PK, auto-increment)
    chat_id: int (FK to Chat.id)
    report_date: date (indexed)
    questions_count: int
    answered_count: int
    unanswered_count: int
    avg_response_time_minutes: float (nullable)
    report_content: text (markdown)
    sent_at: datetime

    INDEX idx_chat_date ON (chat_id, report_date DESC)
```

**Analysis Result Contract (from Claude API):**
```json
{
  "questions": [
    {
      "message_id": 12345,
      "text": "Question text",
      "category": "technical|business|other",
      "is_answered": true|false,
      "answer_message_id": 12350,
      "response_time_minutes": 45
    }
  ],
  "answers": [
    {
      "message_id": 12350,
      "text": "Answer text",
      "answers_to_message_id": 12345
    }
  ],
  "summary": {
    "total_questions": 5,
    "answered": 4,
    "unanswered": 1,
    "avg_response_time_minutes": 120.5
  }
}
```

### APIs and Interfaces

**Telegram Bot API Endpoints (Consumed):**
```
GET  /getUpdates - Poll for new messages (development mode)
POST /sendMessage - Send reports to chats
  Request: {chat_id, text, parse_mode: "Markdown"}
  Response: {ok: true, result: {...}}

GET  /getChat - Get chat information
POST /setWebhook - Configure webhook (production mode, future)
```

**Claude API Endpoints (Consumed):**
```
POST /v1/messages/batches - Create batch analysis job
  Request: {
    requests: [
      {
        custom_id: "chat_123_20251023",
        params: {
          model: "claude-3-5-sonnet-20241022",
          max_tokens: 4096,
          messages: [{role: "user", content: "Analyze messages..."}]
        }
      }
    ]
  }
  Response: {id: "batch_id", processing_status: "in_progress"}

GET  /v1/messages/batches/{batch_id}/results - Retrieve batch results
  Response: Stream of analysis results
```

**Internal Service Interfaces:**

```python
# MessageRepository Interface
class MessageRepositoryInterface:
    def save_message(message: Message) -> Message
    def get_messages_last_24h(chat_id: int) -> List[Message]
    def get_message_by_id(chat_id: int, message_id: int) -> Message
    def update_analysis(message_id: int, is_question: bool, is_answer: bool, answered_id: int)
    def delete_old_messages(before_date: datetime) -> int

# ClaudeAPIService Interface
class ClaudeAPIServiceInterface:
    def analyze_messages_batch(messages: List[Message]) -> AnalysisResult
    def check_batch_status(batch_id: str) -> BatchStatus
    def get_batch_results(batch_id: str) -> AnalysisResult
```

### Workflows and Sequencing

**Workflow 1: Message Collection (Continuous)**
```
1. TelegramBotService receives message event
2. MessageCollectorService extracts metadata
3. MessageRepository.save_message() persists to SQLite
4. Log: "Message {message_id} saved for chat {chat_id}"
```

**Workflow 2: Daily Report Generation (Scheduled at 10:00 AM)**
```
ACTOR: SchedulerService (APScheduler cron trigger)

1. SchedulerService triggers ReportGeneratorService.generate_daily_reports()
2. FOR EACH enabled chat in ChatRepository:
   a. MessageRepository.get_messages_last_24h(chat_id) → messages
   b. IF messages.length == 0: SKIP chat
   c. MessageAnalyzerService.analyze(messages):
      - Format messages into Claude API prompt
      - ClaudeAPIService.analyze_messages_batch(messages)
      - Poll batch status (max 5 min wait)
      - Parse analysis results
   d. ReportGeneratorService.format_report(analysis) → markdown_report
   e. ReportRepository.save_report(chat_id, report)
   f. ReportDeliveryService.send_report(chat_id, markdown_report)
      - TelegramBotService.send_message(chat_id, report)
   g. ChatRepository.update_last_report_sent(chat_id, now())
3. Log summary: "Reports sent to {count} chats"
```

**Workflow 3: Database Cleanup (Daily at 02:00 AM)**
```
1. SchedulerService triggers cleanup job
2. MessageRepository.delete_old_messages(before=now() - 48h)
3. Log: "Deleted {count} old messages"
```

**Error Handling Workflow:**
```
IF Claude API error OR Telegram API error:
  1. Log error with context (chat_id, timestamp, error_details)
  2. Skip current chat, continue with next
  3. Send admin notification if critical failure (>50% chats failed)
  4. Store failed chat_id for retry (future enhancement)
```

## Non-Functional Requirements

### Performance

**Target Metrics:**
- **Report Generation Time:** < 5 minutes per chat (target: 2-3 minutes average)
  - Message retrieval: < 10 seconds per chat
  - Claude API batch processing: < 3 minutes (depends on message volume)
  - Report formatting and delivery: < 30 seconds

- **Message Processing Latency:** < 2 seconds from receipt to storage
  - Real-time message collection without backlog

- **Daily Report Delivery Precision:** ±2 minutes from 10:00 AM target
  - APScheduler cron trigger: 0 10 * * * (10:00 AM daily)

- **Throughput Capacity:**
  - 15 chats × 200 messages/day = 3,000 messages/day handled
  - Headroom: Can scale to 50 chats (10,000 messages/day)

**Performance Requirements from Research:**
- Process messages from ~15 chats daily ✓
- Report generation: < 5 minutes per chat ✓
- Report delivery time: exactly 10:00 AM (±1 minute) ✓

### Security

**Authentication & Authorization:**
- **Telegram Bot Token:** Store in environment variable `TELEGRAM_BOT_TOKEN`
  - Never commit to git (use .env.example template)
  - Rotate token if compromised

- **Claude API Key:** Store in environment variable `ANTHROPIC_API_KEY`
  - Use separate keys for dev/staging/production
  - Monitor usage via Anthropic dashboard

**Data Handling:**
- **Message Data:** Temporary storage only (48-hour retention)
  - Automatic cleanup of messages older than 48 hours
  - No long-term message storage (GDPR-friendly)

- **Chat Access Control:**
  - Bot only accesses explicitly configured chats (whitelist in database)
  - No unauthorized chat monitoring

- **Logging:** Never log sensitive data
  - Log message IDs, not message content
  - Sanitize user data in error logs

**Deployment Security:**
- Docker container runs as non-root user
- Environment variables injected via Render secrets
- No hardcoded credentials in codebase

**Threat Considerations:**
- **Telegram Bot Token Leak:** Immediate rotation, audit access logs
- **Claude API Key Leak:** Immediate rotation, monitor for unusual usage
- **Unauthorized Chat Access:** Whitelist validation on every message

### Reliability/Availability

**Availability Targets:**
- **Uptime:** 95%+ (acceptable for MVP)
  - ~36 hours downtime/year allowed
  - Focus: Ensure daily 10:00 AM reports sent

- **Recovery Time Objective (RTO):** < 30 minutes
  - Manual restart via Render dashboard
  - Auto-restart on crash (Render platform feature)

**Failure Handling:**
- **Graceful Degradation:**
  - If Claude API fails for one chat, continue with others
  - If Telegram send fails, log error and continue
  - No cascading failures

- **Data Loss Prevention:**
  - SQLite database persisted to disk (Docker volume)
  - No data loss during crashes (ACID transactions)
  - 48-hour message retention prevents loss of current day data

**Auto-Recovery:**
- Render platform automatically restarts crashed containers
- APScheduler jobs persist in SQLite (survive restarts)
- No manual intervention required for transient failures

**Monitoring for Reliability:**
- Health check endpoint: GET /health
  - Returns 200 OK if scheduler active and DB accessible
  - Render uses this for liveness probes

- Admin notifications:
  - Alert if >50% of chats fail report generation
  - Alert if scheduler misses 10:00 AM trigger

### Observability

**Logging Requirements:**
- **Log Levels:** INFO (default), DEBUG (development), ERROR (always)

- **Required Log Signals:**
  - `[INFO] Bot started, monitoring {count} chats`
  - `[INFO] Message {msg_id} saved for chat {chat_id}`
  - `[INFO] Scheduler triggered: generate_daily_reports`
  - `[INFO] Processing chat {chat_id}: {message_count} messages`
  - `[INFO] Claude API batch {batch_id}: status={status}`
  - `[INFO] Report sent to chat {chat_id}: {questions} questions, {answered} answered`
  - `[ERROR] Failed to send report to chat {chat_id}: {error}`
  - `[ERROR] Claude API error: {error_details}`

**Metrics to Track:**
- Daily reports sent count
- Average report generation time
- Claude API costs per day
- Message processing rate
- Error rate by chat

**Tracing:**
- Each report generation gets correlation ID (format: `report_{chat_id}_{date}`)
- All logs for a report include correlation ID for traceability

**Log Destination:**
- Render platform logs (stdout/stderr)
- Retention: 7 days (Render free tier limit)
- Future: Consider external log aggregation (Papertrail, Logtail) if needed

**Debugging Support:**
- Environment variable `LOG_LEVEL=DEBUG` for verbose logging
- Endpoint `/debug/last_run` shows last report generation details (dev only)

## Dependencies and Integrations

### Python Dependencies (requirements.txt)

**Core Framework:**
```
python-telegram-bot==20.7
  - Telegram Bot API wrapper (asyncio-based)
  - License: LGPLv3
  - Latest stable: 20.7 (as of Oct 2025)

anthropic==0.18.0
  - Official Claude API Python SDK
  - License: MIT
  - Includes Message Batches API support
```

**Task Scheduling:**
```
APScheduler==3.10.4
  - In-process task scheduler
  - License: MIT
  - Supports asyncio, cron triggers
```

**Database & ORM:**
```
SQLAlchemy==2.0.23
  - ORM for database abstraction
  - License: MIT
  - Enables easy PostgreSQL migration later

alembic==1.12.1
  - Database migration tool
  - License: MIT
  - For schema versioning
```

**Utilities:**
```
python-dotenv==1.0.0
  - Environment variable management
  - License: BSD-3-Clause

pydantic==2.5.0
  - Data validation and settings
  - License: MIT
  - Type-safe config management

aiohttp==3.9.1
  - Async HTTP client (used by anthropic SDK)
  - License: Apache 2.0
```

**Development Dependencies:**
```
pytest==7.4.3
  - Testing framework
  - License: MIT

pytest-asyncio==0.21.1
  - Asyncio support for pytest
  - License: Apache 2.0

black==23.11.0
  - Code formatter
  - License: MIT

mypy==1.7.1
  - Static type checker
  - License: MIT
```

### External Service Integrations

**Telegram Bot API**
- **Endpoint:** https://api.telegram.org/bot{token}/
- **Authentication:** Bot token (stored in TELEGRAM_BOT_TOKEN env var)
- **Rate Limits:** 30 messages/second per bot
- **Methods Used:**
  - getUpdates (polling mode)
  - sendMessage (report delivery)
  - getChat (chat info)
- **Dependency:** Managed by python-telegram-bot library
- **SLA:** 99.9% uptime (Telegram platform)

**Anthropic Claude API**
- **Endpoint:** https://api.anthropic.com/v1/
- **Authentication:** API key (stored in ANTHROPIC_API_KEY env var)
- **Model:** claude-3-5-sonnet-20241022
- **Rate Limits:**
  - Tier 1: 50 requests/minute, 40,000 tokens/minute
  - Batch API: 10,000 requests per batch, 24h processing
- **Methods Used:**
  - POST /v1/messages/batches (batch creation)
  - GET /v1/messages/batches/{id}/results (result retrieval)
- **Cost Structure:**
  - Input: $3 per million tokens
  - Output: $15 per million tokens
  - Batch discount: 50% off
- **Expected Monthly Cost:** ~$20-30 for 15 chats (3,000 messages/day)

**Render Platform**
- **Service Type:** Web Service (Docker container)
- **Plan:** Free tier → Hobby ($7/mo)
- **Features Used:**
  - Docker deployment
  - Environment variable management
  - Persistent disk (for SQLite)
  - Health checks
  - Auto-restart on failure
- **Deployment:** Connected to GitHub repo for auto-deploy

**GitHub Actions (CI/CD)**
- **Trigger:** Push to main branch
- **Workflow:**
  1. Run tests (pytest)
  2. Build Docker image
  3. Push to GitHub Container Registry
  4. Deploy to Render
- **Secrets Required:**
  - RENDER_DEPLOY_HOOK_URL

### Integration Points Summary

| Integration | Direction | Protocol | Authentication | Criticality |
|-------------|-----------|----------|----------------|-------------|
| Telegram Bot API | Inbound/Outbound | HTTPS/REST | Bot Token | Critical |
| Claude API | Outbound | HTTPS/REST | API Key | Critical |
| Render Platform | Deployment | Docker/Git | Render API Key | Critical |
| GitHub Actions | CI/CD | Git/Docker | GitHub Token | High |
| SQLite DB | Local | File system | None | Critical |

### Dependency Constraints

**Version Pinning Strategy:**
- Pin major.minor versions (allow patch updates)
- Review and update dependencies monthly
- Test thoroughly before upgrading major versions

**Known Compatibility Issues:**
- python-telegram-bot v20+ requires Python 3.8+
- APScheduler + asyncio: Must use single-process deployment
- SQLite: Thread-safe mode required for concurrent reads

**Fallback/Alternatives:**
- If Claude API unavailable: Log error, skip analysis, retry next day
- If Telegram API unavailable: Queue messages, retry delivery
- No immediate fallback for Render (manual migration to Railway/Fly.io if needed)

## Acceptance Criteria (Authoritative)

### AC-001: Message Collection
**Given** the bot is running and monitoring 15 configured chats
**When** a new message is posted in any monitored chat
**Then** the message is stored in the database within 2 seconds
**And** the message includes: chat_id, message_id, user_id, user_name, text, timestamp

**Validation:**
- Test with sample message in test group
- Verify database entry created
- Check timestamp accuracy (±1 second)

---

### AC-002: Daily Report Scheduling
**Given** the bot is deployed and scheduler is active
**When** the clock reaches 10:00 AM local time
**Then** the report generation process is triggered for all enabled chats
**And** the trigger occurs within ±2 minutes of 10:00 AM

**Validation:**
- Monitor logs for scheduler trigger at 10:00 AM
- Verify cron expression: `0 10 * * *`
- Test time precision over 3 consecutive days

---

### AC-003: AI Analysis - Question Detection
**Given** messages collected over the last 24 hours for a chat
**When** the report generation is triggered
**Then** all questions are identified with >90% accuracy
**And** each question is tagged with: message_id, text, category (technical/business/other)

**Validation:**
- Create test dataset with 20 known questions
- Run analysis via Claude API
- Measure precision/recall rates
- Edge cases: rhetorical questions, multi-part questions

---

### AC-004: AI Analysis - Answer Mapping
**Given** questions and answers from the last 24 hours
**When** the Claude API analyzes the conversation
**Then** each answer is correctly mapped to its corresponding question with >85% accuracy
**And** response time is calculated (time between question and answer)

**Validation:**
- Test with known question→answer pairs (10 samples)
- Verify mapping accuracy
- Check response time calculation (should match actual timestamps)

---

### AC-005: Response Time Categorization
**Given** a question with a corresponding answer
**When** the response time is calculated
**Then** it is categorized correctly into:
- **< 1 hour:** Fast response
- **1-4 hours:** Medium response
- **4-24 hours:** Slow response
- **> 24 hours:** Very slow response
- **No answer:** Unanswered

**Validation:**
- Test with messages at known time intervals
- Verify category assignment matches expected ranges

---

### AC-006: Report Content Structure
**Given** analysis results for a chat
**When** the report is generated
**Then** it includes the following sections in Markdown format:
1. **Header:** Date, chat name, #IMFReport tag
2. **Summary:** Total questions, answered count, unanswered count
3. **Response Time Stats:** Breakdown by category (<1h, 1-4h, 4-24h, >24h)
4. **Unanswered Questions:** List with timestamps
5. **Top Reactions:** Messages with most ❤️ 👍 or 💩

**Validation:**
- Verify all sections present
- Check Markdown formatting renders correctly in Telegram
- Validate data accuracy against source messages

---

### AC-007: Report Delivery Conditions
**Given** a chat has been analyzed
**When** the report is ready to send
**Then** the report is sent ONLY if at least one question was detected
**And** if no questions exist, no report is sent and this is logged

**Validation:**
- Test chat with 0 questions → no report sent
- Test chat with 1+ questions → report sent
- Verify log entries for both scenarios

---

### AC-008: Report Delivery Success
**Given** a formatted report for a chat
**When** the delivery service sends the report
**Then** the report is successfully posted to the Telegram chat
**And** delivery confirmation is logged
**And** the chat's `last_report_sent` timestamp is updated

**Validation:**
- Send report to test chat
- Verify message appears in Telegram
- Check database timestamp updated
- Review logs for confirmation

---

### AC-009: Database Cleanup
**Given** the bot has been running for more than 48 hours
**When** the cleanup job runs (daily at 02:00 AM)
**Then** all messages older than 48 hours are deleted
**And** only messages from the last 48 hours remain in the database

**Validation:**
- Seed database with messages at various ages
- Run cleanup job
- Verify only messages < 48h old remain
- Check log for deletion count

---

### AC-010: Error Handling - Graceful Degradation
**Given** the report generation process encounters an error for one chat (e.g., Claude API failure)
**When** the error occurs
**Then** the error is logged with context (chat_id, error_details)
**And** processing continues with the next chat
**And** an admin notification is sent if >50% of chats fail

**Validation:**
- Simulate Claude API error for 1 chat
- Verify other chats still get reports
- Check error logged
- Test admin notification threshold

---

### AC-011: Docker Deployment
**Given** the application code and Dockerfile
**When** the Docker image is built and run
**Then** the container starts successfully
**And** the bot connects to Telegram API
**And** the scheduler initializes
**And** health check endpoint responds with 200 OK

**Validation:**
- Build Docker image: `docker build -t telegram-bot .`
- Run container: `docker run --env-file .env telegram-bot`
- Check logs for successful startup
- Test health endpoint: `curl http://localhost:8000/health`

---

### AC-012: CI/CD Pipeline
**Given** changes are pushed to the main branch on GitHub
**When** GitHub Actions workflow is triggered
**Then** tests are run and must pass
**And** Docker image is built successfully
**And** image is deployed to Render automatically
**And** deployment completes within 10 minutes

**Validation:**
- Push commit to main branch
- Monitor GitHub Actions workflow
- Verify tests pass
- Check Render deployment status
- Confirm bot restarts with new code

---

## Traceability Mapping

| AC ID | Requirement Source | Spec Section(s) | Component(s)/API(s) | Test Approach |
|-------|-------------------|-----------------|---------------------|---------------|
| AC-001 | Brainstorming: Message collection | Detailed Design → MessageCollectorService | TelegramBotService, MessageRepository | Integration test: Send message, verify DB entry |
| AC-002 | Brainstorming: Daily report at 10:00 AM | Detailed Design → SchedulerService, NFR Performance | SchedulerService, APScheduler | System test: Monitor 3 consecutive days |
| AC-003 | Brainstorming: AI analysis - identify questions | Detailed Design → MessageAnalyzerService | ClaudeAPIService, MessageAnalyzerService | Unit test: Known question dataset (20 samples) |
| AC-004 | Brainstorming: Map questions to answers | Detailed Design → MessageAnalyzerService | ClaudeAPIService | Unit test: Known Q→A pairs (10 samples) |
| AC-005 | Brainstorming: Track response times | Detailed Design → ReportGeneratorService | MessageAnalyzerService | Unit test: Time interval edge cases |
| AC-006 | Brainstorming: Report format | Detailed Design → ReportGeneratorService | ReportGeneratorService | Integration test: Verify Markdown sections |
| AC-007 | Brainstorming: Send report only if questions exist | Detailed Design → ReportDeliveryService | ReportDeliveryService | Integration test: 0 questions vs 1+ questions |
| AC-008 | Brainstorming: Send report to chat | Detailed Design → ReportDeliveryService | TelegramBotService, ReportDeliveryService | Integration test: Verify Telegram message sent |
| AC-009 | Scope: 48-hour data retention | Detailed Design → Workflow 3, NFR Security | MessageRepository | Integration test: Seed old data, run cleanup |
| AC-010 | Research: Graceful degradation | NFR Reliability | All services | Integration test: Simulate API failures |
| AC-011 | Research: Docker deployment | System Architecture Alignment | Docker, ConfigService | System test: Build and run container |
| AC-012 | Research: CI/CD automation | Dependencies → GitHub Actions | GitHub Actions, Render | End-to-end test: Push to main, verify deploy |

## Risks, Assumptions, Open Questions

### Risks

**RISK-001: Claude API Costs Exceed Budget**
- **Likelihood:** Medium
- **Impact:** Medium (budget constraint)
- **Description:** Message volume or token usage higher than estimated, causing costs >$30/month
- **Mitigation:**
  - Implement cost tracking and alerts at $20, $30, $40 thresholds
  - Use Claude API batch processing (50% discount)
  - Set message count limits per chat (e.g., max 500 messages analyzed)
  - Monitor token usage in first 2 weeks
- **Contingency:** Reduce analysis frequency or implement simple rule-based analysis for some chats

**RISK-002: APScheduler Reliability Issues**
- **Likelihood:** Low-Medium
- **Impact:** High (missing daily reports)
- **Description:** APScheduler jobs fail silently or don't trigger at 10:00 AM
- **Mitigation:**
  - Use persistent job store (SQLAlchemy + SQLite)
  - Implement health check endpoint
  - Set up monitoring/alerting for missed triggers
  - Keep deployment simple (single process, no multi-worker)
- **Contingency:** Quick migration to Celery (estimated 2 days effort)

**RISK-003: Telegram Bot API Rate Limiting**
- **Likelihood:** Low
- **Impact:** Medium (delayed report delivery)
- **Description:** Sending 15 reports simultaneously at 10:00 AM may hit rate limits (30 msg/sec)
- **Mitigation:**
  - Stagger report sending (e.g., 5-second intervals between chats)
  - Implement retry logic with exponential backoff
  - Monitor API response codes for rate limit warnings (429)
- **Contingency:** Queue reports and retry failed sends

**RISK-004: Learning Curve Too Steep for Beginner**
- **Likelihood:** Medium
- **Impact:** High (project timeline at risk)
- **Description:** Beginner developer struggles with asyncio, SQLAlchemy, or Claude API integration
- **Mitigation:**
  - Chosen stack has excellent documentation (python-telegram-bot, Claude SDK)
  - Start with POC to validate approach (Days 1-2)
  - Break implementation into small, testable modules
  - Leverage AI assistance (Claude Code, GitHub Copilot)
- **Contingency:** Consider hiring experienced Python developer for 2-3 days mentorship

**RISK-005: Claude API Question/Answer Mapping Accuracy Below 85%**
- **Likelihood:** Medium
- **Impact:** Medium (report quality)
- **Description:** AI struggles to correctly map answers to questions in complex conversations
- **Mitigation:**
  - Craft detailed prompt with examples for Claude API
  - Iterate on prompt engineering in POC phase
  - Test with real conversation samples during development
  - Consider fallback: mark as "unclear mapping" if confidence low
- **Contingency:** Add manual review step or simplify to just question detection (no mapping)

### Assumptions

**ASSUMPTION-001: Message Volume Stable**
- **Assumption:** Each chat averages 50-200 messages per day
- **Impact if wrong:** Higher costs (Claude API), slower processing, potential scalability issues
- **Validation:** Monitor message counts for first 2 weeks
- **Action if violated:** Implement sampling (e.g., analyze every 2nd message) or increase budget

**ASSUMPTION-002: Telegram Bot API Access**
- **Assumption:** Bot can read all messages in configured group chats
- **Impact if wrong:** Cannot collect messages, core functionality broken
- **Validation:** Test bot permissions in sample group chat during POC
- **Action if violated:** Request admin privileges or use Telegram channels instead

**ASSUMPTION-003: Render Free Tier Sufficient for POC**
- **Assumption:** Free tier (512MB RAM, sleeps after 15min) works for initial testing
- **Impact if wrong:** Need to pay $7/month immediately
- **Validation:** Deploy POC to free tier, monitor resource usage
- **Action if violated:** Upgrade to Hobby tier ($7/mo)

**ASSUMPTION-004: Single-Process Deployment Sufficient**
- **Assumption:** 15-50 chats can be handled by single Docker container
- **Impact if wrong:** Need distributed architecture (more complex)
- **Validation:** Load test with simulated 50 chats × 200 messages
- **Action if violated:** Migrate to Celery + Redis for distributed processing

**ASSUMPTION-005: 48-Hour Data Retention Acceptable**
- **Assumption:** No regulatory or business requirement for longer message storage
- **Impact if wrong:** Compliance issues or inability to generate historical reports
- **Validation:** Confirm with stakeholders during POC
- **Action if violated:** Extend retention period or implement archival to separate storage

### Open Questions

**QUESTION-001: Timezone Handling**
- **Question:** What timezone should "10:00 AM" use? Server timezone or specific region?
- **Owner:** Vladimir (clarify with stakeholders)
- **Blocking:** Medium (affects scheduler configuration)
- **Resolution Target:** Before deployment
- **Proposed Answer:** Use UTC+3 (Moscow time) or configure per-chat

**QUESTION-002: Multi-Language Message Support**
- **Question:** Will messages be in multiple languages (Russian, English, etc.)?
- **Owner:** Vladimir
- **Blocking:** Low (Claude API handles multiple languages)
- **Resolution Target:** POC phase
- **Proposed Answer:** Test with Russian and English samples, no special handling needed

**QUESTION-003: Admin Access and Monitoring**
- **Question:** Who should receive alerts when errors occur? How to access logs?
- **Owner:** Vladimir
- **Blocking:** Low (can be added post-MVP)
- **Resolution Target:** Before production deployment
- **Proposed Answer:** Send errors to configured admin Telegram user ID

**QUESTION-004: Chat Configuration Management**
- **Question:** How are chats added/removed from monitoring? Manual DB edit or admin command?
- **Owner:** Vladimir
- **Blocking:** Medium (affects MVP scope)
- **Resolution Target:** Day 3 of development
- **Proposed Answer:** Manual DB seeding for MVP, admin commands in v2.0

**QUESTION-005: Report History Retention**
- **Question:** How long should generated reports be stored in the database?
- **Owner:** Vladimir
- **Blocking:** Low (doesn't affect core functionality)
- **Resolution Target:** Before production
- **Proposed Answer:** Keep reports for 30 days, then archive or delete

## Test Strategy Summary

### Testing Pyramid

```
           ╱╲
          ╱  ╲
         ╱ E2E ╲         5% - End-to-End (Full system in Docker)
        ╱──────╲
       ╱        ╲
      ╱Integration╲      35% - Integration (API calls, DB, services)
     ╱────────────╲
    ╱              ╲
   ╱      Unit      ╲    60% - Unit (Business logic, pure functions)
  ╱────────────────╲
```

### Test Levels

**Unit Tests (60% coverage target):**
- **Scope:** Business logic, data transformations, utility functions
- **Framework:** pytest
- **Examples:**
  - `test_message_analyzer.py`: Test question detection logic
  - `test_report_generator.py`: Test report formatting
  - `test_response_time_calculator.py`: Test time categorization
- **Mocking:** Mock Claude API responses, Telegram API calls
- **Run Frequency:** On every commit (pre-commit hook + CI)

**Integration Tests (35% coverage target):**
- **Scope:** Component interactions, database operations, external API calls
- **Framework:** pytest + pytest-asyncio
- **Examples:**
  - `test_message_collection_flow.py`: Bot receives message → saves to DB
  - `test_report_generation_flow.py`: Fetch messages → analyze → format → send
  - `test_claude_api_integration.py`: Real Claude API batch call (with test account)
- **Database:** Use in-memory SQLite for speed
- **Run Frequency:** On pull request + before deployment

**End-to-End Tests (5% coverage target):**
- **Scope:** Full system behavior in production-like environment
- **Framework:** pytest + Docker
- **Examples:**
  - `test_full_report_cycle.py`: Seed messages → trigger scheduler → verify report sent
  - `test_deployment.py`: Build Docker image → run container → health check
- **Environment:** Docker Compose with real Telegram test bot
- **Run Frequency:** Before production deployment, weekly regression

### Test Coverage by Acceptance Criteria

| AC ID | Test Type | Test File | Coverage |
|-------|-----------|-----------|----------|
| AC-001 | Integration | `test_message_collection.py` | Message save flow |
| AC-002 | Integration | `test_scheduler.py` | APScheduler trigger |
| AC-003 | Unit + Integration | `test_question_detection.py` | Claude API question analysis |
| AC-004 | Unit + Integration | `test_answer_mapping.py` | Q→A mapping logic |
| AC-005 | Unit | `test_response_time.py` | Time categorization |
| AC-006 | Unit | `test_report_format.py` | Markdown generation |
| AC-007 | Integration | `test_report_delivery_conditions.py` | Conditional sending |
| AC-008 | Integration | `test_report_delivery.py` | Telegram send |
| AC-009 | Integration | `test_cleanup.py` | Old message deletion |
| AC-010 | Integration | `test_error_handling.py` | Graceful degradation |
| AC-011 | E2E | `test_docker_deployment.py` | Container startup |
| AC-012 | E2E | `.github/workflows/ci.yml` | CI/CD pipeline |

### Testing Tools & Frameworks

**Core Testing:**
- `pytest 7.4.3` - Test runner
- `pytest-asyncio 0.21.1` - Async test support
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities

**Test Data:**
- `factory_boy` - Test fixture generation
- `faker` - Fake data generation (names, messages)

**API Testing:**
- `responses` - Mock HTTP requests
- `vcr.py` - Record/replay HTTP interactions

**Database Testing:**
- In-memory SQLite for speed
- `pytest-alembic` - Migration testing

### Test Execution Strategy

**Local Development:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_message_analyzer.py

# Run tests matching pattern
pytest -k "test_question"
```

**CI Pipeline (GitHub Actions):**
```yaml
1. Install dependencies
2. Run linting (black, mypy)
3. Run unit tests
4. Run integration tests
5. Generate coverage report (fail if <80%)
6. Build Docker image
7. Run E2E tests in Docker
8. Deploy to Render (if on main branch)
```

**Pre-Production Checklist:**
- [ ] All acceptance criteria have corresponding tests
- [ ] Test coverage ≥80% overall
- [ ] All tests passing in CI
- [ ] Manual smoke test in staging environment
- [ ] Load test with 50 chats × 200 messages
- [ ] Security scan (dependency vulnerabilities)

### Known Testing Limitations

1. **Claude API Testing:**
   - Cannot fully test in CI (costs money)
   - Use mocked responses for unit tests
   - Manual testing with real API during POC

2. **Telegram Bot API Testing:**
   - Requires test bot and test groups
   - May hit rate limits during testing
   - Mock for unit tests, real API for integration

3. **Scheduler Testing:**
   - Cannot test exact 10:00 AM trigger in CI
   - Use manual time override for testing
   - Validate cron expression syntax separately

4. **Time-based Testing:**
   - 24-hour windows difficult to test quickly
   - Use time mocking (freezegun library)
   - Verify logic, validate in production

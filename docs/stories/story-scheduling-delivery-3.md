# Story: Report Delivery & Scheduling

**Story ID:** IMF-MVP-3
**Epic:** IMF-MVP
**Status:** ContextReadyDraft
**Priority:** High
**Estimate:** 4 points
**Assignee:** TBD

---

## User Story

**As a** team member monitoring partner communication
**I want** daily reports automatically delivered to each chat at 10:00 AM
**So that** I have timely insights without manual intervention

## Acceptance Criteria

### AC-001: Scheduler Setup
- [ ] APScheduler configured and initialized
- [ ] Cron trigger set for 10:00 AM daily (`0 10 * * *`)
- [ ] Scheduler job persisted to SQLite (survives restarts)
- [ ] Scheduler starts automatically with bot
- [ ] Health check confirms scheduler is active

### AC-002: Report Delivery Timing
- [ ] Reports triggered at 10:00 AM ±2 minutes
- [ ] All enabled chats processed in sequence
- [ ] Delivery completes within 15 minutes (15 chats × 5 min max)
- [ ] Timing verified over 3 consecutive days

### AC-003: Delivery Logic
- [ ] Report sent ONLY if questions detected (≥1 question)
- [ ] If 0 questions, no report sent and logged
- [ ] Reports sent to correct chat_id
- [ ] Delivery confirmation received from Telegram API
- [ ] `last_report_sent` timestamp updated in database

### AC-004: Error Handling
- [ ] If Claude API fails for one chat, continue with others
- [ ] If Telegram send fails, log error and continue
- [ ] No cascading failures across chats
- [ ] Admin notification if >50% chats fail
- [ ] Errors logged with context (chat_id, timestamp, details)

### AC-005: Rate Limiting
- [ ] Reports staggered (5-second intervals between chats)
- [ ] Telegram rate limit respected (30 msg/sec)
- [ ] Retry logic with exponential backoff implemented
- [ ] Rate limit errors (429) handled gracefully

### AC-006: Report Content Delivery
- [ ] Markdown formatting renders correctly in Telegram
- [ ] #IMFReport tag included for searchability
- [ ] Links and formatting preserved
- [ ] Long reports (>4096 chars) split correctly

### AC-007: Docker Deployment
- [ ] Dockerfile created with proper configuration
- [ ] Container runs as non-root user
- [ ] Environment variables injected securely
- [ ] Health check endpoint responds (GET /health)
- [ ] Container restart preserves scheduler state

### AC-008: CI/CD Pipeline
- [ ] GitHub Actions workflow configured
- [ ] Tests run on every push
- [ ] Docker image built automatically
- [ ] Deployment to Render triggered on main branch
- [ ] Deployment completes within 10 minutes

## Technical Details

**Components to Implement:**
- `SchedulerService` - APScheduler management
- `ReportDeliveryService` - Report sending orchestration
- `ConfigService` - Environment configuration
- Health check endpoint
- Dockerfile
- GitHub Actions workflow

**APScheduler Configuration:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.db')
}

scheduler = AsyncIOScheduler(jobstores=jobstores)
scheduler.add_job(
    generate_daily_reports,
    trigger='cron',
    hour=10,
    minute=0,
    id='daily_reports',
    replace_existing=True
)
```

**Dockerfile Structure:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN adduser --disabled-password --gecos '' botuser
USER botuser
CMD ["python", "src/main.py"]
```

**GitHub Actions Workflow:**
```yaml
name: CI/CD Pipeline
on:
  push:
    branches: [main]
jobs:
  test-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - Checkout code
      - Run tests
      - Build Docker image
      - Deploy to Render
```

**Dependencies:**
- APScheduler==3.10.4
- python-dotenv==1.0.0

## Testing Strategy

**Unit Tests:**
- Test scheduler configuration
- Test report delivery logic
- Test rate limiting logic
- Test error handling

**Integration Tests:**
- Test scheduler triggers report generation
- Test full delivery flow (mock Telegram API)
- Test graceful degradation on errors
- Test rate limit handling

**End-to-End Tests:**
- Build Docker image and run container
- Verify health check endpoint
- Test CI/CD pipeline with test deployment
- Verify scheduler survives container restart

**Manual Testing:**
- Deploy to Render staging environment
- Monitor 3 consecutive 10:00 AM deliveries
- Test with real Telegram test group

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests written and passing (coverage ≥80%)
- [ ] Integration tests passing
- [ ] E2E tests passing
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Docker deployment verified
- [ ] CI/CD pipeline working
- [ ] Successfully deployed to Render
- [ ] 3-day delivery timing verified

## Deployment Checklist

**Pre-Deployment:**
- [ ] Telegram Bot token obtained
- [ ] Claude API key obtained
- [ ] Render account created
- [ ] GitHub repository configured
- [ ] Environment variables documented

**Deployment:**
- [ ] Push to main branch
- [ ] CI/CD pipeline completes successfully
- [ ] Container starts on Render
- [ ] Health check passes
- [ ] Scheduler initialized
- [ ] First report delivered successfully

**Post-Deployment:**
- [ ] Monitor logs for errors
- [ ] Verify costs tracking
- [ ] Check scheduler reliability (3 days)
- [ ] Document any issues/learnings

## Configuration Required

**Environment Variables:**
```bash
TELEGRAM_BOT_TOKEN=<bot_token>
ANTHROPIC_API_KEY=<api_key>
CHAT_IDS=123456,789012,345678  # Comma-separated
LOG_LEVEL=INFO
TIMEZONE=UTC+3
REPORT_TIME_HOUR=10
CLEANUP_TIME_HOUR=2
```

## Notes

- Single-process deployment is critical (APScheduler limitation)
- Monitor Render free tier sleep behavior (may need Hobby tier)
- Health check prevents Render from sleeping container
- Consider adding admin notification for daily summary

---

## Dev Agent Record

### Context Reference
- Story Context File: `docs/stories/story-context-IMF-MVP.IMF-MVP-3.xml` (Generated: 2025-10-23)

---

**Created:** 2025-10-23
**Updated:** 2025-10-23

# Epic: Telegram Bot MVP - Daily Report Generation

**Epic ID:** IMF-MVP
**Status:** Planning
**Priority:** High
**Start Date:** 2025-10-23
**Target Completion:** TBD

---

## Epic Overview

Create a Telegram bot that monitors 15 partner communication chats, collects messages over 24-hour periods, analyzes question-answer patterns using Claude AI, and delivers structured daily reports at 10:00 AM. The goal is to improve transparency in partner communication, track response times, and identify unanswered questions.

## Business Value

- **Transparency:** Clear visibility into partner communication patterns
- **Accountability:** Track question response times by category
- **Quality:** Identify unanswered questions to improve service
- **Efficiency:** Automated daily reporting saves manual review time

## Success Criteria

- Bot successfully monitors 15 configured chats
- Daily reports delivered at 10:00 AM ±2 minutes
- AI accurately identifies questions (>90%) and maps answers (>85%)
- Response time categorization (<1h, 1-4h, 4-24h, >24h)
- Docker deployment with CI/CD pipeline
- Total cost < $50/month

## Technical Approach

**Architecture Pattern:** Event-Driven Scheduled Bot (Single-Process)

**Technology Stack:**
- python-telegram-bot v20+ (Bot framework)
- APScheduler 3.11+ (Task scheduling)
- SQLite 3 (Database)
- Anthropic Claude API with Message Batches (AI analysis, 50% cost savings)
- Render platform (Hosting)
- GitHub Actions (CI/CD)

**Key Constraints:**
- Single-server deployment (sufficient for 15-50 chats)
- 48-hour message retention (GDPR-friendly)
- Beginner-friendly stack
- Budget: < $50/month

## Stories

| Story ID | Title | Status | Priority |
|----------|-------|--------|----------|
| IMF-MVP-1 | Message Collection & Storage | TODO | High |
| IMF-MVP-2 | AI Analysis & Report Generation | TODO | High |
| IMF-MVP-3 | Report Delivery & Scheduling | TODO | High |

## Dependencies

- Telegram Bot API token
- Anthropic Claude API key
- Render deployment account
- GitHub repository setup

## Risks

1. **Claude API costs exceed budget** - Mitigation: Use batch processing (50% discount), implement cost tracking
2. **APScheduler reliability** - Mitigation: Single-process deployment, health checks
3. **Learning curve for beginner** - Mitigation: Excellent documentation, AI assistance

## References

- Technical Specification: `/docs/tech-spec-epic-IMF-MVP.md`
- Research Document: `/docs/research-technical-2025-10-23.md`
- Brainstorming Results: `/docs/brainstorming-session-results-2025-10-23.md`

---

**Last Updated:** 2025-10-23
**Owner:** Vladimir

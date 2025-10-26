# ADR-001: Migration from Polling to Webhook Mode

## Status
**Proposed** (Ready for Implementation)

## Date
2025-10-26

## Context

The current Telegram bot implementation uses **long polling** to receive updates from the Telegram API. While functional for MVP, this approach has several limitations as the system scales:

### Current Architecture (Polling)
```
Telegram API ← [HTTP GET every ~1s] ← Bot Application
├── Constant network traffic
├── 1-2 second latency per message
├── CPU overhead from continuous polling
└── Limited to single instance deployment
```

### Problems with Current Approach

1. **Latency**: 1-2 second delay between message sent and bot receipt
2. **Resource Usage**: Continuous HTTP requests consume CPU and network bandwidth
3. **Scalability**: Difficult to horizontally scale (only one instance can poll)
4. **API Conflicts**: Rolling deployments cause temporary Telegram API conflicts
5. **Cost**: Higher server resource requirements for constant polling

### Benefits of Webhook Mode

| Metric | Polling (Current) | Webhook (Proposed) |
|--------|-------------------|-------------------|
| **Latency** | 1-2 seconds | < 100ms |
| **Server Load** | High (continuous requests) | Low (push-only) |
| **Scalability** | Single instance | Multiple instances |
| **Network Traffic** | Constant outbound | Inbound only |
| **Deployment** | API conflicts | Zero-downtime |

## Decision

We will **migrate to webhook mode** for production deployments while maintaining polling as a fallback for local development.

### Implementation Strategy

#### Phase 1: Infrastructure (Completed ✅)
- [x] WebhookServer with aiohttp (src/services/webhook_server.py)
- [x] Security validation (IP whitelist + secret token)
- [x] Settings configuration (webhook_enabled, webhook_url, etc.)

#### Phase 2: Integration (In Progress 🔄)
- [x] TelegramBotService.setup_webhook()
- [x] TelegramBotService.remove_webhook()
- [ ] main.py conditional startup logic
- [ ] Health check integration

#### Phase 3: Deployment
- [ ] Update render.yaml (worker → web service type)
- [ ] Configure environment variables in Render dashboard
- [ ] Generate and set WEBHOOK_SECRET_TOKEN
- [ ] Deploy and verify

#### Phase 4: Validation & Monitoring
- [ ] Integration tests for webhook flow
- [ ] Monitor latency improvements
- [ ] Verify zero-downtime deployments
- [ ] Document rollback procedure

## Technical Details

### Security Architecture

```python
# Multi-layer security validation
1. IP Whitelist:
   - 149.154.160.0/20 (Primary Telegram servers)
   - 91.108.4.0/22 (EU Telegram servers)

2. Secret Token:
   - X-Telegram-Bot-Api-Secret-Token header
   - Constant-time comparison (timing attack prevention)

3. HTTPS Only:
   - Telegram requires TLS 1.2+
   - Render provides automatic SSL/TLS
```

### Webhook Flow

```
Telegram API → POST /webhook → WebhookServer
                                     ↓
                          [Security Validation]
                                     ↓
                          [Parse JSON to Update]
                                     ↓
                          application.process_update()
                                     ↓
                          [Message Handlers]
```

### Fallback Strategy

```python
if settings.webhook_enabled:
    # Production: Webhook mode
    await webhook_server.start()
    await bot_service.setup_webhook(...)
else:
    # Development/Fallback: Polling mode
    await application.updater.start_polling(...)
```

## Consequences

### Positive

1. **Performance**: Near-instant message delivery (< 100ms vs 1-2s)
2. **Cost Savings**: 50-70% reduction in CPU usage
3. **Scalability**: Enables horizontal scaling for high-traffic scenarios
4. **Reliability**: Zero-downtime deployments (no API conflicts)
5. **User Experience**: Faster bot responses improve user satisfaction

### Negative

1. **Complexity**: Additional HTTP server component to maintain
2. **Local Development**: Requires ngrok/tunnel for testing webhooks locally
3. **Debugging**: Slightly harder to debug (push vs pull model)
4. **Infrastructure Dependency**: Requires public HTTPS endpoint

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Webhook registration fails | Low | High | Automatic fallback to polling |
| Invalid IP validation | Medium | Medium | Comprehensive logging + monitoring |
| DDoS via webhook | Low | Medium | Rate limiting + IP whitelist |
| Secret token leaks | Low | High | Secrets management (env vars only) |

## Alternatives Considered

### Alternative 1: Keep Polling
- **Pro**: Simpler, no infrastructure changes
- **Con**: Doesn't solve scalability/latency issues
- **Decision**: Rejected - doesn't meet long-term requirements

### Alternative 2: Hybrid Mode (Webhook + Polling Fallback)
- **Pro**: Maximum reliability
- **Con**: Increased complexity
- **Decision**: Partially adopted - polling available via config flag

### Alternative 3: Use Telegram Bot API Server (Local)
- **Pro**: Full control over API layer
- **Con**: Requires self-hosting Telegram infrastructure
- **Decision**: Rejected - overkill for current scale

## Implementation Plan

### Code Changes Required

```python
# 1. main.py modifications (src/main.py)
from src.services.webhook_server import WebhookServer

class BotApplication:
    def __init__(self):
        self.webhook_server = None if not settings.webhook_enabled \
                             else WebhookServer(application, settings)

    async def start(self):
        if settings.webhook_enabled:
            await self.webhook_server.start()
            await self.bot_service.setup_webhook(
                webhook_url=settings.webhook_url,
                secret_token=settings.webhook_secret_token
            )
        else:
            await self.application.updater.start_polling(...)
```

### Infrastructure Changes Required

```yaml
# render.yaml
services:
  - type: web  # ← CRITICAL: Changed from 'worker'
    envVars:
      - key: WEBHOOK_ENABLED
        value: "true"
      - key: WEBHOOK_URL
        value: "https://telegram-imf-bot.onrender.com/webhook"
      - key: WEBHOOK_SECRET_TOKEN
        sync: false  # Sensitive secret
```

### Environment Variables

```env
# New variables for webhook mode
WEBHOOK_ENABLED=true
WEBHOOK_URL=https://your-app.onrender.com/webhook
WEBHOOK_SECRET_TOKEN=<generate-random-64-char-string>
WEBHOOK_PORT=8080
```

## Testing Strategy

### Unit Tests
- [x] WebhookServer.handle_webhook() validation logic
- [ ] IP whitelist validation
- [ ] Secret token verification
- [ ] Update parsing and dispatch

### Integration Tests
- [ ] End-to-end webhook flow
- [ ] Fallback to polling on webhook failure
- [ ] Graceful shutdown during webhook processing

### Manual Testing
1. Deploy to staging with webhook mode
2. Send test messages, measure latency
3. Verify security headers
4. Test rolling deployment (zero-downtime)

## Rollback Plan

If webhook mode fails in production:

```bash
# 1. Disable webhook via Render dashboard
WEBHOOK_ENABLED=false

# 2. (Optional) Explicitly remove webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"

# 3. Redeploy - bot will use polling mode
git push origin main
```

## References

- [Telegram Bot API: Webhooks](https://core.telegram.org/bots/api#setwebhook)
- [Telegram Webhook Guide](https://core.telegram.org/bots/webhooks)
- [python-telegram-bot: Webhooks](https://docs.python-telegram-bot.org/en/stable/examples.webhookbot.html)
- [Render: Web Services](https://render.com/docs/web-services)

## Approval

- **Architect**: Winston (BMad AI Architect)
- **Developer**: Vladimir
- **Date**: 2025-10-26
- **Status**: Ready for implementation

---

**Next Steps**:
1. Complete main.py integration (see migration guide)
2. Update render.yaml service type
3. Generate WEBHOOK_SECRET_TOKEN
4. Deploy to staging for validation
5. Deploy to production with monitoring

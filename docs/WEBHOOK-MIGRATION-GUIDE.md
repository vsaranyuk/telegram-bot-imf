# Webhook Migration Guide

**Complete step-by-step guide for migrating from polling to webhook mode**

---

## 📋 Overview

This guide walks you through migrating the Telegram bot from long polling to webhook mode for production deployment.

**Estimated Time**: 30-45 minutes
**Difficulty**: Intermediate
**Prerequisites**: Access to Render dashboard, bot deployed

---

## ✅ Pre-Migration Checklist

Before starting, ensure you have:

- [ ] Access to Render dashboard
- [ ] Bot currently running in polling mode
- [ ] Git repository access
- [ ] Understanding of environment variables

---

## 🚀 Step-by-Step Migration

### Step 1: Generate Webhook Secret Token

Generate a secure random secret token (64 characters recommended):

```bash
# Option 1: Using Python
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Option 2: Using OpenSSL
openssl rand -base64 48

# Option 3: Online generator
# https://www.random.org/strings/
```

**Save this token securely** - you'll need it for Render configuration.

---

### Step 2: Update render.yaml

**CRITICAL**: Change service type from `worker` to `web`.

```yaml
# render.yaml
services:
  - type: web  # ← CHANGED from 'worker'
    name: telegram-imf-bot
    runtime: python
    runtimeVersion: "3.11"
    region: frankfurt
    plan: starter
    branch: main
    buildCommand: pip install -r requirements.txt
    startCommand: python -m src.main

    # Health check configuration
    healthCheckPath: /health
    healthCheckInterval: 30
    shutdownSeconds: 45

    envVars:
      # Existing variables
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: ADMIN_USER_ID
        sync: false
      - key: DATABASE_URL
        value: sqlite:///./bot_data.db
      - key: LOG_LEVEL
        value: DEBUG
      - key: MESSAGE_RETENTION_HOURS
        value: 48
      - key: ENVIRONMENT
        value: production
      - key: PORT
        value: 8080

      # NEW: Webhook configuration
      - key: WEBHOOK_ENABLED
        value: "true"
      - key: WEBHOOK_URL
        value: "https://telegram-imf-bot.onrender.com/webhook"
      - key: WEBHOOK_SECRET_TOKEN
        sync: false  # Set manually in dashboard
      - key: WEBHOOK_PORT
        value: 8080

    autoDeploy: true
```

**Important Notes**:
- `type: web` enables public HTTPS endpoint
- `WEBHOOK_URL` must match your Render service URL
- Replace `telegram-imf-bot` with your actual service name

---

### Step 3: Update .env.example

Add webhook configuration to `.env.example`:

```env
# Existing configuration...

# Webhook Configuration (Production only)
WEBHOOK_ENABLED=false
WEBHOOK_URL=
WEBHOOK_SECRET_TOKEN=
WEBHOOK_PORT=8080
```

---

### Step 4: Configure Render Environment Variables

1. **Go to Render Dashboard**
   - Navigate to your service
   - Click "Environment" tab

2. **Add/Update Variables**:

| Variable | Value | Notes |
|----------|-------|-------|
| `WEBHOOK_ENABLED` | `true` | Enable webhook mode |
| `WEBHOOK_URL` | `https://your-app.onrender.com/webhook` | Replace with your URL |
| `WEBHOOK_SECRET_TOKEN` | `<paste-generated-token>` | From Step 1 |
| `WEBHOOK_PORT` | `8080` | Default port |

3. **Click "Save Changes"**

---

### Step 5: Commit and Push Changes

```bash
# Stage changes
git add render.yaml .env.example

# Commit with descriptive message
git commit -m "feat: Enable webhook mode for production deployment

- Changed service type from worker to web in render.yaml
- Added webhook environment variables
- Configured HTTPS endpoint for Telegram webhooks

Refs: ADR-001-webhook-migration"

# Push to trigger deployment
git push origin main
```

---

### Step 6: Monitor Deployment

Watch the deployment process in Render:

```bash
# Option 1: Render Dashboard
# Navigate to "Events" tab and watch deployment logs

# Option 2: CLI (if using Render CLI)
render logs --tail

# Option 3: GitHub Actions
gh run list --limit 1
gh run view <run-id> --log
```

**Expected deployment time**: 3-5 minutes

---

### Step 7: Verify Webhook Registration

After deployment completes, check if webhook is registered:

```bash
# Check webhook info via Telegram API
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo" | jq

# Expected response:
# {
#   "ok": true,
#   "result": {
#     "url": "https://your-app.onrender.com/webhook",
#     "has_custom_certificate": false,
#     "pending_update_count": 0,
#     "max_connections": 40
#   }
# }
```

**Green flags** ✅:
- `url` matches your WEBHOOK_URL
- `pending_update_count` is low (< 10)
- No `last_error_date` or `last_error_message`

**Red flags** ⚠️:
- `url` is empty → Webhook not registered
- `last_error_message` present → Check logs

---

### Step 8: Test Webhook Functionality

1. **Send test message to bot**:
   - Open Telegram
   - Find your bot
   - Send `/start` or any message

2. **Check response latency**:
   ```
   Expected: < 200ms (vs 1-2s with polling)
   ```

3. **Verify logs in Render**:
   ```
   Look for:
   ✅ Webhook server started successfully on 0.0.0.0:8080
   ✅ Webhook registered successfully
   📨 Webhook request from <Telegram IP>
   ✅ Processing update <update_id>
   ```

---

### Step 9: Performance Validation

Compare before/after metrics:

| Metric | Polling (Before) | Webhook (After) |
|--------|------------------|-----------------|
| **Message Latency** | 1-2 seconds | < 200ms |
| **CPU Usage** | ~15-20% | ~5-10% |
| **Memory Usage** | Similar | Similar |
| **Network Traffic** | Constant outbound | Inbound only |

---

## 🔧 Troubleshooting

### Issue 1: Webhook Not Registered

**Symptoms**: `getWebhookInfo` shows empty URL

**Solutions**:
```bash
# 1. Check environment variables in Render
# Verify WEBHOOK_ENABLED=true

# 2. Check application logs
# Look for "Failed to set webhook" errors

# 3. Manually register webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://your-app.onrender.com/webhook" \
  -d "secret_token=<YOUR_SECRET>"
```

---

### Issue 2: 403 Forbidden in Logs

**Symptoms**: `⚠️ Rejected webhook from unauthorized IP`

**Cause**: Request not from Telegram servers

**Solutions**:
1. Verify IP ranges in `webhook_server.py:29-32`
2. Check if behind proxy (X-Forwarded-For header)
3. Temporarily disable IP validation for debugging

---

### Issue 3: 401 Unauthorized in Logs

**Symptoms**: `⚠️ Rejected webhook with invalid secret token`

**Cause**: Secret token mismatch

**Solutions**:
```bash
# 1. Verify secret in Render dashboard matches Telegram
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo" | jq .result.secret_token

# 2. Re-register webhook with correct secret
# (See Issue 1, solution 3)
```

---

### Issue 4: Bot Not Responding

**Symptoms**: Messages sent but no response

**Solutions**:
```bash
# 1. Check health endpoint
curl https://your-app.onrender.com/health
# Should return: 200 OK

# 2. Check bot is running
# Look for "Bot is now running!" in logs

# 3. Verify message handlers registered
# Check logs for "Message handlers registered"
```

---

## 🔄 Rollback Plan

If webhook mode fails, rollback to polling:

### Quick Rollback (5 minutes)

```bash
# 1. Update environment variable in Render
WEBHOOK_ENABLED=false

# 2. Redeploy (auto-deploy enabled)
# Or manually trigger redeploy in Render dashboard

# 3. Verify polling resumed
# Check logs for "Bot polling started successfully"
```

### Full Rollback (10 minutes)

```bash
# 1. Revert code changes
git revert HEAD
git push origin main

# 2. Remove webhook from Telegram
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"

# 3. Update Render service type back to worker
# Edit render.yaml: type: worker
# Push changes
```

---

## 📊 Post-Migration Monitoring

Monitor these metrics for 24-48 hours:

### Application Metrics
- [ ] Message delivery latency (< 200ms expected)
- [ ] Error rate in logs (< 1% expected)
- [ ] Memory usage (should be similar)
- [ ] CPU usage (50-70% reduction expected)

### Telegram Metrics
```bash
# Check webhook health daily
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo" | jq

# Monitor:
- pending_update_count (< 10 is healthy)
- last_error_date (should not increase)
```

### Render Metrics
- **Response Time**: Dashboard → Metrics → Response Time
- **Error Rate**: Dashboard → Metrics → Error Rate
- **Deployment Success**: All deployments should succeed

---

## 🎯 Success Criteria

Migration is successful when:

- [x] Webhook registered (getWebhookInfo shows correct URL)
- [x] Bot responds to messages
- [x] Latency < 200ms
- [x] No errors in logs for 1 hour
- [x] Zero-downtime deployment works
- [x] Health check passes

---

## 📚 Additional Resources

- [ADR-001: Webhook Migration](./architecture/ADR-001-webhook-migration.md)
- [WebhookServer Source](../src/services/webhook_server.py)
- [Telegram Webhook Docs](https://core.telegram.org/bots/webhooks)
- [Render Web Services](https://render.com/docs/web-services)

---

## 🆘 Need Help?

1. **Check logs first**: Most issues visible in Render logs
2. **Verify configuration**: Double-check all environment variables
3. **Test endpoints**: Use `curl` to test `/health` and `/webhook`
4. **Rollback if needed**: Don't hesitate to rollback and investigate

---

**Last Updated**: 2025-10-26
**Version**: 1.0
**Author**: Vladimir + Winston (BMad Architect)

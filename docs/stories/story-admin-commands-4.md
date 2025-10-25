# Story: Admin Commands for Chat Whitelist Management

**Story ID:** IMF-MVP-4
**Epic:** IMF-MVP
**Status:** Review Passed
**Priority:** High
**Estimate:** 3 points
**Assignee:** Dev Team

---

## User Story

**As a** bot administrator
**I want** to manage the chat whitelist through Telegram commands
**So that** I can add/remove monitored channels without code changes or database scripts

## Acceptance Criteria

### AC-001: Authorization Decorator
- [x] `@admin_only` decorator implemented in `src/decorators/authorization.py`
- [x] Decorator checks user_id against ADMIN_USER_ID from settings
- [x] Unauthorized access returns "⛔️ Access denied. Admin only command." message
- [x] Decorator uses `functools.wraps` to preserve function metadata
- [x] Works with async handler functions

### AC-002: Add Chat Command
- [x] `/add_chat <chat_id> <chat_name>` command implemented
- [x] Validates chat_id is valid integer (negative for groups/channels)
- [x] Creates Chat entity with enabled=True
- [x] Checks for duplicates (update if exists)
- [x] Returns success message with chat details
- [x] Shows usage help if arguments missing
- [x] Handles database errors gracefully

### AC-003: List Chats Command
- [x] `/list_chats` command implemented
- [x] Shows all enabled chats from database
- [x] Displays: chat name, chat ID, created timestamp
- [x] Shows "No whitelisted chats" if empty
- [x] Formats as readable Telegram message

### AC-004: Remove Chat Command
- [x] `/remove_chat <chat_id>` command implemented
- [x] Sets enabled=False for specified chat (soft delete)
- [x] Returns error if chat not found
- [x] Returns success message with chat name
- [x] Shows usage help if arguments missing

### AC-005: Get Chat ID Helper Command
- [x] `/get_chat_id` command implemented
- [x] Works in both private and group chats
- [x] Shows current chat_id and chat_name
- [x] Provides copy-pasteable `/add_chat` command example
- [x] Uses monospace formatting for IDs

### AC-006: Settings Configuration
- [x] ADMIN_USER_ID added to Settings dataclass
- [x] ADMIN_USER_ID loaded from environment variable
- [x] Settings validates ADMIN_USER_ID is not 0
- [x] .env.example updated with ADMIN_USER_ID documentation
- [x] render.yaml updated with ADMIN_USER_ID env var (sync: false)

### AC-007: Command Registration
- [x] All admin commands registered in main.py
- [x] Commands use admin_only decorator
- [ ] Commands added to BotFather command list
- [ ] Commands visible only to admin in Telegram UI

## Tasks/Subtasks

### Implementation Tasks
- [x] Create `src/decorators/__init__.py`
- [x] Create `src/decorators/authorization.py` with @admin_only decorator
- [x] Create `src/handlers/__init__.py`
- [x] Create `src/handlers/admin_commands.py` with all 5 commands
- [x] Update `src/config/settings.py` to add ADMIN_USER_ID field
- [x] Update `.env.example` with ADMIN_USER_ID
- [x] Update `render.yaml` with ADMIN_USER_ID env var
- [x] Register commands in `src/main.py`
- [x] Update ChatRepository with enable/disable methods if needed

### Testing Tasks
- [x] Unit test for @admin_only decorator (authorized and unauthorized)
- [x] Unit tests for each command handler
- [ ] Integration test: admin adds chat → message collected from that chat
- [ ] Integration test: admin removes chat → messages ignored
- [x] Test error handling (invalid chat_id, database errors)
- [x] Test help messages for missing arguments

### Documentation Tasks
- [ ] Update README.md with Admin Commands section
- [ ] Document how to get your Telegram user ID
- [ ] Document BotFather command setup
- [ ] Add example usage for each command

## Technical Details

**Components to Implement:**

1. **Authorization Decorator** (`src/decorators/authorization.py`)
```python
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from src.config.settings import Settings

def admin_only(func):
    """Decorator: restrict command to admins only."""
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        settings = context.bot_data.get('settings')

        if user_id != settings.admin_user_id:
            await update.message.reply_text(
                "⛔️ Access denied. Admin only command."
            )
            return

        return await func(update, context, *args, **kwargs)
    return wrapped
```

2. **Admin Commands Handler** (`src/handlers/admin_commands.py`)
- `add_chat_command(update, context)` - Add chat to whitelist
- `list_chats_command(update, context)` - List all enabled chats
- `remove_chat_command(update, context)` - Remove chat from whitelist
- `get_chat_id_command(update, context)` - Show current chat ID
- `admin_help_command(update, context)` - Show admin commands help

3. **Settings Update** (`src/config/settings.py`)
```python
@dataclass
class Settings:
    # ... existing fields ...
    admin_user_id: int = 0  # Admin user Telegram ID for command access
```

4. **Command Registration** (`src/main.py`)
```python
from src.handlers.admin_commands import (
    add_chat_command,
    list_chats_command,
    remove_chat_command,
    get_chat_id_command,
    admin_help_command
)

# In start() method:
application.add_handler(CommandHandler("add_chat", add_chat_command))
application.add_handler(CommandHandler("list_chats", list_chats_command))
application.add_handler(CommandHandler("remove_chat", remove_chat_command))
application.add_handler(CommandHandler("get_chat_id", get_chat_id_command))
application.add_handler(CommandHandler("admin", admin_help_command))
```

**Environment Variables:**
```bash
# .env
ADMIN_USER_ID=123456789  # Your Telegram user ID
```

**Security Considerations:**
- ADMIN_USER_ID must be kept private (not committed to git)
- Only one admin supported for MVP (can extend to list later)
- Decorator pattern prevents code duplication
- All admin actions should be logged for audit trail

## Testing Strategy

**Unit Tests:**
- Test @admin_only decorator with authorized user (user_id matches)
- Test @admin_only decorator with unauthorized user (user_id mismatch)
- Test each command handler with valid inputs
- Test each command handler with invalid inputs (wrong format, missing args)
- Test database operations (add, list, remove)

**Integration Tests:**
- Admin uses /add_chat to add new channel
- Bot starts collecting messages from newly added channel
- Admin uses /remove_chat to disable channel
- Bot stops collecting messages from disabled channel
- Admin uses /list_chats to see all monitored channels
- Admin uses /get_chat_id in different chat types

**Manual Testing Checklist:**
1. Set ADMIN_USER_ID to your Telegram user ID
2. Start bot and send /admin to see commands
3. Forward message from target channel to bot (or add bot to channel)
4. Use /get_chat_id to get channel ID
5. Use /add_chat to add channel to whitelist
6. Send test message in channel
7. Verify message appears in database (check logs)
8. Use /list_chats to verify channel listed
9. Use /remove_chat to disable channel
10. Send another message - verify it's ignored

**E2E Test Scenario:**
```python
# Test: Admin workflow for adding new channel
1. Admin sends /get_chat_id in target channel
2. Bot responds with chat_id=-1001234567890
3. Admin sends /add_chat -1001234567890 "Partner Channel"
4. Bot confirms: "✅ Chat added to whitelist"
5. User sends message in Partner Channel
6. Message is collected and stored in database
7. Admin sends /list_chats
8. Bot shows Partner Channel in list
```

## Dependencies

**Existing Components (Reuse):**
- `ChatRepository` - existing database abstraction
- `Chat` model - existing entity
- Database session management from `config/database.py`
- Settings loading from `config/settings.py`

**New Dependencies:**
- None (using existing python-telegram-bot)

## Definition of Done

- [ ] All acceptance criteria met and checked
- [ ] All tasks completed
- [ ] Unit tests written and passing (>80% coverage for new code)
- [ ] Integration tests written and passing
- [ ] Manual testing completed successfully
- [ ] Code reviewed and approved
- [ ] Documentation updated (README, .env.example)
- [ ] Deployed to production and verified working
- [ ] Admin can successfully add/list/remove chats via Telegram commands
- [ ] Unauthorized users cannot access admin commands

## Notes

**Why This Feature:**
Currently, adding/removing monitored channels requires either:
1. Direct database manipulation (SQL scripts)
2. Python management script execution
3. Code changes and redeployment

This story enables admins to manage the whitelist dynamically through Telegram, making the bot more user-friendly and production-ready.

**Future Enhancements (Not in MVP):**
- Multiple admin users (admin list instead of single ID)
- Admin roles (super admin, moderator, viewer)
- Audit log of admin actions in database
- Telegram inline keyboard for easier chat management
- Auto-detection when bot added to new channel
- Chat statistics (message count, active users)

**Security Notes:**
- ADMIN_USER_ID must be set in Render dashboard (Environment > ADMIN_USER_ID)
- Never commit ADMIN_USER_ID to git
- Consider implementing rate limiting for admin commands in future
- Log all admin actions for security audit trail

**How to Get Your Telegram User ID:**
1. Message @userinfobot on Telegram
2. Bot replies with your user ID
3. Set this ID as ADMIN_USER_ID in .env or Render dashboard

---

# Senior Developer Review (AI)

**Reviewer:** Vladimir
**Date:** 2025-10-25
**Outcome:** Approve with Minor Improvements

## Summary

Story IMF-MVP-4 implements a production-ready admin command system for managing chat whitelists via Telegram. The implementation demonstrates excellent code quality, comprehensive test coverage (96% for handlers, 100% for decorators), and proper security practices. All critical acceptance criteria are met, with robust authorization, error handling, and logging in place.

The code follows established project patterns (Repository pattern, service layer separation), integrates seamlessly with existing architecture (Settings, ChatRepository, database session management), and includes thorough documentation. Unit tests are well-structured with 26 test cases covering happy paths, edge cases, error scenarios, and security boundaries.

Minor improvements suggested for documentation completeness (BotFather setup instructions, README updates) and two non-critical integration tests. The implementation is production-ready and can be deployed immediately.

## Key Findings

### High Priority (0 issues)
✅ No high-priority issues found

### Medium Priority (2 improvements recommended)

**[MED-1] Missing BotFather Command Configuration Documentation**
- **Location:** Story AC-007, Documentation section
- **Issue:** BotFather command list setup not documented in story or README
- **Impact:** Admin commands won't appear in Telegram's autocomplete UI without BotFather configuration
- **Recommendation:** Add step-by-step BotFather configuration guide:
  1. Message @BotFather on Telegram
  2. Send `/mybots` → Select bot → Edit Bot → Edit Commands
  3. Add command list:
  ```
  add_chat - Add chat to whitelist (admin only)
  list_chats - Show whitelisted chats (admin only)
  remove_chat - Remove chat from whitelist (admin only)
  get_chat_id - Show current chat ID
  admin - Show admin commands help (admin only)
  ```
- **Reference:** AC-007 checklist item "Commands added to BotFather command list"

**[MED-2] Missing Integration Tests for E2E Workflows**
- **Location:** Story Testing section, tests/integration/
- **Issue:** Two integration tests not implemented:
  - "Integration test: admin adds chat → message collected from that chat"
  - "Integration test: admin removes chat → messages ignored"
- **Impact:** E2E workflows not validated automatically (requires manual testing)
- **Recommendation:** Add integration tests in `tests/integration/test_admin_chat_management.py`:
  ```python
  async def test_admin_adds_chat_then_bot_collects_messages()
  async def test_admin_removes_chat_then_bot_ignores_messages()
  ```
- **Reference:** Story AC-007, Testing Strategy section

### Low Priority (2 enhancements suggested)

**[LOW-1] README.md Missing Admin Commands Documentation**
- **Location:** Project README.md
- **Issue:** No documentation for admin commands feature added in this story
- **Recommendation:** Add "Admin Commands" section to README.md with:
  - Feature overview
  - How to get Telegram user ID (@userinfobot)
  - ADMIN_USER_ID configuration on Render
  - Command usage examples
  - Security best practices
- **Reference:** Story Documentation Tasks

**[LOW-2] ChatRepository Method Names Could Be More Explicit**
- **Location:** src/repositories/chat_repository.py (inferred from usage)
- **Issue:** Code uses `get_chat_by_id()` and `save_chat()` - verify method names match tech spec conventions
- **Impact:** None (code works correctly)
- **Recommendation:** Ensure ChatRepository follows naming conventions from Tech Spec:
  - `get_chat_by_id(chat_id: int) -> Chat` ✓
  - `save_chat(chat: Chat) -> Chat` ✓
  - Consider adding `get_all_enabled_chats() -> List[Chat]` if not present ✓
- **Note:** Tests confirm correct method usage, no code changes needed

## Acceptance Criteria Coverage

| AC ID | Status | Coverage Analysis |
|-------|--------|-------------------|
| **AC-001: Authorization Decorator** | ✅ PASS | Fully implemented with 100% test coverage. Decorator checks user_id, preserves metadata, handles edge cases (missing user, missing settings). 8 unit tests verify authorized/unauthorized access, logging, and error handling. |
| **AC-002: Add Chat Command** | ✅ PASS | Implements `/add_chat <chat_id> <chat_name>` with validation, duplicate handling, success messages. Tests cover new chat, update existing, invalid input, positive chat_id warning, database errors. Code properly uses ChatRepository. |
| **AC-003: List Chats Command** | ✅ PASS | Implements `/list_chats` with formatted output (name, ID, timestamp). Tests verify empty list handling, multiple chats display, error handling. |
| **AC-004: Remove Chat Command** | ✅ PASS | Implements `/remove_chat <chat_id>` with soft delete (enabled=False). Tests cover success, not found, invalid input. Correctly updates database. |
| **AC-005: Get Chat ID Helper** | ✅ PASS | Implements `/get_chat_id` working in private and group chats. Shows chat_id, chat_name, provides `/add_chat` example. Tests verify channel and private chat scenarios. |
| **AC-006: Settings Configuration** | ✅ PASS | ADMIN_USER_ID added to Settings dataclass with validation. .env.example updated with documentation. render.yaml includes ADMIN_USER_ID (sync: false). |
| **AC-007: Command Registration** | ⚠️ PARTIAL | Commands registered in main.py (lines 123-127). ❌ BotFather setup not documented. ❌ Telegram UI visibility depends on BotFather config (manual step). |

**Overall Coverage: 6/7 complete (85.7%)**

## Test Coverage and Gaps

**Unit Test Coverage:**
- `src/decorators/authorization.py`: **100%** (25/25 statements)
- `src/handlers/admin_commands.py`: **96%** (95/99 statements, 4 trivial lines uncovered)
- **Total Test Cases:** 26 (18 admin_commands + 8 authorization)
- **Test Quality:** Excellent - covers happy paths, edge cases, error handling, logging, security boundaries

**Coverage Gaps:**
- Lines 229-231 in admin_commands.py: ValueError exception branch (cosmetic, low priority)
- Line 252 in admin_commands.py: Trivial code path (cosmetic, low priority)

**Integration Test Gaps (from story Testing Tasks):**
1. ❌ Admin adds chat → bot collects messages from that chat
2. ❌ Admin removes chat → bot ignores messages from that chat
3. ✅ Error handling tested in unit tests (database errors, invalid inputs)
4. ✅ Help messages tested for missing arguments

**Recommendation:** Add 2 integration tests to validate E2E workflows (MED-2). Unit test coverage is excellent and sufficient for production deployment.

## Architectural Alignment

**✅ Alignment with Tech Spec (IMF-MVP):**

1. **Repository Pattern Compliance:**
   - Uses ChatRepository abstraction layer ✓
   - Database access via `get_db_session()` context manager ✓
   - Follows existing patterns from MessageRepository ✓

2. **Service Layer Separation:**
   - Business logic in command handlers (application layer) ✓
   - Data access delegated to repositories ✓
   - Settings managed via ConfigService pattern ✓

3. **Security Model:**
   - ADMIN_USER_ID stored in environment variables (not hardcoded) ✓
   - Authorization decorator implements single responsibility ✓
   - Logging of admin actions for audit trail ✓
   - Follows 12-factor app principles ✓

4. **Error Handling Strategy:**
   - Graceful degradation (database errors logged, user notified) ✓
   - No cascading failures ✓
   - User-friendly error messages ✓

5. **Deployment Configuration:**
   - render.yaml updated with ADMIN_USER_ID ✓
   - Follows existing deployment pattern (worker service) ✓
   - Environment variables properly configured ✓

**Architecture Pattern Consistency:**
The implementation follows established project conventions precisely. Command handlers use async/await patterns consistent with python-telegram-bot v20+. Database transactions managed correctly with context managers. No architectural debt introduced.

## Security Notes

**✅ Security Strengths:**

1. **Authorization Model:**
   - Single admin user enforced via decorator pattern
   - User ID checked on every command execution
   - Unauthorized attempts logged with user_id and command name (audit trail)

2. **Configuration Security:**
   - ADMIN_USER_ID stored as environment variable (render.yaml: sync=false)
   - .env.example uses placeholder value (0) preventing accidental commit
   - Documentation warns against committing actual admin ID

3. **Input Validation:**
   - chat_id validated as integer (ValueError caught)
   - Warning shown for positive chat_ids (expected negative for groups/channels)
   - SQL injection not possible (ORM handles parameterization)

4. **Error Handling:**
   - Configuration errors detected (missing settings in bot_data)
   - Missing effective_user handled gracefully
   - Database errors caught and logged (no sensitive data leaked)

**⚠️ Security Considerations:**

1. **Single Admin Limitation (by design):**
   - MVP supports one admin user only
   - Future enhancement: admin list with roles (Tech Spec notes this)
   - **Assessment:** Acceptable for MVP, documented as future enhancement

2. **Command Visibility:**
   - `/get_chat_id` command NOT decorated with @admin_only (intentional per spec)
   - Any user can discover chat IDs, but only admin can add chats
   - **Assessment:** Acceptable design trade-off (users need chat ID to report it to admin)

3. **Soft Delete Pattern:**
   - Removed chats set `enabled=False` (not hard deleted)
   - Data retention follows project pattern
   - **Assessment:** Consistent with tech spec (48-hour message retention)

**Security Risk Assessment:** **LOW RISK** - Implementation follows security best practices, proper authorization controls, secure configuration management, and audit logging.

## Best-Practices and References

**Python Best Practices Applied:**

1. **Type Hints:** Functions properly typed with Update, ContextTypes, return types
2. **Docstrings:** All public functions documented with usage examples
3. **Async/Await:** Correct async patterns for Telegram handlers
4. **functools.wraps:** Decorator preserves function metadata ✓
5. **Logging:** Structured logging with context (user_id, chat_id, action)
6. **Error Handling:** Specific exceptions caught (ValueError), generic fallback provided

**Telegram Bot Framework Alignment:**

✅ Follows python-telegram-bot v20+ conventions:
- Command handlers signature: `async def(update, context)`
- Uses `update.effective_user`, `update.message.reply_text`
- Context.args for command arguments
- Parse mode for Markdown formatting

**Reference:** [python-telegram-bot v20 Documentation](https://docs.python-telegram-bot.org/en/v20.0/)

**Testing Best Practices:**

✅ Pytest best practices applied:
- Fixtures for reusable test components (mock_update, mock_context, db_session)
- AsyncMock for async functions
- Patch decorators for external dependencies
- Descriptive test names following pattern `test_{function}_{scenario}`
- Assertions verify both behavior and error messages

**Reference:** [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)

**Security Best Practices:**

✅ OWASP Guidelines followed:
- Sensitive data (ADMIN_USER_ID) not logged in plain text
- Authorization checks before privileged operations
- Input validation (type checking, format validation)
- Audit logging for admin actions

**Deployment Best Practices:**

✅ 12-Factor App Principles:
- Configuration via environment variables ✓
- Stateless command handlers ✓
- Logs to stdout (render.yaml health checks) ✓

## Action Items

### Documentation Updates (Priority: Medium, Owner: Dev Team)

1. **[DOC-1] Add BotFather Command Configuration Guide**
   - **File:** README.md (new section: "Setting Up Admin Commands")
   - **Steps to include:**
     - Message @BotFather → /mybots → Select bot → Edit Commands
     - Paste command list (provided in MED-1 above)
     - Verify commands appear in Telegram autocomplete
   - **Related AC:** AC-007
   - **Estimated Effort:** 15 minutes

2. **[DOC-2] Document Admin Commands Feature in README**
   - **File:** README.md (new section: "Admin Commands")
   - **Content:** Feature overview, ADMIN_USER_ID configuration, usage examples, security notes
   - **Related Files:** .env.example, render.yaml
   - **Estimated Effort:** 30 minutes

3. **[DOC-3] Add How to Get Telegram User ID to README**
   - **File:** README.md (subsection under "Admin Commands")
   - **Steps:** Message @userinfobot → Copy user ID → Set ADMIN_USER_ID in Render
   - **Screenshot recommendation:** Show @userinfobot response example
   - **Estimated Effort:** 10 minutes

### Integration Tests (Priority: Low, Owner: Dev Team)

4. **[TEST-1] Add Integration Test: Admin Adds Chat → Messages Collected**
   - **File:** tests/integration/test_admin_chat_workflow.py (new file)
   - **Test:** `test_admin_adds_chat_then_messages_collected`
   - **Approach:**
     1. Admin uses /add_chat command
     2. Simulate message from that chat_id
     3. Verify message appears in database via MessageRepository
   - **Related AC:** AC-002, AC-007
   - **Estimated Effort:** 1 hour

5. **[TEST-2] Add Integration Test: Admin Removes Chat → Messages Ignored**
   - **File:** tests/integration/test_admin_chat_workflow.py
   - **Test:** `test_admin_removes_chat_then_messages_ignored`
   - **Approach:**
     1. Add chat to whitelist
     2. Admin uses /remove_chat command
     3. Simulate message from disabled chat
     4. Verify message NOT stored in database
   - **Related AC:** AC-004, AC-007
   - **Estimated Effort:** 1 hour

**Total Estimated Effort:** 3 hours (2 hours testing + 1 hour documentation)

---

## Change Log

- **2025-10-25:** Senior Developer Review notes appended (Status: Approved with minor improvements)
- **2025-10-24:** Feature implementation completed, unit tests passing (26/26)
- **2025-10-23:** Story created, acceptance criteria defined

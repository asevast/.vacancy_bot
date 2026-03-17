# Code Review: Vacancy Bot — Coding Agent Instructions

> Auto-generated from code review. Apply fixes in priority order. Each task is self-contained with exact file, location, and required change.

---

## 🔴 CRITICAL — Fix Immediately

---

### TASK-01 · Rotate Exposed Secrets

**Files:** `.env`, `delete_webhook.bat`, `delete_webhook.ps1`, `test_bot.ps1`

**Problem:** Live Telegram bot token and database password are committed in plaintext.

**Actions:**
1. Revoke the Telegram bot token via BotFather and generate a new one.
2. Change the PostgreSQL password.
3. Add `.env` to `.gitignore` if not already present.
4. Scrub git history: `git filter-branch` or use `git-secrets` / BFG Repo Cleaner.
5. Replace hardcoded token in `.bat` and `.ps1` scripts:

**`delete_webhook.bat`** — replace:
```bat
curl -X POST "https://api.telegram.org/bot963650906:AAF.../deleteWebhook"
```
with:
```bat
curl -X POST "https://api.telegram.org/bot%BOT_TOKEN%/deleteWebhook"
```

**`delete_webhook.ps1`** — replace:
```powershell
$token = "963650906:AAF..."
```
with:
```powershell
$token = $env:BOT_TOKEN
```

**`test_bot.ps1`** — same pattern as above.

---

### TASK-02 · Fix `currency` Parameter Shadowed in Loop

**File:** `app/api.py`
**Function:** `parse_hh_vacancies`

**Problem:** The function parameter `currency` is overwritten inside the vacancy loop, corrupting the API request parameter on subsequent iterations.

**Find:**
```python
currency = salary.get("currency")
if currency == "RUR":
```

**Replace with:**
```python
salary_currency = salary.get("currency")
if salary_currency == "RUR":
```

---

### TASK-03 · Fix `level` Loop Variable Shadows Profile Filter

**File:** `app/handlers.py`
**Functions:** `search_command`, `process_search_confirmation`

**Problem:** `level` is set from the user profile, then immediately clobbered by a `for level in [...]` loop.

**Find (in both functions):**
```python
for level in ["Junior", "Middle", "Senior", "mixed", "unknown"]:
    level_df = df[df['cluster'] == level]
    if not level_df.empty:
        result += f"{level}: {len(level_df)}\n"
```

**Replace with:**
```python
for cluster_label in ["Junior", "Middle", "Senior", "mixed", "unknown"]:
    level_df = df[df['cluster'] == cluster_label]
    if not level_df.empty:
        result += f"{cluster_label}: {len(level_df)}\n"
```

---

### TASK-04 · Remove Dead / Wrong Exception Handlers in `parse_adzuna_vacancies`

**File:** `app/api.py`
**Function:** `parse_adzuna_vacancies`

**Problem:** After `except Exception as e: raise`, there are four unreachable `except` blocks copy-pasted from the SuperJob function. They reference wrong log labels and will never execute.

**Find and delete entirely** (these four blocks at the end of `parse_adzuna_vacancies`):
```python
    except Timeout:
        logger.error(f"SuperJob TIMEOUT | text='{text}'")
        raise TimeoutError("Timeout when requesting SuperJob. Try again later.")
    except SSLError as e:
        logger.error(f"SuperJob SSL ERROR | {e}")
        raise ConnectionError(f"SSL error with SuperJob: {e}")
    except RequestException as e:
        logger.error(f"SuperJob ERROR | {e}")
        raise ConnectionError(f"Connection error with SuperJob: {e}")
    except Exception as e:
        logger.error(f"SuperJob UNEXPECTED | {e}")
        raise
```

---

### TASK-05 · Remove Duplicate `desc` Assignment

**File:** `app/api.py`
**Function:** `parse_hh_vacancies`

**Find (the first occurrence — remove it):**
```python
desc = str(snippet_req) + " " + str(snippet_resp)
skills = [s["name"] for s in vac.get("key_skills", [])]
desc = str(snippet_req) + " " + str(snippet_resp)
```

**Replace with:**
```python
skills = [s["name"] for s in vac.get("key_skills", [])]
desc = str(snippet_req) + " " + str(snippet_resp)
```

---

## 🟠 HIGH — Fix Before Next Release

---

### TASK-06 · Fix Database Connection Leaks

**File:** `app/db.py`
**Functions:** `cache_vacancies`, `get_cached_vacancies`, `get_cached_vacancies_since`, `add_subscription`, `list_subscriptions`, `deactivate_subscription`, `update_subscription_last_sent`

**Problem:** Connections opened manually are never closed if an exception is raised before `conn.close()`.

**Pattern to apply across all affected functions:**

```python
# BEFORE
def cache_vacancies(df):
    if df.empty:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    for _, vac in df.iterrows():
        try:
            ...
            cur.execute(...)
        except Exception as e:
            logger.error(f"DB insert error: {e}")
    conn.commit()
    cur.close()
    conn.close()

# AFTER
def cache_vacancies(df):
    if df.empty:
        return
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        try:
            for _, vac in df.iterrows():
                try:
                    ...
                    cur.execute(...)
                except Exception as e:
                    logger.error(f"DB insert error: {e}")
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()
```

Apply the same `try/finally` pattern to every function in `app/db.py` that calls `get_db_connection()`.

---

### TASK-07 · Remove Duplicate `_apply_profile_filters` Call

**File:** `app/handlers.py`
**Function:** `search_command`

**Problem:** Profile filters are applied twice — once inside the `else` (cache miss) block, and again unconditionally after it. Remove the one inside the `else` block.

**Find inside the `else` block (cache miss path):**
```python
df = pd.concat([hh_df, sj_df, habr_df, jooble_df, adzuna_df, agg_df], ignore_index=True)

df = _apply_profile_filters(df, level=level, work_format=work_format, technologies=technologies)

if not df.empty:
    safe_cache_vacancies(df)
```

**Replace with:**
```python
df = pd.concat([hh_df, sj_df, habr_df, jooble_df, adzuna_df, agg_df], ignore_index=True)

if not df.empty:
    safe_cache_vacancies(df)
```

The unconditional call after the `if cached / else` block remains and is sufficient.

---

### TASK-08 · Fix Subscription Worker Spamming Users

**File:** `app/handlers.py`
**Function:** `subscription_worker`

**Problem:** Every active subscription triggers a message every poll cycle, even if there are no new vacancies (sends "Нет новых вакансий" endlessly).

**In `subscription_worker`, add a recency check before calling `send_subscription_digest`:**

```python
from app.config import SUBSCRIPTION_POLL_SECONDS

for _, sub_row in subs_df.iterrows():
    try:
        last_sent_at = sub_row.get("last_sent_at")
        # Skip if already sent within the last poll window
        if pd.notna(last_sent_at):
            elapsed = (datetime.utcnow() - pd.Timestamp(last_sent_at).to_pydatetime()).total_seconds()
            if elapsed < SUBSCRIPTION_POLL_SECONDS:
                continue
        await send_subscription_digest(bot_instance, sub_row)
    except Exception as e:
        logger.error(f"SUBSCRIPTION ERROR | {e}")
```

Also update `send_subscription_digest` to only call `update_subscription_last_sent` when vacancies were actually found and sent (not on the "no new vacancies" path), so the timestamp accurately reflects the last real digest.

---

### TASK-09 · Fix `init_db.bat` Broken Duplicate Init

**File:** `init_db.bat`

**Problem:** File initializes the DB twice with conflicting methods and contains orphaned/unreachable code (`exit /b 1` without a preceding `if` block).

**Replace entire file contents with:**
```bat
@echo off
set PATH=%PATH%;C:\Program Files\PostgreSQL\18\bin

echo ========================================
echo Creating vacancy_bot database
echo ========================================

psql -U postgres -c "DROP DATABASE IF EXISTS vacancy_bot;"
psql -U postgres -c "CREATE DATABASE vacancy_bot;"
psql -U postgres -d vacancy_bot -f "%~dp0init_db.sql"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Database initialization failed.
    pause
    exit /b 1
)

echo.
echo Done!
pause
```

---

## 🟡 MEDIUM — Code Quality

---

### TASK-10 · Add `functools.wraps` to Log Decorators

**File:** `app/handlers.py`
**Functions:** `log_callback`, `log_message`

**Problem:** Without `@functools.wraps`, the wrapped functions lose their `__name__` and signature, breaking introspection and stack traces.

```python
# BEFORE
def log_callback(func):
    async def wrapper(callback: types.CallbackQuery, state: FSMContext = None):
        ...
    return wrapper

# AFTER
import functools

def log_callback(func):
    @functools.wraps(func)
    async def wrapper(callback: types.CallbackQuery, state: FSMContext = None):
        ...
    return wrapper
```

Apply the same fix to `log_message`.

---

### TASK-11 · Pin Dependency Versions

**File:** `requirements.txt`

**Problem:** `>=` specifiers allow silent breaking changes on major version bumps.

**Replace:**
```
aiogram>=3.0.0
aiohttp
psycopg2-binary
requests
pandas
numpy
scikit-learn
python-dotenv
```

**With pinned ranges (adjust to your currently tested versions):**
```
aiogram>=3.7,<4.0
aiohttp>=3.9,<4.0
psycopg2-binary>=2.9,<3.0
requests>=2.31,<3.0
pandas>=2.0,<3.0
numpy>=1.26,<2.0
scikit-learn>=1.3,<2.0
python-dotenv>=1.0,<2.0
```

---

### TASK-12 · Remove Deprecated `version` Key from `docker-compose.yml`

**File:** `docker-compose.yml`

**Find and delete:**
```yaml
version: '3.8'
```

Modern Docker Compose v2+ ignores this field and emits a deprecation warning.

---

### TASK-13 · Fix `event_loop` Fixture Deprecation in Tests

**File:** `tests/conftest.py`

**Problem:** Session-scoped `event_loop` fixture is deprecated in `pytest-asyncio` when using `asyncio_mode = auto`.

**Find and delete the entire fixture:**
```python
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

The `asyncio_mode = auto` setting in `pytest.ini` already handles loop management correctly.

---

### TASK-14 · Fix CI Lint Job — Missing Env Vars

**File:** `.github/workflows/ci.yml`
**Job:** `lint`

**Problem:** The `check imports` step runs `python -c "import vacancy_bot"` without setting `BOT_TOKEN`, causing the import to fail because `app/context.py` creates a `Bot` object at import time.

**Find in the `lint` job:**
```yaml
- name: Check imports
  run: |
    python -c "import vacancy_bot; print('Import successful')"
```

**Replace with:**
```yaml
- name: Check imports
  env:
    BOT_TOKEN: "1234567890:AAFakeTokenForLintCheckOnly1234567890ab"
    DB_HOST: localhost
    DB_PORT: "5432"
    DB_NAME: test_vacancy_bot
    DB_USER: test_user
    DB_PASS: test_password
  run: |
    python -c "import vacancy_bot; print('Import successful')"
```

---

## 🔵 LOW — Architecture / Design Improvements

---

### TASK-15 · Document `LIST_STORE` Limitations

**File:** `app/lists.py`

**Problem:** `LIST_STORE` is an in-memory dict — lost on restart, not safe for multi-process deployments.

**Add a comment at the top of the dict declaration:**
```python
# NOTE: LIST_STORE is intentionally in-memory.
# Limitations:
#   - All pagination tokens are lost on bot restart.
#   - Not safe for multi-process / webhook deployments.
# Future: replace with Redis or a DB-backed token table.
LIST_STORE = {}
```

No code change required for now — documentation only.

---

### TASK-16 · Add Per-User Rate Limiting on `/search`

**File:** `app/handlers.py`
**Function:** `search_command`

**Problem:** No cooldown prevents a user from spamming `/search` and exhausting HH.ru/SuperJob API rate limits.

**Add a simple in-memory cooldown at the top of the handler:**

```python
import time

_search_cooldown: dict[int, float] = {}
_SEARCH_COOLDOWN_SECONDS = 10

@dp.message(Command("search"))
async def search_command(message: types.Message):
    user_id = message.from_user.id
    now = time.monotonic()
    last = _search_cooldown.get(user_id, 0)
    if now - last < _SEARCH_COOLDOWN_SECONDS:
        remaining = int(_SEARCH_COOLDOWN_SECONDS - (now - last))
        await message.answer(f"Подождите {remaining} сек. перед следующим поиском.")
        return
    _search_cooldown[user_id] = now
    # ... rest of handler unchanged
```

---

## Checklist for Coding Agent

```
[ ] TASK-01  Rotate secrets, update .gitignore, scrub git history
[ ] TASK-02  Fix currency variable shadow in parse_hh_vacancies
[ ] TASK-03  Fix level variable shadow in search_command / process_search_confirmation
[ ] TASK-04  Delete dead SuperJob except blocks from parse_adzuna_vacancies
[ ] TASK-05  Remove duplicate desc assignment in parse_hh_vacancies
[ ] TASK-06  Wrap all db.py connection usage in try/finally
[ ] TASK-07  Remove duplicate _apply_profile_filters call in search_command
[ ] TASK-08  Fix subscription worker to skip recently-sent subs
[ ] TASK-09  Rewrite init_db.bat
[ ] TASK-10  Add functools.wraps to log decorators
[ ] TASK-11  Pin dependency versions in requirements.txt
[ ] TASK-12  Remove version key from docker-compose.yml
[ ] TASK-13  Remove deprecated event_loop fixture from conftest.py
[ ] TASK-14  Add env vars to CI lint import check step
[ ] TASK-15  Document LIST_STORE limitations
[ ] TASK-16  Add per-user
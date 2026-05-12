# CareerPilot — Progress Summary
_Last updated: 2026-02-23 (session 2)_

---

## Stack
| Layer | Tech |
|-------|------|
| Backend | FastAPI · Python 3.13 · LangChain · Google Gemini |
| Database | PostgreSQL 16 + pgvector |
| Frontend | Next.js 15 · React Query · shadcn/ui · Tailwind |
| Automation | Playwright (Chromium, headless) · Gemini Vision |
| Infra | Docker Compose (3 containers: db, api, frontend) |

---

## Fully Implemented Features

### 1 — Resume Upload & Processing
- `POST /resume/upload` accepts PDF or plain-text files
- `ResumeProcessor`: PDF → Markdown (via `pymupdf4llm`) → structured JSON via Gemini
- Stored in `resume_profiles` table (`raw_data` JSON column)
- Frontend: drag-and-drop upload page, prefetches overview/jobs/career-path on success

### 2 — AI Analysis (LangChain Tool-Calling Agent)
All endpoints require `?user_id=<uuid>`:

| Endpoint | Description |
|----------|-------------|
| `GET /analysis/overview` | Resume score, strengths, top improvements |
| `GET /analysis/skills-gap` | Missing skills vs. target role |
| `GET /analysis/career-path` | 3 milestone career timeline |
| `GET /chat/stream` | SSE streaming chat with conversation memory |
| `GET /chat/history` | Past conversations + messages |

### 3 — ATS Scoring
- `POST /ats/score` — paste any JD, get semantic keyword match score
- LLM-powered, not just string matching
- Frontend: `ATSScoreCard` + `ATSKeywordHighlight` components

### 4 — Job Recommendations
- `GET /jobs/recommendations` — Tavily web search → ranked job list
- `GET /jobs/match` — match score vs. a target role (skills % + resume quality %)
- Frontend: `JobMatchCard` with role selector, match score, and job cards

### 5 — Job Application Tracking
Full CRUD backed by `job_applications` PostgreSQL table:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/applications` | GET | List with optional status filter |
| `/applications` | POST | Track a new application |
| `/applications/{id}` | PATCH | Update status / notes |
| `/applications/{id}` | DELETE | Remove |
| `/applications/stats` | GET | Count by status, recent activity |

Frontend: Kanban-style board with drag-free status columns + stats cards

### 6 — Playwright Auto-Fill (Task-Based, Non-Blocking)
Fills form fields on job portals using saved browser sessions + Gemini Vision.

**Flow:**
1. `POST /applications/auto-fill` → returns `task_id` instantly
2. Browser launches as background coroutine — captures screenshots at each stage
3. `GET /applications/auto-fill/{task_id}?user_id=...` → poll for live progress

**Steps + screenshots captured:**
| Step | Icon | Screenshot |
|------|------|-----------|
| `navigating` | Spinner | No (instant) |
| `loaded` | Monitor | ✅ Page after navigation (shows login state) |
| `analyzing` | Sparkles ✦ | ✅ Screenshot sent to Gemini Vision; AI plan shown |
| `filling` | Pen | ✅ After first field typed |
| `done` / `no_fields` | Check / Alert | ✅ Final state |

**Supported portals:** LinkedIn · Indeed · Naukri · Glassdoor · DemoQA (test)

Frontend dialog shows a **live step timeline** — each step has an icon, message, and expandable screenshot. Polls every 2 s automatically until done.

### 7 — Portal Session Persistence
Saves your real browser session so Playwright auto-fills while you're "signed in":

| Endpoint | Description |
|----------|-------------|
| `POST /applications/session/import` | Import cookies from EditThisCookie extension |
| `POST /applications/session/login` | Headless Playwright login (email+password) |
| `GET /applications/session/status` | Which portals have saved sessions |
| `DELETE /applications/session/{portal}` | Remove a saved session |

**Brave Browser → Docker flow:**
1. Install **EditThisCookie** in Brave
2. Navigate to `indeed.com` while signed in
3. Click extension → Export (copies JSON array)
4. `POST /applications/session/import` with the cookie array
5. Auto-fill will now run as you — session is stored in `portal_sessions` DB table

Indeed session for the real user (`ddeec13b-ab1a-4ad0-bf36-9d94ce4f4245`) is **already imported and active**.

### 8 — Interview Preparation
- `GET /interview/questions` — role-specific question bank
- `POST /interview/evaluate` — LLM evaluates a user answer
- Frontend: `InterviewPrepCard` with question display + answer evaluation

### 9 — Feedback System
Thumbs up / thumbs down on job recommendations and career suggestions:
- `POST /feedback` · `GET /feedback` · `DELETE /feedback`
- Persisted in `feedback` table

### 10 — User Accounts (Optional Auth)
- `POST /auth/register` · `POST /auth/login` · `GET /auth/me`
- JWT-based, optional — endpoints degrade gracefully without auth
- `user_id` is always the primary key for all data

---

## Recent Changes (2026-02-23)

### Bug Fix — Session Cookies Not Being Recognised (Indeed / LinkedIn)

**Root cause:** Indeed and LinkedIn use Cloudflare Bot Management to fingerprint
headless Chrome. Even with valid session cookies loaded, `navigator.webdriver = true`
caused both portals to ignore the cookies entirely and show a "Sign In" page.

**Fix 1 — Stealth browser mode** (`_STEALTH_ARGS` + `_make_stealth_context()`)

A shared helper replaces all direct `browser.new_context()` calls across the three
browser-launch sites (`login_and_save_session`, `_run_fill_task`, `fill_application`):

```python
_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox", "--disable-setuid-sandbox",
    "--disable-dev-shm-usage", "--disable-infobars",
    "--window-size=1920,1080",
    ...
]

_STEALTH_INIT_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages',  { get: () => ['en-US','en'] });
    Object.defineProperty(navigator, 'plugins',    { get: () => [1,2,3,4,5] });
    window.chrome = { runtime: {} };
    ...
"""
```

- Every context now has `1920×1080` viewport, `en-US` locale, `America/New_York` timezone
- `ctx.add_init_script(_STEALTH_INIT_SCRIPT)` runs before every page load
- Result: Indeed and LinkedIn now see the session cookies and render the authenticated page

**Fix 2 — Post-navigation hydration wait (1.8 s → 3.5 s)**

React SPAs (Indeed, LinkedIn) need ~3 s to read cookies and re-hydrate the auth
state. Increasing the wait eliminated the race condition where the screenshot was
captured before the session was applied.

---

### New Feature — ToS / Consent Popup Auto-Dismissal (`_dismiss_popups()`)

After session restoration, portals often show a first-visit overlay (Terms of
Service update, GDPR cookie banner, etc.) that blocks form detection. A new
helper tries three escalating strategies before the screenshot is taken:

| Strategy | Method | Notes |
|----------|--------|-------|
| 1 | Playwright CSS `:has-text(...)` | Fast; covers ~90 % of cases |
| 2 | `page.get_by_role("button", name=...)` | More resilient to DOM changes |
| 3 | `page.evaluate(...)` JS text search | Covers shadow DOM / portal iframes |

After a successful click the helper waits for `networkidle` (up to 5 s) so any
redirect / animation completes before field detection begins. Silently ignores
all failures — a missing popup is acceptable.

---

### New Feature — Gemini Vision-Guided Form Interaction (`_llm_vision_interact()`)

The CSS-selector approach required per-portal maintenance and broke whenever a
portal changed its DOM. This is replaced with a **vision-first** pipeline:

**Flow per page:**

```
screenshot → Gemini Vision → JSON action list → Playwright mouse/keyboard → fields_filled[]
```

**Prompt to Gemini:**
> "You are a browser automation agent. The screenshot is exactly W×H CSS pixels.
>  Return a JSON array of `{action, x, y, value, field, reason}` for all visible
>  interactive elements you should interact with to fill this job application form.
>  Never click Submit / Apply. Return `[]` if this is a listing page with no form."

**Action types the model can return:**

| action | Playwright execution | Description |
|--------|---------------------|-------------|
| `fill` | triple-click at `(x,y)` → `keyboard.type(value)` | Type text into a field |
| `click` | `mouse.click(x,y)` + networkidle wait | Click a button (popup dismiss, dropdown open, "Next") |
| `scroll` | `mouse.wheel(0, ±amount)` | Scroll to reveal hidden fields |

**Fallback:** If the LLM returns an empty `[]` (e.g. page is a search results
listing), the original CSS-selector map is used silently as a backup, so existing
portal configurations still work.

**New `analyzing` step in the progress timeline:**

The screenshot that was sent to Gemini is surfaced in the UI as an `analyzing`
step, showing:
- The exact image the AI analysed
- A summary of the actions it identified (e.g. *"AI identified 4 action(s): Filling first name; Filling last name; Filling email…"*)
- Animated violet **Sparkles** icon while running

**Content-type handling:** Gemini multimodal responses return `content` as a list
of parts. The helper normalises both list and string responses before JSON-parsing.
Markdown code fences (` ```json … ``` `) are also stripped automatically.

---

## Implementation Detail — New Functions in `automation_service.py`

```
_STEALTH_ARGS          list[str]          Chromium launch flags for bot-detection bypass
_STEALTH_INIT_SCRIPT   str                JS injected per page to hide automation signals
_STEALTH_UA            str                Realistic Windows Chrome user-agent string
_make_stealth_context  async fn           Creates a BrowserContext with all stealth settings applied
_dismiss_popups        async fn           Clicks consent/ToS overlays before form scanning
_llm_vision_interact   async fn           Screenshot → Gemini Vision → execute coordinate actions
```

### `_make_stealth_context(browser, storage_state=None) → BrowserContext`
- Accepts an optional `storage_state` dict (cookies); passes it directly so 
  cookies are loaded before the first navigation (required for session auth)
- Adds the init script via `ctx.add_init_script()` to guarantee execution on every frame

### `_dismiss_popups(page) → None`
- Waits 800 ms for lazy-rendered overlays to appear
- Tries CSS → role → JS eval in sequence; returns after the first successful click
- Uses `networkidle` post-click wait so any page transition settles

### `_llm_vision_interact(page, contact_data, portal, snap) → list[str]`
- Takes `snap` as a callable so it can emit steps into the task registry directly
- Returns the list of `field` keys filled (e.g. `["first_name","email","phone"]`)
- Emits an `analyzing` step with the screenshot and AI summary regardless of success
- Falls through to return `[]` on any Gemini/network error (CSS fallback then takes over)

---

## Frontend Changes (2026-02-23)

### `frontend/src/types/analysis.ts`
- `AutoFillStep.step` union extended with `"analyzing"`

### `frontend/src/components/analysis/JobMatchCard.tsx`
- Imported `Sparkles` from `lucide-react`
- `analyzing` step renders an animated (`animate-pulse`) violet `Sparkles` icon
- Step label displays "analyzing" in the same capitalised timeline style as other steps
- Screenshot shown under the step (the exact image sent to the AI)

---

## Database Tables
```
users               — optional accounts
resume_profiles     — raw_data JSON (contact, skills, education, experience…)
conversations       — chat session per user
messages            — individual chat messages
job_applications    — tracked applications (status, notes, url, company…)
portal_sessions     — Playwright storage_state per user+portal (cookies)
feedback            — thumbs up/down per item
```

---

## Docker Services
```
careerpilot-postgres   — pg16 + pgvector, port 5432
careerpilot-api        — FastAPI on port 8000
careerpilot-frontend   — Next.js production build on port 3000
```

**Playwright in container:**
- Installed at `/ms-playwright` (Chromium 145 / v1210)
- `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` set in env

---

## Key Files
| Purpose | Path |
|---------|------|
| FastAPI entry | `backend/src/app/main.py` |
| Auto-fill service (stealth + vision) | `backend/src/app/services/automation_service.py` |
| Applications API | `backend/src/app/api/v1/applications.py` |
| DB models | `backend/src/app/infrastructure/database/models.py` |
| Portal session repo | `backend/src/app/infrastructure/database/repositories/portal_session_repository.py` |
| Frontend hooks | `frontend/src/hooks/queries/` |
| Job card (autofill UI + analyzing step) | `frontend/src/components/analysis/JobMatchCard.tsx` |
| Analysis types | `frontend/src/types/analysis.ts` |

---

## Environment Variables Required
**`backend/.env.local`:**
```
GOOGLE_API_KEY=...
TAVILY_API_KEY=...
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/careerpilot
MODEL_NAME=gemini-2.5-flash
```

---

## Known Limitations / Next Steps
- Auto-fill on Indeed `viewjob` URLs lands on the listing page (no form visible). Use direct "Easy Apply" URLs — the LLM will correctly return `[]` for listing pages and the `no_fields` step will fire.
- Portal sessions expire with the browser cookie TTL (~April 2026 for current Indeed session). Re-import when expired.
- Playwright runs headless in Docker — no visible browser window. Screenshots are the only visual feedback.
- Applications tracker AutoFill button only shows for supported portals (indeed/linkedin/naukri/glassdoor).
- LLM vision adds ~5–8 s per page due to Gemini round-trip; CSS fallback runs instantly if the model is unavailable.
- `scroll` actions from the LLM are supported but not yet tested on multi-page forms (Indeed Easy Apply has multiple steps).


---

## Fully Implemented Features

### 1 — Resume Upload & Processing
- `POST /resume/upload` accepts PDF or plain-text files
- `ResumeProcessor`: PDF → Markdown (via `pymupdf4llm`) → structured JSON via Gemini
- Stored in `resume_profiles` table (`raw_data` JSON column)
- Frontend: drag-and-drop upload page, prefetches overview/jobs/career-path on success

### 2 — AI Analysis (LangChain Tool-Calling Agent)
All endpoints require `?user_id=<uuid>`:

| Endpoint | Description |
|----------|-------------|
| `GET /analysis/overview` | Resume score, strengths, top improvements |
| `GET /analysis/skills-gap` | Missing skills vs. target role |
| `GET /analysis/career-path` | 3 milestone career timeline |
| `GET /chat/stream` | SSE streaming chat with conversation memory |
| `GET /chat/history` | Past conversations + messages |

### 3 — ATS Scoring
- `POST /ats/score` — paste any JD, get semantic keyword match score
- LLM-powered, not just string matching
- Frontend: `ATSScoreCard` + `ATSKeywordHighlight` components

### 4 — Job Recommendations
- `GET /jobs/recommendations` — Tavily web search → ranked job list
- `GET /jobs/match` — match score vs. a target role (skills % + resume quality %)
- Frontend: `JobMatchCard` with role selector, match score, and job cards

### 5 — Job Application Tracking
Full CRUD backed by `job_applications` PostgreSQL table:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/applications` | GET | List with optional status filter |
| `/applications` | POST | Track a new application |
| `/applications/{id}` | PATCH | Update status / notes |
| `/applications/{id}` | DELETE | Remove |
| `/applications/stats` | GET | Count by status, recent activity |

Frontend: Kanban-style board with drag-free status columns + stats cards

### 6 — Playwright Auto-Fill (Task-Based, Non-Blocking)
Fills form fields on job portals using saved browser sessions.

**Flow:**
1. `POST /applications/auto-fill` → returns `task_id` instantly
2. Browser launches as background coroutine — captures screenshots at each stage
3. `GET /applications/auto-fill/{task_id}?user_id=...` → poll for live progress

**Steps + screenshots captured:**
| Step | Screenshot |
|------|-----------|
| `navigating` | No (instant) |
| `loaded` | ✅ Page after navigation (shows login state) |
| `filling` | ✅ After first field typed |
| `done` / `no_fields` | ✅ Final state |

**Supported portals:** LinkedIn · Indeed · Naukri · Glassdoor · DemoQA (test)

Frontend dialog shows a **live step timeline** — each step has an icon, message, and expandable screenshot. Polls every 2 s automatically until done.

### 7 — Portal Session Persistence
Saves your real browser session so Playwright auto-fills while you're "signed in":

| Endpoint | Description |
|----------|-------------|
| `POST /applications/session/import` | Import cookies from EditThisCookie extension |
| `POST /applications/session/login` | Headless Playwright login (email+password) |
| `GET /applications/session/status` | Which portals have saved sessions |
| `DELETE /applications/session/{portal}` | Remove a saved session |

**Brave Browser → Docker flow:**
1. Install **EditThisCookie** in Brave
2. Navigate to `indeed.com` while signed in
3. Click extension → Export (copies JSON array)
4. `POST /applications/session/import` with the cookie array
5. Auto-fill will now run as you — session is stored in `portal_sessions` DB table

Indeed session for the real user (`ddeec13b-ab1a-4ad0-bf36-9d94ce4f4245`) is **already imported and active**.

### 8 — Interview Preparation
- `GET /interview/questions` — role-specific question bank
- `POST /interview/evaluate` — LLM evaluates a user answer
- Frontend: `InterviewPrepCard` with question display + answer evaluation

### 9 — Feedback System
Thumbs up / thumbs down on job recommendations and career suggestions:
- `POST /feedback` · `GET /feedback` · `DELETE /feedback`
- Persisted in `feedback` table

### 10 — User Accounts (Optional Auth)
- `POST /auth/register` · `POST /auth/login` · `GET /auth/me`
- JWT-based, optional — endpoints degrade gracefully without auth
- `user_id` is always the primary key for all data

---

## Database Tables
```
users               — optional accounts
resume_profiles     — raw_data JSON (contact, skills, education, experience…)
conversations       — chat session per user
messages            — individual chat messages
job_applications    — tracked applications (status, notes, url, company…)
portal_sessions     — Playwright storage_state per user+portal (cookies)
feedback            — thumbs up/down per item
```

---

## Docker Services
```
careerpilot-postgres   — pg16 + pgvector, port 5432
careerpilot-api        — FastAPI on port 8000
careerpilot-frontend   — Next.js production build on port 3000
```

**Playwright in container:**
- Installed at `/ms-playwright` (Chromium 145 / v1210)
- `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` set in env

---

## Key Files
| Purpose | Path |
|---------|------|
| FastAPI entry | `backend/src/app/main.py` |
| Auto-fill service | `backend/src/app/services/automation_service.py` |
| Applications API | `backend/src/app/api/v1/applications.py` |
| DB models | `backend/src/app/infrastructure/database/models.py` |
| Portal session repo | `backend/src/app/infrastructure/database/repositories/portal_session_repository.py` |
| Frontend hooks | `frontend/src/hooks/queries/` |
| Job card (autofill UI) | `frontend/src/components/analysis/JobMatchCard.tsx` |
| Analysis types | `frontend/src/types/analysis.ts` |

---

## Environment Variables Required
**`backend/.env.local`:**
```
GOOGLE_API_KEY=...
TAVILY_API_KEY=...
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/careerpilot
MODEL_NAME=gemini-2.5-flash
```

---

## Known Limitations / Next Steps
- Auto-fill on `viewjob` URLs lands on listing page (no form). Use "Apply Now" → "Easy Apply" direct URLs for form detection.
- Portal sessions expire with the browser cookie TTL (~April 2026 for current Indeed session). Re-import when expired.
- Playwright runs headless in Docker — no visible browser window. Screenshots are the only visual feedback.
- Applications tracker AutoFill button only shows for supported portals (indeed/linkedin/naukri/glassdoor).

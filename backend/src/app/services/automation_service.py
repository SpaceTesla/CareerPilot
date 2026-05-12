"""
Playwright-based job application form auto-fill service.

Fills (but never submits) job application forms on LinkedIn, Indeed,
Naukri and Glassdoor using resume contact data extracted from the DB.
"""

from __future__ import annotations

import asyncio
import base64
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse

# Point Playwright at the browsers installed in the container.
# Falls back gracefully if the path does not exist (local dev).
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/ms-playwright")

from app.core.logging import get_logger
from app.infrastructure.database.connection import get_session
from app.infrastructure.database.repositories.portal_session_repository import PortalSessionRepository
from app.infrastructure.database.repositories.resume_repository import ResumeRepository

logger = get_logger(__name__)

# ── Stealth browser configuration ────────────────────────────────────────────
# These args + init script prevent sites like Indeed/LinkedIn from detecting
# headless Playwright via navigator.webdriver or Chromium automation flags.

_STEALTH_ARGS: list[str] = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-infobars",
    "--disable-extensions",
    "--disable-gpu",
    "--window-size=1920,1080",
]

# JavaScript injected before every page load to mask automation fingerprints.
_STEALTH_INIT_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    window.chrome = { runtime: {} };
    const origQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (params) =>
        params.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : origQuery(params);
"""

_STEALTH_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


async def _make_stealth_context(
    browser: Any,
    storage_state: dict[str, Any] | None = None,
) -> Any:
    """
    Create a Playwright BrowserContext with anti-bot-detection settings.

    Applies:
    - Realistic User-Agent
    - 1920×1080 viewport
    - English locale / timezone
    - navigator.webdriver hidden via init script
    - Optional storage_state (cookies) pre-loaded before first navigation
    """
    ctx_kwargs: dict[str, Any] = {
        "user_agent": _STEALTH_UA,
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-US",
        "timezone_id": "America/New_York",
        "java_script_enabled": True,
    }
    if storage_state is not None:
        ctx_kwargs["storage_state"] = storage_state

    ctx = await browser.new_context(**ctx_kwargs)
    await ctx.add_init_script(_STEALTH_INIT_SCRIPT)
    return ctx


async def _dismiss_popups(page: Any) -> None:
    """
    Dismiss ToS / cookie-consent / GDPR overlays before scanning for form fields.
    Tries multiple selector strategies so it works across portals.
    Silently ignores failures — a missing popup is fine.
    """
    # Short wait so lazy-rendered overlays have time to appear
    await page.wait_for_timeout(800)

    # Strategy 1 – Playwright :has-text CSS extension (fast, exact text)
    css_selectors = [
        "button:has-text('Accept Terms')",
        "button:has-text('Accept All')",
        "button:has-text('Accept Cookies')",
        "button:has-text('Accept all cookies')",
        "button:has-text('I Accept')",
        "button:has-text('Accept')",
        "button:has-text('Agree')",
        "button:has-text('Got it')",
        "[aria-label='Close']",
        "[aria-label='Dismiss']",
    ]
    for sel in css_selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                await el.click(timeout=2_000)
                # Wait for Accept/dismiss to take effect (page may reload or animate out)
                try:
                    await page.wait_for_load_state("networkidle", timeout=5_000)
                except Exception:
                    await page.wait_for_timeout(1_500)
                logger.info(f"Dismissed popup via selector: {sel!r}")
                return
        except Exception:
            pass

    # Strategy 2 – role-based button matching (more resilient to DOM changes)
    button_labels = [
        "Accept Terms", "Accept All", "Accept Cookies",
        "Accept all cookies", "I Accept", "Accept", "Agree", "Got it", "OK",
    ]
    for label in button_labels:
        try:
            btn = page.get_by_role("button", name=label, exact=True)
            if await btn.count() > 0:
                await btn.first.click(timeout=2_000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=5_000)
                except Exception:
                    await page.wait_for_timeout(1_500)
                logger.info(f"Dismissed popup via role-button: {label!r}")
                return
        except Exception:
            pass

    # Strategy 3 – JavaScript text search (works across shadow DOM / portals)
    dismiss_keywords = [
        "Accept Terms", "Accept All", "Accept Cookies",
        "I Accept", "Accept", "Agree", "Got it",
    ]
    try:
        clicked = await page.evaluate(
            """(keywords) => {
                const allButtons = Array.from(document.querySelectorAll('button, [role="button"]'));
                for (const kw of keywords) {
                    const btn = allButtons.find(b => (b.innerText || b.textContent || '').trim().includes(kw));
                    if (btn) { btn.click(); return kw; }
                }
                return null;
            }""",
            dismiss_keywords,
        )
        if clicked:
            try:
                await page.wait_for_load_state("networkidle", timeout=5_000)
            except Exception:
                await page.wait_for_timeout(1_500)
            logger.info(f"Dismissed popup via JS eval: {clicked!r}")
    except Exception:
        pass


async def _llm_vision_step(
    page: Any,
    contact_data: dict[str, str],
    portal: str,
    job_title: str,
    company: str,
    step_num: int,
    snap: Callable[[str, str, str | None], None],
    page_url: str = "",
) -> dict[str, Any]:
    """
    One step of the multi-step application loop.

    Captures a screenshot, sends it to Gemini Vision with full job context,
    and returns a structured result describing what happened and what to do next.

    Returns:
      {
        "page_type"    : "listing" | "form" | "review" | "unknown",
        "fields_filled": [str, ...],
        "next_action"  : "click_apply" | "click_next" | "at_review" | "done",
        "next_x"       : int | None,   # pixel coords of the next button
        "next_y"       : int | None,
        "summary"      : str,
        "screenshot_b64": str,
      }
    """
    import json  # noqa: PLC0415

    try:
        from langchain_core.messages import HumanMessage          # noqa: PLC0415
        from langchain_google_genai import ChatGoogleGenerativeAI  # noqa: PLC0415
    except ImportError:
        logger.warning("langchain_google_genai not available; skipping LLM vision step")
        return {"page_type": "unknown", "fields_filled": [], "next_action": "done",
                "next_x": None, "next_y": None, "summary": "LLM unavailable", "screenshot_b64": ""}

    from app.core.config import settings  # noqa: PLC0415

    screenshot_bytes = await page.screenshot(full_page=False, type="jpeg", quality=60)
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
    viewport = page.viewport_size or {"width": 1920, "height": 1080}
    vw, vh = int(viewport["width"]), int(viewport["height"])

    available_data = {k: v for k, v in contact_data.items() if v}
    job_ctx = f'"{job_title}" at "{company}"' if (job_title or company) else "a job"

    # Determine if the URL tells us we're already on a form/apply page
    _form_url_hints = (
        "smartapply", "/apply", "/form/", "apply.indeed", "easya", "application",
        "greenhouse.io", "lever.co", "workday.com", "jobvite.com", "icims.com",
        "taleo.net", "myworkdayjobs", "successfactors", "bamboohr.com",
        "ashbyhq.com", "rippling.com", "dover.com",
    )
    _is_form_url = page_url and any(h in page_url.lower() for h in _form_url_hints)
    if _is_form_url:
        url_note = (
            f"\nCURRENT PAGE URL: {page_url}\n"
            "IMPORTANT: This URL indicates you are ALREADY on an application form page — "
            "NOT a job listing. Do NOT return page_type=\"listing\". Use CASE 2 (form) rules."
        )
    else:
        url_note = f"\nCurrent page URL: {page_url}" if page_url else ""

    prompt = f"""You are a browser automation agent helping a user apply for {job_ctx} on {portal}.
Screenshot size: {vw}×{vh} pixels — all (x, y) coordinates must be within this space.
Application step number: {step_num}.{url_note}

User's profile data (use these values to fill form fields):
{json.dumps(available_data, indent=2)}

────────────────────────────────────────────────────
TASK: Analyze the screenshot and return a single JSON object (no markdown, no extra text).

CASE 1 — JOB LISTING / DETAIL PAGE (not yet on an application form):
  Look for an "Easy Apply", "Apply Now", "Apply on company site", or "Apply" button.
  Return:
  {{
    "page_type": "listing",
    "next_x": <integer pixel X of the apply button>,
    "next_y": <integer pixel Y of the apply button>,
    "summary": "Clicking Easy Apply / Apply Now",
    "actions": [],
    "is_review": false
  }}
  If NO apply button is visible at all:
  {{
    "page_type": "listing",
    "next_x": null, "next_y": null,
    "summary": "No apply button found on this page",
    "actions": [], "is_review": false
  }}

CASE 2 — APPLICATION FORM STEP (a form with input fields):
  Fill every visible input, textarea, or select with the user's data.
  Also find the "Next", "Continue", or "Save and continue" button.
  Return:
  {{
    "page_type": "form",
    "actions": [
      {{"action": "fill", "x": <int>, "y": <int>, "value": "<string>", "field": "<field_key>", "reason": "<why>"}},
      ...
    ],
    "next_x": <integer X of Next/Continue button, or null if none>,
    "next_y": <integer Y of Next/Continue button, or null if none>,
    "summary": "Filling N field(s) — <field list>",
    "is_review": false
  }}

CASE 2 SPECIAL RULES — Indeed Easy Apply multi-step form at smartapply.indeed.com:
  Each step is a separate URL page. The button that advances is always "Continue".
  a) CV/Resume selection page (heading "Add a CV for the employer"):
     Click the "Build an Indeed Resume" radio card option, then find Continue button.
     Return a click action on the "Build an Indeed Resume" label/card + next_x/y on Continue.
  b) Employer Screener Questions (heading "Answer these questions from the employer"):
     Questions are DYNAMIC and vary per employer/job. Answer ALL visible questions:
     - Text input asking years of experience → type a number (e.g., "3")
     - Radio buttons (Yes/No) → click the most favourable option (default Yes)
     - Dropdown/select → pick best matching option from user profile
     - Checkbox → check if positive/applicable
     Include fill/click actions for every question, then next_x/y on Continue.
  c) All other pages (contact info, location, work experience) → fill with user data + Continue.

CASE 3 — REVIEW / CONFIRM / SUBMIT PAGE:
  You see a "Submit your application" button (the final step). The page URL often ends in
  /form/review-module or the heading says "Review" with a submit button visible.
  Do NOT click Submit — just signal that the review page is reached.
  Return:
  {{
    "page_type": "review",
    "actions": [],
    "next_x": null, "next_y": null,
    "summary": "Review page reached — ready for user confirmation",
    "is_review": true
  }}

RULES:
- NEVER include an action to click "Submit your application", "Send Application", or any final submission button.
- If a consent/cookie popup is blocking, add a click action to dismiss it before form actions.
- (x, y) must be the EXACT PIXEL CENTER of the element in the {vw}×{vh} screenshot.
- Return ONLY a valid JSON object. No markdown code fences.
────────────────────────────────────────────────────"""

    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.model_name,
            temperature=0,
            google_api_key=settings.google_api_key,
        )
        msg = HumanMessage(content=[
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{screenshot_b64}"}},
            {"type": "text", "text": prompt},
        ])
        response = await asyncio.wait_for(llm.ainvoke([msg]), timeout=60.0)
        content = response.content
        if isinstance(content, list):
            raw = " ".join(
                p.get("text", "") if isinstance(p, dict) else str(p) for p in content
            ).strip()
        else:
            raw = (content or "").strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else ""
        result: dict[str, Any] = json.loads(raw) if raw else {}
        if not isinstance(result, dict):
            result = {}
        logger.info(f"LLM vision step {step_num}: page_type={result.get('page_type')} summary={result.get('summary')}")
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"
        logger.warning(f"LLM vision step {step_num} failed: {err_msg}")
        snap("analyzing", f"AI analysis failed: {err_msg}", screenshot_b64)
        return {"page_type": "unknown", "fields_filled": [], "next_action": "done",
                "next_x": None, "next_y": None, "summary": err_msg, "screenshot_b64": screenshot_b64}

    page_type = result.get("page_type", "unknown")
    actions: list[dict[str, Any]] = result.get("actions") or []
    next_x = result.get("next_x")
    next_y = result.get("next_y")
    summary = result.get("summary", "")
    is_review = bool(result.get("is_review", False))

    # ── Emit analysing step ───────────────────────────────────────────────────
    snap("analyzing", f"Step {step_num + 1}: {summary}", screenshot_b64)

    # ── Execute fill actions ──────────────────────────────────────────────────
    fields_filled: list[str] = []
    first_fill_done = False

    for action in actions:
        action_type = action.get("action")
        x = action.get("x")
        y = action.get("y")
        reason = action.get("reason", "")
        if x is None or y is None:
            continue
        try:
            if action_type == "click":
                await page.mouse.click(float(x), float(y))
                logger.info(f"LLM click ({x},{y}): {reason}")
                try:
                    await page.wait_for_load_state("networkidle", timeout=4_000)
                except Exception:
                    await page.wait_for_timeout(600)

            elif action_type == "fill":
                value = str(action.get("value", ""))
                field = str(action.get("field", ""))
                if not value:
                    continue
                await page.mouse.click(float(x), float(y), click_count=3)
                await page.wait_for_timeout(100)
                await page.keyboard.type(value, delay=22)
                await page.wait_for_timeout(120)
                if field:
                    fields_filled.append(field)
                logger.info(f"LLM fill {field!r} ({x},{y}) = {value[:30]!r}")
                if not first_fill_done:
                    await page.wait_for_timeout(300)
                    ss = base64.b64encode(await page.screenshot(full_page=False, type="jpeg", quality=75)).decode()
                    snap("filling", f"Filling '{field or 'field'}'…", ss)
                    first_fill_done = True

            elif action_type == "scroll":
                direction = str(action.get("direction", "down"))
                amount = int(action.get("amount", 400))
                delta_y = amount if direction == "down" else -amount
                await page.mouse.move(vw // 2, vh // 2)
                await page.mouse.wheel(0, delta_y)
                await page.wait_for_timeout(350)
        except Exception as e:
            logger.warning(f"LLM action failed ({action_type} at {x},{y}): {e}")

    # ── Determine next_action ─────────────────────────────────────────────────
    if is_review or page_type == "review":
        next_action = "at_review"
    elif page_type == "listing" and next_x is not None:
        next_action = "click_apply"
    elif page_type == "form" and next_x is not None:
        next_action = "click_next"
    else:
        next_action = "done"

    return {
        "page_type": page_type,
        "fields_filled": fields_filled,
        "next_action": next_action,
        "next_x": next_x,
        "next_y": next_y,
        "summary": summary,
        "screenshot_b64": screenshot_b64,
    }


# ── In-memory task registry (task_id → task state dict) ─────────────────────
# Holds live autofill jobs so the frontend can poll for progress + screenshots.
_tasks: dict[str, dict[str, Any]] = {}

# Confirmation events: task_id → asyncio.Event (set when user confirms/cancels)
_task_events: dict[str, asyncio.Event] = {}
# Confirmation decisions: task_id → True (submit) | False (cancel)
_task_confirmations: dict[str, bool] = {}

# ── Portal detection ──────────────────────────────────────────────────────────

SUPPORTED_PORTALS: dict[str, str] = {
    "linkedin.com": "linkedin",
    "indeed.com": "indeed",
    "naukri.com": "naukri",
    "glassdoor.com": "glassdoor",
    "glassdoor.co.in": "glassdoor",
    "demoqa.com": "demoqa",
}

# Field selectors per portal  {portal: {field: css_selector}}
FIELD_SELECTORS: dict[str, dict[str, str]] = {
    "linkedin": {
        "first_name": "input[name='firstName'], input[id*='first'][type='text']",
        "last_name": "input[name='lastName'], input[id*='last'][type='text']",
        "email": "input[name='email'], input[type='email']",
        "phone": "input[name='phone'], input[type='tel']",
        "linkedin_url": "input[name='profileUrl'], input[placeholder*='LinkedIn']",
    },
    "indeed": {
        "first_name": "input[name='applicant.name.first'], input[id*='firstName']",
        "last_name": "input[name='applicant.name.last'], input[id*='lastName']",
        "email": "input[name='applicant.emailAddress'], input[type='email']",
        "phone": "input[name='applicant.phoneNumber'], input[type='tel']",
        "city": "input[name='applicant.location.city'], input[id*='location']",
    },
    "naukri": {
        "first_name": "input[name='firstName'], input[id='firstName']",
        "last_name": "input[name='lastName'], input[id='lastName']",
        "email": "input[name='email'], input[type='email']",
        "phone": "input[name='mobile'], input[type='tel']",
    },
    "glassdoor": {
        "first_name": "input[name='firstName'], input[placeholder*='First']",
        "last_name": "input[name='lastName'], input[placeholder*='Last']",
        "email": "input[type='email']",
        "phone": "input[type='tel']",
    },
    # Public demo form – ideal for testing autofill without login
    "demoqa": {
        "first_name": "#firstName",
        "last_name": "#lastName",
        "email": "#userEmail",
        "phone": "#userNumber",
    },
}

# ── Login configuration per portal ──────────────────────────────────────────

PORTAL_LOGIN_CONFIG: dict[str, dict[str, str]] = {
    "indeed": {
        "login_url": "https://secure.indeed.com/account/login",
        "email_selector": "#signin_email",
        "password_selector": "#signin_password",
        "submit_selector": "button[type='submit']",
        "success_exclude": "account/login",   # URL must NOT contain this after login
    },
    "linkedin": {
        "login_url": "https://www.linkedin.com/login",
        "email_selector": "#username",
        "password_selector": "#password",
        "submit_selector": "button[type='submit']",
        "success_exclude": "/login",
    },
    "naukri": {
        "login_url": "https://www.naukri.com/nlogin/login",
        "email_selector": "#usernameField",
        "password_selector": "#passwordField",
        "submit_selector": "button[type='submit']",
        "success_exclude": "nlogin",
    },
    "glassdoor": {
        "login_url": "https://www.glassdoor.com/profile/login_input.htm",
        "email_selector": "#userEmail",
        "password_selector": "#userPassword",
        "submit_selector": "button[type='submit']",
        "success_exclude": "login_input",
    },
}


# ── Cookie format conversion ─────────────────────────────────────────────────

_SAME_SITE_MAP = {
    "no_restriction": "None",
    "unspecified": "None",
    "lax": "Lax",
    "strict": "Strict",
    "none": "None",
}


def _browser_cookies_to_storage_state(
    cookies: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Convert browser-extension cookie exports to Playwright storage_state format.

    Accepts both:
    - EditThisCookie format  (field: expirationDate, sameSite: "no_restriction")
    - Cookie-Editor format   (field: expires as ISO string or epoch float)
    """
    pw_cookies: list[dict[str, Any]] = []
    for c in cookies:
        # ── expiry ────────────────────────────────────────────────────────────
        raw_exp = c.get("expirationDate") or c.get("expires") or c.get("expiry")
        if raw_exp is None or c.get("session"):
            expires = -1.0  # session cookie
        elif isinstance(raw_exp, str):
            # ISO date string e.g. "2026-12-31T00:00:00.000Z"
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(raw_exp.replace("Z", "+00:00"))
                expires = dt.timestamp()
            except Exception:
                expires = -1.0
        else:
            expires = float(raw_exp)

        # ── sameSite ──────────────────────────────────────────────────────────
        raw_ss = (c.get("sameSite") or "").lower()
        same_site = _SAME_SITE_MAP.get(raw_ss, "None")

        # ── domain: ensure it starts with '.' for cross-subdomain cookies ─────
        domain = c.get("domain") or ""

        pw_cookies.append({
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": domain,
            "path": c.get("path", "/"),
            "expires": expires,
            "httpOnly": bool(c.get("httpOnly", False)),
            "secure": bool(c.get("secure", False)),
            "sameSite": same_site,
        })

    return {"cookies": pw_cookies, "origins": []}


def _detect_portal(url: str) -> str | None:
    """Return portal key if URL is from a supported job portal, else None."""
    try:
        host = urlparse(url).netloc.lower().replace("www.", "")
        for domain, key in SUPPORTED_PORTALS.items():
            if host == domain or host.endswith("." + domain):
                return key
    except Exception:
        pass
    return None


def _extract_contact(raw_data: dict[str, Any]) -> dict[str, str]:
    """Extract fillable contact fields from parsed resume data."""
    contact = raw_data.get("contact", {}) or {}
    name_parts = (raw_data.get("name") or "").split(" ", 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    return {
        "first_name": first_name,
        "last_name": last_name,
        "email": contact.get("email") or raw_data.get("email") or "",
        "phone": contact.get("phone") or raw_data.get("phone") or "",
        "city": (contact.get("location") or raw_data.get("location") or "").split(",")[0].strip(),
        "linkedin_url": (contact.get("linkedin") or contact.get("socials", {}).get("linkedin") or ""),
    }


class AutomationService:
    """Uses Playwright to fill job application forms."""

    # ── Session login ────────────────────────────────────────────────────────

    async def login_and_save_session(
        self, user_id: str, portal: str, email: str, password: str
    ) -> dict[str, Any]:
        """
        Log in to a job portal with email + password using Playwright,
        then persist the browser session (cookies + localStorage) to the DB.

        Returns:
            status: "saved" | "failed" | "unsupported" | "error"
            portal: portal name
            message: human-readable result
        """
        login_cfg = PORTAL_LOGIN_CONFIG.get(portal)
        if login_cfg is None:
            return {
                "status": "unsupported",
                "portal": portal,
                "message": (
                    f"Session login is not configured for '{portal}'. "
                    f"Supported: {', '.join(PORTAL_LOGIN_CONFIG)}"
                ),
            }

        try:
            from playwright.async_api import async_playwright  # noqa: PLC0415
        except ImportError:
            return {
                "status": "error",
                "portal": portal,
                "message": "Playwright is not installed.",
            }

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=_STEALTH_ARGS,
                )
                context = await _make_stealth_context(browser)
                page = await context.new_page()

                # Navigate to login page
                await page.goto(login_cfg["login_url"], timeout=20_000, wait_until="domcontentloaded")

                # Fill email
                email_el = page.locator(login_cfg["email_selector"]).first
                await email_el.fill(email, timeout=5_000)

                # Fill password
                pass_el = page.locator(login_cfg["password_selector"]).first
                await pass_el.fill(password, timeout=5_000)

                # Submit
                submit_el = page.locator(login_cfg["submit_selector"]).first
                await submit_el.click(timeout=5_000)

                # Wait for navigation away from the login page (up to 15s)
                try:
                    await page.wait_for_url(
                        lambda url: login_cfg["success_exclude"] not in url,
                        timeout=15_000,
                    )
                except Exception:
                    # Check manually — some portals redirect slowly
                    pass

                current_url = page.url
                if login_cfg["success_exclude"] in current_url:
                    # Still on login page — likely wrong credentials
                    await browser.close()
                    return {
                        "status": "failed",
                        "portal": portal,
                        "message": (
                            "Login failed — still on the login page. "
                            "Check your email and password."
                        ),
                    }

                # Persist full storage state (cookies + localStorage)
                storage_state = await context.storage_state()
                await browser.close()

            with get_session() as db:
                repo = PortalSessionRepository(db)
                ps = repo.upsert(user_id, portal, storage_state)
                session_id = str(ps.id)  # read while session is open

            return {
                "status": "saved",
                "portal": portal,
                "session_id": session_id,
                "message": (
                    f"Successfully logged in to {portal} and saved session. "
                    "Auto-fill will now use this session automatically."
                ),
            }

        except Exception as e:
            logger.error(f"Session login error for {portal}: {e}")
            return {
                "status": "error",
                "portal": portal,
                "message": f"Login automation failed: {e}",
            }

    # ── Session status ───────────────────────────────────────────────────────

    def get_session_status(self, user_id: str) -> list[dict[str, Any]]:
        """Return which portals have active saved sessions for this user."""
        with get_session() as db:
            repo = PortalSessionRepository(db)
            sessions = repo.list_for_user(user_id)
            # Build result inside the session context to avoid DetachedInstanceError
            return [
                {
                    "portal": s.portal,
                    "session_id": str(s.id),
                    "saved_at": s.updated_at.isoformat() if s.updated_at else None,
                }
                for s in sessions
            ]

    def delete_session(self, user_id: str, portal: str) -> bool:
        """Delete a saved session for a portal."""
        with get_session() as db:
            repo = PortalSessionRepository(db)
            return repo.delete(user_id, portal)

    # ── Import session from browser cookie export ─────────────────────────────

    def import_session(
        self, user_id: str, portal: str, cookies: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Import cookies exported from a real browser (e.g. Brave + EditThisCookie
        or Cookie-Editor extension) and save them as a Playwright storage_state.

        Steps for the user:
          1. Install 'EditThisCookie' or 'Cookie-Editor' in Brave.
          2. Navigate to e.g. indeed.com while already signed in via Google OAuth.
          3. Click the extension → Export / Copy all cookies (JSON array).
          4. POST that JSON array here.

        The saved session is then automatically restored by fill_application().
        """
        if not cookies:
            return {
                "status": "error",
                "portal": portal,
                "cookies_imported": 0,
                "message": "No cookies provided.",
            }

        storage_state = _browser_cookies_to_storage_state(cookies)
        n = len(storage_state["cookies"])

        with get_session() as db:
            repo = PortalSessionRepository(db)
            ps = repo.upsert(user_id, portal, storage_state)
            session_id = str(ps.id)  # read while session is still open

        return {
            "status": "saved",
            "portal": portal,
            "session_id": session_id,
            "cookies_imported": n,
            "message": (
                f"Imported {n} cookies for {portal}. "
                "Auto-fill will now use this session — "
                "no login step required."
            ),
        }

    # ── Task-based Fill (non-blocking) ────────────────────────────────────────

    def create_fill_task(self, user_id: str, job_url: str,
                         job_title: str = "", company: str = "") -> str:
        """Register a new autofill task and return its task_id.
        The caller must schedule _run_fill_task() via asyncio.create_task().
        """
        task_id = str(uuid.uuid4())
        _tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",   # pending → running → done | error
            "user_id": user_id,
            "job_url": job_url,
            "job_title": job_title,
            "company": company,
            "portal": _detect_portal(job_url),
            "steps": [],           # [{step, message, screenshot, timestamp}]
            "fields_filled": [],
            "result_status": None, # filled | no_fields_found | error
            "error": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
        }
        # Prune finished tasks if registry grows large
        if len(_tasks) > 200:
            now = datetime.now(timezone.utc)
            stale = [
                tid for tid, t in list(_tasks.items())
                if t["status"] in ("done", "error")
                and t.get("finished_at")
                and (now - datetime.fromisoformat(t["finished_at"])).total_seconds() > 3600
            ]
            for tid in stale:
                _tasks.pop(tid, None)
        return task_id

    def get_fill_task(self, task_id: str) -> dict[str, Any] | None:
        """Return current state of an autofill task (JSON-serializable), or None if not found."""
        task = _tasks.get(task_id)
        if task is None:
            return None
        # Strip any non-serializable internal keys (asyncio objects etc.)
        return {k: v for k, v in task.items() if not k.startswith("_")}

    async def _run_fill_task(self, task_id: str, user_id: str, job_url: str) -> None:
        """
        Background coroutine: runs the full multi-step Playwright autofill flow
        and updates _tasks[task_id] at every stage with screenshots.

        Steps emitted:
            navigating      → initial page navigation
            session_missing → no saved session (warning)
            loaded          → page settled, starting apply loop
            analyzing       → AI screenshot analysis at each step
            filling         → a form field was typed
            navigating      → clicking Apply / Next / Continue between steps
            done            → finished (all fillable steps complete)
            no_fields       → reached end without filling anything
            error           → fatal failure
        """
        task = _tasks[task_id]
        task["status"] = "running"

        def _snap(step: str, msg: str, screenshot: str | None = None) -> None:
            task["steps"].append({
                "step": step,
                "message": msg,
                "screenshot": screenshot,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        portal = task["portal"]
        if portal is None:
            task["status"] = "error"
            task["result_status"] = "unsupported"
            task["error"] = "Unsupported portal"
            task["finished_at"] = datetime.now(timezone.utc).isoformat()
            _snap("error", "This job portal is not supported. Supported: LinkedIn, Indeed, Naukri, Glassdoor.")
            return

        job_title: str = task.get("job_title") or ""
        company: str = task.get("company") or ""
        job_ctx = f'"{job_title} at {company}"' if job_title else "this job"
        _snap("navigating", f"Navigating to {portal} to apply for {job_ctx}...")

        # ── Load user contact data ───────────────────────────────────────────
        contact_data: dict[str, str] = {}
        try:
            with get_session() as session:
                repo = ResumeRepository(session)
                profiles = repo.get_by_user(user_id)
                if profiles:
                    profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
                    raw = getattr(profile, "raw_data", {}) or {}
                    contact_data = _extract_contact(raw)
        except Exception as e:
            logger.warning(f"Could not load profile: {e}")

        # ── Load saved portal session ────────────────────────────────────────
        saved_state: dict[str, Any] | None = None
        try:
            with get_session() as db:
                srepo = PortalSessionRepository(db)
                ps = srepo.get(user_id, portal)
                if ps:
                    saved_state = ps.storage_state
        except Exception as e:
            logger.warning(f"Could not load portal session: {e}")

        try:
            from playwright.async_api import async_playwright  # noqa: PLC0415
        except ImportError:
            task["status"] = "error"
            task["result_status"] = "error"
            task["error"] = "Playwright not installed"
            task["finished_at"] = datetime.now(timezone.utc).isoformat()
            _snap("error", "Playwright is not installed in the container.")
            return

        fields_filled: list[str] = []

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=_STEALTH_ARGS,
                )
                ctx = await _make_stealth_context(browser, storage_state=saved_state)
                if saved_state:
                    logger.info(f"Restored saved {portal} session for {user_id}")

                page = await ctx.new_page()

                # ── Navigate ────────────────────────────────────────────────
                try:
                    await page.goto(job_url, timeout=30_000, wait_until="domcontentloaded")
                    # Give Indeed/LinkedIn React time to hydrate session state from cookies.
                    await page.wait_for_timeout(6_000)
                except Exception as nav_err:
                    logger.warning(f"Navigation issue: {nav_err}")

                # ── Dismiss ToS / cookie consent popups ─────────────────────
                await _dismiss_popups(page)

                ss1 = base64.b64encode(await page.screenshot(full_page=False, type="jpeg", quality=75)).decode()
                if not saved_state:
                    _snap(
                        "session_missing",
                        f"No saved {portal} session found. "
                        "Go to Applications → Import Cookies to restore your login, "
                        "then try Auto-Fill again.",
                    )
                _snap("loaded", f"Page loaded for {job_ctx}. Starting multi-step apply flow...", ss1)

                # Multi-step apply loop: listing → form page(s) → review
                MAX_STEPS = 14
                loop_deadline = datetime.now(timezone.utc).timestamp() + 300  # 5-min hard cap
                apply_clicked = False  # guard: only click the initial Apply button once
                apply_wait_retries = 0  # count consecutive "waiting for form" loops
                for step_num in range(MAX_STEPS):
                    if datetime.now(timezone.utc).timestamp() > loop_deadline:
                        _snap("error", "Auto-fill timed out after 3 minutes. Try again or fill manually.")
                        task["result_status"] = "error"
                        task["error"] = "timeout"
                        break
                    step_result = await _llm_vision_step(
                        page, contact_data, portal, job_title, company, step_num, _snap,
                        page_url=page.url or "",
                    )
                    fields_filled.extend(step_result.get("fields_filled", []))
                    next_action = step_result.get("next_action", "done")
                    next_x = step_result.get("next_x")
                    next_y = step_result.get("next_y")

                    if next_action == "at_review":
                        ss_review = base64.b64encode(await page.screenshot(full_page=False, type="jpeg", quality=75)).decode()

                        # Build a summary of what was filled for the confirmation prompt
                        unique_fields = list(dict.fromkeys(fields_filled))
                        filling_msgs = [
                            s["message"] for s in task["steps"]
                            if s.get("step") == "filling"
                        ]
                        confirm_details = {
                            "job": f"{job_title} at {company}" if company else (job_title or "this job"),
                            "portal": portal,
                            "fields_filled": unique_fields,
                            "filling_summary": filling_msgs,
                        }
                        task["confirm_details"] = confirm_details
                        task["status"] = "awaiting_confirmation"

                        # Set up the asyncio event for the confirm endpoint to trigger
                        confirm_event = asyncio.Event()
                        _task_events[task_id] = confirm_event
                        _task_confirmations[task_id] = False

                        _snap(
                            "awaiting_confirmation",
                            f"Ready to submit application for {confirm_details['job']}. "
                            f"Fields filled: {', '.join(unique_fields) or 'none'}. "
                            "Confirm to submit or cancel.",
                            ss_review,
                        )

                        # Wait up to 10 minutes for user to confirm or cancel
                        try:
                            await asyncio.wait_for(confirm_event.wait(), timeout=600)
                        except asyncio.TimeoutError:
                            _snap("done", "Confirmation timed out — application not submitted.", None)
                            task["result_status"] = "cancelled"
                            break

                        confirmed = _task_confirmations.get(task_id, False)
                        if confirmed:
                            # Click the submit button
                            try:
                                submit_btn = page.locator("button:has-text('Submit your application')")
                                if await submit_btn.count() > 0:
                                    await submit_btn.first.click()
                                    await page.wait_for_timeout(3000)
                                    ss_submitted = base64.b64encode(
                                        await page.screenshot(full_page=False, type="jpeg", quality=75)
                                    ).decode()
                                    _snap("done", "Application submitted successfully!", ss_submitted)
                                    task["result_status"] = "submitted"
                                else:
                                    _snap("done", "Submit button not found — please submit manually.", ss_review)
                                    task["result_status"] = "filled"
                            except Exception as submit_err:
                                logger.error(f"Submit error for {task_id}: {submit_err}")
                                _snap("error", f"Submit failed: {type(submit_err).__name__}: {submit_err}", None)
                                task["result_status"] = "error"
                        else:
                            _snap("done", "Application cancelled — form was not submitted.", None)
                            task["result_status"] = "cancelled"

                        # Clean up event refs
                        _task_events.pop(task_id, None)
                        _task_confirmations.pop(task_id, None)
                        break

                    elif next_action == "click_apply":
                        if apply_clicked:
                            # Coordinate click already fired but nothing changed —
                            # try Playwright selector-based click as fallback.
                            apply_wait_retries += 1
                            if apply_wait_retries >= 4:
                                _snap("error", "Could not open the application form after multiple attempts. The page may require manual interaction.")
                                task["result_status"] = "error"
                                task["error"] = "form_not_detected"
                                break

                            _snap("navigating", f"Retrying apply click via selector (attempt {apply_wait_retries}/3)...")
                            url_before_retry = page.url
                            tabs_before_retry = len(ctx.pages)

                            # Try every common Apply button pattern in order
                            _apply_selectors = [
                                "a:has-text('Apply on company site')",
                                "button:has-text('Apply on company site')",
                                "a:has-text('Easy Apply')",
                                "button:has-text('Easy Apply')",
                                "[data-testid='indeedApplyButton']",
                                "a:has-text('Apply Now')",
                                "button:has-text('Apply Now')",
                                "a:has-text('Apply')",
                                "button:has-text('Apply')",
                            ]
                            clicked_fallback = False
                            for sel in _apply_selectors:
                                try:
                                    locator = page.locator(sel).first
                                    if await locator.count() > 0:
                                        await locator.scroll_into_view_if_needed(timeout=3_000)
                                        await locator.click(timeout=5_000)
                                        clicked_fallback = True
                                        logger.info(f"Fallback apply click via selector: {sel}")
                                        break
                                except Exception:
                                    continue

                            if not clicked_fallback:
                                await page.wait_for_timeout(4_000)
                                continue

                            await page.wait_for_timeout(5_000)
                            # Check what happened after the fallback click
                            if len(ctx.pages) > tabs_before_retry:
                                page = ctx.pages[-1]
                                _snap("navigating", "New tab opened — switching to application form...")
                                try:
                                    await page.wait_for_load_state("domcontentloaded", timeout=15_000)
                                    await page.wait_for_timeout(4_000)
                                except Exception:
                                    await page.wait_for_timeout(5_000)
                                await _dismiss_popups(page)
                                apply_wait_retries = 0  # successfully switched
                            elif page.url != url_before_retry:
                                _snap("navigating", "Page navigated — waiting for form...")
                                try:
                                    await page.wait_for_load_state("domcontentloaded", timeout=15_000)
                                    await page.wait_for_timeout(4_000)
                                except Exception:
                                    await page.wait_for_timeout(5_000)
                                apply_wait_retries = 0
                            else:
                                # Might be a modal/overlay — let LLM analyze next
                                await page.wait_for_timeout(3_000)
                            continue

                        apply_wait_retries = 0  # reset once we fire the first click
                        if next_x is None:
                            break
                        apply_clicked = True
                        _snap("navigating", "Clicking 'Apply' button...")
                        url_before = page.url
                        tabs_before = len(ctx.pages)
                        await page.mouse.click(float(next_x), float(next_y))
                        await page.wait_for_timeout(5_000)  # let popup/tab/modal fully appear

                        if len(ctx.pages) > tabs_before:
                            # Case A: new tab opened (e.g. "Apply on company site")
                            page = ctx.pages[-1]
                            _snap("navigating", "New tab opened — switching to application form...")
                            try:
                                await page.wait_for_load_state("domcontentloaded", timeout=15_000)
                                await page.wait_for_timeout(5_000)
                            except Exception:
                                await page.wait_for_timeout(6_000)
                            await _dismiss_popups(page)
                        elif page.url != url_before:
                            # Case B: same-tab navigation (full page redirect)
                            _snap("navigating", "Page navigated — waiting for form...")
                            try:
                                await page.wait_for_load_state("domcontentloaded", timeout=15_000)
                                await page.wait_for_timeout(5_000)
                            except Exception:
                                await page.wait_for_timeout(6_000)
                        else:
                            # Case C: modal / drawer opened on the same page (e.g. Indeed Easy Apply)
                            _snap("navigating", "Apply form opened as overlay — letting it settle...")
                            await page.wait_for_timeout(5_000)

                    elif next_action == "click_next" and next_x is not None:
                        _snap("navigating", "Clicking 'Next' button...")
                        url_before = page.url
                        tabs_before = len(ctx.pages)
                        await page.mouse.click(float(next_x), float(next_y))
                        await page.wait_for_timeout(5_000)
                        if len(ctx.pages) > tabs_before:
                            page = ctx.pages[-1]
                            try:
                                await page.wait_for_load_state("domcontentloaded", timeout=15_000)
                                await page.wait_for_timeout(5_000)
                            except Exception:
                                await page.wait_for_timeout(6_000)
                            await _dismiss_popups(page)
                        elif page.url != url_before:
                            try:
                                await page.wait_for_load_state("domcontentloaded", timeout=15_000)
                                await page.wait_for_timeout(5_000)
                            except Exception:
                                await page.wait_for_timeout(6_000)
                        else:
                            # Same page — form step advanced in-place (SPA)
                            await page.wait_for_timeout(5_000)
                    else:
                        break

                # Final state if loop ended without hitting review
                if task.get("result_status") is None:
                    ss_final = base64.b64encode(await page.screenshot(full_page=False, type="jpeg", quality=75)).decode()
                    unique_fields = list(dict.fromkeys(fields_filled))
                    task["fields_filled"] = unique_fields
                    if unique_fields:
                        _snap(
                            "done",
                            f"Done - filled {len(unique_fields)} field(s): {', '.join(unique_fields)}. "
                            "Review the form and click Submit manually.",
                            ss_final,
                        )
                        task["result_status"] = "filled"
                    else:
                        _snap(
                            "no_fields",
                            "No fillable fields detected. "
                            "The page may require additional login steps or uses a custom form.",
                            ss_final,
                        )
                        task["result_status"] = "no_fields_found"
                else:
                    task["fields_filled"] = list(dict.fromkeys(fields_filled))

                await browser.close()

        except Exception as e:
            logger.error(f"Playwright task error for {task_id}: {e}")
            task["result_status"] = "error"
            task["error"] = str(e)
            _snap("error", f"Automation failed: {e}")

        task["status"] = "done" if task["result_status"] not in ("error",) else "error"
        task["finished_at"] = datetime.now(timezone.utc).isoformat()

    def confirm_fill_task(self, task_id: str, confirmed: bool) -> bool:
        """
        Resolve a pending confirmation for an autofill task.
        Returns True if the event was found and set, False if task not awaiting.
        """
        event = _task_events.get(task_id)
        if event is None:
            return False
        _task_confirmations[task_id] = confirmed
        event.set()
        return True

    # ── Fill application (legacy blocking) ──────────────────────────────────

    async def fill_application(self, user_id: str, job_url: str) -> dict[str, Any]:
        """
        Navigate to job_url and fill detected form fields with the user's
        resume contact info.

        Returns a dict with:
            status: "filled" | "unsupported" | "no_fields_found" | "error"
            portal: detected portal name or null
            fields_filled: list of field names that were filled
            screenshot: base64-encoded PNG of the page after filling
            message: human-readable description
        """
        portal = _detect_portal(job_url)
        if portal is None:
            return {
                "status": "unsupported",
                "portal": None,
                "fields_filled": [],
                "screenshot": None,
                "message": (
                    "This job portal is not supported for auto-fill. "
                    "Supported portals: LinkedIn, Indeed, Naukri, Glassdoor."
                ),
            }

        # Load user's resume contact data
        contact_data: dict[str, str] = {}
        try:
            with get_session() as session:
                repo = ResumeRepository(session)
                profiles = repo.get_by_user(user_id)
                if profiles:
                    profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
                    raw_data = getattr(profile, "raw_data", {}) or {}
                    contact_data = _extract_contact(raw_data)
        except Exception as e:
            logger.warning(f"Could not load profile for auto-fill: {e}")

        # Load saved portal session (cookies) if available
        saved_storage_state: dict[str, Any] | None = None
        try:
            with get_session() as db:
                srepo = PortalSessionRepository(db)
                ps = srepo.get(user_id, portal)
                if ps:
                    saved_storage_state = ps.storage_state
        except Exception as e:
            logger.warning(f"Could not load portal session: {e}")

        # Use Playwright to navigate and fill
        try:
            from playwright.async_api import async_playwright  # noqa: PLC0415
        except ImportError:
            return {
                "status": "error",
                "portal": portal,
                "fields_filled": [],
                "screenshot": None,
                "message": "Playwright is not installed. Run: uv run playwright install chromium",
            }

        fields_filled: list[str] = []
        screenshot_b64: str | None = None
        selectors = FIELD_SELECTORS.get(portal, {})

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=_STEALTH_ARGS,
                )
                context = await _make_stealth_context(browser, storage_state=saved_storage_state)
                if saved_storage_state:
                    logger.info(f"Restored saved {portal} session for user {user_id}")
                page = await context.new_page()

                # Navigate with a reasonable timeout
                try:
                    await page.goto(job_url, timeout=30_000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3500)  # let React/session hydrate
                except Exception as nav_err:
                    logger.warning(f"Navigation error for {job_url}: {nav_err}")

                # Dismiss ToS / cookie consent popups before scanning fields
                await _dismiss_popups(page)

                # Try filling each known field
                for field_name, selector in selectors.items():
                    value = contact_data.get(field_name, "")
                    if not value:
                        continue
                    try:
                        # Try each selector alternative (split by ", ")
                        for sel in [s.strip() for s in selector.split(",")]:
                            el = page.locator(sel).first
                            if await el.count() > 0:
                                await el.fill(value, timeout=3_000)
                                fields_filled.append(field_name)
                                break
                    except Exception:
                        pass  # Field not found or not fillable — skip silently

                # Capture screenshot
                try:
                    screenshot_bytes = await page.screenshot(full_page=False)
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
                except Exception:
                    screenshot_b64 = None

                await browser.close()

        except Exception as e:
            logger.error(f"Playwright automation error: {e}")
            return {
                "status": "error",
                "portal": portal,
                "fields_filled": [],
                "screenshot": None,
                "message": f"Automation failed: {e}",
            }

        if not fields_filled:
            return {
                "status": "no_fields_found",
                "portal": portal,
                "fields_filled": [],
                "screenshot": screenshot_b64,
                "message": (
                    "Could not detect fillable form fields on this page. "
                    "The page may require login first, or use a different form layout."
                ),
            }

        return {
            "status": "filled",
            "portal": portal,
            "fields_filled": fields_filled,
            "screenshot": screenshot_b64,
            "message": (
                f"Successfully pre-filled {len(fields_filled)} field(s): "
                f"{', '.join(fields_filled)}. "
                "Please review before submitting."
            ),
        }


automation_service = AutomationService()

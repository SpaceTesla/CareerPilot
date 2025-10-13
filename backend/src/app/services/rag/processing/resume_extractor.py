from __future__ import annotations

import json
import json as _json
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import ValidationError

from ....schemas.resume import (
    AchievementItem,
    EducationItem,
    ExperienceItem,
    ProjectItem,
    Resume,
    Skills,
    Socials,
)

SECTION_TITLES = [
    "education",
    "experience",
    "projects",
    "technical skills",
    "skills",
    "achievements",
    "certifications",
    "summary",
    "profile",
]

# Limits for model input to avoid excessive token usage
SOURCE_SNIPPET_LIMIT = 16000

# Common date period regex (e.g., "Jan 2024 – Present")
MONTH_PERIOD_RE = re.compile(
    r"(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s*\d{4}\b).*?(?:\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s*\d{4}\b|Present|present)",
)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
URL_RE = re.compile(r"(https?://[^\s)]+)")
GITHUB_RE = re.compile(r"github\.com/[\w\-]+", re.IGNORECASE)
LINKEDIN_RE = re.compile(r"linkedin\.com/(in|company)/[^\s)]+", re.IGNORECASE)
X_RE = re.compile(r"(?:x\.com|twitter\.com)/[^\s)]+", re.IGNORECASE)


def _clean_text(md: str) -> str:
    text = unicodedata.normalize("NFKC", md)
    text = text.replace("\ufffd", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.replace("\u2022", "-").replace("_•_", "-").replace("•", "-")
    return text.strip()


def _first_line(text: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s:
            return s
    return ""


def _extract_contacts_and_socials(text: str) -> tuple[dict[str, str | None], Socials]:
    email = None
    phone = None
    if m := EMAIL_RE.search(text):
        email = m.group(0)
    if m := PHONE_RE.search(text):
        phone = m.group(0).strip()

    urls = set(URL_RE.findall(text))
    github = next((u for u in urls if "github.com" in u.lower()), None)
    linkedin = next((u for u in urls if "linkedin.com" in u.lower()), None)
    x = next(
        (u for u in urls if "x.com" in u.lower() or "twitter.com" in u.lower()), None
    )

    website = None
    for u in urls:
        lu = u.lower()
        if (
            ("github.com" in lu)
            or ("linkedin.com" in lu)
            or ("x.com" in lu)
            or ("twitter.com" in lu)
        ):
            continue
        website = u
        break

    socials = Socials(
        github=(
            "https://" + github if github and not github.startswith("http") else github
        )
        if github
        else None,
        linkedin=(
            "https://" + linkedin
            if linkedin and not linkedin.startswith("http")
            else linkedin
        )
        if linkedin
        else None,
        website=website,
        x=("https://" + x if x and not x.startswith("http") else x) if x else None,
    )
    return {"email": email, "phone": phone}, socials


def _split_sections(text: str) -> dict[str, str]:
    # Simple heading split: lines that are Title Cased or match known section titles
    lines = text.splitlines()
    sections: dict[str, list[str]] = {}
    current_key = "header"
    sections[current_key] = []

    def is_heading(line: str) -> str | None:
        raw = re.sub(r"[*_#:`]+", "", line).strip()
        low = raw.lower()
        if low in SECTION_TITLES:
            return low if low != "technical skills" else "skills"
        # Bold or all-caps line heuristic
        if len(raw) <= 60 and (raw.istitle() or (raw.isupper() and len(raw) >= 3)):
            if low in {
                "education",
                "experience",
                "projects",
                "skills",
                "achievements",
                "certifications",
                "summary",
                "profile",
            }:
                return low
        return None

    for line in lines:
        key = is_heading(line)
        if key:
            current_key = key
            if current_key not in sections:
                sections[current_key] = []
            continue
        sections.setdefault(current_key, []).append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items() if v}


def _guess_name(header_text: str) -> str | None:
    first = _first_line(header_text)
    # Remove leading hashes and bold markers
    first = re.sub(r"^[#*_\s]+", "", first).strip()
    # If line contains obvious contact tokens, skip
    if (
        "@" in first
        or "http" in first
        or any(tok in first.lower() for tok in ["github", "linkedin", "email", "phone"])
    ):
        return None
    # Likely name if 2-4 words, title case
    parts = first.split()
    if 2 <= len(parts) <= 5:
        return first
    return None


def _bullets_to_list(block: str) -> list[str]:
    items: list[str] = []
    for line in block.splitlines():
        s = line.strip()
        if re.match(r"^(-|\*|\u2022)\s+", s):
            s = re.sub(r"^(-|\*|\u2022)\s+", "", s).strip()
            if s:
                items.append(s)
    # If no explicit bullets, fallback to sentences
    if not items:
        chunks = re.split(r"\.\s+", block.strip())
        items = [c.strip().rstrip(".") for c in chunks if len(c.strip()) > 5]
    return items


def _parse_education(text: str) -> list[EducationItem]:
    if not text:
        return []
    items: list[EducationItem] = []
    lines = [line_text.strip() for line_text in text.splitlines() if line_text.strip()]
    buf = " ".join(lines)
    # naive patterns
    college = None
    degree = None
    gpa = None
    years = None

    m = re.search(r"(?:GPA|CGPA)\s*[:\-]?\s*([0-9.\/]+)", buf, re.IGNORECASE)
    if m:
        gpa = m.group(1).strip()
    m = re.search(r"(\b\d{4}\b)\s*[-–]\s*(\b\d{4}\b|Present|present)", buf)
    if m:
        years = f"{m.group(1)} - {m.group(2)}"
    # take first strong-looking phrase as college
    candidates = [
        line_text
        for line_text in lines
        if len(line_text) > 10 and not line_text.lower().startswith(("gpa", "cgpa"))
    ]
    if candidates:
        college = candidates[0]
    # degree heuristic
    m = re.search(
        r"(B\.?E\.?|B\.?Tech|Bachelors?|M\.?S\.?|M\.?Tech|Masters?)\b.*",
        buf,
        re.IGNORECASE,
    )
    if m:
        degree = m.group(0).strip()

    if college:
        items.append(
            EducationItem(college=college, degree=degree, gpa=gpa, years=years)
        )
    return items


def _parse_experience(text: str) -> list[ExperienceItem]:
    if not text:
        return []
    blocks = re.split(r"\n\s*\n", text.strip())
    items: list[ExperienceItem] = []
    for block in blocks:
        header = _first_line(block)
        role = None
        company = None
        period = None

        # Try patterns like "**Role** | **Company** Dates"
        hdr = re.sub(r"[*_`]+", "", header)
        parts = [p.strip() for p in re.split(r"\||·|\-", hdr) if p.strip()]
        if parts:
            role = parts[0]
            if len(parts) >= 2:
                company = parts[1]
        # period
        m = MONTH_PERIOD_RE.search(block)
        if m:
            period = m.group(0).strip()
        if not (role or company):
            continue
        details = _bullets_to_list(block)
        items.append(
            ExperienceItem(
                role=role or "Role", company=company, period=period, details=details
            )
        )
    return items


def _parse_projects(text: str) -> list[ProjectItem]:
    if not text:
        return []
    blocks = re.split(r"\n\s*\n", text.strip())
    items: list[ProjectItem] = []
    for block in blocks:
        header = _first_line(block)
        name = re.sub(r"[*_`]+", "", header).strip() or "Project"
        # try to collect tech stack from header line
        tech = None
        m = re.search(r"\|\s*(.+)$", header)
        if m:
            tech = m.group(1).strip()
        details = _bullets_to_list(block)
        items.append(ProjectItem(name=name, tech_stack=tech, details=details))
    return items


def _parse_skills(text: str) -> Skills:
    if not text:
        return Skills()
    lines = [line_text.strip() for line_text in text.splitlines() if line_text.strip()]
    blob = " ".join(lines)

    def grab(label: str) -> list[str]:
        m = re.search(
            rf"{label}\s*[:\-]\s*(.+?)(?=\s+[A-Z][a-zA-Z]+(\s*[A-Z][a-zA-Z]+)*\s*[:\-]|$)",
            blob,
            re.IGNORECASE,
        )
        if not m:
            return []
        raw = m.group(1) or ""
        if not isinstance(raw, str) or not raw.strip():
            return []
        parts = re.split(r"[,\|/]", raw)
        return [p.strip() for p in parts if p and p.strip()]

    languages = grab("Languages?")
    frameworks = grab("Frontend Development|Frameworks?")
    tools = grab("Backend Development|Tools?|DevOps|Cloud|Databases?")
    return Skills(languages=languages, frameworks=frameworks, tools=tools)


def _parse_achievements(text: str) -> list[AchievementItem]:
    if not text:
        return []
    items = []
    for bullet in _bullets_to_list(text):
        title = bullet
        desc = None
        m = re.match(r"\*{0,2}(.+?)\*{0,2}\s*[:\-]\s*(.+)$", bullet)
        if m:
            title = m.group(1).strip()
            desc = m.group(2).strip()
        items.append(AchievementItem(title=title, description=desc))
    return items


def extract_resume_from_markdown(
    md_path: str | Path, source_file: str | None = None
) -> Resume:
    path = Path(md_path)
    text = path.read_text(encoding="utf-8")
    cleaned = _clean_text(text)
    sections = _split_sections(cleaned)

    contacts, socials = _extract_contacts_and_socials(cleaned)

    name = _guess_name(sections.get("header", "")) or _guess_name(cleaned)

    education = _parse_education(sections.get("education", ""))
    experience = _parse_experience(sections.get("experience", ""))
    projects = _parse_projects(sections.get("projects", ""))
    skills = _parse_skills(
        sections.get("skills", "") or sections.get("technical skills", "")
    )
    achievements = _parse_achievements(sections.get("achievements", ""))
    certifications = (
        _bullets_to_list(sections.get("certifications", ""))
        if sections.get("certifications")
        else []
    )
    summary = sections.get("summary") or sections.get("profile")

    resume = Resume(
        source_file=source_file,
        name=name,
        email=contacts.get("email"),
        phone=contacts.get("phone"),
        socials=socials,
        education=education,
        experience=experience,
        projects=projects,
        skills=skills,
        certifications=certifications,
        achievements=achievements,
        summary=summary.strip() if summary else None,
    )

    try:
        _ = Resume.model_validate(resume.model_dump())
    except ValidationError as e:
        raise ValueError(f"Resume validation failed: {e}") from e

    return resume


def resume_to_json(resume: Resume) -> str:
    # Ensure Pydantic fields (e.g., HttpUrl, EmailStr) are converted to JSON-safe types
    data = resume.model_dump(mode="json")
    return json.dumps(data, indent=2, ensure_ascii=False)


# --- Gemini + LangChain enrichment (structured output) ---
def enrich_with_llm_gemini(
    cleaned_text: str,
    resume_json: dict,
    model: str = "gemini-1.5-flash",
    api_key_env: str = "GOOGLE_API_KEY",
) -> dict:
    """
    Uses Gemini via LangChain to fix segmentation and normalize to a strict schema.
    Returns a JSON-safe dict matching the Resume shape.
    """

    # Use shared Resume schema for structured output
    schema_model = Resume

    api_key = os.getenv(api_key_env)
    # Fallback to app settings if env var is missing
    if not api_key:
        try:
            from ....core.config import settings  # type: ignore

            api_key = settings.google_api_key
            # If caller didn't override model, prefer settings.model_name
            if model == "gemini-1.5-flash" and getattr(settings, "model_name", None):
                model = settings.model_name
        except Exception:
            api_key = None
    if not api_key:
        print(
            "[enrich_with_llm_gemini] Skipped: GOOGLE_API_KEY not set and settings fallback failed."
        )
        return resume_json

    # Build parser and model
    parser = PydanticOutputParser(pydantic_object=schema_model)
    model_client = ChatGoogleGenerativeAI(
        model=model,
        temperature=0,
        convert_system_message_to_human=True,
    )

    format_instructions = parser.get_format_instructions()
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a resume normalizer. Return ONLY a valid JSON object that matches the provided schema. "
                "Fix segmentation for experience (role, company, period, details), clean markdown/bold artifacts, "
                "and do not hallucinate. If unknown, leave as null or empty arrays.",
            ),
            (
                "user",
                "SCHEMA (Pydantic JSON schema):\n{schema}\n\n"
                "CURRENT_EXTRACTION (noisy; fix it, keep truth consistent with source):\n{current}\n\n"
                "SOURCE_TEXT (ground truth; use to correct splits and fill missing values):\n{source}\n\n"
                "{format_instructions}",
            ),
        ]
    )

    chain = prompt | model_client | parser

    source_snippet = cleaned_text[:SOURCE_SNIPPET_LIMIT]
    try:
        result = chain.invoke(
            {
                "schema": _json.dumps(
                    schema_model.model_json_schema(), ensure_ascii=False
                ),
                "current": _json.dumps(resume_json, ensure_ascii=False),
                "source": source_snippet,
                "format_instructions": format_instructions,
            }
        )
        # result is a Resume instance
        enriched = result.model_dump(mode="json")
        # preserve these from original if present
        if "schemaVersion" in resume_json:
            enriched["schemaVersion"] = resume_json["schemaVersion"]
        if "source_file" in resume_json:
            enriched["source_file"] = resume_json["source_file"]
        print("[enrich_with_llm_gemini] Enrichment applied using", model)
        return enriched
    except Exception as e:
        print("[enrich_with_llm_gemini] Error during enrichment:", str(e))
        return resume_json


# -----------------------
# Class-based API
# -----------------------


@dataclass
class EnrichmentConfig:
    model: str = "gemini-1.5-flash"
    api_key_env: str = "GOOGLE_API_KEY"


class SimpleLogger:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def info(self, *args: object) -> None:
        if self.enabled:
            print(*args)

    def warn(self, *args: object) -> None:
        if self.enabled:
            print(*args)

    def error(self, *args: object) -> None:
        if self.enabled:
            print(*args)


class ResumeExtractor:
    """Extracts a Resume from markdown using deterministic heuristics."""

    def __init__(self, logger: SimpleLogger | None = None) -> None:
        self.logger = logger or SimpleLogger(enabled=False)

    def from_markdown(
        self, md_path: str | Path, source_file: str | None = None
    ) -> Resume:
        path = Path(md_path)
        text = path.read_text(encoding="utf-8")
        cleaned = _clean_text(text)
        sections = _split_sections(cleaned)

        contacts, socials = _extract_contacts_and_socials(cleaned)

        name = _guess_name(sections.get("header", "")) or _guess_name(cleaned)

        education = _parse_education(sections.get("education", ""))
        experience = _parse_experience(sections.get("experience", ""))
        projects = _parse_projects(sections.get("projects", ""))
        skills = _parse_skills(
            sections.get("skills", "") or sections.get("technical skills", "")
        )
        achievements = _parse_achievements(sections.get("achievements", ""))
        certifications = (
            _bullets_to_list(sections.get("certifications", ""))
            if sections.get("certifications")
            else []
        )
        summary = sections.get("summary") or sections.get("profile")

        resume = Resume(
            source_file=source_file,
            name=name,
            email=contacts.get("email"),
            phone=contacts.get("phone"),
            socials=socials,
            education=education,
            experience=experience,
            projects=projects,
            skills=skills,
            certifications=certifications,
            achievements=achievements,
            summary=summary.strip() if summary else None,
        )

        _ = Resume.model_validate(resume.model_dump())
        return resume


class GeminiEnricher:
    """Enriches a Resume JSON using Gemini via LangChain with strict schema output."""

    def __init__(
        self, config: EnrichmentConfig | None = None, logger: SimpleLogger | None = None
    ) -> None:
        self.config = config or EnrichmentConfig()
        self.logger = logger or SimpleLogger(enabled=True)

    def enrich(self, cleaned_text: str, resume_json: dict) -> dict:
        return enrich_with_llm_gemini(
            cleaned_text=cleaned_text,
            resume_json=resume_json,
            model=self.config.model,
            api_key_env=self.config.api_key_env,
        )


__all__ = [
    "EnrichmentConfig",
    "SimpleLogger",
    "ResumeExtractor",
    "GeminiEnricher",
    "resume_to_json",
    "enrich_with_llm_gemini",
]

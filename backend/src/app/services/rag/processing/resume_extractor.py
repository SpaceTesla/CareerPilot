from __future__ import annotations

import json as _json
from pathlib import Path

from ....schemas.resume import Resume
from .detection.contacts import ContactDetector
from .detection.name_detector import NameDetector
from .enrichment.enrichment_orchestrator import EnrichmentConfig, EnrichmentOrchestrator
from .parsing.achievements_parser import AchievementsParser
from .parsing.bullets import BulletParser
from .parsing.education_parser import EducationParser
from .parsing.experience_parser import ExperienceParser
from .parsing.projects_parser import ProjectsParser
from .parsing.skills_parser import SkillsParser
from .text.cleaner import TextCleaner
from .text.section_splitter import SectionSplitter

# Limits for model input to avoid excessive token usage
SOURCE_SNIPPET_LIMIT = 16000


def resume_to_json(resume: Resume) -> str:
    """Convert Resume to JSON string."""
    data = resume.model_dump(mode="json")
    return _json.dumps(data, indent=2, ensure_ascii=False)


# -----------------------
# Class-based API
# -----------------------


class ResumeExtractor:
    """Extracts a Resume from markdown using deterministic heuristics."""

    def __init__(
        self,
        text_cleaner: TextCleaner | None = None,
        section_splitter: SectionSplitter | None = None,
        contact_detector: ContactDetector | None = None,
        name_detector: NameDetector | None = None,
        education_parser: EducationParser | None = None,
        experience_parser: ExperienceParser | None = None,
        projects_parser: ProjectsParser | None = None,
        skills_parser: SkillsParser | None = None,
        achievements_parser: AchievementsParser | None = None,
    ) -> None:
        self.text_cleaner = text_cleaner or TextCleaner()
        self.section_splitter = section_splitter or SectionSplitter()
        self.contact_detector = contact_detector or ContactDetector()
        self.name_detector = name_detector or NameDetector()
        self.education_parser = education_parser or EducationParser()
        self.experience_parser = experience_parser or ExperienceParser()
        self.projects_parser = projects_parser or ProjectsParser()
        self.skills_parser = skills_parser or SkillsParser()
        self.achievements_parser = achievements_parser or AchievementsParser()

    def from_markdown(
        self, md_path: str | Path, source_file: str | None = None
    ) -> Resume:
        path = Path(md_path)
        text = path.read_text(encoding="utf-8")
        cleaned = self.text_cleaner.clean(text)
        sections = self.section_splitter.split(cleaned)

        contacts, socials = self.contact_detector.extract(cleaned)

        name = self.name_detector.guess(sections.get("header", ""), cleaned)

        education = self.education_parser.parse(sections.get("education", ""))
        experience = self.experience_parser.parse(sections.get("experience", ""))
        projects = self.projects_parser.parse(sections.get("projects", ""))
        skills = self.skills_parser.parse(
            sections.get("skills", "") or sections.get("technical skills", "")
        )
        achievements = self.achievements_parser.parse(sections.get("achievements", ""))
        certifications = (
            BulletParser.to_list(sections.get("certifications", ""))
            if sections.get("certifications")
            else []
        )
        summary = sections.get("summary") or sections.get("profile")

        resume = Resume(
            source_file=source_file,
            name=name,
            email=contacts.get("email"),
            phone=contacts.get("phone"),
            socials=socials.model_dump() if socials else None,
            education=[item.model_dump() for item in education],
            experience=[item.model_dump() for item in experience],
            projects=[item.model_dump() for item in projects],
            skills=skills.model_dump() if skills else None,
            certifications=certifications,
            achievements=[item.model_dump() for item in achievements],
            summary=summary.strip() if summary else None,
        )

        _ = Resume.model_validate(resume.model_dump())
        return resume


class GeminiEnricher:
    """Enriches a Resume JSON using the agent-based architecture."""

    def __init__(self, config: EnrichmentConfig | None = None) -> None:
        self.config = config or EnrichmentConfig()
        self.orchestrator = EnrichmentOrchestrator(self.config)

    def enrich(self, cleaned_text: str, resume_json: dict) -> dict:
        """Enrich resume data using the complete agent workflow."""
        return self.orchestrator.enrich(
            cleaned_text, resume_json, Resume, SOURCE_SNIPPET_LIMIT
        )


__all__ = [
    "EnrichmentConfig",
    "ResumeExtractor",
    "GeminiEnricher",
    "resume_to_json",
]

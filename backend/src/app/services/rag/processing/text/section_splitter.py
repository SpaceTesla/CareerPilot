from __future__ import annotations

import re


class SectionSplitter:
    """Splits resume markdown into logical sections based on headings.

    Heuristics:
    - Known section title matches (case-insensitive)
    - Title-cased or ALL-CAPS short lines considered as headings if they match known buckets
    - Maps "technical skills" to "skills"
    """

    DEFAULT_TITLES = {
        "education",
        "experience",
        "projects",
        "technical skills",
        "skills",
        "achievements",
        "certifications",
        "summary",
        "profile",
    }

    def __init__(self, titles: list[str] | None = None) -> None:
        # Maintain a lowercase set for quick checks
        base = set(t.lower() for t in (titles or []))
        if not base:
            base = set(self.DEFAULT_TITLES)
        self.section_titles = base

    def split(self, text: str) -> dict[str, str]:
        lines = text.splitlines()
        sections: dict[str, list[str]] = {}
        current_key = "header"
        sections[current_key] = []

        def normalize_heading(line: str) -> str | None:
            raw = re.sub(r"[*_#:`]+", "", line).strip()
            low = raw.lower()
            if low in self.section_titles:
                return "skills" if low == "technical skills" else low
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
            key = normalize_heading(line)
            if key:
                current_key = key
                if current_key not in sections:
                    sections[current_key] = []
                continue
            sections.setdefault(current_key, []).append(line)

        return {k: "\n".join(v).strip() for k, v in sections.items() if v}

from __future__ import annotations

import re

from app.schemas.resume import Skills


class SkillsParser:
    def parse(self, text: str) -> Skills:
        if not text:
            return Skills()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
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

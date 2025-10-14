from __future__ import annotations

import re

from app.schemas.resume import ExperienceItem

from .bullets import BulletParser


class ExperienceParser:
    MONTH_PERIOD_RE = re.compile(
        r"(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s*\d{4}\b).*?(?:\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s*\d{4}\b|Present|present)"
    )

    def parse(self, text: str) -> list[ExperienceItem]:
        if not text:
            return []
        blocks = re.split(r"\n\s*\n", text.strip())
        items: list[ExperienceItem] = []
        for block in blocks:
            header = self._first_line(block)
            role = None
            company = None
            period = None

            hdr = re.sub(r"[*_`]+", "", header)
            parts = [p.strip() for p in re.split(r"\||·|\-", hdr) if p.strip()]
            if parts:
                role = parts[0]
                if len(parts) >= 2:
                    company = parts[1]

            m = self.MONTH_PERIOD_RE.search(block)
            if m:
                period = m.group(0).strip()

            if not (role or company):
                continue
            details = BulletParser.to_list(block)
            items.append(
                ExperienceItem(
                    role=role or "Role", company=company, period=period, details=details
                )
            )
        return items

    @staticmethod
    def _first_line(text: str) -> str:
        for line in text.splitlines():
            s = line.strip()
            if s:
                return s
        return ""

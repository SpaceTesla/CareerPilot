from __future__ import annotations

import re

from app.schemas.resume import ProjectItem

from .bullet_parser import BulletParser


class ProjectsParser:
    def parse(self, text: str) -> list[ProjectItem]:
        if not text:
            return []
        blocks = re.split(r"\n\s*\n", text.strip())
        items: list[ProjectItem] = []
        for block in blocks:
            header = self._first_line(block)
            name = re.sub(r"[*_`]+", "", header).strip() or "Project"
            tech = None
            m = re.search(r"\|\s*(.+)$", header)
            if m:
                tech = m.group(1).strip()
            details = BulletParser.to_list(block)
            items.append(ProjectItem(name=name, tech_stack=tech, details=details))
        return items

    @staticmethod
    def _first_line(text: str) -> str:
        for line in text.splitlines():
            s = line.strip()
            if s:
                return s
        return ""

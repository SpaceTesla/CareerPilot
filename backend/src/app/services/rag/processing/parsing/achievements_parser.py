from __future__ import annotations

import re

from app.schemas.resume import AchievementItem

from .bullets import BulletParser


class AchievementsParser:
    def parse(self, text: str) -> list[AchievementItem]:
        if not text:
            return []
        items: list[AchievementItem] = []
        for bullet in BulletParser.to_list(text):
            title = bullet
            desc = None
            m = re.match(r"\*{0,2}(.+?)\*{0,2}\s*[:\-]\s*(.+)$", bullet)
            if m:
                title = m.group(1).strip()
                desc = m.group(2).strip()
            items.append(AchievementItem(title=title, description=desc))
        return items

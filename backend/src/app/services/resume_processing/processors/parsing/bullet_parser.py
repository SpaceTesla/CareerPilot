from __future__ import annotations

import re


class BulletParser:
    """Parses bullet lists from a text block with sentence fallback."""

    @staticmethod
    def to_list(block: str) -> list[str]:
        items: list[str] = []
        for line in block.splitlines():
            s = line.strip()
            if re.match(r"^(-|\*|\u2022)\s+", s):
                s = re.sub(r"^(-|\*|\u2022)\s+", "", s).strip()
                if s:
                    items.append(s)
        if not items:
            chunks = re.split(r"\.\s+", block.strip())
            items = [c.strip().rstrip(".") for c in chunks if len(c.strip()) > 5]
        return items

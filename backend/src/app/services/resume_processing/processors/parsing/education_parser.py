from __future__ import annotations

import re

from app.schemas.resume import EducationItem


class EducationParser:
    def parse(self, text: str) -> list[EducationItem]:
        if not text:
            return []
        items: list[EducationItem] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        buf = " ".join(lines)

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

        candidates = [
            line
            for line in lines
            if len(line) > 10 and not line.lower().startswith(("gpa", "cgpa"))
        ]
        if candidates:
            college = candidates[0]

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

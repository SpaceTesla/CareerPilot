from __future__ import annotations

import re


class NameDetector:
    """Guesses candidate name from header text or entire document.

    Heuristics:
    - Ignore lines with obvious contact tokens (@, http, github, linkedin, email, phone)
    - Prefer the first non-empty line in the header
    - Accept 2-5 words in Title Case
    """

    CONTACT_TOKENS = ["github", "linkedin", "email", "phone"]

    @staticmethod
    def first_non_empty_line(text: str) -> str:
        for line in text.splitlines():
            s = line.strip()
            if s:
                return s
        return ""

    def guess(self, header_text: str, fallback_text: str | None = None) -> str | None:
        first = self.first_non_empty_line(header_text)
        first = re.sub(r"^[#*_\s]+", "", first).strip()

        def invalid(line: str) -> bool:
            low = line.lower()
            return (
                ("@" in line)
                or ("http" in low)
                or any(tok in low for tok in self.CONTACT_TOKENS)
            )

        if first and not invalid(first):
            parts = first.split()
            if 2 <= len(parts) <= 5:
                return first

        if fallback_text:
            candidate = self.first_non_empty_line(fallback_text)
            candidate = re.sub(r"^[#*_\s]+", "", candidate).strip()
            if candidate and not invalid(candidate):
                parts = candidate.split()
                if 2 <= len(parts) <= 5:
                    return candidate
        return None

from __future__ import annotations

import re
import unicodedata


class TextCleaner:
    """Normalizes markdown/plaintext for downstream parsing.

    Responsibilities:
    - Unicode normalization (NFKC)
    - Replacement of broken characters
    - Whitespace collapsing (spaces/tabs and excessive newlines)
    - Bullet normalization (• variants to '-')
    """

    @staticmethod
    def clean(text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text)
        normalized = normalized.replace("\ufffd", " ")
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        normalized = (
            normalized.replace("\u2022", "-").replace("_•_", "-").replace("•", "-")
        )
        return normalized.strip()

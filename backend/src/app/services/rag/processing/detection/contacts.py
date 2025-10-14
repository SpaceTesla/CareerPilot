from __future__ import annotations

import re

from app.schemas.resume import Socials


class ContactDetector:
    """Extracts email, phone, and social/website links from text."""

    EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
    PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
    URL_RE = re.compile(r"(https?://[^\s)]+)")

    def extract(self, text: str) -> tuple[dict[str, str | None], Socials]:
        email = None
        phone = None
        if m := self.EMAIL_RE.search(text):
            email = m.group(0)
        if m := self.PHONE_RE.search(text):
            phone = m.group(0).strip()

        urls = set(self.URL_RE.findall(text))
        github = next((u for u in urls if "github.com" in u.lower()), None)
        linkedin = next((u for u in urls if "linkedin.com" in u.lower()), None)
        x = next(
            (u for u in urls if "x.com" in u.lower() or "twitter.com" in u.lower()),
            None,
        )

        website = None
        for u in urls:
            lu = u.lower()
            if (
                ("github.com" in lu)
                or ("linkedin.com" in lu)
                or ("x.com" in lu)
                or ("twitter.com" in lu)
            ):
                continue
            website = u
            break

        socials = Socials(
            github=(
                "https://" + github
                if github and not github.startswith("http")
                else github
            )
            if github
            else None,
            linkedin=(
                "https://" + linkedin
                if linkedin and not linkedin.startswith("http")
                else linkedin
            )
            if linkedin
            else None,
            website=website,
            x=("https://" + x if x and not x.startswith("http") else x) if x else None,
        )
        return {"email": email, "phone": phone}, socials

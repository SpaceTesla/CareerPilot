from __future__ import annotations

import re

from app.schemas.resume import CoCurricularItem

from .bullet_parser import BulletParser


class CoCurricularParser:
    def parse(self, text: str) -> list[CoCurricularItem]:
        if not text:
            return []
        items: list[CoCurricularItem] = []
        for bullet in BulletParser.to_list(text):
            title = bullet
            organization = None
            period = None
            description = None

            # Try to extract organization and period from the bullet point
            # Pattern: "Title at Organization (Period)" or "Title - Organization (Period)"
            org_period_match = re.search(
                r"(.+?)\s+(?:at|-|–|—)\s+(.+?)\s*\(([^)]+)\)", bullet
            )
            if org_period_match:
                title = org_period_match.group(1).strip()
                organization = org_period_match.group(2).strip()
                period = org_period_match.group(3).strip()
            else:
                # Try pattern: "Title: Description" first
                desc_match = re.match(r"(.+?)\s*:\s*(.+)", bullet)
                if desc_match:
                    title = desc_match.group(1).strip()
                    description = desc_match.group(2).strip()
                else:
                    # Try pattern: "Title - Organization" or "Title at Organization"
                    # But only if it doesn't look like a description (no "won", "achieved", etc.)
                    org_match = re.search(r"(.+?)\s+(?:at|-|–|—)\s+(.+)", bullet)
                    if org_match and not any(word in org_match.group(2).lower() for word in ["won", "achieved", "led", "organized", "participated", "volunteered"]):
                        title = org_match.group(1).strip()
                        organization = org_match.group(2).strip()
                    else:
                        # If it contains description-like words, treat the whole thing as title
                        # and the part after dash as description
                        dash_match = re.match(r"(.+?)\s*-\s*(.+)", bullet)
                        if dash_match:
                            title = dash_match.group(1).strip()
                            description = dash_match.group(2).strip()

            items.append(
                CoCurricularItem(
                    title=title,
                    organization=organization,
                    period=period,
                    description=description,
                )
            )
        return items

from __future__ import annotations

from typing import Dict, Any


class LocationNormalizationService:
    """
    Geographic location normalization and cost-of-living (COL) tier mapping service.
    """

    @staticmethod
    def normalize_location(location_str: str) -> Dict[str, Any]:
        """
        Maps a location string to a canonical location name and a Cost-of-Living tier.
        Tiers:
          - TIER_1: High cost of living (SF, NY, Bay Area)
          - TIER_2: Medium-high cost of living (Austin, Seattle, Boston, Denver, LA)
          - TIER_3: Standard cost of living and Remote
        """
        loc = location_str.lower().strip()

        if not loc or any(word in loc for word in ("remote", "anywhere", "virtual", "wfh")):
            return {"location": "Remote", "col_tier": "TIER_3"}

        # Tier 1: SF, NY, Bay Area
        if any(
            word in loc
            for word in (
                "san francisco",
                "sf",
                "new york",
                "nyc",
                "bay area",
                "manhattan",
                "brooklyn",
            )
        ):
            canon = (
                "New York, NY"
                if any(w in loc for w in ("new york", "nyc", "manhattan", "brooklyn"))
                else "San Francisco, CA"
            )
            return {"location": canon, "col_tier": "TIER_1"}

        # Tier 2: Austin, Seattle, Boston, Denver, LA
        if any(
            word in loc
            for word in (
                "austin",
                "seattle",
                "boston",
                "denver",
                "los angeles",
                "la",
                "chicago",
            )
        ):
            canon = "Austin, TX"
            if "seattle" in loc:
                canon = "Seattle, WA"
            elif "boston" in loc:
                canon = "Boston, MA"
            elif "denver" in loc:
                canon = "Denver, CO"
            elif "los angeles" in loc or "la" in loc:
                canon = "Los Angeles, CA"
            elif "chicago" in loc:
                canon = "Chicago, IL"
            return {"location": canon, "col_tier": "TIER_2"}

        # Tier 3: Default/Others
        # Capitalize words for clean display
        canon_parts = [word.capitalize() for word in location_str.strip().split()]
        return {"location": " ".join(canon_parts), "col_tier": "TIER_3"}

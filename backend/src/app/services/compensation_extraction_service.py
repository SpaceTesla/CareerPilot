from __future__ import annotations

import re
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import CompensationRecord
from app.services.location_normalization_service import LocationNormalizationService

logger = get_logger(__name__)


class CompensationExtractionService:
    """
    Compensation Extraction and Normalization Service (F2.6).
    Extracts salary bounds from raw texts and converts them to
    standard USD annual figures.
    """

    @staticmethod
    def convert_to_usd(amount: float, currency: str) -> float:
        """
        Converts non-USD currencies to USD using baseline conversion rates.
        """
        cur = currency.upper().strip()
        if cur == "GBP":
            return amount * 1.3
        elif cur == "EUR":
            return amount * 1.1
        elif cur == "CAD":
            return amount * 0.75
        elif cur == "INR":
            return amount / 80.0
        return amount

    @staticmethod
    def normalize_range(
        min_val: float, max_val: float, interval: str, currency: str
    ) -> dict[str, float]:
        """
        Normalizes hourly, monthly, or annual rates into annual equivalents
        (assuming 2000 hours/yr).
        """
        multiplier = 1.0
        intv = interval.upper().strip()
        if intv == "HOURLY":
            multiplier = 2000.0
        elif intv == "MONTHLY":
            multiplier = 12.0
        elif intv == "WEEKLY":
            multiplier = 52.0

        min_annual = min_val * multiplier
        max_annual = max_val * multiplier

        # Translate to USD
        min_usd = CompensationExtractionService.convert_to_usd(min_annual, currency)
        max_usd = CompensationExtractionService.convert_to_usd(max_annual, currency)

        return {
            "computed_annual_min": round(min_usd, 2),
            "computed_annual_max": round(max_usd, 2),
        }

    @staticmethod
    def extract_salary_from_text(text: str) -> dict[str, Any] | None:
        """
        Runs regex parsing to identify salary ranges, currencies, and payment intervals.
        Supports ranges like:
          - "$140,000 - $180,000/yr"
          - "£60 - £80 per hour"
          - "$10,000 to $15,000 per month"
        """
        if not text:
            return None

        # Clean commas for easier regex number parsing (e.g. 140,000 -> 140000)
        text_clean = re.sub(r"(?<=\d),(?=\d)", "", text)

        # Detect currency
        currency = "USD"
        if "£" in text or "gbp" in text.lower():
            currency = "GBP"
        elif "€" in text or "eur" in text.lower():
            currency = "EUR"
        elif "₹" in text or "inr" in text.lower():
            currency = "INR"

        patterns = [
            # Annual range (e.g., $140000 - $180000 a year)
            (
                r"(?:\$|£|€|₹)\s*(\d+)\s*(?:-|to)\s*(?:\$|£|€|₹)\s*(\d+)\s*"
                r"(?:/\s*yr|/\s*year|/annum|per\s+year|a\s+year|a\s+yr|"
                r"annually|yr|annual)",
                "ANNUAL",
            ),
            # Hourly range (e.g., $60 - $80 per hour)
            (
                r"(?:\$|£|€|₹)\s*(\d+)\s*(?:-|to)\s*(?:\$|£|€|₹)\s*(\d+)\s*"
                r"(?:/\s*hr|/\s*hour|per\s+hour|a\s+hour|an\s+hour|"
                r"a\s+hr|an\s+hr|hourly|hr)",
                "HOURLY",
            ),
            # Monthly range (e.g., $10000 - $15000 / month)
            (
                r"(?:\$|£|€|₹)\s*(\d+)\s*(?:-|to)\s*(?:\$|£|€|₹)\s*(\d+)\s*"
                r"(?:/\s*mo|/\s*month|per\s+month|a\s+month|a\s+mo|"
                r"monthly|mo)",
                "MONTHLY",
            ),
            # Generic range without explicit interval
            (
                r"(?:\$|£|€|₹)\s*(\d{5,})\s*(?:-|to)\s*(?:\$|£|€|₹)\s*(\d{5,})",
                "ANNUAL",
            ),
            # Single generic salary (e.g., $140000 a year or $60/hr)
            (
                r"(?:\$|£|€|₹)\s*(\d+)\s*"
                r"(?:/\s*yr|/\s*year|/annum|per\s+year|a\s+year|a\s+yr|"
                r"annually|yr|annual)",
                "ANNUAL_SINGLE",
            ),
            (
                r"(?:\$|£|€|₹)\s*(\d+)\s*"
                r"(?:/\s*hr|/\s*hour|per\s+hour|a\s+hour|an\s+hour|"
                r"a\s+hr|an\s+hr|hourly|hr)",
                "HOURLY_SINGLE",
            ),
            (
                r"(?:\$|£|€|₹)\s*(\d+)\s*"
                r"(?:/\s*mo|/\s*month|per\s+month|a\s+month|a\s+mo|"
                r"monthly|mo)",
                "MONTHLY_SINGLE",
            ),
        ]

        for pattern, interval in patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                if "SINGLE" in interval:
                    val = float(match.group(1))
                    min_val, max_val = val, val
                    interval = interval.replace("_SINGLE", "")
                else:
                    min_val = float(match.group(1))
                    max_val = float(match.group(2))

                # Normalize range bounds
                return {
                    "min_salary": min_val,
                    "max_salary": max_val,
                    "currency": currency,
                    "payment_interval": interval,
                }

        return None

    @staticmethod
    async def process_and_save_compensation(
        db: AsyncSession, job_posting_id: str, description: str, location_raw: str
    ) -> CompensationRecord | None:
        """
        Extracts salary details from job description, normalizes values,
        maps location COL tier, and stores a CompensationRecord.
        Drops outlier records exceeding $1,000,000 and logs a warning.
        """
        extracted = CompensationExtractionService.extract_salary_from_text(description)
        if not extracted:
            return None

        # Normalize pay bounds to annual USD
        normalized = CompensationExtractionService.normalize_range(
            min_val=extracted["min_salary"],
            max_val=extracted["max_salary"],
            interval=extracted["payment_interval"],
            currency=extracted["currency"],
        )

        # Drop outliers
        if normalized["computed_annual_max"] > 1000000.0:
            logger.warning(
                f"Outlier salary parsed: "
                f"{normalized['computed_annual_max']} USD. Dropping record."
            )
            return None

        # Normalize location and map cost of living tier
        loc_normalized = LocationNormalizationService.normalize_location(location_raw)

        record = CompensationRecord(
            id=str(uuid4()),
            job_posting_id=job_posting_id,
            source_type="JOB_POSTING",
            min_salary=Decimal(str(extracted["min_salary"])),
            max_salary=Decimal(str(extracted["max_salary"])),
            currency=extracted["currency"],
            payment_interval=extracted["payment_interval"],
            computed_annual_min=Decimal(str(normalized["computed_annual_min"])),
            computed_annual_max=Decimal(str(normalized["computed_annual_max"])),
            equity_min=None,
            equity_max=None,
            location_normalized=loc_normalized["location"],
            col_tier=loc_normalized["col_tier"],
        )

        db.add(record)
        await db.flush()

        return record

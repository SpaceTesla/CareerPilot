from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal
from typing import List
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.infrastructure.database.models import (
    CompensationBenchmark,
    CompensationRecord,
    JobPosting,
    JobPostingSkill,
)
from app.utils.event_bus import EventBus

logger = get_logger(__name__)


def calculate_percentile(data: List[float], pct: float) -> float:
    """
    Computes the percentile using linear interpolation (equivalent to NumPy's default).
    """
    if not data:
        return 0.0
    sorted_data = sorted(data)
    n = len(sorted_data)
    k = (n - 1) * pct
    idx_floor = int(k)
    idx_ceil = idx_floor + 1
    if idx_ceil < n:
        return sorted_data[idx_floor] + (sorted_data[idx_ceil] - sorted_data[idx_floor]) * (
            k - idx_floor
        )
    return sorted_data[idx_floor]


class BenchmarkCalculatorService:
    """
    Weekly Compensation Benchmarking Aggregation Service (F2.6).
    Groups salaries by role, location, and skill and runs percentile statistics.
    """

    @staticmethod
    async def recalculate_benchmarks(db: AsyncSession) -> None:
        """
        Calculates P25, P50, and P75 benchmarks from raw compensation records.
        Wipes the old benchmarks table and aggregates fresh data.
        Only keeps benchmarks where sample size >= 5.
        Excludes records where max_salary / min_salary > 3.0.
        """
        logger.info("Starting compensation benchmarks recalculation...")

        # 1. Fetch all records that are eligible (ratio max/min <= 3.0)
        stmt = select(CompensationRecord).where(
            CompensationRecord.computed_annual_min > 0
        )
        res = await db.execute(stmt)
        all_records = res.scalars().all()

        eligible_records = []
        for r in all_records:
            min_val = float(r.computed_annual_min)
            max_val = float(r.computed_annual_max)
            if min_val > 0 and (max_val / min_val) <= 3.0:
                eligible_records.append(r)

        if not eligible_records:
            logger.info("No eligible compensation records found to compute benchmarks.")
            return

        # 2. Extract job posting relationships in batch to get title (role_type) and skills
        posting_ids = [r.job_posting_id for r in eligible_records if r.job_posting_id]
        postings_map = {}
        skills_map = {}

        if posting_ids:
            # Query postings
            stmt_postings = (
                select(JobPosting)
                .where(JobPosting.id.in_(posting_ids))
                .options(selectinload(JobPosting.skills))
            )
            res_postings = await db.execute(stmt_postings)
            for p in res_postings.scalars().all():
                postings_map[p.id] = p
                skills_map[p.id] = [s.skill_id for s in p.skills]

        # 3. Group records by (role_type, location) and (role_type, location, skill_id)
        # Groups will map: key -> list of midpoints (float)
        general_groups = {}
        skill_groups = {}

        for r in eligible_records:
            p_id = r.job_posting_id
            if not p_id or p_id not in postings_map:
                # If it's a verified user offer or no posting link, we skip or use default role
                role = "Software Engineer"
            else:
                role = postings_map[p_id].title

            location = r.location_normalized
            midpoint = float(r.computed_annual_min + r.computed_annual_max) / 2.0

            # General group
            g_key = (role, location)
            general_groups.setdefault(g_key, []).append(midpoint)

            # Skill-specific groups
            p_skills = skills_map.get(p_id, [])
            for s_id in p_skills:
                s_key = (role, location, s_id)
                skill_groups.setdefault(s_key, []).append(midpoint)

        # 4. Wipe old benchmarks
        await db.execute(delete(CompensationBenchmark))
        await db.flush()

        new_benchmarks = []

        # 5. Calculate & insert general benchmarks (sample size >= 5)
        for (role, loc), salaries in general_groups.items():
            if len(salaries) >= 5:
                p25 = calculate_percentile(salaries, 0.25)
                p50 = calculate_percentile(salaries, 0.50)
                p75 = calculate_percentile(salaries, 0.75)

                bench = CompensationBenchmark(
                    id=str(uuid4()),
                    role_type=role,
                    location_normalized=loc,
                    skill_id=None,
                    p25_salary=Decimal(str(round(p25, 2))),
                    p50_salary=Decimal(str(round(p50, 2))),
                    p75_salary=Decimal(str(round(p75, 2))),
                    sample_size=len(salaries),
                )
                db.add(bench)
                new_benchmarks.append(bench)

                # Emit benchmark updated event for general benchmarks
                await EventBus.publish(
                    "market.compensation_benchmark.updated",
                    {
                        "role_type": role,
                        "location": loc,
                        "p50_salary": float(round(p50, 2)),
                        "sample_size": len(salaries),
                    },
                )

        # 6. Calculate & insert skill-specific benchmarks (sample size >= 5)
        for (role, loc, s_id), salaries in skill_groups.items():
            if len(salaries) >= 5:
                p25 = calculate_percentile(salaries, 0.25)
                p50 = calculate_percentile(salaries, 0.50)
                p75 = calculate_percentile(salaries, 0.75)

                bench = CompensationBenchmark(
                    id=str(uuid4()),
                    role_type=role,
                    location_normalized=loc,
                    skill_id=s_id,
                    p25_salary=Decimal(str(round(p25, 2))),
                    p50_salary=Decimal(str(round(p50, 2))),
                    p75_salary=Decimal(str(round(p75, 2))),
                    sample_size=len(salaries),
                )
                db.add(bench)
                new_benchmarks.append(bench)

        await db.flush()
        logger.info(
            f"Successfully recalculated benchmarks. Inserted {len(new_benchmarks)} records."
        )

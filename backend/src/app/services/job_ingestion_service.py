from __future__ import annotations

import os
import re
from datetime import datetime, UTC
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.database.models import (
    Company,
    IngestionAuditLog,
    JobIngestionRun,
    JobPosting,
    JobPostingSkill,
    JobSource,
    NormalizedSkill,
    RawJobPosting,
)
from app.services.compensation_extraction_service import (
    CompensationExtractionService,
)
from app.services.job_deduplication_service import JobDeduplicationService
from app.services.location_normalization_service import (
    LocationNormalizationService,
)
from app.services.skill_extraction_service import SkillExtractionService
from app.utils.event_bus import EventBus

logger = get_logger(__name__)


class JSearchIngestionClient:
    """Client for JSearch API via RapidAPI."""

    @staticmethod
    async def fetch_jobs(
        query: str, location: str, page: int = 1
    ) -> List[Dict[str, Any]]:
        api_key = settings.jsearch_api_key or os.getenv("JSEARCH_API_KEY")
        if not api_key:
            logger.warning("JSearch API Key is not configured.")
            return []

        url = f"https://{settings.jsearch_api_host}/search"
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": settings.jsearch_api_host,
        }
        params = {
            "query": f"{query} in {location}",
            "page": str(page),
            "num_pages": "1",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("data", [])
            unified = []
            for job in results:
                ext_id = job.get("job_id")
                if not ext_id:
                    continue
                min_sal = job.get("job_min_salary")
                max_sal = job.get("job_max_salary")
                salary_raw = None
                if min_sal is not None or max_sal is not None:
                    salary_raw = {
                        "min_salary": min_sal,
                        "max_salary": max_sal,
                        "currency": job.get("job_salary_currency", "USD"),
                        "payment_interval": job.get("job_salary_period", "YEAR"),
                    }

                city = job.get("job_city") or ""
                state = job.get("job_state") or ""
                country = job.get("job_country") or ""
                loc_parts = [p for p in (city, state, country) if p]
                loc_raw = ", ".join(loc_parts) if loc_parts else "Remote"

                unified.append(
                    {
                        "external_id": ext_id,
                        "title": job.get("job_title") or "Unknown Title",
                        "company_name": job.get("employer_name") or "Unknown Company",
                        "description": job.get("job_description") or "",
                        "location_raw": loc_raw,
                        "url": job.get("job_apply_link") or "",
                        "salary_raw": salary_raw,
                        "raw_payload": job,
                    }
                )
            return unified


class AdzunaIngestionClient:
    """Client for Adzuna API."""

    @staticmethod
    async def fetch_jobs(
        query: str, location: str, page: int = 1
    ) -> List[Dict[str, Any]]:
        app_id = os.getenv("ADZUNA_APP_ID")
        app_key = os.getenv("ADZUNA_APP_KEY")
        if not app_id or not app_key:
            logger.warning("Adzuna API App ID or App Key not configured.")
            return []

        url = f"https://api.adzuna.com/v1/api/jobs/us/search/{page}"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": "20",
            "what": query,
            "where": location,
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            unified = []
            for job in results:
                ext_id = job.get("id")
                if not ext_id:
                    continue
                min_sal = job.get("salary_min")
                max_sal = job.get("salary_max")
                salary_raw = None
                if min_sal is not None or max_sal is not None:
                    salary_raw = {
                        "min_salary": min_sal,
                        "max_salary": max_sal,
                        "currency": "USD",
                        "payment_interval": "ANNUAL",
                    }

                loc_data = job.get("location", {})
                loc_raw = loc_data.get("display_name") or "Remote"

                unified.append(
                    {
                        "external_id": str(ext_id),
                        "title": job.get("title") or "Unknown Title",
                        "company_name": job.get("company", {}).get("display_name")
                        or "Unknown Company",
                        "description": job.get("description") or "",
                        "location_raw": loc_raw,
                        "url": job.get("redirect_url") or "",
                        "salary_raw": salary_raw,
                        "raw_payload": job,
                    }
                )
            return unified


class GreenhouseCrawlerClient:
    """Client for crawling public Greenhouse job boards."""

    @staticmethod
    async def fetch_board_jobs(company_board_id: str) -> List[Dict[str, Any]]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_board_id}/jobs"
        params = {"content": "true"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("jobs", [])
            unified = []
            for job in results:
                ext_id = job.get("id")
                if not ext_id:
                    continue

                loc_data = job.get("location", {})
                loc_raw = loc_data.get("name") or "Remote"

                desc_html = job.get("content") or ""
                desc_clean = re.sub(r"<[^>]*>", "", desc_html).strip()

                unified.append(
                    {
                        "external_id": f"greenhouse_{ext_id}",
                        "title": job.get("title") or "Unknown Title",
                        "company_name": company_board_id.title(),
                        "description": desc_clean,
                        "location_raw": loc_raw,
                        "url": job.get("absolute_url") or "",
                        "salary_raw": None,
                        "raw_payload": job,
                    }
                )
            return unified


class LeverCrawlerClient:
    """Client for crawling public Lever job boards."""

    @staticmethod
    async def fetch_board_jobs(company_board_id: str) -> List[Dict[str, Any]]:
        url = f"https://api.lever.co/v0/postings/{company_board_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            results = resp.json()

            unified = []
            for job in results:
                ext_id = job.get("id")
                if not ext_id:
                    continue

                categories = job.get("categories", {})
                loc_raw = categories.get("location") or "Remote"

                desc_clean = job.get("descriptionPlain") or ""
                if not desc_clean:
                    desc_html = job.get("description") or ""
                    desc_clean = re.sub(r"<[^>]*>", "", desc_html).strip()

                unified.append(
                    {
                        "external_id": f"lever_{ext_id}",
                        "title": job.get("text") or "Unknown Title",
                        "company_name": company_board_id.title(),
                        "description": desc_clean,
                        "location_raw": loc_raw,
                        "url": job.get("hostedUrl") or "",
                        "salary_raw": None,
                        "raw_payload": job,
                    }
                )
            return unified


class JobIngestionService:
    """
    Ingestion service orchestrating job collection, staging, normalization,
    deduplication, and skill taxonomy resolution.
    """

    @staticmethod
    def normalize_title(raw_title: str) -> str:
        """
        Maps raw titles to standardized role tiers.
        """
        t = raw_title.lower().strip()
        is_senior = any(
            w in t for w in ("sr", "senior", "lead", "principal", "staff")
        )
        is_junior = any(w in t for w in ("jr", "junior"))
        is_backend = any(
            w in t
            for w in ("backend", "back-end", "python", "django", "node", "java")
        )
        is_frontend = any(
            w in t
            for w in (
                "frontend",
                "front-end",
                "react",
                "angular",
                "vue",
                "javascript",
                "typescript",
            )
        )
        is_fullstack = any(w in t for w in ("fullstack", "full-stack"))

        role = "Software Engineer"
        if is_backend:
            role = "Backend Engineer"
        elif is_frontend:
            role = "Frontend Engineer"
        elif is_fullstack:
            role = "Fullstack Engineer"

        if is_senior:
            return f"Senior {role}"
        if is_junior:
            return f"Junior {role}"
        return role

    @staticmethod
    async def process_job_entry(
        db: AsyncSession,
        raw_job: Dict[str, Any],
        run_id: str,
        source_key: str,
    ) -> bool:
        """
        Processes a single job dictionary: saves RawJobPosting, maps Company,
        normalizes Title & Location, extracts salary/compensation, evaluates duplicate states,
        resolves/links skills taxonomy, and publishes events.
        Returns True if newly inserted, False if duplicate or skipped.
        """
        source_key_clean = source_key.lower().strip()

        # Check if already staged in RawJobPosting
        chk_stmt = select(RawJobPosting).where(
            RawJobPosting.source_key == source_key_clean,
            RawJobPosting.external_id == raw_job["external_id"],
        )
        chk_res = await db.execute(chk_stmt)
        existing_raw = chk_res.scalar_one_or_none()

        if not existing_raw:
            raw_post = RawJobPosting(
                id=str(uuid4()),
                ingestion_run_id=run_id,
                source_key=source_key_clean,
                external_id=raw_job["external_id"],
                title=raw_job["title"],
                company_name=raw_job["company_name"],
                description=raw_job["description"],
                location_raw=raw_job["location_raw"],
                url=raw_job["url"],
                salary_raw=raw_job["salary_raw"],
                raw_payload=raw_job["raw_payload"],
            )
            db.add(raw_post)
            await db.flush()

            await EventBus.publish(
                "market.raw_job.ingested",
                {
                    "raw_job_id": raw_post.id,
                    "source_key": source_key_clean,
                    "external_id": raw_job["external_id"],
                    "company_name": raw_job["company_name"],
                    "title": raw_job["title"],
                },
            )

        # Process/Normalize into core job_postings table
        core_chk = select(JobPosting).where(
            JobPosting.source_id == raw_job["external_id"]
        )
        core_res = await db.execute(core_chk)
        existing_core = core_res.scalar_one_or_none()

        if existing_core:
            return False

        # Get/Create Company
        comp_name_clean = JobDeduplicationService.clean_company(
            raw_job["company_name"]
        ).title()
        comp_stmt = select(Company).where(Company.name == comp_name_clean)
        comp_res = await db.execute(comp_stmt)
        company = comp_res.scalar_one_or_none()

        if not company:
            company = Company(
                id=str(uuid4()),
                name=comp_name_clean,
            )
            db.add(company)
            await db.flush()

        # Normalize title & location
        normalized_title = JobIngestionService.normalize_title(raw_job["title"])
        loc_normalized = LocationNormalizationService.normalize_location(
            raw_job["location_raw"]
        )

        job_posting = JobPosting(
            id=str(uuid4()),
            company_id=company.id,
            title=normalized_title,
            raw_title=raw_job["title"],
            location=loc_normalized["location"],
            description=raw_job["description"],
            url=raw_job["url"],
            source=source_key_clean.upper(),
            source_id=raw_job["external_id"],
            post_date=datetime.utcnow().date(),
            is_active=True,
            is_primary=True,
        )
        db.add(job_posting)
        await db.flush()

        # Extract salary bounds
        comp_rec = (
            await CompensationExtractionService.process_and_save_compensation(
                db=db,
                job_posting_id=job_posting.id,
                description=job_posting.description,
                location_raw=raw_job["location_raw"],
            )
        )

        if comp_rec:
            if comp_rec.min_salary > 0:
                ratio = float(comp_rec.max_salary / comp_rec.min_salary)
                if ratio > 3.0:
                    logger.warning(
                        f"Exaggerated salary range ratio ({ratio:.2f}) for job {job_posting.id}. Excluded."
                    )
                    await db.delete(comp_rec)
                    comp_rec = None

            if comp_rec:
                job_posting.compensation_min = comp_rec.min_salary
                job_posting.compensation_max = comp_rec.max_salary
                job_posting.currency = comp_rec.currency
                await db.flush()

        # Run deduplication engine
        merge_primary_id = (
            await JobDeduplicationService.evaluate_and_deduplicate(
                db, job_posting
            )
        )

        if merge_primary_id:
            return False

        # Extract and link required skills
        ext_skills = await SkillExtractionService.extract_skills_from_text(
            db, job_posting.description
        )
        skill_names = []
        for ext_s in ext_skills:
            skill_stmt = select(NormalizedSkill).where(
                NormalizedSkill.name == ext_s.canonical_name
            )
            skill_res = await db.execute(skill_stmt)
            skill_db = skill_res.scalar_one_or_none()

            if not skill_db:
                skill_db = await SkillExtractionService.add_new_skill(
                    db,
                    ext_s.canonical_name,
                    ext_s.category,
                    [ext_s.alias_resolved_from],
                )

            jp_skill = JobPostingSkill(
                id=str(uuid4()),
                job_posting_id=job_posting.id,
                skill_id=skill_db.id,
                raw_mention=ext_s.alias_resolved_from,
                extraction_method=(
                    "SPACY_NER"
                    if ext_s.confidence_score >= 1.0
                    else "LLM_FALLBACK"
                ),
                confidence_score=Decimal(str(round(ext_s.confidence_score, 3))),
                context_sentence=ext_s.context_sentence,
            )
            db.add(jp_skill)
            skill_names.append(ext_s.canonical_name)

        await db.flush()

        # Publish job ingested event
        await EventBus.publish(
            "market.job_ingested",
            {
                "job_posting_id": job_posting.id,
                "company_name": company.name,
                "normalized_title": job_posting.title,
                "skills": skill_names,
            },
        )

        return True

    @staticmethod
    async def trigger_run(
        db: AsyncSession,
        source_key: str,
        query: str,
        location: str,
        limit: int = 100,
    ) -> str:
        """
        Initializes an ingestion run, queries the client, stages raw postings,
        and processes the raw postings.
        """
        source_key_clean = source_key.lower().strip()
        stmt = select(JobSource).where(JobSource.source_key == source_key_clean)
        res = await db.execute(stmt)
        job_source = res.scalar_one_or_none()

        if not job_source:
            job_source = JobSource(
                id=str(uuid4()),
                name=source_key.upper() + " Ingestion Source",
                source_key=source_key_clean,
                is_active=True,
                error_count_24h=0,
                last_run_status="PENDING",
            )
            db.add(job_source)
            await db.flush()

        run_id = str(uuid4())
        run = JobIngestionRun(
            id=run_id,
            source_id=job_source.id,
            status="RUNNING",
            items_scraped=0,
            items_inserted=0,
            items_failed=0,
            started_at=datetime.utcnow(),
        )
        db.add(run)
        await db.flush()

        await EventBus.publish(
            "market.job_ingestion_run.started",
            {
                "run_id": run_id,
                "source_key": source_key_clean,
                "triggered_by": "api_trigger",
            },
        )

        try:
            raw_postings = []
            if source_key_clean == "jsearch":
                raw_postings = await JSearchIngestionClient.fetch_jobs(
                    query, location
                )
            elif source_key_clean == "adzuna":
                raw_postings = await AdzunaIngestionClient.fetch_jobs(
                    query, location
                )
            elif source_key_clean == "greenhouse":
                raw_postings = await GreenhouseCrawlerClient.fetch_board_jobs(
                    query
                )
            elif source_key_clean == "lever":
                raw_postings = await LeverCrawlerClient.fetch_board_jobs(query)
            else:
                raise ValueError(f"Unknown source key: {source_key_clean}")

            raw_postings = raw_postings[:limit]
            run.items_scraped = len(raw_postings)
            await db.flush()

            inserted_count = 0
            duplicated_count = 0
            failed_count = 0
            log_details = {"duplicates": [], "failures": []}

            for raw_job in raw_postings:
                try:
                    is_new = await JobIngestionService.process_job_entry(
                        db=db,
                        raw_job=raw_job,
                        run_id=run_id,
                        source_key=source_key_clean,
                    )
                    if is_new:
                        inserted_count += 1
                    else:
                        duplicated_count += 1
                except Exception as ex:
                    logger.error(
                        f"Failed processing individual job: {ex}",
                        exc_info=True,
                    )
                    failed_count += 1
                    log_details["failures"].append(
                        {
                            "external_id": raw_job.get("external_id"),
                            "error": str(ex),
                        }
                    )

            audit = IngestionAuditLog(
                id=str(uuid4()),
                source=source_key_clean.upper(),
                job_count_attempted=len(raw_postings),
                job_count_inserted=inserted_count,
                job_count_duplicated=duplicated_count,
                job_count_failed=failed_count,
                log_details=log_details,
                created_at=datetime.utcnow(),
            )
            db.add(audit)

            run.status = "COMPLETED"
            run.items_inserted = inserted_count
            run.items_failed = failed_count
            run.completed_at = datetime.utcnow()

            job_source.last_run_status = "SUCCESS"
            job_source.last_run_at = datetime.utcnow()
            job_source.error_count_24h = max(0, job_source.error_count_24h - 1)

            await db.flush()

            await EventBus.publish(
                "market.job_ingestion_run.completed",
                {
                    "run_id": run_id,
                    "source_key": source_key_clean,
                    "items_scraped": len(raw_postings),
                    "items_inserted": inserted_count,
                    "items_failed": failed_count,
                },
            )

            await EventBus.publish(
                "market.ingestion_completed",
                {
                    "audit_log_id": audit.id,
                    "source": source_key_clean.upper(),
                    "inserted_count": inserted_count,
                    "failed_count": failed_count,
                },
            )

        except Exception as e:
            logger.error(f"Ingestion run failed: {e}", exc_info=True)
            run.status = "FAILED"
            run.error_log = str(e)
            run.completed_at = datetime.utcnow()

            job_source.last_run_status = "DEGRADED"
            job_source.error_count_24h += 1
            await db.flush()

            await EventBus.publish(
                "market.job_ingestion_run.completed",
                {
                    "run_id": run_id,
                    "source_key": source_key_clean,
                    "items_scraped": 0,
                    "items_inserted": 0,
                    "items_failed": 0,
                    "error": str(e),
                },
            )
            raise

        return run_id

    @staticmethod
    async def ingest_postings(
        db: AsyncSession, source: str, postings: List[Dict[str, Any]]
    ) -> str:
        """
        Directly ingests a list of dictionary postings. Used by admin APIs.
        """
        source_key_clean = source.lower().strip()
        stmt = select(JobSource).where(JobSource.source_key == source_key_clean)
        res = await db.execute(stmt)
        job_source = res.scalar_one_or_none()

        if not job_source:
            job_source = JobSource(
                id=str(uuid4()),
                name=source.upper() + " Ingestion Source",
                source_key=source_key_clean,
                is_active=True,
                error_count_24h=0,
                last_run_status="PENDING",
            )
            db.add(job_source)
            await db.flush()

        run_id = str(uuid4())
        run = JobIngestionRun(
            id=run_id,
            source_id=job_source.id,
            status="RUNNING",
            items_scraped=len(postings),
            items_inserted=0,
            items_failed=0,
            started_at=datetime.utcnow(),
        )
        db.add(run)
        await db.flush()

        await EventBus.publish(
            "market.job_ingestion_run.started",
            {
                "run_id": run_id,
                "source_key": source_key_clean,
                "triggered_by": "admin_ingest",
            },
        )

        inserted_count = 0
        duplicated_count = 0
        failed_count = 0
        log_details = {"duplicates": [], "failures": []}

        for p_dict in postings:
            try:
                # Format to matching unified schema
                salary_raw = None
                if (
                    p_dict.get("compensation_min") is not None
                    or p_dict.get("compensation_max") is not None
                ):
                    salary_raw = {
                        "min_salary": float(p_dict.get("compensation_min") or 0.0),
                        "max_salary": float(p_dict.get("compensation_max") or 0.0),
                        "currency": p_dict.get("currency") or "USD",
                        "payment_interval": "ANNUAL",
                    }

                unified = {
                    "external_id": p_dict["source_id"],
                    "title": p_dict["title"],
                    "company_name": p_dict["company_name"],
                    "description": p_dict["description"],
                    "location_raw": p_dict["location"],
                    "url": p_dict["url"],
                    "salary_raw": salary_raw,
                    "raw_payload": p_dict,
                }

                is_new = await JobIngestionService.process_job_entry(
                    db=db,
                    raw_job=unified,
                    run_id=run_id,
                    source_key=source_key_clean,
                )
                if is_new:
                    inserted_count += 1
                else:
                    duplicated_count += 1
            except Exception as ex:
                logger.error(
                    f"Failed processing individual job: {ex}", exc_info=True
                )
                failed_count += 1
                log_details["failures"].append(
                    {
                        "source_id": p_dict.get("source_id"),
                        "error": str(ex),
                    }
                )

        audit = IngestionAuditLog(
            id=str(uuid4()),
            source=source_key_clean.upper(),
            job_count_attempted=len(postings),
            job_count_inserted=inserted_count,
            job_count_duplicated=duplicated_count,
            job_count_failed=failed_count,
            log_details=log_details,
            created_at=datetime.utcnow(),
        )
        db.add(audit)

        run.status = "COMPLETED"
        run.items_inserted = inserted_count
        run.items_failed = failed_count
        run.completed_at = datetime.utcnow()

        job_source.last_run_status = "SUCCESS"
        job_source.last_run_at = datetime.utcnow()

        await db.flush()

        await EventBus.publish(
            "market.job_ingestion_run.completed",
            {
                "run_id": run_id,
                "source_key": source_key_clean,
                "items_scraped": len(postings),
                "items_inserted": inserted_count,
                "items_failed": failed_count,
            },
        )

        await EventBus.publish(
            "market.ingestion_completed",
            {
                "audit_log_id": audit.id,
                "source": source_key_clean.upper(),
                "inserted_count": inserted_count,
                "failed_count": failed_count,
            },
        )

        return audit.id

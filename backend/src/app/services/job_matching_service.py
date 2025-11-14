"""Job matching and recommendation service using JSearch API and Tavily fallback."""

from __future__ import annotations

from typing import Any

import httpx
from tavily import TavilyClient

from app.core.config import settings
from app.infrastructure.database.connection import get_session
from app.infrastructure.database.repositories.resume_repository import ResumeRepository
from app.services.analysis_service import analysis_service


class JobMatchingService:
    """Service for job matching and recommendations."""

    def __init__(self) -> None:
        self.tavily_client = TavilyClient(api_key=settings.tavily_api_key)
        self.jsearch_api_key = settings.jsearch_api_key
        self.jsearch_api_host = settings.jsearch_api_host

    def _load_user_profile(self, user_id: str | None) -> dict[str, Any]:
        """Load user profile data."""
        if not user_id:
            return {}

        with get_session() as session:
            repo = ResumeRepository(session)
            profiles = repo.get_by_user(user_id)
            if not profiles:
                return {}

            profile = sorted(profiles, key=lambda p: p.updated_at, reverse=True)[0]
            raw_data = getattr(profile, "raw_data", {}) or {}

            return {
                "skills": raw_data.get("skills", {}),
                "experience": raw_data.get("experience", []),
                "location": getattr(profile, "location", None),
            }

    async def _get_jobs_from_jsearch(
        self, query: str, location: str | None, limit: int
    ) -> list[dict[str, Any]]:
        """Get real job postings from JSearch API."""
        if not self.jsearch_api_key:
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://jsearch.p.rapidapi.com/search"
                params = {
                    "query": query,
                    "page": "1",
                    "num_pages": "1",
                }
                if location:
                    params["location"] = location

                headers = {
                    "X-RapidAPI-Key": self.jsearch_api_key,
                    "X-RapidAPI-Host": self.jsearch_api_host,
                }

                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()

                jobs = []
                results = data.get("data", [])
                
                for job in results[:limit]:
                    # Filter out non-job results (guides, articles, etc.)
                    job_title = job.get("job_title", "").lower()
                    job_url = job.get("job_apply_link") or job.get("job_google_link", "")
                    
                    # Skip if it's clearly not a job posting
                    skip_keywords = ["guide", "how to", "career path", "salary", "article", "blog"]
                    if any(keyword in job_title for keyword in skip_keywords):
                        continue
                    
                    # Only include if we have a valid application URL
                    if not job_url or "google.com/search" in job_url:
                        continue
                    
                    jobs.append({
                        "title": job.get("job_title", "Job Opening"),
                        "company": job.get("employer_name", "Company"),
                        "location": job.get("job_city") or job.get("job_state") or location or "Remote",
                        "url": job_url,
                        "description": job.get("job_description", "")[:300] + "...",
                        "posted_date": job.get("job_posted_at_datetime_utc"),
                        "job_type": job.get("job_employment_type"),
                        "salary_min": job.get("job_min_salary"),
                        "salary_max": job.get("job_max_salary"),
                        "source": job.get("job_publisher", "Job Board"),
                    })

                return jobs
        except Exception as e:
            print(f"JSearch API error: {e}")
            return []

    async def _get_jobs_from_tavily_fallback(
        self, query: str, limit: int
    ) -> list[dict[str, Any]]:
        """Fallback to Tavily search (returns general results, not ideal)."""
        try:
            response = self.tavily_client.search(
                query=f"{query} site:linkedin.com/jobs OR site:indeed.com OR site:naukri.com",
                search_depth="basic",
                max_results=limit * 2,  # Get more to filter
            )

            jobs = []
            for result in response.get("results", [])[:limit * 2]:
                title = result.get("title", "")
                url = result.get("url", "")
                
                # Filter for actual job postings
                if not url or not any(
                    domain in url.lower()
                    for domain in ["linkedin.com/jobs", "indeed.com", "naukri.com", "glassdoor.com"]
                ):
                    continue
                
                # Skip guides and articles
                skip_keywords = ["guide", "how to", "career path", "salary guide"]
                if any(keyword in title.lower() for keyword in skip_keywords):
                    continue

                jobs.append({
                    "title": title,
                    "url": url,
                    "description": result.get("content", "")[:200] + "...",
                    "source": self._extract_source_from_url(url),
                })
                
                if len(jobs) >= limit:
                    break

            return jobs
        except Exception as e:
            print(f"Tavily fallback error: {e}")
            return []

    def _extract_source_from_url(self, url: str) -> str:
        """Extract job board name from URL."""
        url_lower = url.lower()
        if "linkedin.com" in url_lower:
            return "LinkedIn"
        elif "indeed.com" in url_lower:
            return "Indeed"
        elif "naukri.com" in url_lower:
            return "Naukri"
        elif "glassdoor.com" in url_lower:
            return "Glassdoor"
        elif "monster.com" in url_lower:
            return "Monster"
        else:
            return "Job Board"

    async def get_recommendations(self, user_id: str | None, limit: int = 10) -> dict[str, Any]:
        """Get personalized job recommendations."""
        if not user_id:
            return {"error": "User ID is required"}

        profile = self._load_user_profile(user_id)
        if not profile:
            return {"error": "No profile found"}

        # Determine role focus
        from app.services.agent.tools.resume_tools import get_skills_tool

        skills_data = await get_skills_tool(user_id)
        if "error" in skills_data:
            return skills_data

        current_focus = analysis_service._determine_role_focus(
            skills_data, profile.get("experience", [])
        )

        # Extract key skills for better matching
        all_skills = []
        skills_dict = profile.get("skills", {})
        all_skills.extend(skills_dict.get("languages", [])[:3])
        all_skills.extend(skills_dict.get("frameworks", [])[:2])
        
        # Build search query
        query = current_focus
        if all_skills:
            query += f" {' '.join(all_skills[:2])}"
        
        location = profile.get("location")

        # Try JSearch API first (real job postings)
        jobs = await self._get_jobs_from_jsearch(query, location, limit)
        
        # Fallback to Tavily if JSearch fails or not configured
        if not jobs:
            jobs = await self._get_jobs_from_tavily_fallback(query, limit)

        return {
            "jobs": jobs,
            "role_focus": current_focus,
            "total_found": len(jobs),
            "source": "jsearch" if self.jsearch_api_key and jobs else "tavily",
        }

    async def get_salary_insights(
        self, user_id: str | None, location: str | None = None
    ) -> dict[str, Any]:
        """Get salary insights based on skills and experience."""
        if not user_id:
            return {"error": "User ID is required"}

        profile = self._load_user_profile(user_id)
        if not profile:
            return {"error": "No profile found"}

        from app.services.agent.tools.resume_tools import get_experience_tool, get_skills_tool

        skills_data = await get_skills_tool(user_id)
        experience_data = await get_experience_tool(user_id)

        if "error" in skills_data:
            return skills_data

        current_focus = analysis_service._determine_role_focus(skills_data, experience_data)
        years_experience = len(experience_data)

        # Build salary search query
        search_query = f"{current_focus} salary"
        if location:
            search_query += f" {location}"
        if years_experience > 0:
            search_query += f" {years_experience} years experience"

        try:
            response = self.tavily_client.search(
                query=search_query,
                search_depth="basic",
                max_results=5,
            )

            # Extract salary information from results
            salary_ranges = []
            for result in response.get("results", [])[:3]:
                content = result.get("content", "").lower()
                # Simple extraction (in production, use more sophisticated parsing)
                if "$" in result.get("content", ""):
                    salary_ranges.append({
                        "source": result.get("title", "Salary Data"),
                        "url": result.get("url", ""),
                        "content": result.get("content", "")[:300],
                    })

            # Default ranges based on role and experience
            default_ranges = self._get_default_salary_ranges(current_focus, years_experience, location)

            return {
                "role": current_focus,
                "years_experience": years_experience,
                "location": location or "General",
                "salary_ranges": salary_ranges if salary_ranges else default_ranges,
                "sources": [s.get("url", "") for s in salary_ranges[:3]],
            }
        except Exception as e:
            # Return default ranges if search fails
            return {
                "role": current_focus,
                "years_experience": years_experience,
                "location": location or "General",
                "salary_ranges": self._get_default_salary_ranges(current_focus, years_experience, location),
                "error": f"Could not fetch live data: {str(e)}",
            }

    def _get_default_salary_ranges(
        self, role: str, years_experience: int, location: str | None
    ) -> list[dict[str, Any]]:
        """Get default salary ranges when API fails."""
        base_salaries = {
            "Backend Developer": {"junior": 60000, "mid": 90000, "senior": 130000},
            "Frontend Developer": {"junior": 55000, "mid": 85000, "senior": 120000},
            "Full-Stack Developer": {"junior": 65000, "mid": 95000, "senior": 140000},
            "DevOps Engineer": {"junior": 70000, "mid": 100000, "senior": 150000},
            "Software Developer": {"junior": 60000, "mid": 90000, "senior": 130000},
        }

        role_key = role
        for key in base_salaries:
            if key.lower() in role.lower():
                role_key = key
                break

        salaries = base_salaries.get(role_key, base_salaries["Software Developer"])

        if years_experience < 2:
            level = "junior"
        elif years_experience < 5:
            level = "mid"
        else:
            level = "senior"

        base_salary = salaries[level]

        return [
            {
                "level": level.title(),
                "range": f"${base_salary - 10000:,} - ${base_salary + 20000:,}",
                "median": f"${base_salary:,}",
                "note": "Estimated based on role and experience level",
            }
        ]


# Singleton instance
job_matching_service = JobMatchingService()

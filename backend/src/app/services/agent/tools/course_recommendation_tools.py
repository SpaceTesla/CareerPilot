"""Course recommendation tools using Tavily search and agent context."""

from __future__ import annotations

from typing import Any

from tavily import TavilyClient

from app.core.config import settings


class CourseRecommendationService:
    """Service for recommending courses using Tavily search and agent context."""

    def __init__(self) -> None:
        self.search_tool = TavilyClient(api_key=settings.tavily_api_key)

    def _extract_skills_from_context(self, skills_data: dict[str, Any]) -> list[str]:
        """Extract skills from agent's skills tool result."""
        skills = []

        # Extract from skills section (already processed by agent)
        skills.extend(skills_data.get("languages", []))
        skills.extend(skills_data.get("frameworks", []))
        skills.extend(skills_data.get("tools", []))

        # Remove duplicates and normalize
        unique_skills = list(
            {skill.lower().strip() for skill in skills if skill.strip()}
        )
        return unique_skills[:10]  # Return top 10 skills

    def _determine_role_focus_from_context(
        self, skills_data: dict[str, Any], experience_data: list[dict[str, Any]]
    ) -> str:
        """Determine the primary role focus based on agent tool results."""
        # Count backend-related terms
        backend_terms = [
            "backend",
            "api",
            "server",
            "database",
            "python",
            "java",
            "node",
            "django",
            "flask",
            "spring",
            "sql",
            "postgresql",
            "mongodb",
            "redis",
            "aws",
            "docker",
            "kubernetes",
            "microservices",
        ]
        frontend_terms = [
            "frontend",
            "front-end",
            "ui",
            "ux",
            "react",
            "angular",
            "vue",
            "javascript",
            "typescript",
            "html",
            "css",
            "sass",
            "scss",
        ]
        fullstack_terms = [
            "fullstack",
            "full-stack",
            "full stack",
            "mern",
            "mean",
            "lamp",
            "jamstack",
        ]
        devops_terms = [
            "devops",
            "dev-ops",
            "ci/cd",
            "jenkins",
            "terraform",
            "ansible",
            "kubernetes",
            "docker",
            "aws",
            "azure",
            "gcp",
            "monitoring",
            "logging",
        ]
        data_terms = [
            "data",
            "analytics",
            "machine learning",
            "ml",
            "ai",
            "python",
            "r",
            "sql",
            "pandas",
            "numpy",
            "tensorflow",
            "pytorch",
            "scikit-learn",
        ]

        backend_score = 0
        frontend_score = 0
        fullstack_score = 0
        devops_score = 0
        data_score = 0

        # Analyze experience data from agent
        for exp in experience_data:
            if isinstance(exp, dict):
                role = exp.get("role", "").lower()
                details = exp.get("details", [])
                combined_text = role + " " + " ".join(details).lower()

                backend_score += sum(
                    1 for term in backend_terms if term in combined_text
                )
                frontend_score += sum(
                    1 for term in frontend_terms if term in combined_text
                )
                fullstack_score += sum(
                    1 for term in fullstack_terms if term in combined_text
                )
                devops_score += sum(1 for term in devops_terms if term in combined_text)
                data_score += sum(1 for term in data_terms if term in combined_text)

        # Analyze skills data from agent
        all_skills = []
        for skill_list in skills_data.values():
            if isinstance(skill_list, list):
                all_skills.extend([skill.lower() for skill in skill_list])

        skills_text = " ".join(all_skills)
        backend_score += sum(1 for term in backend_terms if term in skills_text)
        frontend_score += sum(1 for term in frontend_terms if term in skills_text)
        fullstack_score += sum(1 for term in fullstack_terms if term in skills_text)
        devops_score += sum(1 for term in devops_terms if term in skills_text)
        data_score += sum(1 for term in data_terms if term in skills_text)

        # Determine primary focus
        scores = {
            "backend": backend_score,
            "frontend": frontend_score,
            "fullstack": fullstack_score,
            "devops": devops_score,
            "data": data_score,
        }

        primary_role = max(scores, key=scores.get)
        return primary_role if scores[primary_role] > 0 else "general"

    def _generate_search_queries(self, skills: list[str], role: str) -> list[str]:
        """Generate search queries for course recommendations."""
        queries = []

        # Role-specific course queries with platform-specific searches
        role_queries = {
            "backend": [
                "backend development course coursera udemy",
                "API development course online",
                "microservices course 2024",
                "database design course online",
                "AWS cloud computing course",
                "Python backend course",
                "Node.js course online",
                "Spring Boot course",
            ],
            "frontend": [
                "React course online 2024",
                "JavaScript course udemy coursera",
                "frontend development course",
                "UI UX design course online",
                "TypeScript course 2024",
                "Vue.js course online",
                "Angular course online",
                "CSS course online",
            ],
            "fullstack": [
                "fullstack development course 2024",
                "MERN stack course online",
                "web development bootcamp",
                "fullstack JavaScript course",
                "MEAN stack course",
                "web development course online",
                "programming bootcamp online",
                "coding bootcamp 2024",
            ],
            "devops": [
                "DevOps course online 2024",
                "Docker course udemy",
                "Kubernetes course online",
                "AWS DevOps course",
                "CI CD course online",
                "Terraform course",
                "Jenkins course online",
                "cloud computing course",
            ],
            "data": [
                "data science course online 2024",
                "machine learning course coursera",
                "Python data analysis course",
                "SQL course online",
                "data visualization course",
                "pandas course online",
                "numpy course online",
                "statistics course online",
            ],
        }

        # Add role-specific queries
        if role in role_queries:
            queries.extend(role_queries[role][:4])  # Top 4 role-specific queries

        # Add skill-specific queries with platform names
        for skill in skills[:3]:  # Top 3 skills
            queries.append(f"{skill} course udemy coursera")
            queries.append(f"learn {skill} online course")

        # Add platform-specific general queries
        queries.extend(
            [
                "programming course udemy",
                "coding course coursera",
                "software engineering course online",
                "computer science course online",
            ]
        )

        return queries[:6]  # Limit to 6 queries for better results

    def _parse_search_results(
        self, search_results: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Parse Tavily search results into structured course recommendations."""
        courses = []

        # Tavily returns a dict with 'results' containing a list of result objects
        if not isinstance(search_results, dict) or "results" not in search_results:
            return courses

        results = search_results.get("results", [])

        course_indicators = [
            "course",
            "tutorial",
            "learn",
            "training",
            "bootcamp",
            "certification",
            "certificate",
            "class",
            "lesson",
            "program",
            "masterclass",
            "workshop",
            "seminar",
            "webinar",
        ]

        for result in results:
            if not isinstance(result, dict):
                continue

            title = result.get("title", "")
            content = result.get("content", "")
            url = result.get("url", "")

            # Combine title and content for analysis
            combined_text = f"{title} {content}".lower()

            # Check if this result contains course-related content
            if any(indicator in combined_text for indicator in course_indicators):
                # Extract platform from title, content, and URL
                platform = self._extract_platform(title, content + " " + url)

                # Clean up the title
                clean_title = title[:100] + "..." if len(title) > 100 else title
                clean_description = (
                    content[:200] + "..." if len(content) > 200 else content
                )

                courses.append(
                    {
                        "title": clean_title,
                        "description": clean_description,
                        "platform": platform,
                        "url": url,
                        "relevance_score": self._calculate_relevance_score(
                            title, content
                        ),
                    }
                )

        # Remove duplicates and sort by relevance
        seen_titles = set()
        unique_courses = []

        for course in courses:
            if course["title"] not in seen_titles:
                unique_courses.append(course)
                seen_titles.add(course["title"])

        # Sort by relevance score
        unique_courses = sorted(
            unique_courses, key=lambda x: x["relevance_score"], reverse=True
        )

        return unique_courses[:10]  # Return top 10 courses

    def _extract_platform(self, title: str, description: str) -> str:
        """Extract platform information from title and description."""
        text = (title + " " + description).lower()

        # Platform indicators with more comprehensive matching
        platform_indicators = {
            "coursera": "Coursera",
            "udemy": "Udemy",
            "edx": "edX",
            "pluralsight": "Pluralsight",
            "linkedin learning": "LinkedIn Learning",
            "linkedin": "LinkedIn Learning",
            "youtube": "YouTube",
            "freecodecamp": "freeCodeCamp",
            "free code camp": "freeCodeCamp",
            "khan academy": "Khan Academy",
            "mit": "MIT",
            "stanford": "Stanford",
            "harvard": "Harvard",
            "google": "Google",
            "microsoft": "Microsoft",
            "aws": "AWS",
            "mozilla": "Mozilla",
            "codecademy": "Codecademy",
            "skillshare": "Skillshare",
            "udacity": "Udacity",
            "treehouse": "Treehouse",
            "lynda": "Lynda",
            "masterclass": "MasterClass",
            "domestika": "Domestika",
            "creative live": "CreativeLive",
            "future learn": "FutureLearn",
            "alison": "Alison",
            "openlearn": "OpenLearn",
            "mit opencourseware": "MIT OpenCourseWare",
            "stanford online": "Stanford Online",
            "harvard online": "Harvard Online",
            "yale online": "Yale Online",
            "princeton online": "Princeton Online",
        }

        # Check for platform indicators
        for indicator, platform_name in platform_indicators.items():
            if indicator in text:
                return platform_name

        # Check for URL patterns
        url_patterns = {
            "coursera.org": "Coursera",
            "udemy.com": "Udemy",
            "edx.org": "edX",
            "pluralsight.com": "Pluralsight",
            "linkedin.com/learning": "LinkedIn Learning",
            "youtube.com": "YouTube",
            "freecodecamp.org": "freeCodeCamp",
            "khanacademy.org": "Khan Academy",
            "codecademy.com": "Codecademy",
            "skillshare.com": "Skillshare",
            "udacity.com": "Udacity",
            "teamtreehouse.com": "Treehouse",
            "lynda.com": "Lynda",
            "masterclass.com": "MasterClass",
            "domestika.org": "Domestika",
            "creativelive.com": "CreativeLive",
            "futurelearn.com": "FutureLearn",
            "alison.com": "Alison",
            "open.edu": "OpenLearn",
        }

        for url_pattern, platform_name in url_patterns.items():
            if url_pattern in text:
                return platform_name

        return "Online Platform"

    def _calculate_relevance_score(self, title: str, description: str) -> int:
        """Calculate relevance score for course recommendations."""
        score = 0
        text = (title + " " + description).lower()

        # High-value keywords
        high_value = [
            "advanced",
            "expert",
            "professional",
            "certification",
            "bootcamp",
            "comprehensive",
            "complete",
        ]
        medium_value = [
            "intermediate",
            "practical",
            "hands-on",
            "project-based",
            "real-world",
        ]
        low_value = ["beginner", "introduction", "basics", "fundamentals"]

        score += sum(3 for keyword in high_value if keyword in text)
        score += sum(2 for keyword in medium_value if keyword in text)
        score += sum(1 for keyword in low_value if keyword in text)

        # Platform preference
        preferred_platforms = [
            "coursera",
            "udemy",
            "edx",
            "pluralsight",
            "linkedin learning",
        ]
        score += sum(2 for platform in preferred_platforms if platform in text)

        return score

    async def search_courses_with_context(
        self,
        skills_data: dict[str, Any] | None = None,
        experience_data: list[dict[str, Any]] | None = None,
        _user_id: str | None = None,
    ) -> dict[str, Any]:
        """Search for course recommendations using Tavily and agent context data."""
        try:
            # Use provided context or default to general search queries
            if skills_data and experience_data:
                # Extract skills and determine role from agent context
                skills = self._extract_skills_from_context(skills_data)
                role = self._determine_role_focus_from_context(
                    skills_data, experience_data
                )
            else:
                # Default to general search queries when no context provided
                skills = []
                role = "general"

            # Generate search queries
            queries = self._generate_search_queries(skills, role)

            # Search for courses using Tavily
            all_courses = []
            successful_searches = 0

            for query in queries:
                try:
                    search_results = self.search_tool.search(
                        query=query, max_results=10
                    )
                    courses = self._parse_search_results(search_results)
                    if courses:  # Only count if we got results
                        all_courses.extend(courses)
                        successful_searches += 1
                except Exception:
                    # Continue with other queries if one fails
                    continue

            # Remove duplicates and sort by relevance
            seen_titles = set()
            unique_courses = []
            for course in all_courses:
                if course["title"] not in seen_titles:
                    unique_courses.append(course)
                    seen_titles.add(course["title"])

            # Sort by relevance score
            unique_courses = sorted(
                unique_courses, key=lambda x: x["relevance_score"], reverse=True
            )

            return {
                "user_profile": {
                    "primary_role": role,
                    "key_skills": skills[:5],
                    "total_skills": len(skills),
                },
                "recommendations": unique_courses[:8],  # Top 8 recommendations
                "search_queries_used": queries[:5],  # Show which queries were used
                "total_courses_found": len(unique_courses),
                "search_success_rate": f"{successful_searches}/{len(queries)}",
            }
        except Exception as e:
            # Return empty results if search fails - rely solely on Tavily
            return {
                "user_profile": {
                    "primary_role": "general",
                    "key_skills": [],
                    "total_skills": 0,
                },
                "recommendations": [],
                "search_queries_used": [],
                "total_courses_found": 0,
                "search_success_rate": "0/0",
                "error": f"Course search failed: {str(e)}",
            }


# Global instance
course_service = CourseRecommendationService()


async def recommend_courses_tool(user_id: str | None) -> dict[str, Any]:
    """Tool to recommend courses based on user profile - DEPRECATED.

    This tool is deprecated in favor of using the agent's context-aware approach.
    Use recommend_courses_with_context_tool instead.
    """
    return await course_service.search_courses_with_context(user_id=user_id)


async def recommend_courses_with_context_tool(
    skills_data: dict[str, Any] | None = None,
    experience_data: list[dict[str, Any]] | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Tool to recommend courses using agent context data.

    This is the preferred method that leverages data from other agent tools.
    """
    return await course_service.search_courses_with_context(
        skills_data=skills_data,
        experience_data=experience_data,
        user_id=user_id,
    )

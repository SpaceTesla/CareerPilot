"""Course recommendation tools using DuckDuckGo search and agent context."""

from __future__ import annotations

from typing import Any

from langchain_community.tools import DuckDuckGoSearchRun


class CourseRecommendationService:
    """Service for recommending courses based on user profile context from agent tools."""

    def __init__(self) -> None:
        self.search_tool = DuckDuckGoSearchRun()

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

    def _parse_search_results(self, search_results: str) -> list[dict[str, Any]]:
        """Parse DuckDuckGo search results into structured course recommendations."""
        courses = []

        # DuckDuckGo returns results as a single string, so we need to parse it differently
        # Look for course-related patterns in the search results

        # Split by common separators to find individual courses
        # Look for patterns like "course", "tutorial", "learn", etc.
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

        # Split the text into sentences and look for course-related content
        sentences = search_results.split(". ")

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if this sentence contains course-related content
            if any(indicator in sentence.lower() for indicator in course_indicators):
                # Extract platform from sentence
                platform = self._extract_platform(sentence, "")

                # Only add if we found a valid platform or it looks like a course
                if platform != "Online Platform" or any(
                    indicator in sentence.lower() for indicator in course_indicators
                ):
                    # Clean up the title
                    title = sentence[:100] + "..." if len(sentence) > 100 else sentence

                    courses.append(
                        {
                            "title": title,
                            "description": sentence[:200] + "..."
                            if len(sentence) > 200
                            else sentence,
                            "platform": platform,
                            "relevance_score": self._calculate_relevance_score(
                                sentence, sentence
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

    def _generate_fallback_courses(
        self, role: str, skills: list[str]
    ) -> list[dict[str, Any]]:
        """Generate fallback course recommendations when search fails."""
        fallback_courses = {
            "backend": [
                {
                    "title": "Complete Python Developer Course",
                    "description": "Master Python programming from beginner to advanced with hands-on projects and real-world applications.",
                    "platform": "Udemy",
                    "relevance_score": 9,
                },
                {
                    "title": "AWS Certified Solutions Architect",
                    "description": "Learn cloud architecture and AWS services to design scalable and reliable applications.",
                    "platform": "Coursera",
                    "relevance_score": 8,
                },
                {
                    "title": "Docker and Kubernetes: The Complete Guide",
                    "description": "Learn containerization and orchestration with Docker and Kubernetes for modern applications.",
                    "platform": "Udemy",
                    "relevance_score": 8,
                },
                {
                    "title": "RESTful API Design and Development",
                    "description": "Build robust and scalable REST APIs using best practices and modern frameworks.",
                    "platform": "edX",
                    "relevance_score": 7,
                },
            ],
            "frontend": [
                {
                    "title": "The Complete React Developer Course",
                    "description": "Master React.js from fundamentals to advanced concepts with modern development practices.",
                    "platform": "Udemy",
                    "relevance_score": 9,
                },
                {
                    "title": "JavaScript: The Complete Guide",
                    "description": "Learn modern JavaScript from ES6+ to advanced concepts and frameworks.",
                    "platform": "Coursera",
                    "relevance_score": 8,
                },
                {
                    "title": "Advanced CSS and Sass",
                    "description": "Master advanced CSS techniques, animations, and Sass for modern web development.",
                    "platform": "Udemy",
                    "relevance_score": 7,
                },
                {
                    "title": "TypeScript: The Complete Developer's Guide",
                    "description": "Learn TypeScript for large-scale JavaScript applications and better code quality.",
                    "platform": "Udemy",
                    "relevance_score": 8,
                },
            ],
            "fullstack": [
                {
                    "title": "The Complete Web Developer Bootcamp",
                    "description": "Learn full-stack web development with HTML, CSS, JavaScript, Node.js, and databases.",
                    "platform": "Udemy",
                    "relevance_score": 9,
                },
                {
                    "title": "MERN Stack Front To Back",
                    "description": "Build full-stack applications with MongoDB, Express, React, and Node.js.",
                    "platform": "Udemy",
                    "relevance_score": 8,
                },
                {
                    "title": "The Complete Node.js Developer Course",
                    "description": "Master Node.js for backend development with Express, MongoDB, and authentication.",
                    "platform": "Udemy",
                    "relevance_score": 8,
                },
            ],
            "devops": [
                {
                    "title": "Docker Mastery: The Complete Toolset",
                    "description": "Learn Docker from basics to advanced containerization and orchestration.",
                    "platform": "Udemy",
                    "relevance_score": 9,
                },
                {
                    "title": "Kubernetes for the Absolute Beginners",
                    "description": "Learn Kubernetes container orchestration from scratch with hands-on labs.",
                    "platform": "Udemy",
                    "relevance_score": 8,
                },
                {
                    "title": "AWS Certified Cloud Practitioner",
                    "description": "Learn AWS cloud fundamentals and prepare for the AWS certification exam.",
                    "platform": "Coursera",
                    "relevance_score": 8,
                },
            ],
            "data": [
                {
                    "title": "Python for Data Science and Machine Learning",
                    "description": "Master Python for data analysis, visualization, and machine learning with pandas, numpy, and scikit-learn.",
                    "platform": "Udemy",
                    "relevance_score": 9,
                },
                {
                    "title": "Machine Learning Course by Stanford",
                    "description": "Learn machine learning algorithms and applications from Stanford University.",
                    "platform": "Coursera",
                    "relevance_score": 9,
                },
                {
                    "title": "SQL for Data Analysis",
                    "description": "Master SQL for data analysis and database querying with real-world projects.",
                    "platform": "Udemy",
                    "relevance_score": 8,
                },
            ],
        }

        # Get role-specific courses
        courses = fallback_courses.get(role, fallback_courses["backend"])

        # Add skill-specific courses if we have skills
        if skills:
            skill_courses = []
            for skill in skills[:3]:  # Top 3 skills
                skill_lower = skill.lower()
                if skill_lower in [
                    "python",
                    "javascript",
                    "react",
                    "node",
                    "aws",
                    "docker",
                    "typescript",
                    "go",
                    "fastapi",
                    "flask",
                    "django",
                    "express",
                    "fastify",
                    "gin",
                    "fiber",
                    "next.js",
                    "tailwind",
                    "bootstrap",
                    "redux",
                    "zustand",
                ]:
                    skill_courses.append(
                        {
                            "title": f"Complete {skill.title()} Course - From Beginner to Advanced",
                            "description": f"Master {skill} programming with comprehensive tutorials, hands-on projects, and real-world applications. Perfect for developers looking to advance their skills.",
                            "platform": "Udemy",
                            "relevance_score": 8,
                        }
                    )
            courses.extend(skill_courses)

        return courses[:6]  # Return top 6 fallback courses

    async def search_courses_with_context(
        self,
        skills_data: dict[str, Any] | None = None,
        experience_data: list[dict[str, Any]] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Search for course recommendations using agent context data."""
        try:
            # Use provided context or fallback to general recommendations
            if skills_data and experience_data:
                # Extract skills and determine role from agent context
                skills = self._extract_skills_from_context(skills_data)
                role = self._determine_role_focus_from_context(
                    skills_data, experience_data
                )
            else:
                # Fallback to general recommendations
                skills = []
                role = "general"

            # Generate search queries
            queries = self._generate_search_queries(skills, role)

            # Search for courses
            all_courses = []
            successful_searches = 0

            for query in queries:
                try:
                    search_results = self.search_tool.invoke(query)
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

            # Always provide fallback recommendations as the search parsing is not reliable
            try:
                fallback_courses = self._generate_fallback_courses(role, skills)
                # Merge with search results, prioritizing search results
                for course in fallback_courses:
                    if course["title"] not in seen_titles:
                        unique_courses.append(course)
                        seen_titles.add(course["title"])

                # Re-sort after adding fallback courses
                unique_courses = sorted(
                    unique_courses, key=lambda x: x["relevance_score"], reverse=True
                )
            except Exception:
                # If fallback fails, at least return some basic courses
                unique_courses = [
                    {
                        "title": "Complete Programming Course",
                        "description": "Learn programming fundamentals and best practices",
                        "platform": "Udemy",
                        "relevance_score": 5,
                    }
                ]

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
            # Return basic fallback if everything fails
            return {
                "user_profile": {
                    "primary_role": "general",
                    "key_skills": [],
                    "total_skills": 0,
                },
                "recommendations": [
                    {
                        "title": "Complete Programming Course",
                        "description": "Learn programming fundamentals and best practices",
                        "platform": "Udemy",
                        "relevance_score": 5,
                    }
                ],
                "search_queries_used": ["general programming courses"],
                "total_courses_found": 1,
                "search_success_rate": "0/1",
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

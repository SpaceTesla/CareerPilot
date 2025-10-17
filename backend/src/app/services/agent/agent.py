from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.services.agent.llm.prompt_templates import AgentPrompts
from app.services.agent.tools.analysis_tools import (
    analyze_resume_strengths_tool,
    get_resume_metrics_tool,
    suggest_improvements_tool,
)
from app.services.agent.tools.course_recommendation_tools import (
    recommend_courses_tool,
    recommend_courses_with_context_tool,
)
from app.services.agent.tools.resume_tools import (
    get_achievements_tool,
    get_co_curricular_tool,
    get_contact_info_tool,
    get_education_tool,
    get_experience_tool,
    get_projects_tool,
    get_skills_tool,
    get_summary_tool,
)


class AgentService:
    """Enhanced LangChain agent with comprehensive resume analysis capabilities."""

    def __init__(self) -> None:
        self.model = ChatGoogleGenerativeAI(
            model=settings.model_name,
            temperature=settings.temperature,
        )
        self.prompt = AgentPrompts.get_main_prompt()
        self.chain = self.prompt | self.model

        # Comprehensive tool registry
        self.tools: dict[str, Callable[..., Any]] = {
            # Resume data tools
            "get_contact_info": get_contact_info_tool,
            "get_skills": get_skills_tool,
            "get_experience": get_experience_tool,
            "get_education": get_education_tool,
            "get_projects": get_projects_tool,
            "get_achievements": get_achievements_tool,
            "get_co_curricular": get_co_curricular_tool,
            "get_summary": get_summary_tool,
            # Analysis tools
            "analyze_resume_strengths": analyze_resume_strengths_tool,
            "suggest_improvements": suggest_improvements_tool,
            "get_resume_metrics": get_resume_metrics_tool,
            # Course recommendation tools
            "recommend_courses": recommend_courses_tool,
            "recommend_courses_with_context": recommend_courses_with_context_tool,
        }

        # Intent patterns for better routing
        self.intent_patterns = {
            "contact": [
                r"\b(email|phone|contact|address|location|where|reach)\b",
                r"\b(how to contact|contact info|contact details)\b",
            ],
            "skills": [
                r"\b(skills?|technologies?|programming|languages?|frameworks?|tools?)\b",
                r"\b(what can you do|technical skills|competencies)\b",
            ],
            "experience": [
                r"\b(experience|work|job|career|employment|position|role)\b",
                r"\b(where have you worked|work history|professional experience)\b",
            ],
            "education": [
                r"\b(education|degree|university|college|school|graduated|gpa)\b",
                r"\b(where did you study|educational background|academic)\b",
            ],
            "projects": [
                r"\b(projects?|portfolio|built|developed|created|github)\b",
                r"\b(what have you built|show me your work|side projects)\b",
            ],
            "achievements": [
                r"\b(achievements?|awards?|accomplishments?|recognition|honors?)\b",
                r"\b(what are you proud of|notable achievements)\b",
            ],
            "co_curricular": [
                r"\b(activities?|clubs?|societies?|volunteer|extracurricular|co.?curricular)\b",
                r"\b(involvement|leadership|organizations?)\b",
            ],
            "analysis": [
                r"\b(analyze|analysis|strengths?|weaknesses?|improve|feedback)\b",
                r"\b(how good|rate|score|evaluate|review)\b",
                r"\b(suggestions?|recommendations?|tips?|advice)\b",
            ],
            "courses": [
                r"\b(courses?|learn|study|training|education|tutorial|bootcamp)\b",
                r"\b(what should I learn|recommend courses|suggest courses)\b",
                r"\b(skills to improve|upskill|reskill|professional development)\b",
                r"\b(certification|certificate|course recommendations)\b",
            ],
            "summary": [
                r"\b(summary|about|overview|introduction|profile)\b",
                r"\b(who are you|tell me about yourself|background)\b",
            ],
        }

    def _detect_intent(self, message: str) -> list[str]:
        """Detect user intent based on message content."""
        message_lower = message.lower()
        detected_intents = []

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    detected_intents.append(intent)
                    break

        return detected_intents

    async def _execute_tools(
        self, intents: list[str], user_id: str | None
    ) -> dict[str, Any]:
        """Execute tools based on detected intents."""
        results = {}
        actions_taken = []

        # Map intents to tools
        intent_to_tool = {
            "contact": "get_contact_info",
            "skills": "get_skills",
            "experience": "get_experience",
            "education": "get_education",
            "projects": "get_projects",
            "achievements": "get_achievements",
            "co_curricular": "get_co_curricular",
            "summary": "get_summary",
            "analysis": "analyze_resume_strengths",
            "courses": "recommend_courses",
        }

        # Execute tools for detected intents
        for intent in intents:
            if intent in intent_to_tool:
                tool_name = intent_to_tool[intent]
                if tool_name in self.tools:
                    try:
                        tool_result = await self.tools[tool_name](user_id=user_id)
                        results[tool_name] = tool_result
                        actions_taken.append(tool_name)
                        print(
                            f"DEBUG: Tool {tool_name} executed successfully, result keys: {tool_result.keys() if isinstance(tool_result, dict) else 'Not a dict'}"
                        )
                    except Exception as e:
                        results[f"{tool_name}_error"] = str(e)
                        print(f"DEBUG: Tool {tool_name} failed with error: {e}")

        # If analysis intent detected, also get suggestions
        if "analysis" in intents and "suggest_improvements" in self.tools:
            try:
                suggestions = await self.tools["suggest_improvements"](user_id=user_id)
                results["suggestions"] = suggestions
                actions_taken.append("suggest_improvements")
            except Exception as e:
                results["suggestions_error"] = str(e)

        # If courses intent detected, use context-aware approach
        if "courses" in intents and "recommend_courses_with_context" in self.tools:
            try:
                # Get skills and experience data for context
                skills_data = results.get("get_skills", {})
                experience_data = results.get("get_experience", [])

                # Use context-aware course recommendation
                courses = await self.tools["recommend_courses_with_context"](
                    skills_data=(skills_data if "error" not in skills_data else None),
                    experience_data=(
                        experience_data if "error" not in experience_data else None
                    ),
                    user_id=user_id,
                )
                results["recommend_courses"] = courses
                actions_taken.append("recommend_courses_with_context")
            except Exception:
                # Fallback to basic course recommendation
                try:
                    courses = await self.tools["recommend_courses"](user_id=user_id)
                    results["recommend_courses"] = courses
                    actions_taken.append("recommend_courses")
                except Exception as fallback_error:
                    results["recommend_courses_error"] = str(fallback_error)

        return {"results": results, "actions_taken": actions_taken}

    def _format_response(
        self, tool_results: dict[str, Any], actions_taken: list[str]
    ) -> str:
        """Format a comprehensive response based on tool results."""
        if not tool_results or not actions_taken:
            return (
                "I couldn't find specific information to answer your question. "
                "Please try asking about your contact info, skills, experience, "
                "education, projects, achievements, or ask for resume analysis."
            )

        response_parts = []

        # Handle contact info
        if "get_contact_info" in tool_results:
            contact = tool_results["get_contact_info"]
            if "error" not in contact:
                response_parts.append("**Contact Information:**\n")
                if contact.get("name"):
                    response_parts.append(f"Name: {contact['name']}")
                if contact.get("email"):
                    response_parts.append(f"Email: {contact['email']}")
                if contact.get("phone"):
                    response_parts.append(f"Phone: {contact['phone']}")
                if contact.get("location"):
                    response_parts.append(f"Location: {contact['location']}")
                response_parts.append("")

        # Handle skills
        if "get_skills" in tool_results:
            skills = tool_results["get_skills"]
            if "error" not in skills:
                response_parts.append("**Technical Skills:**\n")
                if skills.get("languages"):
                    langs = ", ".join(skills["languages"])
                    response_parts.append(f"Languages: {langs}")
                if skills.get("frameworks"):
                    frameworks = ", ".join(skills["frameworks"])
                    response_parts.append(f"Frameworks: {frameworks}")
                if skills.get("tools"):
                    tools = ", ".join(skills["tools"])
                    response_parts.append(f"Tools: {tools}")
                total = skills.get("total_skills", 0)
                response_parts.append(f"Total Skills: {total}")
                response_parts.append("")

        # Handle experience
        if "get_experience" in tool_results:
            experience = tool_results["get_experience"]
            if "error" not in experience and experience:
                response_parts.append("**Work Experience:**\n")
                for i, exp in enumerate(experience[:3], 1):  # Show top 3
                    if isinstance(exp, dict):
                        role = exp.get("role", "Unknown Role")
                        company = exp.get("company", "Unknown Company")
                        period = exp.get("period", "")
                        response_parts.append(f"{i}. **{role}** at {company}")
                        if period:
                            response_parts.append(f"   Period: {period}")
                        if exp.get("details"):
                            response_parts.append(
                                "   Key responsibilities and achievements:"
                            )
                            for detail in exp["details"][:2]:  # Show top 2 details
                                response_parts.append(f"   • {detail}")
                        response_parts.append("")

        # Handle projects
        if "get_projects" in tool_results:
            projects = tool_results["get_projects"]
            if "error" not in projects and projects:
                response_parts.append("**Projects:**\n")
                for i, proj in enumerate(projects[:3], 1):  # Show top 3
                    if isinstance(proj, dict):
                        name = proj.get("name", "Unknown Project")
                        tech_stack = proj.get("tech_stack", "")
                        response_parts.append(f"{i}. **{name}**")
                        if tech_stack:
                            response_parts.append(f"   Tech Stack: {tech_stack}")
                        if proj.get("details"):
                            first_detail = proj["details"][0] if proj["details"] else ""
                            response_parts.append(f"   Description: {first_detail}")
                        response_parts.append("")

        # Handle analysis
        if "analyze_resume_strengths" in tool_results:
            analysis = tool_results["analyze_resume_strengths"]
            if "error" not in analysis:
                response_parts.append("**Resume Analysis:**\n")
                overall_score = analysis.get("overall_score", 0)
                response_parts.append(f"Overall Score: {overall_score:.1f}/1.0")

                if analysis.get("strengths"):
                    response_parts.append("Strengths:")
                    for strength in analysis["strengths"]:
                        response_parts.append(f"• {strength}")

                if analysis.get("areas_for_improvement"):
                    response_parts.append("Areas for Improvement:")
                    for area in analysis["areas_for_improvement"]:
                        response_parts.append(f"• {area}")
                response_parts.append("")

        # Handle suggestions
        if "suggestions" in tool_results:
            suggestions = tool_results["suggestions"]
            if "error" not in suggestions:
                response_parts.append("**Recommendations:**\n")
                if suggestions.get("priority_improvements"):
                    response_parts.append("Priority Improvements:")
                    for improvement in suggestions["priority_improvements"][:3]:
                        response_parts.append(f"• {improvement['suggestion']}")
                    response_parts.append("")

        # Handle course recommendations
        if "recommend_courses" in tool_results:
            courses_data = tool_results["recommend_courses"]
            print(
                f"DEBUG: Course data keys: "
                f"{courses_data.keys() if isinstance(courses_data, dict) else 'Not a dict'}"
            )
            print(
                f"DEBUG: Recommendations count: "
                f"{len(courses_data.get('recommendations', []))}"
            )

            if "error" not in courses_data:
                response_parts.append("**Course Recommendations:**\n")

                # Show user profile analysis
                if "user_profile" in courses_data:
                    profile = courses_data["user_profile"]
                    role = profile["primary_role"]
                    skills_count = profile["total_skills"]
                    response_parts.append(
                        f"Based on your profile as a **{role}** developer "
                        f"with {skills_count} skills:"
                    )
                    key_skills = ", ".join(profile["key_skills"])
                    response_parts.append(f"Key skills: {key_skills}")
                    response_parts.append("")

                # Show course recommendations
                if "recommendations" in courses_data:
                    recommendations = courses_data["recommendations"]
                    response_parts.append("**Recommended Courses:**\n")
                    for i, course in enumerate(recommendations[:5], 1):  # Top 5
                        response_parts.append(f"{i}. **{course['title']}**")
                        response_parts.append(f"   Platform: {course['platform']}")
                        response_parts.append(
                            f"   Description: {course['description']}"
                        )
                        response_parts.append("")

                # Show search queries used
                if "search_queries_used" in courses_data:
                    queries = courses_data["search_queries_used"]
                    response_parts.append("**Search Strategy:**")
                    response_parts.append(
                        "I analyzed your resume and searched for courses using "
                        "these criteria:"
                    )
                    for query in queries:
                        response_parts.append(f"• {query}")
                    response_parts.append("")

        if response_parts:
            return "\n".join(response_parts)
        return (
            "I found some information but couldn't format it properly. "
            "Please try a more specific question."
        )

    async def chat(self, user_id: str | None, message: str) -> dict[str, Any]:
        """Enhanced chat method with intelligent tool routing and comprehensive responses."""
        try:
            # Detect user intent
            intents = self._detect_intent(message)

            # Execute relevant tools
            tool_results = await self._execute_tools(intents, user_id)

            # Format response
            if tool_results["actions_taken"]:
                formatted_message = self._format_response(
                    tool_results["results"], tool_results["actions_taken"]
                )
                return {
                    "message": formatted_message,
                    "data": tool_results["results"],
                    "actions_taken": tool_results["actions_taken"],
                    "confidence": 0.9,
                }
            else:
                # Fallback to LLM for general questions
                out = await self.chain.ainvoke(
                    {"question": message}, config=RunnableConfig()
                )
                return {
                    "message": str(out.content),
                    "data": None,
                    "actions_taken": [],
                    "confidence": 0.7,
                }

        except Exception as e:
            import traceback

            return {
                "message": f"I encountered an error while processing your request: {str(e)}",
                "data": None,
                "actions_taken": [],
                "confidence": 0.0,
                "error_details": traceback.format_exc(),
            }

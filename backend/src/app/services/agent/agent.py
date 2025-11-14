from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.services.agent.llm.prompt_templates import AgentPrompts
from app.services.agent.memory import ConversationMemory
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


@tool("get_contact_info", return_direct=False)
async def agent_get_contact_info(user_id: str) -> dict[str, Any]:
    """Retrieve the latest contact information (name, email, phone, location) for the user."""
    return await get_contact_info_tool(user_id=user_id)


@tool("get_skills", return_direct=False)
async def agent_get_skills(user_id: str) -> dict[str, Any]:
    """Fetch the structured skills breakdown (languages, frameworks, tools) for the user."""
    return await get_skills_tool(user_id=user_id)


@tool("get_experience", return_direct=False)
async def agent_get_experience(user_id: str) -> List[dict[str, Any]]:
    """Return the work experience entries for the user with roles, companies, and bullet points."""
    return await get_experience_tool(user_id=user_id)


@tool("get_education", return_direct=False)
async def agent_get_education(user_id: str) -> List[dict[str, Any]]:
    """Return the education history (degrees, schools, GPA) for the user."""
    return await get_education_tool(user_id=user_id)


@tool("get_projects", return_direct=False)
async def agent_get_projects(user_id: str) -> List[dict[str, Any]]:
    """Return notable project entries including tech stack and impact statements."""
    return await get_projects_tool(user_id=user_id)


@tool("get_achievements", return_direct=False)
async def agent_get_achievements(user_id: str) -> List[dict[str, Any]]:
    """Fetch awards or achievements listed in the resume."""
    return await get_achievements_tool(user_id=user_id)


@tool("get_co_curricular", return_direct=False)
async def agent_get_co_curricular(user_id: str) -> List[dict[str, Any]]:
    """Fetch co-curricular or extracurricular activities for the user."""
    return await get_co_curricular_tool(user_id=user_id)


@tool("get_summary", return_direct=False)
async def agent_get_summary(user_id: str) -> dict[str, Any]:
    """Get the professional summary and headline information."""
    return await get_summary_tool(user_id=user_id)


@tool("analyze_resume_strengths", return_direct=False)
async def agent_analyze_resume_strengths(user_id: str) -> dict[str, Any]:
    """Provide a quantitative assessment of the resume's strengths and gaps."""
    return await analyze_resume_strengths_tool(user_id=user_id)


@tool("suggest_improvements", return_direct=False)
async def agent_suggest_improvements(user_id: str) -> dict[str, Any]:
    """Generate actionable suggestions to improve the resume."""
    return await suggest_improvements_tool(user_id=user_id)


@tool("get_resume_metrics", return_direct=False)
async def agent_get_resume_metrics(user_id: str) -> dict[str, Any]:
    """Return quantitative metrics like word counts, completeness, and diversity."""
    return await get_resume_metrics_tool(user_id=user_id)


@tool("recommend_courses", return_direct=False)
async def agent_recommend_courses(user_id: str) -> dict[str, Any]:
    """Provide general course recommendations for the user."""
    return await recommend_courses_tool(user_id=user_id)


@tool("recommend_courses_with_context", return_direct=False)
async def agent_recommend_courses_with_context(user_id: str) -> dict[str, Any]:
    """Provide context-aware course recommendations that leverage resume data."""
    return await recommend_courses_with_context_tool(user_id=user_id)


class AgentService:
    """LangChain-powered agent that relies on tool-calling instead of manual routing."""

    MAX_ITERATIONS = 4

    def __init__(self) -> None:
        self.model = ChatGoogleGenerativeAI(
            model=settings.model_name,
            temperature=settings.temperature,
        )
        self.memory = ConversationMemory(max_messages=20)
        self.tools = self._build_tools()
        self.tool_lookup = {tool.name: tool for tool in self.tools}
        self.tool_enabled_llm = self.model.bind_tools(self.tools)

    def _build_tools(self) -> list:
        """Register all agent tools."""
        return [
            agent_get_contact_info,
            agent_get_skills,
            agent_get_experience,
            agent_get_education,
            agent_get_projects,
            agent_get_achievements,
            agent_get_co_curricular,
            agent_get_summary,
            agent_analyze_resume_strengths,
            agent_suggest_improvements,
            agent_get_resume_metrics,
            agent_recommend_courses,
            agent_recommend_courses_with_context,
        ]

    def _serialize_tool_result(self, result: Any) -> str:
        """Ensure tool outputs are serialized for ToolMessages."""
        try:
            return json.dumps(result, default=str)
        except TypeError:
            return json.dumps({"result": str(result)})

    async def _invoke_tool(
        self, tool_name: str | None, args: Dict[str, Any]
    ) -> Any:
        if not tool_name:
            return {"error": "Tool name missing in model response."}

        tool = self.tool_lookup.get(tool_name)
        if not tool:
            return {"error": f"Tool '{tool_name}' is not registered."}

        try:
            return await tool.ainvoke(args)
        except Exception as exc:  # pragma: no cover - defensive
            return {"error": f"{tool_name} failed: {str(exc)}"}

    def _finalize_text(self, ai_message: AIMessage) -> str:
        """Normalize AI content into plain text."""
        if isinstance(ai_message.content, str):
            return ai_message.content

        if isinstance(ai_message.content, list):
            parts = []
            for chunk in ai_message.content:
                if isinstance(chunk, dict) and "text" in chunk:
                    parts.append(chunk["text"])
            if parts:
                return "\n".join(parts)

        return "I wasn't able to generate a detailed response this time."

    async def chat(self, user_id: str | None, message: str) -> dict[str, Any]:
        """Process a chat request using tool-calling with lightweight memory."""
        try:
            history = self.memory.get(user_id)
            messages: list = [SystemMessage(content=AgentPrompts.SYSTEM_PROMPT), *history]

            user_message = HumanMessage(content=message)
            messages.append(user_message)
            self.memory.append(user_id, user_message)

            actions_taken: list[str] = []
            collected_data: Dict[str, list[Any]] = {}

            for iteration in range(self.MAX_ITERATIONS):
                ai_response: AIMessage = await self.tool_enabled_llm.ainvoke(
                    messages, config=RunnableConfig()
                )
                messages.append(ai_response)
                self.memory.append(user_id, ai_response)

                tool_calls = getattr(ai_response, "tool_calls", None) or []
                if not tool_calls:
                    final_message = self._finalize_text(ai_response)
                    return {
                        "message": final_message,
                        "data": collected_data or None,
                        "actions_taken": actions_taken,
                        "confidence": 0.9 if actions_taken else 0.75,
                    }

                for call in tool_calls:
                    tool_name = call.get("name")
                    args = call.get("args") or {}
                    if user_id:
                        args["user_id"] = user_id

                    result = await self._invoke_tool(tool_name, args)
                    if tool_name:
                        collected_data.setdefault(tool_name, []).append(result)
                        if tool_name not in actions_taken:
                            actions_taken.append(tool_name)

                    tool_message = ToolMessage(
                        content=self._serialize_tool_result(result),
                        tool_call_id=call.get("id") or tool_name or f"tool_{iteration}",
                    )
                    messages.append(tool_message)
                    self.memory.append(user_id, tool_message)

            return {
                "message": (
                    "I reached the maximum number of tool calls and could not finish "
                    "your request. Please try again with more specific instructions."
                ),
                "data": collected_data or None,
                "actions_taken": actions_taken,
                "confidence": 0.4,
            }
        except Exception as exc:  # pragma: no cover - defensive
            import traceback

            return {
                "message": f"I encountered an error while processing your request: {str(exc)}",
                "data": None,
                "actions_taken": [],
                "confidence": 0.0,
                "error_details": traceback.format_exc(),
            }

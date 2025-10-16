from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.services.agent.tools import get_contact_info_tool, get_projects_tool


class AgentService:
    """LangChain ReAct-like agent wrapper.

    Minimal initial version that routes questions to tools or model.
    """

    def __init__(self) -> None:
        self.model = ChatGoogleGenerativeAI(
            model=settings.model_name,
            temperature=settings.temperature,
        )
        self.system = "You are a resume assistant. Use tools where possible;\
             answer with only user's data."
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system),
                ("user", "{question}"),
            ]
        )
        self.chain = self.prompt | self.model

        # Tool registry
        self.tools: dict[str, Callable[..., Any]] = {
            "get_contact_info": get_contact_info_tool,
            "get_projects": get_projects_tool,
        }

    async def chat(self, user_id: str | None, message: str) -> dict[str, Any]:
        q = message.strip().lower()
        # Simple intent routing (expand later)
        if "email" in q or "phone" in q or "contact" in q:
            data = await get_contact_info_tool(user_id=user_id)
            return {
                "message": str(data),
                "data": data,
                "actions_taken": ["get_contact_info"],
            }
        if "project" in q:
            data = await get_projects_tool(user_id=user_id)
            return {
                "message": str(data),
                "data": data,
                "actions_taken": ["get_projects"],
            }

        # Fallback to model
        out = await self.chain.ainvoke({"question": message}, config=RunnableConfig())
        return {"message": str(out.content), "data": None, "actions_taken": []}

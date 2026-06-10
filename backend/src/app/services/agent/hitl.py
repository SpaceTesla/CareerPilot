from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models import AgentApprovalRequest, AgentApprovalAuditLog, AgentSession
from app.services.agent.models import ApprovalSummary, ApprovalRequestPayload

logger = get_logger(__name__)


class HumanInTheLoopService:
    """
    Manages human approval requests, editing drafts before submission,
    and recording audit logs of modifications.
    """

    @staticmethod
    async def create_approval_request(
        db: AsyncSession, user_id: UUID, thread_id: str, action_type: str, payload: dict
    ) -> UUID:
        req_id = uuid4()
        try:
            # 1. Register the approval request
            request = AgentApprovalRequest(
                id=str(req_id),
                user_id=str(user_id),
                thread_id=thread_id,
                action_type=action_type,
                payload=payload,
                status="pending",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(request)

            # 2. Pause the agent session status
            session_stmt = update(AgentSession).where(
                AgentSession.thread_id == thread_id
            ).values(
                current_status="paused_for_approval",
                updated_at=datetime.utcnow()
            )
            await db.execute(session_stmt)
            await db.commit()

            logger.info(f"Created pending approval request {req_id} for thread {thread_id}")
            return req_id
        except Exception as e:
            logger.error(f"Failed to create approval request: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def process_approval_action(
        db: AsyncSession, approval_id: UUID, actor_id: UUID, action: str, edited_payload: Optional[dict] = None
    ) -> dict:
        """
        Process user decisions: 'approved', 'rejected', or 'modified'.
        Resumes the thread in LangGraph.
        """
        try:
            # 1. Fetch Request
            stmt = select(AgentApprovalRequest).where(AgentApprovalRequest.id == str(approval_id))
            res = await db.execute(stmt)
            request = res.scalar_one_or_none()
            if not request:
                raise ValueError("Approval request not found.")

            if request.status != "pending":
                raise ValueError("Approval request is already processed.")

            final_status = action
            changes_made = None

            # 2. Calculate Diffs if modified
            if action == "modified" or edited_payload:
                final_status = "edited"
                # Simple diff calculator between request.payload and edited_payload
                before_fields = request.payload
                after_fields = edited_payload or {}
                changes_made = {
                    "before": {k: v for k, v in before_fields.items() if after_fields.get(k) != v},
                    "after": {k: v for k, v in after_fields.items() if before_fields.get(k) != v}
                }
                request.payload = after_fields

            # Update status
            request.status = final_status
            request.updated_at = datetime.utcnow()

            # 3. Create Audit Log
            audit_log = AgentApprovalAuditLog(
                id=str(uuid4()),
                approval_request_id=str(approval_id),
                actor_id=str(actor_id),
                action_taken=action,
                changes_made=changes_made,
                timestamp=datetime.utcnow()
            )
            db.add(audit_log)

            # 4. Update Agent Session status to active
            session_stmt = update(AgentSession).where(
                AgentSession.thread_id == request.thread_id
            ).values(
                current_status="active",
                updated_at=datetime.utcnow()
            )
            await db.execute(session_stmt)
            await db.commit()

            # Trigger graph resume through GraphExecutionService (imported locally to avoid circular dependencies)
            from app.services.agent.graph import GraphExecutionService
            next_node = "end"
            if action in ["approved", "modified"]:
                # resume graph execution asynchronously
                await GraphExecutionService.resume_graph(db, request.thread_id, approval_status=True, edited_payload=request.payload)
                next_node = "execution_node"
            else:
                await GraphExecutionService.resume_graph(db, request.thread_id, approval_status=False)

            return {
                "approval_id": approval_id,
                "status": final_status,
                "workflow_status": "resumed",
                "next_node": next_node,
                "message": "Approval processed. LangGraph thread execution has resumed."
            }

        except Exception as e:
            logger.error(f"Failed to process approval action: {e}")
            await db.rollback()
            raise

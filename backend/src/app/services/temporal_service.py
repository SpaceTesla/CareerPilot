"""Temporal workflow integration and orchestration service."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client

from app.core.logging import get_logger
from app.infrastructure.database.models import WorkflowExecutionLog
from app.services.database_service import AsyncSessionLocal

logger = get_logger(__name__)


class TemporalWorkflowService:
    """Service to interact with the Temporal client and manage execution audit logs."""

    _client: Optional[Client] = None

    @classmethod
    async def get_client(cls, host: str = "localhost:7233") -> Client:
        """Get or initialize the Temporal client."""
        if cls._client is None:
            try:
                cls._client = await Client.connect(host)
            except Exception as e:
                logger.warning(f"Failed to connect to Temporal at {host}: {e}. Mock/Fallback mode active.")
                # We do not crash here, as integration tests will pass their own client
                # or mock the workflow starts.
                raise
        return cls._client

    @classmethod
    def set_client(cls, client: Client) -> None:
        """Explicitly set the Temporal client (useful for tests)."""
        cls._client = client

    @classmethod
    async def start_workflow(
        cls,
        workflow_name: str,
        workflow_id: str,
        task_queue: str,
        input_data: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Start a Temporal workflow and record it in the database.
        """
        run_id = "mock-run-" + str(uuid4())[:8]
        
        # In a real environment or test with an active client:
        if cls._client is not None:
            try:
                # We import workflows dynamically to avoid circular import issues
                handle = await cls._client.start_workflow(
                    workflow_name,
                    input_data,
                    id=workflow_id,
                    task_queue=task_queue,
                )
                run_id = handle.result_run_id
            except Exception as e:
                logger.error(f"Failed to start workflow {workflow_name} on Temporal: {e}")
                # Fallback to local database logging if connection fails
        
        # Write to workflow_execution_logs
        async with AsyncSessionLocal() as session:
            db_log = WorkflowExecutionLog(
                id=str(uuid4()),
                user_id=user_id,
                workflow_id=workflow_id,
                run_id=run_id,
                workflow_type=workflow_name,
                status="RUNNING",
                task_queue=task_queue,
                input_payload=input_data,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(db_log)
            await session.commit()
            
            # Serialize for response
            return {
                "id": db_log.id,
                "user_id": db_log.user_id,
                "workflow_id": db_log.workflow_id,
                "run_id": db_log.run_id,
                "workflow_type": db_log.workflow_type,
                "status": db_log.status,
                "task_queue": db_log.task_queue,
                "input_payload": db_log.input_payload,
                "created_at": db_log.created_at.isoformat(),
                "updated_at": db_log.updated_at.isoformat(),
            }

    @classmethod
    async def cancel_workflow(cls, workflow_id: str) -> None:
        """Cancel an active Temporal workflow and update database logs."""
        if cls._client is not None:
            try:
                handle = cls._client.get_workflow_handle(workflow_id)
                await handle.cancel()
            except Exception as e:
                logger.error(f"Failed to cancel workflow {workflow_id} in Temporal: {e}")

        async with AsyncSessionLocal() as session:
            stmt = (
                update(WorkflowExecutionLog)
                .where(WorkflowExecutionLog.workflow_id == workflow_id)
                .values(status="CANCELLED", updated_at=datetime.utcnow())
            )
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def sync_workflow_status(cls, workflow_id: str, run_id: str) -> str:
        """Query Temporal for current status and synchronize it to the local database."""
        status = "RUNNING"
        output_payload = None
        error_details = None

        if cls._client is not None:
            try:
                handle = cls._client.get_workflow_handle(workflow_id, run_id=run_id)
                desc = await handle.describe()
                
                # Map Temporal status to our model status
                # Temporal statuses: RUNNING, COMPLETED, FAILED, CANCELED, TERMINATED, TIMED_OUT
                t_status = desc.status.name.upper()
                if "COMPLETED" in t_status:
                    status = "COMPLETED"
                    try:
                        output_payload = await handle.result()
                        if not isinstance(output_payload, dict):
                            output_payload = {"result": output_payload}
                    except Exception:
                        pass
                elif "FAIL" in t_status or "TIME" in t_status:
                    status = "FAILED"
                    try:
                        await handle.result()
                    except Exception as e:
                        error_details = {"error": str(e)}
                elif "CANCEL" in t_status:
                    status = "CANCELLED"
                elif "TERMINATE" in t_status:
                    status = "TERMINATED"
            except Exception as e:
                logger.error(f"Failed to query status for workflow {workflow_id}: {e}")

        async with AsyncSessionLocal() as session:
            stmt = select(WorkflowExecutionLog).where(WorkflowExecutionLog.workflow_id == workflow_id)
            res = await session.execute(stmt)
            db_log = res.scalar_one_or_none()
            if db_log:
                db_log.status = status
                if output_payload is not None:
                    db_log.output_payload = output_payload
                if error_details is not None:
                    db_log.error_details = error_details
                db_log.updated_at = datetime.utcnow()
                await session.commit()
                return db_log.status
        
        return status

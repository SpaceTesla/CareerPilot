from __future__ import annotations

from fastapi import APIRouter, Request, Response, HTTPException
from app.schemas.observability import ADRListResponse
from app.services.documentation_service import DocumentationService

router = APIRouter(prefix="/docs", tags=["documentation"])

@router.get("/adrs", response_model=ADRListResponse)
def get_architecture_decision_records():
    """
    Parses and lists the local Architecture Decision Records (ADRs).
    """
    try:
        return DocumentationService.list_adrs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load ADRs: {e}")

@router.get("/openapi.json")
def get_openapi_specification(request: Request):
    """
    Dynamically returns the OpenAPI specification in JSON format.
    """
    try:
        spec = DocumentationService.get_openapi_spec(request.app)
        return Response(content=spec, media_type="application/json")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate OpenAPI specification: {e}")

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import List

from app.core.logging import get_logger
from app.schemas.observability import ADRItem, ADRListResponse

logger = get_logger(__name__)

class DocumentationService:
    """
    Documentation Service (F6.5).
    Parses local Markdown files in the /docs/adrs/ directory to serve ADR metadata.
    """

    @classmethod
    def list_adrs(cls) -> ADRListResponse:
        """
        Scans /docs/adrs/ and parses ADR titles, status, dates, and summaries.
        """
        # Search parent directories for docs/adrs
        base_paths = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../docs/adrs")),
            "C:/Users/shiva/Desktop/Projects/CareerPilot/docs/adrs"
        ]
        
        adrs_dir = ""
        for p in base_paths:
            if os.path.exists(p):
                adrs_dir = p
                break
        
        adrs = []
        if not adrs_dir:
            logger.warning("ADR directory docs/adrs not found.")
            return ADRListResponse(adrs=[])

        try:
            for filename in sorted(os.listdir(adrs_dir)):
                if filename.endswith(".md"):
                    filepath = os.path.join(adrs_dir, filename)
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()
                    
                    # 1. Parse ID and Title from the first line: e.g. "# ADR 0001: FastAPI..."
                    first_line = content.split("\n")[0] if content else ""
                    title_match = re.search(r"#\s*ADR\s+(\d+):\s*(.*)", first_line)
                    if title_match:
                        adr_id = f"adr-{title_match.group(1)}"
                        title = title_match.group(2).strip()
                    else:
                        num_match = re.search(r"(\d+)", filename)
                        adr_id = f"adr-{num_match.group(1)}" if num_match else filename.replace(".md", "")
                        title = filename.replace(".md", "").replace("-", " ").title()
                    
                    # 2. Parse Status (from ## Status section)
                    status = "ACCEPTED"
                    status_match = re.search(r"##\s*Status\s*\n+([^\n#\s]+)", content, re.IGNORECASE)
                    if status_match:
                        status = status_match.group(1).strip().upper()

                    # 3. Parse Summary from Decision or Context
                    summary = ""
                    decision_match = re.search(r"##\s*Decision\s*\n+([^\n#]+)", content, re.IGNORECASE)
                    if decision_match:
                        summary = decision_match.group(1).strip()
                    else:
                        context_match = re.search(r"##\s*Context\s*\n+([^\n#]+)", content, re.IGNORECASE)
                        if context_match:
                            summary = context_match.group(1).strip()
                    
                    # Standardize whitespace and limit length
                    summary = re.sub(r"\s+", " ", summary)
                    if len(summary) > 200:
                        summary = summary[:197] + "..."
                    
                    # 4. Use file modification date
                    mtime = os.path.getmtime(filepath)
                    date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                    
                    adrs.append(
                        ADRItem(
                            id=adr_id,
                            title=title,
                            status=status,
                            date=date_str,
                            summary=summary
                        )
                    )
        except Exception as e:
            logger.error(f"Failed to list or parse ADRs: {e}")
            
        return ADRListResponse(adrs=adrs)

    @classmethod
    def get_openapi_spec(cls, app) -> str:
        """
        Dynamically exports FastAPI OpenAPI JSON spec representation.
        """
        import json
        from fastapi.openapi.utils import get_openapi
        
        spec = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
        return json.dumps(spec)

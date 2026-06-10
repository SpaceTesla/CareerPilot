from __future__ import annotations

import time
import re
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.metrics_collection_service import MetricsCollectionService

class MetricsMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Metrics Interceptor Middleware.
    Updates Prometheus counters and histograms with HTTP request latencies and codes.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start_time
        
        path = request.url.path
        if path.startswith("/api"):
            method = request.method
            
            # Clean path to prevent label cardinality explosion in Prometheus (e.g. replace UUIDs/variables)
            clean_route = re.sub(r"/[a-f0-9\-]{36}", "/{uuid}", path)
            clean_route = re.sub(r"/circuits/[a-zA-Z0-9\-_]+/reset", "/circuits/{service_name}/reset", clean_route)
            
            MetricsCollectionService.record_api_request(
                method=method,
                route=clean_route,
                status=response.status_code,
                duration=duration
            )
            
        return response

from __future__ import annotations

import re
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.services.reliability_manager_service import ReliabilityManagerService

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Rate Limiting Middleware.
    Enforces Redis token-bucket limits on API routes.
    """
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Rate limit only v2 API routes, exclude health checks and documentation routes
        if not path.startswith("/api/v2") or "health" in path or "docs" in path or "openapi.json" in path:
            return await call_next(request)
            
        # Determine rate-limiting key (authenticated user token prefix or fallback to client IP)
        user_id = "anonymous"
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Use a slice of the token as a unique key prefix
            token = auth_header.split(" ")[1]
            user_id = token[-20:] if len(token) > 20 else token
        else:
            user_id = request.client.host if request.client else "unknown_ip"
            
        # Rate limit configuration: 100 requests per 60 seconds by default
        limit = 100
        window = 60
        
        # Admin routes have lower limits to prevent brute-force (e.g. 10/minute)
        if "/admin/" in path:
            limit = 15
            
        allowed = await ReliabilityManagerService.check_rate_limit(user_id, path, limit, window)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."}
            )
            
        return await call_next(request)

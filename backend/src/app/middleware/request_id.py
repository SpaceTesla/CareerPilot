import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import request_id_var


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that generates/extracts a unique Request ID for each incoming
    HTTP request, stores it in contextvars for log tracing, and sets it in
    the response headers.
    """


    async def dispatch(self, request: Request, call_next) -> Response:
        # Check if the request already has a request ID header
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Set the request ID in the context variable
        token = request_id_var.set(request_id)
        # Store in request state for endpoint visibility
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Reset the context variable
            request_id_var.reset(token)

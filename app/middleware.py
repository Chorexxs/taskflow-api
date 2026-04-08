"""
TaskFlow API - Middleware

This module provides custom middleware for the FastAPI application.
Currently includes LoggingMiddleware for request/response logging.

Middleware features:
- Request ID generation and propagation
- Request duration timing
- Structured logging with JSON format
- Error logging with stack traces
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_config import get_logger, request_id_context

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.
    
    This middleware:
    - Generates a unique request ID for each request
    - Logs request method, path, status code, and duration
    - Adds request ID to response headers for tracing
    - Logs errors with full stack traces
    
    The middleware uses structlog for structured JSON logging,
    making it easy to parse logs in production environments.
    
    Attributes:
        None: This class doesn't define class-level attributes.
    
    Example:
        Log output example:
        {
            "event": "request_completed",
            "method": "GET",
            "path": "/api/v1/teams/",
            "status_code": 200,
            "duration_ms": 45.32,
            "request_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and log the result.
        
        Generates a unique request ID, times the request execution,
        and logs the outcome with relevant metadata.
        
        Args:
            request (Request): The incoming HTTP request.
            call_next (Callable): The next middleware or route handler.
        
        Returns:
            Response: The HTTP response with X-Request-ID header added.
        
        Raises:
            Exception: Any exception from the request processing is logged
                      and re-raised for handling by error handlers.
        """
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())
        request_id_context.set(request_id)
        
        # Record start time for duration calculation
        start_time = time.time()
        
        try:
            # Process the request through the application
            response = await call_next(request)
            
            # Calculate request duration
            duration = time.time() - start_time
            
            # Log successful request
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                request_id=request_id,
            )
            
            # Add request ID to response headers for client tracing
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            # Calculate duration even for failed requests
            duration = time.time() - start_time
            
            # Log error with full details
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                request_id=request_id,
                error=str(exc),
                exc_info=True,
            )
            # Re-raise for handling by exception handlers
            raise

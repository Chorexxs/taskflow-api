import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_config import get_logger, request_id_context

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request_id_context.set(request_id)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            duration = time.time() - start_time
            
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                request_id=request_id,
            )
            
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            duration = time.time() - start_time
            
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                request_id=request_id,
                error=str(exc),
                exc_info=True,
            )
            raise

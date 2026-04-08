"""
TaskFlow API - Logging Configuration

This module configures structured logging for the application using structlog.
It provides JSON-formatted logs that are easy to parse and search in
production environments.

Features:
- Structured JSON logging
- Request ID tracking per request
- Automatic timestamp addition
- Exception stack trace formatting
- Logger name tracking

The logging is configured at module import time, so all loggers
created after this module will inherit the configuration.
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.types import EventDict, Processor


# Context variable for storing request ID across async operations
# This allows the request ID to be propagated through all log calls
# in a single request without passing it explicitly
request_id_context: ContextVar[str] = ContextVar("request_id", default="")


def add_request_id(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add request ID to log entries.
    
    This processor retrieves the request ID from the context variable
    and adds it to every log entry. If no request ID is set, it generates
    a new UUID for the log entry.
    
    Args:
        logger (Any): The structlog logger instance.
        method_name (str): The logging method name (info, error, etc.).
        event_dict (EventDict): The log entry dictionary to modify.
    
    Returns:
        EventDict: The log entry with request_id added.
    
    Example:
        >>> # Log output:
        >>> # {"event": "message", "request_id": "550e8400-...", ...}
    """
    event_dict["request_id"] = request_id_context.get() or str(uuid.uuid4())
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog for the application.
    
    This function sets up the logging pipeline with the following processors:
    1. merge_contextvars: Merge context variables into the log entry
    2. add_request_id: Add request ID from context
    3. add_log_level: Add log level (INFO, ERROR, etc.)
    4. add_logger_name: Add logger name
    5. TimeStamper: Add ISO timestamp
    6. StackInfoRenderer: Add stack info for exceptions
    7. format_exc_info: Format exception info
    8. JSONRenderer: Output as JSON
    
    The logging is configured to output to stdout in JSON format,
    which works well with container orchestration systems like
    Docker and Kubernetes.
    
    Returns:
        None: This function doesn't return anything.
    
    Example:
        >>> configure_logging()
        >>> logger = get_logger(__name__)
        >>> logger.info("message", key="value")
        # Output: {"event": "message", "key": "value", "timestamp": "...", ...}
    """
    # Define the processor chain for log entries
    processors = [
        structlog.contextvars.merge_contextvars,
        add_request_id,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]

    # Configure structlog with the processors
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to output through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )


def get_logger(name: str = __name__):
    """
    Get a structured logger for the given module.
    
    This is the main entry point for creating loggers in the application.
    The returned logger will use the configuration set up by configure_logging().
    
    Args:
        name (str): The logger name, typically __name__ from the module.
                    This helps identify the source of log entries.
    
    Returns:
        BoundLogger: A structlog logger instance configured for JSON output.
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("request_received", path="/api/v1/teams/")
        >>> logger.error("error_occurred", error="details", exc_info=True)
    """
    return structlog.get_logger(name)

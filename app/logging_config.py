import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.types import EventDict, Processor


request_id_context: ContextVar[str] = ContextVar("request_id", default="")


def add_request_id(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    event_dict["request_id"] = request_id_context.get() or str(uuid.uuid4())
    return event_dict


def configure_logging() -> None:
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

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )


def get_logger(name: str = __name__):
    return structlog.get_logger(name)

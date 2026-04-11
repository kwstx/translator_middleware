import logging
import re
from typing import Optional, Any, Dict

import structlog

from app.core.config import settings

SENSITIVE_KEYS = {"token", "password", "key", "secret", "authorization", "cookie", "jwt", "auth"}

def _mask_value(val: Any, key_name: str = "") -> Any:
    if not isinstance(val, str):
        return "********"
    # Always fully mask passwords and secrets
    if "password" in key_name.lower() or "secret" in key_name.lower():
        return "********"
    # Partial mask for others if they are long enough
    if len(val) > 8:
        return f"{val[:4]}...{val[-4:]}"
    return "********"


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        sanitized: Dict[str, Any] = {}
        for key, value in obj.items():
            key_str = str(key)
            if any(sk in key_str.lower() for sk in SENSITIVE_KEYS):
                sanitized[key] = _mask_value(value, key_str)
            else:
                sanitized[key] = _sanitize(value)
        return sanitized
    if isinstance(obj, list):
        return [_sanitize(item) for item in obj]
    return obj


def mask_sensitive_data(_, __, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Masks values of sensitive keys in the log event (including nested structures)."""
    return _sanitize(event_dict)

def configure_logging(log_level: Optional[str] = None) -> None:
    """Configure structured JSON logging via structlog."""
    level = (log_level or settings.LOG_LEVEL).upper()

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    pre_chain = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        timestamper,
    ]

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=pre_chain,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            mask_sensitive_data,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def bind_context(**kwargs):
    """Binds context variables to the current structlog context."""
    structlog.contextvars.bind_contextvars(**kwargs)

def unbind_context(*keys):
    """Unbinds context variables from the current structlog context."""
    structlog.contextvars.unbind_contextvars(*keys)

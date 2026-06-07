"""
Structured logging configuration for Vrski.

Call configure_logging() once at startup (done in api/main.py).
All modules use standard logging.getLogger() — structlog intercepts it.
"""
import logging
import sys
import structlog


def configure_logging(level: str = "INFO") -> None:
    """Wire structlog into the standard logging system."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )


def get_tool_call_logger():
    """Returns a structlog logger for MCP tool-call structured entries."""
    return structlog.get_logger("vrski.tool_calls")

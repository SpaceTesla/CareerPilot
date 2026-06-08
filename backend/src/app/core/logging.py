import contextvars
import datetime
import json
import logging
import sys
from pathlib import Path

# Context variable to hold request ID for logging tracing
request_id_var = contextvars.ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured application logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.datetime.fromtimestamp(
                record.created, datetime.UTC
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "filename": record.filename,
            "lineno": record.lineno,
        }

        # Capture request_id from context variable or record attributes if present
        req_id = request_id_var.get()
        if req_id:
            log_record["request_id"] = req_id
        elif hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        # Capture other extra fields provided to logger methods
        extra_attrs = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                "request_id",
            }
        }
        if extra_attrs:
            log_record["extra"] = extra_attrs

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def setup_logging(
    level: str = "INFO",
    format_string: str | None = None,
    include_file_handler: bool = False,
    log_file: str = "app.log",
) -> None:
    """
    Configure application logging to use JSON format.
    """
    # Keep format_string parameter for backwards compatibility
    _ = format_string
    log_level = getattr(logging, level.upper(), logging.INFO)


    # Create stream handler with JSON formatter
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(JsonFormatter())

    handlers = [stream_handler]

    # Add file handler if requested
    if include_file_handler:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(JsonFormatter())
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True,  # Override any existing configuration
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.
    """
    return logging.getLogger(name)

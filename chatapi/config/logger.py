import contextvars
import logging
from copy import copy
from datetime import UTC, datetime

from pythonjsonlogger.json import JsonFormatter

# สร้าง context variable สำหรับ trace-id
CTX_TRACE_ID = contextvars.ContextVar("trace_id", default=None)
HEADER_TRACE_NAME = "x-cap-trace-id"
HEADER_KEY_NAME = "x-cap-api-key"


class UvicornJSONAccessFormatter(JsonFormatter):
    def __init__(self) -> None:
        super().__init__()  # type:ignore
        self.json_ensure_ascii = False

    def format(self, record: logging.LogRecord) -> str:
        recordcopy = copy(record)
        _addr, method, full_path, _version, status_code = recordcopy.args  # type: ignore[misc]

        # Format the message before processing
        recordcopy.getMessage()  # This will format the message with args

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
        recordcopy.__dict__.pop("taskName", None)
        recordcopy.__dict__.update(
            {
                "level": recordcopy.levelname,
                "time": now,
                "method": method,
                "path": full_path,
                "status_code": status_code,
                "trace_id": CTX_TRACE_ID.get(),
            },
        )

        return super().format(record=recordcopy)

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:  # type: ignore
        super().add_fields(log_record, record, message_dict)
        log_record["name"] = record.name
        log_record["msg"] = "access"
        log_record.pop("message")


class UvicornJSONDefaultFormatter(JsonFormatter):
    def __init__(self, fs: str = "", dfs: str = "", stl: str = "") -> None:
        super().__init__()  # type:ignore
        self.json_ensure_ascii = False

    def format(self, record: logging.LogRecord) -> str:
        recordcopy = copy(record)
        recordcopy.__dict__.pop("color_message", None)
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
        recordcopy.__dict__.update(
            {
                "name": recordcopy.name,
                "level": recordcopy.levelname,
                "time": now,
                "trace_id": CTX_TRACE_ID.get(),
            },
        )
        return super().format(record=recordcopy)

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:  # type: ignore
        super().add_fields(log_record, record, message_dict)
        log_record["name"] = record.name
        log_record["msg"] = record.getMessage()
        log_record.pop("message")


class ExcludeRouter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/healthz" not in record.getMessage()

import contextvars
import logging
import re
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_ID_HEADER = "X-Correlation-ID"
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")

SENSITIVE_PATTERNS = [
    (re.compile(r'(?i)("?password"?\s*[:=]\s*)"[^"]+"'), r'\1"[REDACTED]"'),
    (re.compile(r'(?i)("?token"?\s*[:=]\s*)"[^"]+"'), r'\1"[REDACTED]"'),
    (re.compile(r'(?i)("?api_key"?\s*[:=]\s*)"[^"]+"'), r'\1"[REDACTED]"'),
    (re.compile(r'(?i)("?secret"?\s*[:=]\s*)"[^"]+"'), r'\1"[REDACTED]"'),
    (re.compile(r'(?i)(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*'), r'\1[REDACTED]'),
]


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware extracting or generating correlation ID for HTTP request context."""

    async def dispatch(self, request: Request, call_next) -> Response:
        corr_id = request.headers.get(CORRELATION_ID_HEADER) or uuid.uuid4().hex
        token = correlation_id_var.set(corr_id)
        request.state.correlation_id = corr_id

        try:
            response = await call_next(request)
            response.headers[CORRELATION_ID_HEADER] = corr_id
            return response
        finally:
            correlation_id_var.reset(token)


class StructuredLogFilter(logging.Filter):
    """Logging filter adding correlation_id context parameter and redacting sensitive credentials."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get("")
        if isinstance(record.msg, str):
            msg = record.msg
            for pattern, replacement in SENSITIVE_PATTERNS:
                msg = pattern.sub(replacement, msg)
            record.msg = msg
        return True

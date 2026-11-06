"""Request correlation for API/worker logs; not a substitute for distributed spans."""
import contextvars
import logging
import re
import time
import uuid

from starlette.requests import Request

request_id = contextvars.ContextVar("ibanking_request_id", default="-")
log = logging.getLogger("ibanking.requests")
_VALID_ID = re.compile(r"^[A-Za-z0-9._-]{8,128}$")


def outbound_headers(extra=None):
    return {**(extra or {}), "X-Request-ID": request_id.get()}


def install_request_logging(app, service):
    @app.middleware("http")
    async def correlation(request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        rid = incoming if _VALID_ID.fullmatch(incoming) else uuid.uuid4().hex
        token = request_id.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            log.info("service=%s request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
                     service, rid, request.method, request.url.path, response.status_code,
                     (time.perf_counter() - start) * 1000)
            return response
        except Exception:
            log.exception("service=%s request_id=%s method=%s path=%s unhandled_error",
                          service, rid, request.method, request.url.path)
            raise
        finally:
            request_id.reset(token)

import json
import logging
import os
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, Any

from fastapi import FastAPI, Request, Query
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

START_TIME = time.monotonic()
USER_EMAIL = "24f2007269@ds.study.iitm.ac.in"

# A single live counter, incremented for every HTTP request, including /metrics.
HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests received by the application",
    ["method", "path", "status"],
)

LOG_ENTRIES: Deque[Dict[str, Any]] = deque(maxlen=2000)

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = getattr(record, "payload", {})
        return json.dumps(payload, separators=(",", ":"), default=str)

logger = logging.getLogger("request_json")
logger.setLevel(logging.INFO)
logger.propagate = False
_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter())
logger.handlers.clear()
logger.addHandler(_handler)

app = FastAPI(title="Prometheus Work Service")

class RequestMetricsAndLogsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            path = request.url.path
            elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
            entry = {
                "level": "INFO" if status_code < 500 else "ERROR",
                "ts": datetime.now(timezone.utc).isoformat(),
                "path": path,
                "request_id": request_id,
                "method": request.method,
                "status": status_code,
                "duration_ms": elapsed_ms,
            }
            LOG_ENTRIES.append(entry)
            logger.info("request", extra={"payload": entry})
            HTTP_REQUESTS.labels(
                method=request.method,
                path=path,
                status=str(status_code),
            ).inc()

app.add_middleware(RequestMetricsAndLogsMiddleware)

@app.get("/")
def root():
    return {"status": "ok", "service": "prometheus-work-service"}

@app.get("/work")
def work(n: int = Query(default=1, ge=0, le=1000000)):
    # Simulate K units of work deterministically without unnecessary delay.
    return {"email": USER_EMAIL, "done": n}

@app.get("/healthz")
def healthz():
    return {"status": "ok", "uptime_s": max(0.0, time.monotonic() - START_TIME)}

@app.get("/logs/tail")
def logs_tail(limit: int = Query(default=100, ge=1, le=1000)):
    return list(LOG_ENTRIES)[-limit:]

@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

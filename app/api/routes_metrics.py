"""
Prometheus metrics endpoint (PROD-02).
Exposes openhub_* metrics in text format for Prometheus scraping.
"""
from fastapi import APIRouter, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

router = APIRouter(tags=["observability"])

# --- Metrics definitions ---
REQUESTS_TOTAL = Counter(
    "openhub_requests_total",
    "Total HTTP requests by method, endpoint, and status code",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION_SECONDS = Histogram(
    "openhub_request_duration_seconds",
    "HTTP request duration in seconds",
    ["endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

ACTIVE_AGENTS = Gauge(
    "openhub_active_agents",
    "Number of agents currently in 'online' status",
)

TASKS_BY_STATUS = Gauge(
    "openhub_tasks_by_status",
    "Number of tasks by status",
    ["status"],
)


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics() -> Response:
    """
    Prometheus metrics endpoint.
    Returns all openhub_* metrics in Prometheus text exposition format.
    Not included in OpenAPI schema (include_in_schema=False).
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )

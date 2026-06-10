from __future__ import annotations

import time
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, REGISTRY, generate_latest
from app.core.logging import get_logger

logger = get_logger(__name__)

# System Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "careerpilot_api_requests_total",
    "Total HTTP requests handled",
    ["method", "route", "status"]
)

HTTP_REQUEST_DURATION = Histogram(
    "careerpilot_api_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route"]
)

# Business Metrics
APPLICATION_SUBMISSIONS = Counter(
    "careerpilot_application_submissions_total",
    "Total applications submitted",
    ["ats_type", "status"]
)

AVERAGE_HEALTH_SCORE = Gauge(
    "careerpilot_avg_health_score",
    "Average Career Health Score across users"
)

class MetricsCollectionService:
    """
    Metrics Collection Service (F6.2).
    A utility class to record system events and map them to Prometheus metric counters.
    """

    @classmethod
    def record_api_request(cls, method: str, route: str, status: int, duration: float) -> None:
        """
        Increments HTTP_REQUESTS_TOTAL and observes request latency.
        """
        try:
            HTTP_REQUESTS_TOTAL.labels(method=method, route=route, status=str(status)).inc()
            HTTP_REQUEST_DURATION.labels(method=method, route=route).observe(duration)
        except Exception as e:
            logger.warning(f"Failed to record API request metrics: {e}")

    @classmethod
    def record_application_submission(cls, ats_type: str, status: str) -> None:
        """
        Increments the APPLICATION_SUBMISSIONS counter.
        """
        try:
            APPLICATION_SUBMISSIONS.labels(ats_type=ats_type, status=status).inc()
        except Exception as e:
            logger.warning(f"Failed to record application submission metrics: {e}")

    @classmethod
    def update_average_health_score(cls, score: float) -> None:
        """
        Sets the AVERAGE_HEALTH_SCORE gauge.
        """
        try:
            AVERAGE_HEALTH_SCORE.set(score)
        except Exception as e:
            logger.warning(f"Failed to update average health score gauge: {e}")

    @classmethod
    def get_serialized_metrics(cls) -> str:
        """
        Returns serialized metrics output in standard Prometheus format.
        """
        try:
            return generate_latest(REGISTRY).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to serialize Prometheus metrics: {e}")
            return ""

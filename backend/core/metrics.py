from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest


REQUEST_COUNT = Counter(
    "vendor_onboarding_api_requests_total",
    "Total API requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "vendor_onboarding_api_latency_seconds",
    "API latency",
    ["method", "path"],
)
HIPAA_CHECK_RESULTS = Counter(
    "vendor_onboarding_hipaa_checks_total",
    "HIPAA check results",
    ["check_name", "result"],
)
QUEUE_DEPTH = Gauge(
    "vendor_onboarding_queue_depth",
    "Logical queue depth by name",
    ["queue_name"],
)
WORKER_THROUGHPUT = Counter(
    "vendor_onboarding_worker_throughput_total",
    "Processed tasks per worker",
    ["worker_name", "queue_name"],
)
CONTINUAL_MODEL_ACCURACY = Gauge(
    "vendor_onboarding_continual_model_accuracy",
    "Continual model accuracy",
)


def render_metrics() -> bytes:
    return generate_latest()


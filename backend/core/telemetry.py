from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


def setup_telemetry() -> None:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # noqa: F401
    except ImportError:
        return


@contextmanager
def trace_span(name: str, **_: object) -> Iterator[None]:
    try:
        from opentelemetry import trace
    except ImportError:
        yield
        return

    tracer = trace.get_tracer("vendor_onboarding")
    with tracer.start_as_current_span(name):
        yield


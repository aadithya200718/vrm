from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routers import approvals, dashboard, documents, healthcare, metrics, vendors
from backend.core.config import get_settings
from backend.core.logging import logger
from backend.core.metrics import REQUEST_COUNT, REQUEST_LATENCY
from backend.middleware.auth import AuthContextMiddleware
from backend.middleware.masking import MaskSensitiveFieldsMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.add_middleware(AuthContextMiddleware)
    app.add_middleware(MaskSensitiveFieldsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - started
        REQUEST_COUNT.labels(
            method=request.method,
            path=request.url.path,
            status=str(response.status_code),
        ).inc()
        REQUEST_LATENCY.labels(method=request.method, path=request.url.path).observe(elapsed)
        return response

    @app.get("/health", tags=["system"])
    def healthcheck():
        return {"status": "ok"}

    app.include_router(vendors.router, prefix=settings.api_prefix, tags=["vendors"])
    app.include_router(documents.router, prefix=settings.api_prefix, tags=["documents"])
    app.include_router(approvals.router, prefix=settings.api_prefix, tags=["approvals"])
    app.include_router(healthcare.router, prefix=settings.api_prefix, tags=["healthcare"])
    app.include_router(dashboard.router, prefix=settings.api_prefix, tags=["dashboard"])
    app.include_router(metrics.router)

    logger.info("FastAPI application initialized", extra={"service": "fastapi"})
    return app

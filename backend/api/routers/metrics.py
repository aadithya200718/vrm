from __future__ import annotations

from fastapi import APIRouter, Response

from backend.core.metrics import render_metrics


router = APIRouter(include_in_schema=False)


@router.get("/metrics")
def metrics():
    return Response(render_metrics(), media_type="text/plain; version=0.0.4")

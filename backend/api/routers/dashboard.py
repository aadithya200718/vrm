from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.deps import service_dependency
from backend.core.services import VendorOnboardingService


router = APIRouter()


@router.get("/dashboard/stats")
def dashboard_stats(
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_dashboard_stats()


@router.get("/dashboard/recent")
def dashboard_recent(
    service: VendorOnboardingService = Depends(service_dependency),
):
    return service.get_dashboard_recent()

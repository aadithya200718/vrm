from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from backend.api.deps import service_dependency
from backend.core.services import VendorOnboardingService


router = APIRouter()


@router.post("/documents/parse")
async def parse_documents(
    service: VendorOnboardingService = Depends(service_dependency),
    files: list[UploadFile] = File(...),
):
    return await service.parse_documents(files)

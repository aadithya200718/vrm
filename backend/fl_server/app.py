from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field


class FederatedRoundRequest(BaseModel):
    organization_id: str
    round_id: str
    encrypted_weight_deltas: list[float] = Field(default_factory=list)


class FederatedRoundResponse(BaseModel):
    status: str
    round_id: str
    global_model_version: str


app = FastAPI(title="Vendor Onboarding FL Server")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/rounds", response_model=FederatedRoundResponse)
def submit_round(payload: FederatedRoundRequest):
    return FederatedRoundResponse(
        status="accepted",
        round_id=payload.round_id,
        global_model_version=f"global-{payload.round_id}",
    )


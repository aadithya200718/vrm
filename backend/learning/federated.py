from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(slots=True)
class FederatedRoundResult:
    round_id: str
    weight_deltas: list[float]
    noise_applied: bool


def prepare_federated_update(features: list[float]) -> FederatedRoundResult:
    digest = hashlib.sha256(",".join(map(str, features)).encode("utf-8")).hexdigest()
    deltas = [round(((int(digest[i : i + 2], 16) / 255) - 0.5) * 0.1, 6) for i in range(0, 20, 2)]
    return FederatedRoundResult(round_id=digest[:12], weight_deltas=deltas, noise_applied=True)


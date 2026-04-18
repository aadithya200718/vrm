from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


def stable_score(*parts: str, floor: float = 0.7, ceiling: float = 0.98) -> float:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    number = int(digest[:8], 16) / 0xFFFFFFFF
    return round(floor + (ceiling - floor) * number, 4)


@dataclass(slots=True)
class ToolResult:
    result: str
    confidence_score: float
    details: dict[str, Any]
    provider: str = "heuristic"


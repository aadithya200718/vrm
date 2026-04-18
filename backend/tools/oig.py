from __future__ import annotations

from backend.tools.base import ToolResult


def check_oig(names: list[str]) -> ToolResult:
    normalized = " ".join(names).lower()
    excluded = "excluded" in normalized or "oig-hit" in normalized
    return ToolResult(
        result="excluded" if excluded else "clear",
        confidence_score=0.0 if excluded else 1.0,
        details={"excluded_parties": names[:1] if excluded else []},
    )


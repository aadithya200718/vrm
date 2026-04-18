from __future__ import annotations

from backend.tools.base import ToolResult, stable_score


def check_sanctions(names: list[str], healthcare: bool = False) -> ToolResult:
    normalized = " ".join(names).lower()
    risky = any(bad in normalized for bad in ("sanction", "watchlist", "blocked"))
    result = "flagged" if risky else "clear"
    lists_checked = ["ComplyAdvantage"]
    if healthcare:
        lists_checked.extend(["CDSCO", "NMC"])
    return ToolResult(
        result=result,
        confidence_score=0.0 if risky else stable_score(*names, floor=0.86, ceiling=0.99),
        details={
            "matches": names[:1] if risky else [],
            "risk_level": "HIGH RISK" if risky else "LOW",
            "lists_checked": lists_checked,
        },
    )


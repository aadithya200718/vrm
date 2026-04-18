from __future__ import annotations

import re

from backend.tools.base import ToolResult, stable_score


def verify_pan(raw_text: str, vendor_name: str) -> ToolResult:
    pan_match = re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", raw_text.upper())
    result = "verified" if pan_match else "failed"
    return ToolResult(
        result=result,
        confidence_score=stable_score(vendor_name, pan_match.group(0) if pan_match else "missing"),
        details={
            "pan": pan_match.group(0) if pan_match else None,
            "name_match": bool(pan_match),
        },
    )


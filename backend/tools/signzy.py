from __future__ import annotations

import re

from backend.tools.base import ToolResult, stable_score


def verify_gst(raw_text: str, vendor_name: str) -> ToolResult:
    gst_match = re.search(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]\b", raw_text.upper())
    gst_number = gst_match.group(0) if gst_match else "UNKNOWN"
    status = "verified" if gst_match else "failed"
    return ToolResult(
        result=status,
        confidence_score=1.0 if gst_match else 0.42,
        details={
            "gst_number": gst_number,
            "company_name": vendor_name,
            "registration_status": "active" if gst_match else "missing",
        },
    )


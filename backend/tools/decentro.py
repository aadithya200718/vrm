from __future__ import annotations

import re

from backend.tools.base import ToolResult, stable_score


def verify_bank_account(raw_text: str, vendor_name: str) -> ToolResult:
    account = re.search(r"\b\d{9,18}\b", raw_text)
    ifsc = re.search(r"\b[A-Z]{4}0[A-Z0-9]{6}\b", raw_text.upper())
    valid = bool(account and ifsc)
    return ToolResult(
        result="verified" if valid else "failed",
        confidence_score=stable_score(vendor_name, account.group(0) if account else "missing"),
        details={
            "account_number": account.group(0) if account else None,
            "ifsc": ifsc.group(0) if ifsc else None,
            "account_holder_name": vendor_name,
            "name_match_percentage": 1.0 if valid else 0.4,
        },
    )


from __future__ import annotations

from backend.tools.oig import check_oig


def run_oig_check(names: list[str]):
    return check_oig(names)


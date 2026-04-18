from __future__ import annotations

from typing import Any

from backend.models.enums import WorkflowType


def route_by_ephi(ephi_involved: bool) -> WorkflowType:
    return WorkflowType.HEALTHCARE if ephi_involved else WorkflowType.SAAS


def build_supervisor_graph() -> dict[str, Any]:
    return {
        "entry": "ephi_gate",
        "nodes": {
            "ephi_gate": {
                "description": "Routes intake requests to SaaS or Healthcare workflow",
                "routes": {
                    "saas": "saas_workflow",
                    "healthcare": "healthcare_workflow",
                },
            },
            "saas_workflow": {"agents": 18, "approval_steps": 3},
            "healthcare_workflow": {"agents": 24, "approval_steps": 4},
            "learning_feedback": {"description": "Post-outcome feedback node"},
        },
    }

"""
LangGraph state machine — Phase 2 multi-agent orchestration with parallel execution.

Graph structure:
    START → intake_node
        → (parallel) security_node + compliance_node + financial_node
        → supervisor_aggregate_node
        → evidence_node
        → supervisor_final_node
        → END
"""
import logging
from datetime import datetime, timezone
from typing import TypedDict, Annotated, Literal

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage

from app.core.db import update_vendor, create_audit_log
from app.core.redis_state import save_state, load_state
from app.agents.document_intake import run_intake_agent
from app.agents.security_review import run_security_agent
from app.agents.compliance_review import run_compliance_agent
from app.agents.financial_review import run_financial_agent
from app.agents.evidence_coordinator import run_evidence_coordinator
from app.agents.supervisor import run_supervisor

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Graph State Definition
# ═══════════════════════════════════════════════════════════════════

class GraphState(TypedDict):
    """State shared across all nodes in the LangGraph."""
    vendor_id: str
    vendor_name: str
    vendor_type: str
    contract_value: float
    vendor_domain: str
    file_paths: list[str]
    current_phase: str
    messages: Annotated[list, add_messages]
    intake_result: dict
    security_result: dict
    compliance_result: dict
    financial_result: dict
    evidence_result: dict
    supervisor_result: dict
    errors: list[str]
    final_report: dict


# ═══════════════════════════════════════════════════════════════════
# Node Functions
# ═══════════════════════════════════════════════════════════════════

def intake_node(state: GraphState) -> GraphState:
    """Document Intake Agent node — processes vendor documents."""
    vendor_id = state["vendor_id"]
    file_paths = state.get("file_paths", [])

    logger.info(f"[intake_node] Processing {len(file_paths)} files for vendor {vendor_id}")

    save_state(vendor_id, {
        "current_phase": "intake",
        "current_agent": "document_intake",
        "progress_percentage": 10,
    })

    create_audit_log(
        vendor_id=vendor_id,
        agent_name="document_intake",
        action="agent_started",
    )

    result = run_intake_agent(vendor_id, file_paths)

    create_audit_log(
        vendor_id=vendor_id,
        agent_name="document_intake",
        action="agent_completed",
        output_data={"status": result.get("status")},
    )

    save_state(vendor_id, {
        "current_phase": "intake_complete",
        "progress_percentage": 20,
    })

    return {
        **state,
        "intake_result": result,
        "current_phase": "intake_complete",
        "messages": [
            AIMessage(
                content=f"[Document Intake] {result.get('status', 'unknown')}: "
                f"Processed {result.get('files_processed', 0)} documents."
            )
        ],
    }


def security_node(state: GraphState) -> GraphState:
    """Security Review Agent node — assesses vendor security posture."""
    vendor_id = state["vendor_id"]

    logger.info(f"[security_node] Starting security review for vendor {vendor_id}")

    save_state(vendor_id, {
        "current_phase": "security_review",
        "current_agent": "security_review",
        "progress_percentage": 35,
    })

    create_audit_log(vendor_id=vendor_id, agent_name="security_review", action="agent_started")

    result = run_security_agent(vendor_id)

    create_audit_log(
        vendor_id=vendor_id, agent_name="security_review", action="agent_completed",
        output_data={"status": result.get("status")},
    )

    return {
        **state,
        "security_result": result,
        "messages": [AIMessage(content=f"[Security Review] {result.get('status', 'unknown')}: Assessment complete.")],
    }


def compliance_node(state: GraphState) -> GraphState:
    """Compliance Review Agent node — regulatory compliance assessment."""
    vendor_id = state["vendor_id"]

    logger.info(f"[compliance_node] Starting compliance review for vendor {vendor_id}")

    save_state(vendor_id, {
        "current_phase": "compliance_review",
        "current_agent": "compliance_review",
    })

    create_audit_log(vendor_id=vendor_id, agent_name="compliance_review", action="agent_started")

    result = run_compliance_agent(vendor_id)

    create_audit_log(
        vendor_id=vendor_id, agent_name="compliance_review", action="agent_completed",
        output_data={"status": result.get("status")},
    )

    return {
        **state,
        "compliance_result": result,
        "messages": [AIMessage(content=f"[Compliance Review] {result.get('status', 'unknown')}: Assessment complete.")],
    }


def financial_node(state: GraphState) -> GraphState:
    """Financial Review Agent node — financial risk assessment."""
    vendor_id = state["vendor_id"]

    logger.info(f"[financial_node] Starting financial review for vendor {vendor_id}")

    save_state(vendor_id, {
        "current_phase": "financial_review",
        "current_agent": "financial_review",
    })

    create_audit_log(vendor_id=vendor_id, agent_name="financial_review", action="agent_started")

    result = run_financial_agent(vendor_id)

    create_audit_log(
        vendor_id=vendor_id, agent_name="financial_review", action="agent_completed",
        output_data={"status": result.get("status")},
    )

    return {
        **state,
        "financial_result": result,
        "messages": [AIMessage(content=f"[Financial Review] {result.get('status', 'unknown')}: Assessment complete.")],
    }


def supervisor_aggregate_node(state: GraphState) -> GraphState:
    """Supervisor aggregation node — gathers results from parallel reviews."""
    vendor_id = state["vendor_id"]

    logger.info(f"[supervisor_aggregate] Aggregating parallel review results for vendor {vendor_id}")

    save_state(vendor_id, {
        "current_phase": "aggregating",
        "current_agent": "supervisor",
        "progress_percentage": 60,
    })

    create_audit_log(vendor_id=vendor_id, agent_name="supervisor", action="aggregate_results")

    sec = state.get("security_result", {})
    comp = state.get("compliance_result", {})
    fin = state.get("financial_result", {})

    summary = (
        f"Parallel reviews complete.\n"
        f"Security: {sec.get('status', 'unknown')} (score: {sec.get('score', 'N/A')})\n"
        f"Compliance: {comp.get('status', 'unknown')} (score: {comp.get('score', 'N/A')})\n"
        f"Financial: {fin.get('status', 'unknown')} (score: {fin.get('score', 'N/A')})"
    )

    return {
        **state,
        "current_phase": "aggregated",
        "messages": [AIMessage(content=f"[Supervisor] {summary}")],
    }


def evidence_node(state: GraphState) -> GraphState:
    """Evidence Coordinator Agent node — gap analysis and collection."""
    vendor_id = state["vendor_id"]

    logger.info(f"[evidence_node] Starting evidence coordination for vendor {vendor_id}")

    save_state(vendor_id, {
        "current_phase": "evidence_coordination",
        "current_agent": "evidence_coordinator",
        "progress_percentage": 75,
    })

    create_audit_log(vendor_id=vendor_id, agent_name="evidence_coordinator", action="agent_started")

    result = run_evidence_coordinator(vendor_id)

    create_audit_log(
        vendor_id=vendor_id, agent_name="evidence_coordinator", action="agent_completed",
        output_data={"status": result.get("status")},
    )

    return {
        **state,
        "evidence_result": result,
        "current_phase": "evidence_complete",
        "messages": [AIMessage(content=f"[Evidence Coordinator] {result.get('status', 'unknown')}: Coordination complete.")],
    }


def supervisor_final_node(state: GraphState) -> GraphState:
    """Supervisor final node — compiles all results and makes recommendation."""
    vendor_id = state["vendor_id"]

    logger.info(f"[supervisor_final] Compiling final results for vendor {vendor_id}")

    save_state(vendor_id, {
        "current_phase": "compiling",
        "current_agent": "supervisor",
        "progress_percentage": 90,
    })

    create_audit_log(vendor_id=vendor_id, agent_name="supervisor", action="compile_final")

    result = run_supervisor(vendor_id)

    create_audit_log(
        vendor_id=vendor_id, agent_name="supervisor", action="agent_completed",
        output_data={"status": result.get("status")},
    )

    save_state(vendor_id, {
        "current_phase": "done",
        "progress_percentage": 100,
    })

    update_vendor(vendor_id, {"status": "review_completed"})

    return {
        **state,
        "supervisor_result": result,
        "current_phase": "done",
        "final_report": result,
        "messages": [
            AIMessage(content=f"[Supervisor] Review complete. Status: {result.get('status', 'unknown')}")
        ],
    }


# ═══════════════════════════════════════════════════════════════════
# Routing Logic
# ═══════════════════════════════════════════════════════════════════

def route_after_intake(state: GraphState) -> list[str]:
    """After intake, fan out to parallel review agents (or supervisor on error)."""
    intake_result = state.get("intake_result", {})
    if intake_result.get("status") == "error":
        logger.warning("Intake failed — routing to supervisor for error handling")
        return ["supervisor_final_node"]
    # Fan-out to all three review agents
    return ["security_node", "compliance_node", "financial_node"]


# ═══════════════════════════════════════════════════════════════════
# Build the Graph
# ═══════════════════════════════════════════════════════════════════

def build_workflow_graph() -> StateGraph:
    """
    Build the LangGraph state machine for the vendor review workflow.

    Graph structure:
        START → intake_node
            → (parallel fan-out) security_node, compliance_node, financial_node
            → (fan-in) supervisor_aggregate_node
            → evidence_node
            → supervisor_final_node
            → END
    """
    workflow = StateGraph(GraphState)

    # Add all nodes
    workflow.add_node("intake_node", intake_node)
    workflow.add_node("security_node", security_node)
    workflow.add_node("compliance_node", compliance_node)
    workflow.add_node("financial_node", financial_node)
    workflow.add_node("supervisor_aggregate_node", supervisor_aggregate_node)
    workflow.add_node("evidence_node", evidence_node)
    workflow.add_node("supervisor_final_node", supervisor_final_node)

    # Entry point
    workflow.set_entry_point("intake_node")

    # After intake: fan-out to parallel review agents
    workflow.add_conditional_edges(
        "intake_node",
        route_after_intake,
        ["security_node", "compliance_node", "financial_node", "supervisor_final_node"],
    )

    # All three review nodes fan-in to the supervisor aggregate
    workflow.add_edge("security_node", "supervisor_aggregate_node")
    workflow.add_edge("compliance_node", "supervisor_aggregate_node")
    workflow.add_edge("financial_node", "supervisor_aggregate_node")

    # After aggregation → evidence coordination → final supervisor → END
    workflow.add_edge("supervisor_aggregate_node", "evidence_node")
    workflow.add_edge("evidence_node", "supervisor_final_node")
    workflow.add_edge("supervisor_final_node", END)

    return workflow


def get_compiled_graph():
    """Get the compiled workflow graph, ready for execution."""
    workflow = build_workflow_graph()
    return workflow.compile()


def run_full_workflow(
    vendor_id: str,
    vendor_name: str,
    vendor_type: str,
    contract_value: float,
    vendor_domain: str,
    file_paths: list[str],
) -> dict:
    """
    Execute the complete vendor review workflow.

    This is the main entry point for the entire multi-agent system.
    Phase 2: Includes parallel Security/Compliance/Financial execution
    and Evidence Coordinator.
    """
    logger.info(
        f"Starting full workflow for vendor {vendor_name} ({vendor_id})"
    )

    graph = get_compiled_graph()

    initial_state: GraphState = {
        "vendor_id": vendor_id,
        "vendor_name": vendor_name,
        "vendor_type": vendor_type,
        "contract_value": contract_value,
        "vendor_domain": vendor_domain,
        "file_paths": file_paths,
        "current_phase": "init",
        "messages": [
            HumanMessage(
                content=f"Begin vendor onboarding review for {vendor_name}"
            )
        ],
        "intake_result": {},
        "security_result": {},
        "compliance_result": {},
        "financial_result": {},
        "evidence_result": {},
        "supervisor_result": {},
        "errors": [],
        "final_report": {},
    }

    try:
        final_state = graph.invoke(initial_state)

        return {
            "status": "success",
            "vendor_id": vendor_id,
            "current_phase": final_state.get("current_phase", "unknown"),
            "intake_result": final_state.get("intake_result", {}),
            "security_result": final_state.get("security_result", {}),
            "compliance_result": final_state.get("compliance_result", {}),
            "financial_result": final_state.get("financial_result", {}),
            "evidence_result": final_state.get("evidence_result", {}),
            "supervisor_result": final_state.get("supervisor_result", {}),
            "final_report": final_state.get("final_report", {}),
        }

    except Exception as e:
        logger.error(f"Workflow failed for vendor {vendor_id}: {e}")
        save_state(vendor_id, {
            "current_phase": "error",
            "errors": [str(e)],
        })
        return {
            "status": "error",
            "vendor_id": vendor_id,
            "error": str(e),
        }

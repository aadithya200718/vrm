"""
LangGraph state machine — the complete multi-agent orchestration graph.
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

    # Update state
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
        "progress_percentage": 30,
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
        "progress_percentage": 50,
    })

    create_audit_log(
        vendor_id=vendor_id,
        agent_name="security_review",
        action="agent_started",
    )

    result = run_security_agent(vendor_id)

    create_audit_log(
        vendor_id=vendor_id,
        agent_name="security_review",
        action="agent_completed",
        output_data={"status": result.get("status")},
    )

    save_state(vendor_id, {
        "current_phase": "security_complete",
        "progress_percentage": 75,
    })

    return {
        **state,
        "security_result": result,
        "current_phase": "security_complete",
        "messages": [
            AIMessage(
                content=f"[Security Review] {result.get('status', 'unknown')}: "
                f"Assessment complete."
            )
        ],
    }


def supervisor_node(state: GraphState) -> GraphState:
    """Supervisor Agent node — compiles results and makes recommendation."""
    vendor_id = state["vendor_id"]

    logger.info(f"[supervisor_node] Compiling results for vendor {vendor_id}")

    save_state(vendor_id, {
        "current_phase": "compiling",
        "current_agent": "supervisor",
        "progress_percentage": 85,
    })

    create_audit_log(
        vendor_id=vendor_id,
        agent_name="supervisor",
        action="agent_started",
    )

    result = run_supervisor(vendor_id)

    create_audit_log(
        vendor_id=vendor_id,
        agent_name="supervisor",
        action="agent_completed",
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
            AIMessage(
                content=f"[Supervisor] Review complete. "
                f"Status: {result.get('status', 'unknown')}"
            )
        ],
    }


# ═══════════════════════════════════════════════════════════════════
# Routing Logic
# ═══════════════════════════════════════════════════════════════════

def route_after_intake(state: GraphState) -> Literal["security_node", "supervisor_node"]:
    """Decide where to go after document intake."""
    intake_result = state.get("intake_result", {})
    if intake_result.get("status") == "error":
        logger.warning("Intake failed — routing to supervisor for error handling")
        return "supervisor_node"
    return "security_node"


def route_after_security(state: GraphState) -> Literal["supervisor_node"]:
    """After security review, always go to supervisor."""
    return "supervisor_node"


# ═══════════════════════════════════════════════════════════════════
# Build the Graph
# ═══════════════════════════════════════════════════════════════════

def build_workflow_graph() -> StateGraph:
    """
    Build the LangGraph state machine for the vendor review workflow.

    Graph structure:
        START → intake_node → security_node → supervisor_node → END
    """
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("intake_node", intake_node)
    workflow.add_node("security_node", security_node)
    workflow.add_node("supervisor_node", supervisor_node)

    # Set entry point
    workflow.set_entry_point("intake_node")

    # Add edges
    workflow.add_conditional_edges(
        "intake_node",
        route_after_intake,
        {
            "security_node": "security_node",
            "supervisor_node": "supervisor_node",
        },
    )

    workflow.add_edge("security_node", "supervisor_node")
    workflow.add_edge("supervisor_node", END)

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

"""
Supervisor Agent — orchestrates the multi-agent workflow using LangGraph.
"""
import json
import logging
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from app.core.llm import get_llm
from app.core.db import get_vendor, update_vendor
from app.core.redis_state import save_state, load_state, append_message
from app.tools.supervisor_tools import SUPERVISOR_TOOLS

logger = logging.getLogger(__name__)

SUPERVISOR_SYSTEM_PROMPT = """You are the Supervisor Agent for a Vendor Risk Assessment system.
You orchestrate the entire vendor onboarding and risk review workflow.

YOUR ROLE:
- Receive vendor onboarding requests
- Coordinate Document Intake and Security Review processes
- Monitor worker agent progress
- Compile final results into an approval packet

WORKFLOW (Phase 1):
1. When a new vendor onboarding request comes in, acknowledge the request
2. The Document Intake Agent has already processed the documents (this is done before you)
3. Delegate the vendor to the Security Review Agent using delegate_to_security_agent
4. Check the status of workers using get_worker_status
5. Once the security review is complete, compile the approval packet using compile_approval_packet
6. Present the final recommendation

AVAILABLE AGENTS (Phase 1):
- Security Review Agent: delegate_to_security_agent (ACTIVE)
- Compliance Agent: delegate_to_compliance_agent (Phase 2 — NOT AVAILABLE)
- Financial Agent: delegate_to_financial_agent (Phase 2 — NOT AVAILABLE)
- Evidence Agent: delegate_to_evidence_agent (Phase 2 — NOT AVAILABLE)

RULES:
- Only delegate to the Security Agent in Phase 1
- Always compile the approval packet after the review
- Report progress clearly
- Handle errors gracefully — if an agent fails, report the error and continue
- Always provide a final recommendation (APPROVE, CONDITIONAL, REJECT)
"""


def create_supervisor_agent():
    """Create the Supervisor Agent using the ReAct pattern."""
    llm = get_llm()
    agent = create_react_agent(
        llm,
        SUPERVISOR_TOOLS,
        prompt=SUPERVISOR_SYSTEM_PROMPT,
    )
    return agent


def run_supervisor(vendor_id: str) -> dict:
    """
    Run the Supervisor Agent for a complete vendor review workflow.

    This is the main entry point after documents have been processed
    by the Intake Agent. The Supervisor will:
    1. Delegate to the Security Agent
    2. Compile the approval packet
    3. Return the final recommendation
    """
    try:
        vendor = get_vendor(vendor_id)
        if not vendor:
            return {"status": "error", "error": f"Vendor {vendor_id} not found"}

        # Update state
        save_state(vendor_id, {
            "current_phase": "supervisor",
            "current_agent": "supervisor",
            "progress_percentage": 40,
            "messages": [],
            "errors": [],
        })

        agent = create_supervisor_agent()

        task = f"""A vendor onboarding request has been received and documents have been processed.

VENDOR DETAILS:
- Vendor ID: {vendor_id}
- Name: {vendor.get('name', 'Unknown')}
- Type: {vendor.get('vendor_type', 'Unknown')}
- Contract Value: ${vendor.get('contract_value', 0)}

The Document Intake Agent has already processed the uploaded documents.

Now please:
1. Delegate the security review to the Security Agent using delegate_to_security_agent with vendor_id "{vendor_id}"
2. After delegation, compile the approval packet using compile_approval_packet with vendor_id "{vendor_id}"
3. Provide the final recommendation for this vendor

Note: Compliance, Financial, and Evidence agents are not yet available (Phase 2).
"""

        result = agent.invoke({
            "messages": [HumanMessage(content=task)],
        })

        # Extract response
        final_messages = result.get("messages", [])
        final_response = ""
        if final_messages:
            last_msg = final_messages[-1]
            final_response = (
                last_msg.content
                if hasattr(last_msg, "content")
                else str(last_msg)
            )

        # Update state to completed
        save_state(vendor_id, {
            "current_phase": "done",
            "current_agent": "",
            "progress_percentage": 100,
        })

        update_vendor(vendor_id, {"status": "review_completed"})

        logger.info(f"Supervisor completed for vendor {vendor_id}")

        return {
            "status": "success",
            "vendor_id": vendor_id,
            "agent_response": final_response,
        }

    except Exception as e:
        logger.error(f"Supervisor failed for vendor {vendor_id}: {e}")
        save_state(vendor_id, {
            "current_phase": "error",
            "errors": [str(e)],
        })
        return {
            "status": "error",
            "vendor_id": vendor_id,
            "error": str(e),
        }

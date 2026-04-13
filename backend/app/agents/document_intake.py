"""
Document Intake Agent — autonomous document processing with ReAct pattern.
"""
import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from app.core.llm import get_llm
from app.tools.intake_tools import INTAKE_TOOLS

logger = logging.getLogger(__name__)

INTAKE_SYSTEM_PROMPT = """You are the Document Intake Agent for a Vendor Risk Assessment system.

Your role is to autonomously process uploaded vendor documents:
1. Parse each document using the appropriate parser (parse_pdf, parse_docx, parse_excel, or ocr_scan)
2. Classify each document into a category (SOC2, ISO27001, Insurance, DPA, etc.)
3. Extract vendor metadata (company name, address, contacts, industry)
4. Extract important dates (expiration, effective, issue dates)
5. Store the processed metadata in the database

WORKFLOW:
- For each document file path provided, determine the file type from its extension
- Use the appropriate parsing tool (pdf → parse_pdf, docx → parse_docx, xlsx → parse_excel, images → ocr_scan)
- Once you have the text, classify it with classify_document
- Extract vendor metadata with extract_vendor_metadata
- Extract dates with extract_dates
- Store everything with store_document_metadata

RULES:
- Process ALL documents provided, do not skip any
- If a parser fails, try ocr_scan as a fallback
- Always classify every document
- Always store the results in the database
- Report any errors but continue processing remaining documents
- Be thorough and systematic

When done, provide a summary of all documents processed with their classifications.
"""


def create_intake_agent():
    """Create a Document Intake Agent using the ReAct pattern."""
    llm = get_llm()
    agent = create_react_agent(
        llm,
        INTAKE_TOOLS,
        prompt=INTAKE_SYSTEM_PROMPT,
    )
    return agent


def run_intake_agent(vendor_id: str, file_paths: list[str]) -> dict:
    """
    Run the Document Intake Agent on a list of files.

    Args:
        vendor_id: The vendor UUID
        file_paths: List of file paths to process

    Returns:
        dict with results or errors
    """
    try:
        agent = create_intake_agent()

        # Build the task message
        files_list = "\n".join(f"- {fp}" for fp in file_paths)
        task = f"""Process the following vendor documents for vendor_id: {vendor_id}

Files to process:
{files_list}

For each file:
1. Parse it using the correct tool based on file extension (.pdf → parse_pdf, .docx → parse_docx, .xlsx/.xls → parse_excel, .jpg/.png/.tiff → ocr_scan)
2. Classify the document content
3. Extract vendor metadata from the content
4. Extract important dates
5. Store the metadata in the database using store_document_metadata with vendor_id "{vendor_id}"

Process all files and provide a final summary."""

        result = agent.invoke({
            "messages": [HumanMessage(content=task)],
        })

        # Extract the final message content
        final_messages = result.get("messages", [])
        final_response = ""
        if final_messages:
            last_msg = final_messages[-1]
            final_response = (
                last_msg.content
                if hasattr(last_msg, "content")
                else str(last_msg)
            )

        logger.info(
            f"Intake agent completed for vendor {vendor_id}: "
            f"processed {len(file_paths)} files"
        )

        return {
            "status": "success",
            "vendor_id": vendor_id,
            "files_processed": len(file_paths),
            "agent_response": final_response,
        }

    except Exception as e:
        logger.error(f"Intake agent failed for vendor {vendor_id}: {e}")
        return {
            "status": "error",
            "vendor_id": vendor_id,
            "error": str(e),
        }

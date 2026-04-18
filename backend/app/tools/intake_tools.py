"""
Document Intake Agent tools — 8 tools for parsing, classifying, and extracting data.
"""
import io
import os
import re
import json
import logging
from datetime import datetime
from typing import Optional

import pdfplumber
from docx import Document as DocxDocument
import openpyxl
import pandas as pd
from langchain_core.tools import tool

from app.core.db import (
    create_document,
    update_document,
    check_duplicate_document,
    upload_file,
)
from app.core.llm import get_llm

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Tool 1: parse_pdf
# ═══════════════════════════════════════════════════════════════════

@tool
def parse_pdf(file_path: str) -> str:
    """
    Extract text and tables from a PDF document using pdfplumber.
    Returns the extracted text content along with any tables found.

    Args:
        file_path: Path to the PDF file on disk.
    """
    try:
        all_text = []
        all_tables = []

        with pdfplumber.open(file_path) as pdf:
            metadata = {
                "num_pages": len(pdf.pages),
                "metadata": pdf.metadata or {},
            }

            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                all_text.append(f"--- Page {i + 1} ---\n{text}")

                tables = page.extract_tables()
                if tables:
                    for t_idx, table in enumerate(tables):
                        all_tables.append(
                            f"[Table on page {i + 1}, #{t_idx + 1}]: "
                            + json.dumps(table)
                        )

        combined = "\n".join(all_text)
        if all_tables:
            combined += "\n\n=== TABLES ===\n" + "\n".join(all_tables)

        result = json.dumps({
            "status": "success",
            "text": combined[:50000],  # Limit to 50k chars
            "num_pages": metadata["num_pages"],
            "has_tables": len(all_tables) > 0,
            "table_count": len(all_tables),
        })
        logger.info(f"Parsed PDF: {file_path} ({metadata['num_pages']} pages)")
        return result

    except Exception as e:
        logger.error(f"Failed to parse PDF {file_path}: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 2: parse_docx
# ═══════════════════════════════════════════════════════════════════

@tool
def parse_docx(file_path: str) -> str:
    """
    Extract text and tables from a DOCX (Word) document.

    Args:
        file_path: Path to the DOCX file on disk.
    """
    try:
        doc = DocxDocument(file_path)

        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs)

        tables_data = []
        for t_idx, table in enumerate(doc.tables):
            rows = []
            for row in table.rows:
                rows.append([cell.text for cell in row.cells])
            tables_data.append(f"[Table #{t_idx + 1}]: {json.dumps(rows)}")

        combined = text
        if tables_data:
            combined += "\n\n=== TABLES ===\n" + "\n".join(tables_data)

        result = json.dumps({
            "status": "success",
            "text": combined[:50000],
            "num_paragraphs": len(paragraphs),
            "table_count": len(tables_data),
        })
        logger.info(f"Parsed DOCX: {file_path}")
        return result

    except Exception as e:
        logger.error(f"Failed to parse DOCX {file_path}: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 3: parse_excel
# ═══════════════════════════════════════════════════════════════════

@tool
def parse_excel(file_path: str) -> str:
    """
    Extract data from all sheets of an Excel file.

    Args:
        file_path: Path to the Excel file on disk.
    """
    try:
        excel_data = {}
        xls = pd.ExcelFile(file_path)

        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            excel_data[sheet_name] = {
                "columns": df.columns.tolist(),
                "row_count": len(df),
                "data_preview": df.head(20).to_dict(orient="records"),
                "summary": df.describe(include="all").to_dict()
                if not df.empty
                else {},
            }

        result = json.dumps(
            {
                "status": "success",
                "sheet_count": len(xls.sheet_names),
                "sheets": excel_data,
            },
            default=str,
        )
        logger.info(
            f"Parsed Excel: {file_path} ({len(xls.sheet_names)} sheets)"
        )
        return result

    except Exception as e:
        logger.error(f"Failed to parse Excel {file_path}: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 4: classify_document
# ═══════════════════════════════════════════════════════════════════

@tool
def classify_document(text: str) -> str:
    """
    Classify a document into a category using LLM analysis.
    Categories: SOC2, ISO27001, Insurance, DPA, Financial_Statements,
    BCP, Pen_Test_Report, Security_Questionnaire, Privacy_Policy, Other.

    Args:
        text: Extracted text content of the document (first 4000 chars recommended).
    """
    try:
        llm = get_llm()
        prompt = f"""You are a document classification expert for vendor risk assessment.

Classify the following document text into exactly ONE of these categories:
- SOC2 (SOC 2 Type 1 or Type 2 audit report)
- ISO27001 (ISO 27001 certification or audit)
- Insurance (General liability, cyber, E&O insurance certificates)
- DPA (Data Processing Agreement / Data Protection Agreement)
- Financial_Statements (Balance sheet, P&L, income statements)
- BCP (Business Continuity Plan / Disaster Recovery)
- Pen_Test_Report (Penetration testing report)
- Security_Questionnaire (Security assessment questionnaire responses)
- Privacy_Policy (Privacy policy document)
- Other (None of the above)

Respond in JSON format ONLY:
{{"classification": "<CATEGORY>", "confidence": <0.0-1.0>, "reasoning": "<brief explanation>"}}

Document text (first 4000 characters):
{text[:4000]}
"""
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        # Try to extract JSON from response
        try:
            # Find JSON in response
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return json.dumps({
                    "status": "success",
                    "classification": parsed.get("classification", "Other"),
                    "confidence": parsed.get("confidence", 0.5),
                    "reasoning": parsed.get("reasoning", ""),
                })
        except json.JSONDecodeError:
            pass

        return json.dumps({
            "status": "success",
            "classification": "Other",
            "confidence": 0.3,
            "reasoning": "Could not parse LLM response, defaulting to Other",
        })

    except Exception as e:
        logger.error(f"Document classification failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 5: extract_vendor_metadata
# ═══════════════════════════════════════════════════════════════════

@tool
def extract_vendor_metadata(text: str) -> str:
    """
    Extract structured vendor metadata from document text using LLM.
    Extracts: company name, address, contact, industry, employee count.

    Args:
        text: Extracted text from a vendor document (first 4000 chars recommended).
    """
    try:
        llm = get_llm()
        prompt = f"""Extract vendor/company metadata from this document text.

Return JSON ONLY with these fields (use null for missing):
{{
    "company_name": "string",
    "address": "string",
    "contact_name": "string",
    "contact_email": "string",
    "phone": "string",
    "industry": "string",
    "employee_count": number or null,
    "website": "string",
    "domain": "string"
}}

Document text (first 4000 characters):
{text[:4000]}
"""
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        try:
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return json.dumps({"status": "success", "metadata": parsed})
        except json.JSONDecodeError:
            pass

        return json.dumps({
            "status": "success",
            "metadata": {},
            "note": "Could not extract metadata from LLM response",
        })

    except Exception as e:
        logger.error(f"Vendor metadata extraction failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 6: extract_dates
# ═══════════════════════════════════════════════════════════════════

@tool
def extract_dates(text: str) -> str:
    """
    Extract important dates from document text using regex and LLM.
    Finds: expiration dates, effective dates, issue dates, audit period dates.

    Args:
        text: Extracted document text to search for dates.
    """
    try:
        # Phase 1: Regex extraction for common date patterns
        date_patterns = [
            r'(?:expir(?:ation|es?|y)\s*(?:date)?[\s:]*)'
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:effective\s*(?:date)?[\s:]*)'
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:issue(?:d)?\s*(?:date)?[\s:]*)'
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:valid\s*(?:until|through|to)\s*[\s:]*)'
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            # ISO format
            r'(\d{4}-\d{2}-\d{2})',
            # Written format
            r'(\w+\s+\d{1,2},?\s+\d{4})',
        ]

        regex_dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text[:10000], re.IGNORECASE)
            regex_dates.extend(matches)

        # Phase 2: LLM extraction for contextual dates
        llm = get_llm()
        prompt = f"""Extract all important dates from this document text.

Return JSON ONLY:
{{
    "expiration_dates": ["YYYY-MM-DD", ...],
    "effective_dates": ["YYYY-MM-DD", ...],
    "issue_dates": ["YYYY-MM-DD", ...],
    "audit_period_start": "YYYY-MM-DD" or null,
    "audit_period_end": "YYYY-MM-DD" or null,
    "other_dates": [{{"label": "description", "date": "YYYY-MM-DD"}}]
}}

Document text (excerpt):
{text[:3000]}
"""
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        llm_dates = {}
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                llm_dates = json.loads(json_match.group())
        except (json.JSONDecodeError, AttributeError):
            pass

        return json.dumps({
            "status": "success",
            "regex_dates": regex_dates[:20],
            "llm_dates": llm_dates,
        })

    except Exception as e:
        logger.error(f"Date extraction failed: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 7: store_document_metadata
# ═══════════════════════════════════════════════════════════════════

@tool
def store_document_metadata(
    vendor_id: str,
    file_name: str,
    file_type: str,
    classification: str,
    classification_confidence: float,
    extracted_text_summary: str,
    extracted_metadata: str,
    extracted_dates: str,
) -> str:
    """
    Store processed document metadata in the database.

    Args:
        vendor_id: The vendor UUID to associate the document with.
        file_name: Original file name.
        file_type: File extension (pdf, docx, xlsx).
        classification: Document classification category.
        classification_confidence: Classification confidence score (0-1).
        extracted_text_summary: Summary or first portion of extracted text.
        extracted_metadata: JSON string of extracted metadata.
        extracted_dates: JSON string of extracted dates.
    """
    try:
        # Check for duplicates
        if check_duplicate_document(vendor_id, file_name):
            return json.dumps({
                "status": "duplicate",
                "message": f"Document '{file_name}' already exists for this vendor.",
            })

        # Parse JSON strings
        try:
            meta = json.loads(extracted_metadata) if isinstance(extracted_metadata, str) else extracted_metadata
        except json.JSONDecodeError:
            meta = {"raw": extracted_metadata}

        try:
            dates = json.loads(extracted_dates) if isinstance(extracted_dates, str) else extracted_dates
        except json.JSONDecodeError:
            dates = {"raw": extracted_dates}

        doc_data = {
            "vendor_id": vendor_id,
            "file_name": file_name,
            "file_type": file_type,
            "classification": classification,
            "classification_confidence": classification_confidence,
            "extracted_text": extracted_text_summary[:10000],
            "extracted_metadata": meta,
            "extracted_dates": dates,
            "processing_status": "completed",
        }

        result = create_document(doc_data)
        return json.dumps({
            "status": "success",
            "document_id": result.get("id", ""),
            "message": f"Document '{file_name}' stored successfully.",
        })

    except Exception as e:
        logger.error(f"Failed to store document metadata: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Tool 8: ocr_scan
# ═══════════════════════════════════════════════════════════════════

@tool
def ocr_scan(file_path: str) -> str:
    """
    Perform OCR on an image or scanned document using EasyOCR.
    Supports multi-language text extraction.

    Args:
        file_path: Path to the image file (PNG, JPG, TIFF, etc.).
    """
    try:
        import easyocr

        reader = easyocr.Reader(["en"], gpu=False)
        results = reader.readtext(file_path)

        extracted_lines = []
        total_confidence = 0.0

        for bbox, text, confidence in results:
            extracted_lines.append(text)
            total_confidence += confidence

        avg_confidence = (
            total_confidence / len(results) if results else 0.0
        )
        full_text = "\n".join(extracted_lines)

        return json.dumps({
            "status": "success",
            "text": full_text[:50000],
            "line_count": len(extracted_lines),
            "average_confidence": round(avg_confidence, 4),
            "quality": (
                "high" if avg_confidence > 0.8
                else "medium" if avg_confidence > 0.5
                else "low"
            ),
        })

    except Exception as e:
        logger.error(f"OCR scan failed for {file_path}: {e}")
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# Collect all intake tools
# ═══════════════════════════════════════════════════════════════════

INTAKE_TOOLS = [
    parse_pdf,
    parse_docx,
    parse_excel,
    classify_document,
    extract_vendor_metadata,
    extract_dates,
    store_document_metadata,
    ocr_scan,
]

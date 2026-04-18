from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from backend.core.config import get_settings
from backend.tools.base import stable_score


DOC_TYPES = [
    "GST Certificate",
    "PAN Card",
    "Incorporation Certificate",
    "Cancelled Cheque",
    "SOC 2 Type II",
    "ISO 27001",
    "Penetration Test Report",
    "NDA",
    "HIPAA Attestation",
    "BAA",
    "ePHI Data Flow Map",
    "Subprocessor List",
    "Cyber Insurance",
    "Breach Policy",
]


@dataclass(slots=True)
class ClassificationResult:
    classification: str
    confidence: float
    key_fields_found: list[str]
    reasoning: str
    provider: str


def classify_document(file_name: str, extracted_text: str) -> ClassificationResult:
    text = f"{file_name}\n{extracted_text}".lower()
    mapping = {
        "gst": "GST Certificate",
        "pan": "PAN Card",
        "incorporation": "Incorporation Certificate",
        "cheque": "Cancelled Cheque",
        "soc": "SOC 2 Type II",
        "iso": "ISO 27001",
        "penetration": "Penetration Test Report",
        "pentest": "Penetration Test Report",
        "nda": "NDA",
        "hipaa": "HIPAA Attestation",
        "business associate": "BAA",
        "baa": "BAA",
        "flow": "ePHI Data Flow Map",
        "subprocessor": "Subprocessor List",
        "insurance": "Cyber Insurance",
        "breach": "Breach Policy",
    }
    for needle, label in mapping.items():
        if needle in text:
            fields = sorted(
                {
                    token
                    for token in re.findall(
                        r"\b(?:gst|pan|hipaa|breach|encryption|subprocessor|soc|iso)\b",
                        text,
                    )
                }
            )
            return ClassificationResult(
                classification=label,
                confidence=stable_score(label, file_name),
                key_fields_found=fields,
                reasoning="Heuristic keyword classifier used because no live OpenAI call was made.",
                provider="heuristic",
            )
    return ClassificationResult(
        classification="Unclassified",
        confidence=0.55,
        key_fields_found=[],
        reasoning="No known document markers were found.",
        provider="heuristic",
    )


def generate_embedding_vector(text: str, dimensions: int | None = None) -> list[float]:
    dims = dimensions or get_settings().embedding_dimensions
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < dims:
        for byte in digest:
            values.append(round(byte / 255, 6))
            if len(values) >= dims:
                break
        digest = hashlib.sha256(digest).digest()
    return values


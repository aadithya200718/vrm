from __future__ import annotations

from backend.core.repository import RepositoryType


def query_compliance_knowledge(
    repo: RepositoryType,
    query: str,
    vendor_id: str | None = None,
) -> dict:
    sources = []
    if vendor_id:
        baa = repo.get_baa_record(vendor_id)
        if baa:
            sources.append(
                {
                    "type": "baa_record",
                    "status": baa.status,
                    "missing_clauses": baa.clauses_missing,
                }
            )
    return {
        "answer": f"Retrieved {len(sources)} vendor-specific compliance source(s) for query: {query}",
        "sources": sources,
    }

"""
Supabase database client and helper functions.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from supabase import create_client, Client
from app.config import get_settings

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """Get or create a Supabase client singleton."""
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        _supabase_client = create_client(settings.supabase_url, settings.supabase_key)
        logger.info("Supabase client initialized")
    return _supabase_client


# ── Vendor Operations ──────────────────────────────────────────────

def create_vendor(data: dict) -> dict:
    """Insert a new vendor record."""
    sb = get_supabase()
    result = sb.table("vendors").insert(data).execute()
    return result.data[0] if result.data else {}


def get_vendor(vendor_id: str) -> Optional[dict]:
    """Retrieve a vendor by ID."""
    sb = get_supabase()
    result = sb.table("vendors").select("*").eq("id", vendor_id).execute()
    return result.data[0] if result.data else None


def update_vendor(vendor_id: str, data: dict) -> dict:
    """Update a vendor record."""
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    sb = get_supabase()
    result = sb.table("vendors").update(data).eq("id", vendor_id).execute()
    return result.data[0] if result.data else {}


# ── Document Operations ────────────────────────────────────────────

def create_document(data: dict) -> dict:
    """Insert a new document record."""
    sb = get_supabase()
    result = sb.table("documents").insert(data).execute()
    return result.data[0] if result.data else {}


def get_documents_for_vendor(vendor_id: str) -> list[dict]:
    """Get all documents for a vendor."""
    sb = get_supabase()
    result = sb.table("documents").select("*").eq("vendor_id", vendor_id).execute()
    return result.data or []


def update_document(doc_id: str, data: dict) -> dict:
    """Update a document record."""
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    sb = get_supabase()
    result = sb.table("documents").update(data).eq("id", doc_id).execute()
    return result.data[0] if result.data else {}


def check_duplicate_document(vendor_id: str, file_name: str) -> bool:
    """Check if a document with the same name already exists for a vendor."""
    sb = get_supabase()
    result = (
        sb.table("documents")
        .select("id")
        .eq("vendor_id", vendor_id)
        .eq("file_name", file_name)
        .execute()
    )
    return len(result.data) > 0


# ── Security Review Operations ─────────────────────────────────────

def create_security_review(data: dict) -> dict:
    """Insert a new security review record."""
    sb = get_supabase()
    result = sb.table("security_reviews").insert(data).execute()
    return result.data[0] if result.data else {}


def get_security_review(vendor_id: str) -> Optional[dict]:
    """Get the latest security review for a vendor."""
    sb = get_supabase()
    result = (
        sb.table("security_reviews")
        .select("*")
        .eq("vendor_id", vendor_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def update_security_review(review_id: str, data: dict) -> dict:
    """Update a security review record."""
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    sb = get_supabase()
    result = sb.table("security_reviews").update(data).eq("id", review_id).execute()
    return result.data[0] if result.data else {}


# ── Audit Log Operations ──────────────────────────────────────────

def create_audit_log(
    vendor_id: Optional[str],
    agent_name: str,
    action: str,
    tool_name: Optional[str] = None,
    input_data: Optional[dict] = None,
    output_data: Optional[dict] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None,
    token_usage: Optional[dict] = None,
) -> dict:
    """Create an audit log entry."""
    sb = get_supabase()
    log_data = {
        "vendor_id": vendor_id,
        "agent_name": agent_name,
        "action": action,
        "tool_name": tool_name,
        "input_data": input_data or {},
        "output_data": output_data or {},
        "status": status,
        "error_message": error_message,
        "duration_ms": duration_ms,
        "token_usage": token_usage or {},
    }
    result = sb.table("audit_logs").insert(log_data).execute()
    return result.data[0] if result.data else {}


def get_audit_logs(vendor_id: str) -> list[dict]:
    """Get all audit logs for a vendor."""
    sb = get_supabase()
    result = (
        sb.table("audit_logs")
        .select("*")
        .eq("vendor_id", vendor_id)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


# ── Policy Operations ─────────────────────────────────────────────

def create_policy(data: dict) -> dict:
    """Insert a new policy record."""
    sb = get_supabase()
    result = sb.table("policies").insert(data).execute()
    return result.data[0] if result.data else {}


def get_active_policies(category: str = "security") -> list[dict]:
    """Get all active policies for a category."""
    sb = get_supabase()
    result = (
        sb.table("policies")
        .select("*")
        .eq("category", category)
        .eq("is_active", True)
        .execute()
    )
    return result.data or []


# ── Breach Operations ─────────────────────────────────────────────

def search_breaches(company_name: str, domain: Optional[str] = None) -> list[dict]:
    """Search for breaches by company name or domain."""
    sb = get_supabase()
    query = sb.table("breaches").select("*")
    # Search by company name (case-insensitive partial match)
    query = query.ilike("company_name", f"%{company_name}%")
    result = query.execute()
    results = result.data or []

    if domain:
        domain_result = (
            sb.table("breaches")
            .select("*")
            .ilike("domain", f"%{domain}%")
            .execute()
        )
        # Merge unique results
        existing_ids = {r["id"] for r in results}
        for r in domain_result.data or []:
            if r["id"] not in existing_ids:
                results.append(r)

    return results


# ── Vendor Review State Operations ─────────────────────────────────

def save_review_state(vendor_id: str, state_data: dict, current_phase: str) -> dict:
    """Save or update the vendor review state."""
    sb = get_supabase()
    # Check if exists
    existing = (
        sb.table("vendor_review_states")
        .select("id")
        .eq("vendor_id", vendor_id)
        .execute()
    )
    payload = {
        "vendor_id": vendor_id,
        "state_data": state_data,
        "current_phase": current_phase,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if existing.data:
        result = (
            sb.table("vendor_review_states")
            .update(payload)
            .eq("vendor_id", vendor_id)
            .execute()
        )
    else:
        result = sb.table("vendor_review_states").insert(payload).execute()
    return result.data[0] if result.data else {}


def get_review_state(vendor_id: str) -> Optional[dict]:
    """Get the current review state for a vendor."""
    sb = get_supabase()
    result = (
        sb.table("vendor_review_states")
        .select("*")
        .eq("vendor_id", vendor_id)
        .execute()
    )
    return result.data[0] if result.data else None


# ── File Storage Operations ────────────────────────────────────────

def upload_file(vendor_id: str, file_name: str, file_content: bytes) -> str:
    """Upload a file to Supabase Storage and return its path."""
    sb = get_supabase()
    storage_path = f"{vendor_id}/{file_name}"
    sb.storage.from_("vendor-documents").upload(
        storage_path, file_content
    )
    return storage_path


def get_file_url(storage_path: str) -> str:
    """Get a signed URL for a file in Supabase Storage."""
    sb = get_supabase()
    result = sb.storage.from_("vendor-documents").create_signed_url(
        storage_path, 3600  # 1 hour expiry
    )
    return result.get("signedURL", "")


# ── Health Check ───────────────────────────────────────────────────

def check_db_health() -> bool:
    """Check if the database connection is healthy."""
    try:
        sb = get_supabase()
        sb.table("vendors").select("id").limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

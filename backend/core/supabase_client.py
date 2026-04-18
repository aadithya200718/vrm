from __future__ import annotations

from functools import lru_cache
from typing import Any

from backend.core.config import get_settings


@lru_cache(maxsize=2)
def get_supabase_client(service_role: bool = False) -> Any | None:
    settings = get_settings()
    url = settings.supabase_url
    key = (
        settings.supabase_service_role_key if service_role else settings.supabase_key
    )
    if not url or not key:
        return None

    try:
        from supabase import create_client
    except ImportError:
        return None

    return create_client(url, key)


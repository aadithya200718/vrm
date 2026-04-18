"""
Redis-backed state management for active vendor review workflows.
"""
import json
import logging
from typing import Optional, Any
import redis
from app.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None

STATE_TTL = 7 * 24 * 3600  # 7 days


def get_redis() -> redis.Redis:
    """Get or create a Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.Redis.from_url(
            settings.redis_url, decode_responses=True
        )
        logger.info("Redis client initialized")
    return _redis_client


def _state_key(vendor_id: str) -> str:
    return f"vrm:review_state:{vendor_id}"


def save_state(vendor_id: str, state: dict) -> None:
    """Persist a vendor review state to Redis."""
    r = get_redis()
    r.setex(_state_key(vendor_id), STATE_TTL, json.dumps(state, default=str))
    logger.debug(f"State saved for vendor {vendor_id}")


def load_state(vendor_id: str) -> Optional[dict]:
    """Load a vendor review state from Redis."""
    r = get_redis()
    data = r.get(_state_key(vendor_id))
    if data:
        return json.loads(data)
    return None


def delete_state(vendor_id: str) -> None:
    """Delete a vendor review state from Redis."""
    r = get_redis()
    r.delete(_state_key(vendor_id))


def update_state_field(vendor_id: str, field: str, value: Any) -> None:
    """Update a single field in the vendor review state."""
    state = load_state(vendor_id) or {}
    state[field] = value
    save_state(vendor_id, state)


def append_message(vendor_id: str, agent: str, content: str) -> None:
    """Append a message to the state's message history."""
    state = load_state(vendor_id) or {}
    messages = state.get("messages", [])
    messages.append({"agent": agent, "content": content})
    state["messages"] = messages
    save_state(vendor_id, state)


def append_error(vendor_id: str, error: str) -> None:
    """Append an error to the state's error list."""
    state = load_state(vendor_id) or {}
    errors = state.get("errors", [])
    errors.append(error)
    state["errors"] = errors
    save_state(vendor_id, state)


def check_redis_health() -> bool:
    """Check if Redis is reachable."""
    try:
        r = get_redis()
        return r.ping()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False

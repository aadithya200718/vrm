"""
Base tool framework with standardized interface, logging, retry, and tracing.
"""
import time
import logging
import functools
from typing import Any, Callable
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.db import create_audit_log

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all agent tools."""

    _tools: dict[str, dict] = {}

    @classmethod
    def register(cls, name: str, description: str, agent: str):
        """Decorator to register a tool function."""
        def decorator(func: Callable):
            cls._tools[name] = {
                "name": name,
                "description": description,
                "agent": agent,
                "function": func,
            }

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper
        return decorator

    @classmethod
    def get_tool(cls, name: str) -> dict:
        return cls._tools.get(name, {})

    @classmethod
    def get_tools_for_agent(cls, agent: str) -> list[dict]:
        return [t for t in cls._tools.values() if t["agent"] == agent]

    @classmethod
    def list_all(cls) -> list[str]:
        return list(cls._tools.keys())


def traced_tool(vendor_id: str | None = None, agent_name: str = "unknown"):
    """
    Decorator that wraps a tool call with:
    - Timing
    - Structured logging
    - Audit trail entry
    - Error handling
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tool_name = func.__name__
            start = time.time()
            logger.info(f"[{agent_name}] Tool '{tool_name}' invoked")

            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start) * 1000)
                logger.info(
                    f"[{agent_name}] Tool '{tool_name}' completed in {duration_ms}ms"
                )

                # Record audit log
                try:
                    vid = kwargs.get("vendor_id") or vendor_id
                    create_audit_log(
                        vendor_id=vid,
                        agent_name=agent_name,
                        action=f"tool_call:{tool_name}",
                        tool_name=tool_name,
                        input_data={"args_summary": str(kwargs.keys()) if kwargs else str(len(args))},
                        output_data={"result_type": type(result).__name__},
                        status="success",
                        duration_ms=duration_ms,
                    )
                except Exception:
                    pass  # Don't fail the tool if audit logging fails

                return result

            except Exception as e:
                duration_ms = int((time.time() - start) * 1000)
                logger.error(
                    f"[{agent_name}] Tool '{tool_name}' failed after {duration_ms}ms: {e}"
                )
                try:
                    vid = kwargs.get("vendor_id") or vendor_id
                    create_audit_log(
                        vendor_id=vid,
                        agent_name=agent_name,
                        action=f"tool_call:{tool_name}",
                        tool_name=tool_name,
                        status="error",
                        error_message=str(e),
                        duration_ms=duration_ms,
                    )
                except Exception:
                    pass
                raise

        return wrapper
    return decorator


def with_retry(max_attempts: int = 3, min_wait: float = 1, max_wait: float = 10):
    """Decorator to add retry logic to a tool function."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=min_wait, max=max_wait),
        reraise=True,
    )

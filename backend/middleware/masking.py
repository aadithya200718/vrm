from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from backend.core.config import get_settings
from backend.models.enums import Role


def _mask_payload(value: Any, hidden_fields: set[str]) -> Any:
    if isinstance(value, Mapping):
        masked = {}
        for key, item in value.items():
            if key in hidden_fields:
                continue
            masked[key] = _mask_payload(item, hidden_fields)
        return masked
    if isinstance(value, list):
        return [_mask_payload(item, hidden_fields) for item in value]
    return value


class MaskSensitiveFieldsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if not isinstance(response, JSONResponse):
            return response

        auth_context = getattr(request.state, "auth_context", None)
        if auth_context and auth_context.role in {Role.ADMIN, Role.SYSTEM}:
            return response

        payload = response.body
        if not payload:
            return response
        try:
            parsed = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return response
        return JSONResponse(
            content=_mask_payload(parsed, set(get_settings().pii_mask_fields)),
            status_code=response.status_code,
            headers=dict(response.headers),
        )

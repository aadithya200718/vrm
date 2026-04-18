from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import jwt
from fastapi import HTTPException, Request, status

from backend.core.config import get_settings
from backend.models.enums import Role


@dataclass(slots=True)
class AuthContext:
    email: str
    role: Role
    token: str


def _parse_dev_token(token: str) -> AuthContext | None:
    if not token.startswith("dev-role:"):
        return None
    parts = token.split(":")
    if len(parts) < 3:
        return None
    _, role, email = parts[:3]
    return AuthContext(email=email, role=Role(role), token=token)


def decode_access_token(token: str) -> AuthContext:
    settings = get_settings()

    if settings.allow_dev_auth_bypass:
        dev_context = _parse_dev_token(token)
        if dev_context:
            return dev_context

    if not settings.jwt_secret and not settings.jwt_public_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT validation is not configured",
        )

    key = settings.jwt_public_key or settings.jwt_secret or ""
    try:
        payload = jwt.decode(
            token,
            key=key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp"]},
            audience=None,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid JWT: {exc}",
        ) from exc

    role_value = payload.get("role") or payload.get("app_metadata", {}).get("role")
    email = payload.get("email") or payload.get("sub")
    if not role_value or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT missing required claims",
        )
    return AuthContext(email=email, role=Role(role_value), token=token)


def get_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    return auth_header.removeprefix("Bearer ").strip()


def require_roles(request: Request, allowed_roles: Iterable[Role]) -> AuthContext:
    token = get_bearer_token(request)
    context = decode_access_token(token)
    if context.role not in set(allowed_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {context.role.value} is not allowed",
        )
    return context


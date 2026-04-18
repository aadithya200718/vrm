from __future__ import annotations

from fastapi import Depends, Request

from backend.core.auth import AuthContext, require_roles
from backend.core.services import VendorOnboardingService, get_service
from backend.models.enums import Role


def service_dependency() -> VendorOnboardingService:
    return get_service()


def auth_dependency(request: Request) -> AuthContext:
    context = require_roles(
        request,
        {
            Role.EMPLOYEE,
            Role.LEGAL,
            Role.FINANCE,
            Role.IT,
            Role.COMPLIANCE_OFFICER,
            Role.ADMIN,
            Role.PROCUREMENT,
        },
    )
    request.state.auth_context = context
    return context


def employee_only(request: Request) -> AuthContext:
    context = require_roles(request, {Role.EMPLOYEE, Role.ADMIN, Role.PROCUREMENT})
    request.state.auth_context = context
    return context


def procurement_only(request: Request) -> AuthContext:
    context = require_roles(request, {Role.ADMIN, Role.PROCUREMENT})
    request.state.auth_context = context
    return context


def approver_roles(*roles: Role):
    def _dependency(request: Request) -> AuthContext:
        context = require_roles(request, set(roles) | {Role.ADMIN})
        request.state.auth_context = context
        return context

    return _dependency


ServiceDep = Depends(service_dependency)
AuthDep = Depends(auth_dependency)


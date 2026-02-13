"""API v1 router - aggregates all controllers"""
from fastapi import APIRouter
from app.presentation.api.v1.controllers import (
    contact_controller,
    company_controller,
    address_controller,
    lookup_controller,
)

# Legacy endpoints (to be refactored to clean architecture)
from app.api.v1.endpoints import (
    auth,
    tenants,
    roles,
    companies,
    supplies,
    orders,
    manufacturing,
    shipments,
    departments
)

api_router = APIRouter()

# New clean architecture endpoints
api_router.include_router(
    contact_controller.router,
    prefix="/contacts",
    tags=["contacts"]
)

api_router.include_router(
    company_controller.router,
    prefix="/companies-v2",  # Use different prefix to avoid conflict with legacy
    tags=["companies-v2"]
)

api_router.include_router(
    address_controller.router,
    prefix="",  # No prefix since routes include /companies/{id}/addresses
    tags=["addresses"]
)

api_router.include_router(
    lookup_controller.router,
    prefix="/lookup-values",
    tags=["lookup-values"]
)

# Legacy endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(supplies.router, prefix="/supplies", tags=["supplies"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(manufacturing.router, prefix="/manufacturing", tags=["manufacturing"])
api_router.include_router(shipments.router, prefix="/shipments", tags=["shipments"])
api_router.include_router(departments.router, prefix="/departments", tags=["departments"])

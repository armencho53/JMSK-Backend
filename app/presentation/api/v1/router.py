"""API v1 router - aggregates all controllers"""
from fastapi import APIRouter
from app.presentation.api.v1.controllers import customer_controller

# Import old endpoints temporarily for backward compatibility
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

# New layered architecture endpoints
api_router.include_router(
    customer_controller.router,
    prefix="/customers",
    tags=["customers"]
)

# Legacy endpoints (to be refactored)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(supplies.router, prefix="/supplies", tags=["supplies"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(manufacturing.router, prefix="/manufacturing", tags=["manufacturing"])
api_router.include_router(shipments.router, prefix="/shipments", tags=["shipments"])
api_router.include_router(departments.router, prefix="/departments", tags=["departments"])

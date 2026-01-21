from fastapi import APIRouter
from app.api.v1.endpoints import auth, tenants, roles, supplies, customers, companies, orders, manufacturing, shipments, departments

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(supplies.router, prefix="/supplies", tags=["supplies"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(manufacturing.router, prefix="/manufacturing", tags=["manufacturing"])
api_router.include_router(shipments.router, prefix="/shipments", tags=["shipments"])
api_router.include_router(departments.router, prefix="/departments", tags=["departments"])

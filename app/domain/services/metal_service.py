"""Metal business logic service"""
from typing import List
from sqlalchemy.orm import Session
from app.data.repositories.metal_repository import MetalRepository
from app.data.models.metal import Metal
from app.schemas.metal import MetalCreate, MetalUpdate, MetalResponse
from app.domain.enums import MetalType
from app.domain.exceptions import (
    ResourceNotFoundError,
    DuplicateResourceError,
)

# Default metals to seed for new tenants
# (code, name, metal_type, fine_percentage)
DEFAULT_METALS = [
    ("GOLD_24K", "Gold 24K", MetalType.GOLD, 0.999),
    ("GOLD_22K", "Gold 22K", MetalType.GOLD, 0.916),
    ("GOLD_18K", "Gold 18K", MetalType.GOLD, 0.750),
    ("GOLD_14K", "Gold 14K", MetalType.GOLD, 0.585),
    ("SILVER_925", "Silver 925", MetalType.SILVER, 0.925),
    ("PLATINUM", "Platinum", MetalType.PLATINUM, 0.950),
]


class MetalService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = MetalRepository(db)

    def get_all(self, tenant_id: int, include_inactive: bool = False) -> List[MetalResponse]:
        if include_inactive:
            metals = self.repository.get_all_with_inactive(tenant_id)
        else:
            metals = self.repository.get_active(tenant_id)
        return [MetalResponse.model_validate(m) for m in metals]

    def get_by_id(self, metal_id: int, tenant_id: int) -> MetalResponse:
        metal = self.repository.get_by_id(metal_id, tenant_id)
        if not metal:
            raise ResourceNotFoundError("Metal", metal_id)
        return MetalResponse.model_validate(metal)

    def get_by_code(self, code: str, tenant_id: int) -> Metal:
        metal = self.repository.get_by_code(code, tenant_id)
        if not metal:
            raise ResourceNotFoundError("Metal", code)
        return metal

    def create(self, data: MetalCreate, tenant_id: int) -> MetalResponse:
        normalized_code = data.code  # Already uppercased by schema validator

        if self.repository.code_exists(tenant_id, normalized_code):
            raise DuplicateResourceError("Metal", "code", normalized_code)

        metal = Metal(
            tenant_id=tenant_id,
            code=normalized_code,
            name=data.name,
            metal_type=data.metal_type,
            fine_percentage=data.fine_percentage,
            average_cost_per_gram=data.average_cost_per_gram,
        )
        metal = self.repository.create(metal)
        return MetalResponse.model_validate(metal)

    def update(self, metal_id: int, data: MetalUpdate, tenant_id: int) -> MetalResponse:
        metal = self.repository.get_by_id(metal_id, tenant_id)
        if not metal:
            raise ResourceNotFoundError("Metal", metal_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(metal, field, value)

        metal = self.repository.update(metal)
        return MetalResponse.model_validate(metal)

    def deactivate(self, metal_id: int, tenant_id: int) -> MetalResponse:
        metal = self.repository.get_by_id(metal_id, tenant_id)
        if not metal:
            raise ResourceNotFoundError("Metal", metal_id)

        metal.is_active = False
        metal = self.repository.update(metal)
        return MetalResponse.model_validate(metal)

    def seed_defaults(self, tenant_id: int) -> None:
        for code, name, metal_type, fine_percentage in DEFAULT_METALS:
            if not self.repository.code_exists(tenant_id, code):
                metal = Metal(
                    tenant_id=tenant_id,
                    code=code,
                    name=name,
                    metal_type=metal_type,
                    fine_percentage=fine_percentage,
                )
                self.repository.create(metal)

"""Safe supply repository for data access"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.data.repositories.base import BaseRepository
from app.data.models.safe_supply import SafeSupply


class SafeSupplyRepository(BaseRepository[SafeSupply]):
    def __init__(self, db: Session):
        super().__init__(SafeSupply, db)

    def get_or_create(
        self, tenant_id: int, metal_id: Optional[int], supply_type: str
    ) -> SafeSupply:
        record = (
            self.db.query(SafeSupply)
            .filter(
                SafeSupply.tenant_id == tenant_id,
                SafeSupply.metal_id == metal_id if metal_id is not None
                else SafeSupply.metal_id.is_(None),
                SafeSupply.supply_type == supply_type,
            )
            .first()
        )
        if not record:
            record = SafeSupply(
                tenant_id=tenant_id,
                metal_id=metal_id,
                supply_type=supply_type,
                quantity_grams=0.0,
            )
            self.db.add(record)
            self.db.flush()
        return record

    def get_all_for_tenant(self, tenant_id: int) -> List[SafeSupply]:
        return (
            self.db.query(SafeSupply)
            .filter(SafeSupply.tenant_id == tenant_id)
            .all()
        )

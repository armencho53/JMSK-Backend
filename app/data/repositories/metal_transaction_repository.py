"""Metal transaction repository for data access"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.data.repositories.base import BaseRepository
from app.data.models.metal_transaction import MetalTransaction


class MetalTransactionRepository(BaseRepository[MetalTransaction]):
    def __init__(self, db: Session):
        super().__init__(MetalTransaction, db)

    def get_filtered(
        self,
        tenant_id: int,
        company_id: Optional[int] = None,
        metal_id: Optional[int] = None,
        transaction_type: Optional[str] = None,
    ) -> List[MetalTransaction]:
        query = self.db.query(MetalTransaction).filter(
            MetalTransaction.tenant_id == tenant_id
        )
        if company_id is not None:
            query = query.filter(MetalTransaction.company_id == company_id)
        if metal_id is not None:
            query = query.filter(MetalTransaction.metal_id == metal_id)
        if transaction_type is not None:
            query = query.filter(MetalTransaction.transaction_type == transaction_type)
        return query.order_by(MetalTransaction.created_at.desc()).all()

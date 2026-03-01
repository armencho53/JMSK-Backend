"""Company metal balance repository for data access"""
from typing import List
from sqlalchemy.orm import Session
from app.data.repositories.base import BaseRepository
from app.data.models.company_metal_balance import CompanyMetalBalance


class CompanyMetalBalanceRepository(BaseRepository[CompanyMetalBalance]):
    def __init__(self, db: Session):
        super().__init__(CompanyMetalBalance, db)

    def get_or_create(
        self, tenant_id: int, company_id: int, metal_id: int
    ) -> CompanyMetalBalance:
        record = (
            self.db.query(CompanyMetalBalance)
            .filter(
                CompanyMetalBalance.tenant_id == tenant_id,
                CompanyMetalBalance.company_id == company_id,
                CompanyMetalBalance.metal_id == metal_id,
            )
            .first()
        )
        if not record:
            record = CompanyMetalBalance(
                tenant_id=tenant_id,
                company_id=company_id,
                metal_id=metal_id,
                balance_grams=0.0,
            )
            self.db.add(record)
            self.db.flush()
        return record

    def get_by_company(
        self, tenant_id: int, company_id: int
    ) -> List[CompanyMetalBalance]:
        return (
            self.db.query(CompanyMetalBalance)
            .filter(
                CompanyMetalBalance.tenant_id == tenant_id,
                CompanyMetalBalance.company_id == company_id,
            )
            .all()
        )

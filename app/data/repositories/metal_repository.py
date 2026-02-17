"""Metal repository for data access"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.data.repositories.base import BaseRepository
from app.data.models.metal import Metal


class MetalRepository(BaseRepository[Metal]):
    def __init__(self, db: Session):
        super().__init__(Metal, db)

    def get_by_code(self, code: str, tenant_id: int) -> Optional[Metal]:
        return (
            self.db.query(Metal)
            .filter(
                Metal.tenant_id == tenant_id,
                Metal.code == code,
            )
            .first()
        )

    def code_exists(self, tenant_id: int, code: str) -> bool:
        return (
            self.db.query(Metal)
            .filter(
                Metal.tenant_id == tenant_id,
                Metal.code == code,
            )
            .count()
            > 0
        )

    def get_active(self, tenant_id: int) -> List[Metal]:
        return (
            self.db.query(Metal)
            .filter(
                Metal.tenant_id == tenant_id,
                Metal.is_active == True,
            )
            .order_by(Metal.name.asc())
            .all()
        )

    def get_all_with_inactive(self, tenant_id: int) -> List[Metal]:
        return (
            self.db.query(Metal)
            .filter(Metal.tenant_id == tenant_id)
            .order_by(Metal.name.asc())
            .all()
        )

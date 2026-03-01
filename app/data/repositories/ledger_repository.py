"""Ledger repository for department ledger data access"""
from typing import List, Optional
from datetime import date

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.data.repositories.base import BaseRepository
from app.data.models.department_ledger_entry import DepartmentLedgerEntry
from app.data.models.department_balance import DepartmentBalance


class LedgerRepository(BaseRepository[DepartmentLedgerEntry]):
    def __init__(self, db: Session):
        super().__init__(DepartmentLedgerEntry, db)

    def get_filtered(
        self,
        tenant_id: int,
        department_id: Optional[int] = None,
        order_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        include_archived: bool = False,
    ) -> List[DepartmentLedgerEntry]:
        query = self.db.query(DepartmentLedgerEntry).filter(
            DepartmentLedgerEntry.tenant_id == tenant_id
        )
        if department_id is not None:
            query = query.filter(DepartmentLedgerEntry.department_id == department_id)
        if order_id is not None:
            query = query.filter(DepartmentLedgerEntry.order_id == order_id)
        if date_from is not None:
            query = query.filter(DepartmentLedgerEntry.date >= date_from)
        if date_to is not None:
            query = query.filter(DepartmentLedgerEntry.date <= date_to)
        if not include_archived:
            query = query.filter(DepartmentLedgerEntry.is_archived == False)
        return query.order_by(DepartmentLedgerEntry.date.desc()).all()

    def get_summary(
        self,
        tenant_id: int,
        department_id: Optional[int] = None,
    ) -> List[dict]:
        query = self.db.query(
            DepartmentLedgerEntry.metal_type,
            func.sum(
                case(
                    (DepartmentLedgerEntry.direction == "IN", DepartmentLedgerEntry.quantity),
                    else_=0,
                )
            ).label("total_qty_in"),
            func.sum(
                case(
                    (DepartmentLedgerEntry.direction == "OUT", DepartmentLedgerEntry.quantity),
                    else_=0,
                )
            ).label("total_qty_out"),
            func.sum(DepartmentLedgerEntry.fine_weight).label("fine_weight_balance"),
        ).filter(
            DepartmentLedgerEntry.tenant_id == tenant_id
        )
        if department_id is not None:
            query = query.filter(DepartmentLedgerEntry.department_id == department_id)
        query = query.group_by(DepartmentLedgerEntry.metal_type)
        rows = query.all()
        return [
            {
                "metal_type": row.metal_type,
                "total_qty_in": row.total_qty_in or 0,
                "total_qty_out": row.total_qty_out or 0,
                "fine_weight_balance": row.fine_weight_balance or 0,
            }
            for row in rows
        ]

    def get_department_balance(
        self,
        department_id: int,
        metal_type: str,
    ) -> Optional[DepartmentBalance]:
        return (
            self.db.query(DepartmentBalance)
            .filter(
                DepartmentBalance.department_id == department_id,
                DepartmentBalance.metal_type == metal_type,
            )
            .first()
        )

    def upsert_department_balance(
        self,
        tenant_id: int,
        department_id: int,
        metal_type: str,
        weight_delta: float,
    ) -> DepartmentBalance:
        balance = self.get_department_balance(department_id, metal_type)
        if balance is None:
            balance = DepartmentBalance(
                tenant_id=tenant_id,
                department_id=department_id,
                metal_type=metal_type,
                balance_grams=weight_delta,
            )
            self.db.add(balance)
        else:
            balance.balance_grams += weight_delta
        self.db.flush()
        return balance

    def archive_by_date_range(
        self,
        tenant_id: int,
        date_from: date,
        date_to: date,
    ) -> int:
        count = (
            self.db.query(DepartmentLedgerEntry)
            .filter(
                DepartmentLedgerEntry.tenant_id == tenant_id,
                DepartmentLedgerEntry.date >= date_from,
                DepartmentLedgerEntry.date <= date_to,
                DepartmentLedgerEntry.is_archived == False,
            )
            .update({"is_archived": True})
        )
        self.db.flush()
        return count

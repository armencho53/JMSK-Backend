"""Ledger business logic service"""
from typing import List, Optional
from datetime import date

from sqlalchemy.orm import Session

from app.data.repositories.ledger_repository import LedgerRepository
from app.data.models.department_ledger_entry import DepartmentLedgerEntry
from app.domain.services.metal_service import MetalService
from app.domain.exceptions import ResourceNotFoundError, ValidationError
from app.schemas.ledger import (
    LedgerEntryCreate,
    LedgerEntryUpdate,
    LedgerEntryResponse,
    LedgerSummaryResponse,
    MetalBalanceItem,
)


class LedgerService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = LedgerRepository(db)
        self.metal_service = MetalService(db)

    def _compute_fine_weight(self, metal_id: int, weight: float, direction: str, tenant_id: int) -> float:
        """Compute fine weight = weight × purity_factor, negated for OUT direction."""
        try:
            metal = self.metal_service.get_by_id(metal_id, tenant_id)
        except ResourceNotFoundError:
            raise ValidationError(f"Metal with id '{metal_id}' not found for this tenant")
        if not metal.is_active:
            raise ValidationError(f"Metal with id {metal_id} is inactive")
        fine_weight = weight * metal.fine_percentage
        if direction == "OUT":
            fine_weight = -fine_weight
        return fine_weight

    def _update_balance(self, tenant_id: int, department_id: int, metal_id: int, weight_delta: float) -> None:
        """Update department balance by weight_delta (positive for IN, negative for OUT)."""
        self.repository.upsert_department_balance(tenant_id, department_id, metal_id, weight_delta)

    def create_entry(self, data: LedgerEntryCreate, tenant_id: int, user_id: int) -> LedgerEntryResponse:
        """Create a new ledger entry, compute fine weight, and update department balance."""
        fine_weight = self._compute_fine_weight(data.metal_id, data.weight, data.direction, tenant_id)

        entry = DepartmentLedgerEntry(
            tenant_id=tenant_id,
            date=data.date,
            department_id=data.department_id,
            order_id=data.order_id,
            metal_id=data.metal_id,
            direction=data.direction,
            quantity=data.quantity,
            weight=data.weight,
            fine_weight=fine_weight,
            notes=data.notes,
            created_by=user_id,
        )
        self.db.add(entry)
        self.db.flush()

        weight_delta = data.weight if data.direction == "IN" else -data.weight
        self._update_balance(tenant_id, data.department_id, data.metal_id, weight_delta)

        self.db.commit()
        self.db.refresh(entry)
        return LedgerEntryResponse.model_validate(entry)

    def update_entry(self, entry_id: int, data: LedgerEntryUpdate, tenant_id: int) -> LedgerEntryResponse:
        """Update a ledger entry: reverse old balance, apply updates, recompute fine weight, apply new balance."""
        entry = self.repository.get_by_id(entry_id, tenant_id)
        if not entry:
            raise ResourceNotFoundError("LedgerEntry", entry_id)

        # Capture old values for balance reversal
        old_weight = entry.weight
        old_direction = entry.direction
        old_department_id = entry.department_id
        old_metal_id = entry.metal_id

        # Reverse old balance impact
        old_delta = old_weight if old_direction == "IN" else -old_weight
        self._update_balance(tenant_id, old_department_id, old_metal_id, -old_delta)

        # Apply updates
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(entry, field, value)

        # Recompute fine weight with current values
        entry.fine_weight = self._compute_fine_weight(entry.metal_id, entry.weight, entry.direction, tenant_id)

        # Apply new balance impact
        new_delta = entry.weight if entry.direction == "IN" else -entry.weight
        self._update_balance(tenant_id, entry.department_id, entry.metal_id, new_delta)

        self.db.commit()
        self.db.refresh(entry)
        return LedgerEntryResponse.model_validate(entry)

    def delete_entry(self, entry_id: int, tenant_id: int) -> None:
        """Delete a ledger entry and reverse its balance impact."""
        entry = self.repository.get_by_id(entry_id, tenant_id)
        if not entry:
            raise ResourceNotFoundError("LedgerEntry", entry_id)

        # Reverse balance impact
        delta = entry.weight if entry.direction == "IN" else -entry.weight
        self._update_balance(tenant_id, entry.department_id, entry.metal_id, -delta)

        self.db.delete(entry)
        self.db.commit()

    def list_entries(
        self,
        tenant_id: int,
        department_id: Optional[int] = None,
        order_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        include_archived: bool = False,
    ) -> List[LedgerEntryResponse]:
        """List ledger entries with optional filters."""
        entries = self.repository.get_filtered(
            tenant_id=tenant_id,
            department_id=department_id,
            order_id=order_id,
            date_from=date_from,
            date_to=date_to,
            include_archived=include_archived,
        )
        return [LedgerEntryResponse.model_validate(e) for e in entries]

    def get_summary(self, tenant_id: int, department_id: Optional[int] = None) -> LedgerSummaryResponse:
        """Get aggregated balance summary, excluding zero-balance metal types."""
        rows = self.repository.get_summary(tenant_id, department_id)

        total_qty_held = 0.0
        total_qty_out = 0.0
        balances = []

        for row in rows:
            qty_in = row["total_qty_in"]
            qty_out = row["total_qty_out"]
            fine_weight_balance = row["fine_weight_balance"]

            total_qty_held += qty_in - qty_out
            total_qty_out += qty_out

            if fine_weight_balance != 0:
                balances.append(MetalBalanceItem(
                    metal_id=row["metal_id"],
                    metal_name=row["metal_name"],
                    fine_weight_balance=fine_weight_balance,
                ))

        return LedgerSummaryResponse(
            total_qty_held=total_qty_held,
            total_qty_out=total_qty_out,
            balances=balances,
        )

    def archive_entries(self, tenant_id: int, date_from: date, date_to: date) -> int:
        """Archive ledger entries within a date range. Returns count of archived entries."""
        count = self.repository.archive_by_date_range(tenant_id, date_from, date_to)
        self.db.commit()
        return count

    def unarchive_entry(self, entry_id: int, tenant_id: int) -> LedgerEntryResponse:
        """Restore an archived entry to non-archived status."""
        entry = self.repository.get_by_id(entry_id, tenant_id)
        if not entry:
            raise ResourceNotFoundError("LedgerEntry", entry_id)

        entry.is_archived = False
        self.db.commit()
        self.db.refresh(entry)
        return LedgerEntryResponse.model_validate(entry)

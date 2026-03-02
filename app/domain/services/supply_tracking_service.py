"""Supply tracking business logic service"""
import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.data.repositories.metal_repository import MetalRepository
from app.data.repositories.safe_supply_repository import SafeSupplyRepository
from app.data.repositories.company_metal_balance_repository import CompanyMetalBalanceRepository
from app.data.repositories.metal_transaction_repository import MetalTransactionRepository
from app.data.repositories.company_repository import CompanyRepository
from app.data.models.metal_transaction import MetalTransaction
from app.data.models.order import Order
from app.schemas.supply_tracking import (
    SafeSupplyResponse,
    MetalTransactionResponse,
    CompanyMetalBalanceResponse,
    CastingConsumptionResult,
)
from app.domain.exceptions import ResourceNotFoundError, ValidationError

logger = logging.getLogger(__name__)


class SupplyTrackingService:
    def __init__(self, db: Session):
        self.db = db
        self.metal_repo = MetalRepository(db)
        self.safe_repo = SafeSupplyRepository(db)
        self.balance_repo = CompanyMetalBalanceRepository(db)
        self.transaction_repo = MetalTransactionRepository(db)
        self.company_repo = CompanyRepository(db)

    def record_safe_purchase(
        self,
        tenant_id: int,
        metal_id: Optional[int],
        supply_type: str,
        quantity_grams: float,
        cost_per_gram: float,
        user_id: int,
        notes: Optional[str] = None,
    ) -> MetalTransactionResponse:
        # Validate metal exists if purchasing fine metal
        if supply_type == "FINE_METAL":
            if metal_id is None:
                raise ValidationError("metal_id is required for FINE_METAL purchases")
            metal = self.metal_repo.get_by_id(metal_id, tenant_id)
            if not metal:
                raise ResourceNotFoundError("Metal", metal_id)

            # Update weighted average cost
            safe_supply = self.safe_repo.get_or_create(tenant_id, metal_id, "FINE_METAL")
            old_qty = safe_supply.quantity_grams
            old_cost = metal.average_cost_per_gram or 0.0

            if old_qty + quantity_grams > 0:
                metal.average_cost_per_gram = (
                    (old_cost * old_qty) + (cost_per_gram * quantity_grams)
                ) / (old_qty + quantity_grams)
            else:
                metal.average_cost_per_gram = cost_per_gram

        # Increase safe supply
        safe_supply = self.safe_repo.get_or_create(tenant_id, metal_id, supply_type)
        safe_supply.quantity_grams += quantity_grams

        # Create transaction record
        transaction = MetalTransaction(
            tenant_id=tenant_id,
            transaction_type="SAFE_PURCHASE",
            metal_id=metal_id,
            quantity_grams=quantity_grams,
            notes=notes,
            created_by=user_id,
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        return self._to_transaction_response(transaction)

    def get_safe_supplies(self, tenant_id: int) -> List[SafeSupplyResponse]:
        supplies = self.safe_repo.get_all_for_tenant(tenant_id)
        result = []
        for s in supplies:
            metal_code = s.metal.code if s.metal else None
            metal_name = s.metal.name if s.metal else None
            result.append(SafeSupplyResponse(
                id=s.id,
                metal_id=s.metal_id,
                supply_type=s.supply_type,
                metal_code=metal_code,
                metal_name=metal_name,
                quantity_grams=s.quantity_grams,
            ))
        return result

    def get_transactions(
        self,
        tenant_id: int,
        company_id: Optional[int] = None,
        metal_id: Optional[int] = None,
        transaction_type: Optional[str] = None,
    ) -> List[MetalTransactionResponse]:
        transactions = self.transaction_repo.get_filtered(
            tenant_id, company_id, metal_id, transaction_type
        )
        return [self._to_transaction_response(t) for t in transactions]

    def record_company_deposit(
        self,
        tenant_id: int,
        company_id: int,
        metal_id: int,
        quantity_grams: float,
        user_id: int,
        notes: Optional[str] = None,
    ) -> MetalTransactionResponse:
        # Validate company exists
        company = self.company_repo.get_by_id(company_id, tenant_id)
        if not company:
            raise ResourceNotFoundError("Company", company_id)

        # Validate metal exists and is active
        metal = self.metal_repo.get_by_id(metal_id, tenant_id)
        if not metal:
            raise ResourceNotFoundError("Metal", metal_id)
        if not metal.is_active:
            raise ResourceNotFoundError("Metal", metal_id)

        # Increase company metal balance
        balance = self.balance_repo.get_or_create(tenant_id, company_id, metal_id)
        balance.balance_grams += quantity_grams

        # Also increase safe supply (fine metal)
        safe_supply = self.safe_repo.get_or_create(tenant_id, metal_id, "FINE_METAL")
        safe_supply.quantity_grams += quantity_grams

        # Create transaction record
        transaction = MetalTransaction(
            tenant_id=tenant_id,
            transaction_type="COMPANY_DEPOSIT",
            metal_id=metal_id,
            company_id=company_id,
            quantity_grams=quantity_grams,
            notes=notes,
            created_by=user_id,
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        return self._to_transaction_response(transaction)

    def get_company_balances(
        self, tenant_id: int, company_id: int
    ) -> List[CompanyMetalBalanceResponse]:
        # Validate company exists
        company = self.company_repo.get_by_id(company_id, tenant_id)
        if not company:
            raise ResourceNotFoundError("Company", company_id)

        balances = self.balance_repo.get_by_company(tenant_id, company_id)
        return [
            CompanyMetalBalanceResponse(
                id=b.id,
                metal_id=b.metal_id,
                metal_code=b.metal.code,
                metal_name=b.metal.name,
                balance_grams=b.balance_grams,
            )
            for b in balances
        ]

    def _calculate_casting_consumption(
        self, total_weight: float, fine_percentage: float
    ) -> Tuple[float, float]:
        """Returns (fine_metal_grams, alloy_grams)"""
        fine_metal_grams = total_weight * fine_percentage
        alloy_grams = total_weight - fine_metal_grams
        return fine_metal_grams, alloy_grams

    def process_casting_consumption(
        self, tenant_id: int, order_id: int, user_id: int
    ) -> Optional[CastingConsumptionResult]:
        # Fetch order
        order = self.db.query(Order).filter(
            Order.id == order_id,
            Order.tenant_id == tenant_id,
        ).first()
        if not order:
            raise ResourceNotFoundError("Order", order_id)

        # Validate order has a metal assigned
        if not order.metal_id:
            raise ValidationError(
                f"Order {order_id} has no metal assigned"
            )

        # Validate the referenced metal is active
        metal = order.metal
        if not metal or not metal.is_active:
            raise ValidationError(
                f"Metal with id {order.metal_id} is inactive"
            )

        # Skip if order missing target_weight_per_piece
        if not order.target_weight_per_piece:
            logger.warning(
                "Order %d missing target_weight_per_piece, skipping casting consumption",
                order_id,
            )
            return None

        if not order.quantity or order.quantity <= 0:
            logger.warning("Order %d has zero quantity, skipping casting consumption", order_id)
            return None

        # Calculate consumption
        total_weight = order.quantity * order.target_weight_per_piece
        fine_metal_grams, alloy_grams = self._calculate_casting_consumption(
            total_weight, metal.fine_percentage
        )

        # Subtract fine metal from company balance
        company_balance = self.balance_repo.get_or_create(
            tenant_id, order.company_id, metal.id
        )
        balance_before = company_balance.balance_grams
        company_balance.balance_grams -= fine_metal_grams

        # If company balance went negative, subtract deficit from safe fine metal supply
        safe_fine = self.safe_repo.get_or_create(tenant_id, metal.id, "FINE_METAL")
        if company_balance.balance_grams < 0 and balance_before >= 0:
            # Balance just crossed zero — deficit is the full negative amount
            safe_fine.quantity_grams += company_balance.balance_grams  # adds negative = subtracts
        elif company_balance.balance_grams < 0 and balance_before < 0:
            # Balance was already negative — entire consumption comes from safe
            safe_fine.quantity_grams -= fine_metal_grams

        # Subtract alloy from safe
        safe_alloy = self.safe_repo.get_or_create(tenant_id, None, "ALLOY")
        safe_alloy.quantity_grams -= alloy_grams

        # Create transaction records
        fine_txn = MetalTransaction(
            tenant_id=tenant_id,
            transaction_type="MANUFACTURING_CONSUMPTION",
            metal_id=metal.id,
            company_id=order.company_id,
            order_id=order_id,
            quantity_grams=-fine_metal_grams,
            notes=f"Casting consumption: {fine_metal_grams:.4f}g fine metal for order {order.order_number}",
            created_by=user_id,
        )
        alloy_txn = MetalTransaction(
            tenant_id=tenant_id,
            transaction_type="MANUFACTURING_CONSUMPTION",
            metal_id=None,
            company_id=order.company_id,
            order_id=order_id,
            quantity_grams=-alloy_grams,
            notes=f"Casting consumption: {alloy_grams:.4f}g alloy for order {order.order_number}",
            created_by=user_id,
        )
        self.db.add(fine_txn)
        self.db.add(alloy_txn)
        self.db.commit()

        return CastingConsumptionResult(
            fine_metal_grams=fine_metal_grams,
            alloy_grams=alloy_grams,
            metal_code=metal.code,
            company_id=order.company_id,
            order_id=order_id,
            company_balance_after=company_balance.balance_grams,
            safe_fine_metal_after=safe_fine.quantity_grams,
            safe_alloy_after=safe_alloy.quantity_grams,
        )

    def _to_transaction_response(self, t: MetalTransaction) -> MetalTransactionResponse:
        metal_code = t.metal.code if t.metal else None
        return MetalTransactionResponse(
            id=t.id,
            transaction_type=t.transaction_type,
            metal_id=t.metal_id,
            metal_code=metal_code,
            company_id=t.company_id,
            order_id=t.order_id,
            quantity_grams=t.quantity_grams,
            notes=t.notes,
            created_at=t.created_at,
            created_by=t.created_by,
        )

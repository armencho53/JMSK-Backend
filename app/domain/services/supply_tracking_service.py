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
from app.data.models.department_ledger_entry import DepartmentLedgerEntry
from app.data.models.department import Department
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

    def process_casting_ledger_entry(
        self,
        ledger_entry: DepartmentLedgerEntry,
        tenant_id: int,
        user_id: int,
    ) -> Optional[CastingConsumptionResult]:
        """
        Process casting department ledger entry to deduct pure metal from company balance.
        
        This method:
        - Calculates pure metal weight = gross weight × purity factor
        - Deducts from company metal balance
        - Creates MANUFACTURING_CONSUMPTION transaction
        - Allows negative balances (doesn't block)
        
        Args:
            ledger_entry: The department ledger entry to process
            tenant_id: Tenant ID for multi-tenant isolation
            user_id: User ID for audit trail
            
        Returns:
            CastingConsumptionResult if processing succeeded, None if skipped
        """
        # Check if this is a casting department entry with IN direction
        if ledger_entry.direction != "IN":
            logger.debug(
                "Ledger entry %d is not IN direction, skipping casting consumption",
                ledger_entry.id,
            )
            return None
            
        # Check if department is casting department (by name lookup)
        department = self.db.query(Department).filter(
            Department.id == ledger_entry.department_id,
            Department.tenant_id == tenant_id,
        ).first()
        
        if not department:
            logger.warning(
                "Department %d not found for ledger entry %d",
                ledger_entry.department_id,
                ledger_entry.id,
            )
            return None
            
        # Identify casting department by name (case-insensitive)
        if department.name.lower() not in ["casting", "cast"]:
            logger.debug(
                "Department '%s' is not casting department, skipping consumption",
                department.name,
            )
            return None
        
        # Validate order exists and has company
        order = self.db.query(Order).filter(
            Order.id == ledger_entry.order_id,
            Order.tenant_id == tenant_id,
        ).first()
        
        if not order:
            logger.warning(
                "Order %d not found for ledger entry %d",
                ledger_entry.order_id,
                ledger_entry.id,
            )
            return None
            
        if not order.company_id:
            logger.warning(
                "Order %d has no company_id, skipping casting consumption",
                order.id,
            )
            return None
        
        # Validate metal exists
        metal = self.metal_repo.get_by_id(ledger_entry.metal_id, tenant_id)
        if not metal:
            logger.warning(
                "Metal %d not found for ledger entry %d",
                ledger_entry.metal_id,
                ledger_entry.id,
            )
            return None
        
        # Calculate pure metal weight from ledger entry
        # The ledger entry already has fine_weight calculated, but we recalculate for clarity
        pure_metal_weight = ledger_entry.weight * metal.fine_percentage
        
        # Get or create company metal balance
        company_balance = self.balance_repo.get_or_create(
            tenant_id, order.company_id, metal.id
        )
        balance_before = company_balance.balance_grams
        
        # Deduct pure metal from company balance (allow negative)
        company_balance.balance_grams -= pure_metal_weight
        
        # Create MANUFACTURING_CONSUMPTION transaction
        transaction = MetalTransaction(
            tenant_id=tenant_id,
            transaction_type="MANUFACTURING_CONSUMPTION",
            metal_id=metal.id,
            company_id=order.company_id,
            order_id=order.id,
            quantity_grams=-pure_metal_weight,  # Negative for consumption
            notes=f"Casting consumption from ledger entry {ledger_entry.id}: {pure_metal_weight:.4f}g pure metal for order {order.order_number}",
            created_by=user_id,
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        logger.info(
            "Processed casting consumption for ledger entry %d: %.4fg pure metal deducted from company %d balance",
            ledger_entry.id,
            pure_metal_weight,
            order.company_id,
        )
        
        # Return result (note: we don't track alloy separately in this new method)
        return CastingConsumptionResult(
            fine_metal_grams=pure_metal_weight,
            alloy_grams=0.0,  # Not tracked in ledger-based consumption
            metal_code=metal.code,
            company_id=order.company_id,
            order_id=order.id,
            company_balance_after=company_balance.balance_grams,
            safe_fine_metal_after=0.0,  # Not updated in ledger-based consumption
            safe_alloy_after=0.0,  # Not tracked
        )
    
    def reverse_casting_ledger_entry(
        self,
        ledger_entry: DepartmentLedgerEntry,
        tenant_id: int,
        user_id: int,
    ) -> Optional[CastingConsumptionResult]:
        """
        Reverse casting consumption when a ledger entry is deleted.
        
        This adds back the previously deducted pure metal to the company balance.
        
        Args:
            ledger_entry: The ledger entry being deleted
            tenant_id: Tenant ID for multi-tenant isolation
            user_id: User ID for audit trail
            
        Returns:
            CastingConsumptionResult if reversal succeeded, None if skipped
        """
        # Check if this is a casting department entry with IN direction
        if ledger_entry.direction != "IN":
            return None
            
        # Check if department is casting department
        department = self.db.query(Department).filter(
            Department.id == ledger_entry.department_id,
            Department.tenant_id == tenant_id,
        ).first()
        
        if not department or department.name.lower() not in ["casting", "cast"]:
            return None
        
        # Validate order exists
        order = self.db.query(Order).filter(
            Order.id == ledger_entry.order_id,
            Order.tenant_id == tenant_id,
        ).first()
        
        if not order or not order.company_id:
            return None
        
        # Validate metal exists
        metal = self.metal_repo.get_by_id(ledger_entry.metal_id, tenant_id)
        if not metal:
            return None
        
        # Calculate pure metal weight
        pure_metal_weight = ledger_entry.weight * metal.fine_percentage
        
        # Get company metal balance
        company_balance = self.balance_repo.get_or_create(
            tenant_id, order.company_id, metal.id
        )
        
        # Add back the pure metal (reverse the deduction)
        company_balance.balance_grams += pure_metal_weight
        
        # Create reversal transaction
        transaction = MetalTransaction(
            tenant_id=tenant_id,
            transaction_type="MANUFACTURING_CONSUMPTION",
            metal_id=metal.id,
            company_id=order.company_id,
            order_id=order.id,
            quantity_grams=pure_metal_weight,  # Positive for reversal
            notes=f"Reversal of casting consumption from deleted ledger entry {ledger_entry.id}: {pure_metal_weight:.4f}g pure metal returned to company {order.company_id}",
            created_by=user_id,
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        logger.info(
            "Reversed casting consumption for deleted ledger entry %d: %.4fg pure metal returned to company %d",
            ledger_entry.id,
            pure_metal_weight,
            order.company_id,
        )
        
        return CastingConsumptionResult(
            fine_metal_grams=pure_metal_weight,
            alloy_grams=0.0,
            metal_code=metal.code,
            company_id=order.company_id,
            order_id=order.id,
            company_balance_after=company_balance.balance_grams,
            safe_fine_metal_after=0.0,
            safe_alloy_after=0.0,
        )
    
    def update_casting_ledger_entry(
        self,
        old_entry: DepartmentLedgerEntry,
        new_entry: DepartmentLedgerEntry,
        tenant_id: int,
        user_id: int,
    ) -> Optional[CastingConsumptionResult]:
        """
        Handle casting consumption update when a ledger entry is modified.
        
        This reverses the old deduction and applies the new deduction.
        
        Args:
            old_entry: The original ledger entry (before update)
            new_entry: The updated ledger entry (after update)
            tenant_id: Tenant ID for multi-tenant isolation
            user_id: User ID for audit trail
            
        Returns:
            CastingConsumptionResult if update succeeded, None if skipped
        """
        # Reverse the old entry
        self.reverse_casting_ledger_entry(old_entry, tenant_id, user_id)
        
        # Process the new entry
        return self.process_casting_ledger_entry(new_entry, tenant_id, user_id)

    def recalculate_safe_supply_balance(
            self, metal_id: int, tenant_id: int
        ) -> float:
            """
            Recalculate safe supply balance for a specific metal type.

            Formula: safe_supply = sum(all company balances for metal) + manufacturer's own stock

            The safe supply contains two components:
            1. Company deposits (tracked in company_metal_balance table)
            2. Manufacturer's own purchases (tracked via SAFE_PURCHASE transactions)

            This method recalculates the safe supply to ensure it matches the sum of:
            - All company metal balances for this metal type
            - Manufacturer's own stock (calculated from SAFE_PURCHASE transactions minus consumption)

            This method is idempotent and does not create transaction records.
            It should be triggered when retrieving company metal balances.

            Args:
                metal_id: The metal ID to recalculate balance for
                tenant_id: Tenant ID for multi-tenant isolation

            Returns:
                The recalculated safe supply balance in grams
            """
            from app.data.models.company_metal_balance import CompanyMetalBalance

            # Sum all company balances for this metal type
            total_company_balances = (
                self.db.query(CompanyMetalBalance)
                .filter(
                    CompanyMetalBalance.tenant_id == tenant_id,
                    CompanyMetalBalance.metal_id == metal_id,
                )
                .with_entities(CompanyMetalBalance.balance_grams)
                .all()
            )

            sum_company_balances = sum(balance[0] for balance in total_company_balances)

            # Calculate manufacturer's own stock from transactions
            # SAFE_PURCHASE adds to manufacturer stock
            # COMPANY_DEPOSIT does NOT add to manufacturer stock (it's company metal)
            # MANUFACTURING_CONSUMPTION may reduce manufacturer stock if company balance goes negative

            # Get all transactions for this metal
            safe_purchases = (
                self.db.query(MetalTransaction)
                .filter(
                    MetalTransaction.tenant_id == tenant_id,
                    MetalTransaction.metal_id == metal_id,
                    MetalTransaction.transaction_type == "SAFE_PURCHASE",
                )
                .with_entities(MetalTransaction.quantity_grams)
                .all()
            )

            manufacturer_stock = sum(txn[0] for txn in safe_purchases)

            # Get or create the safe supply record for this metal (FINE_METAL type)
            safe_supply = self.safe_repo.get_or_create(tenant_id, metal_id, "FINE_METAL")

            # Update the safe supply balance directly
            # Safe supply = company deposits + manufacturer's own stock
            recalculated_balance = sum_company_balances + manufacturer_stock
            safe_supply.quantity_grams = recalculated_balance

            # Commit the update
            self.db.commit()
            self.db.refresh(safe_supply)

            logger.info(
                "Recalculated safe supply balance for metal %d, tenant %d: %.4fg (company: %.4fg + manufacturer: %.4fg)",
                metal_id,
                tenant_id,
                recalculated_balance,
                sum_company_balances,
                manufacturer_stock,
            )

            return safe_supply.quantity_grams


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

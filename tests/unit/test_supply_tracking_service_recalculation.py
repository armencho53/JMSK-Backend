"""Unit tests for SupplyTrackingService recalculate_safe_supply_balance method"""
import pytest

from app.data.models.tenant import Tenant
from app.data.models.user import User
from app.data.models.company import Company
from app.data.models.metal import Metal
from app.data.models.company_metal_balance import CompanyMetalBalance
from app.data.models.metal_transaction import MetalTransaction
from app.data.models.safe_supply import SafeSupply
from app.domain.services.supply_tracking_service import SupplyTrackingService


@pytest.fixture
def seed_data(db_session):
    """Create the minimal entity graph needed for recalculation tests."""
    tenant = Tenant(id=1, name="Test Co", subdomain="test")
    db_session.add(tenant)
    db_session.flush()

    user = User(
        id=1, tenant_id=1, username="testuser", email="u@test.com",
        hashed_password="x", full_name="Test User",
    )
    db_session.add(user)
    db_session.flush()

    metal = Metal(
        id=1, tenant_id=1, code="GOLD_22K",
        name="Gold 22K", fine_percentage=0.916, is_active=True,
    )
    db_session.add(metal)
    db_session.flush()

    company1 = Company(id=1, tenant_id=1, name="Acme Jewelry")
    company2 = Company(id=2, tenant_id=1, name="Best Jewelry")
    db_session.add_all([company1, company2])
    db_session.commit()

    return {
        "tenant_id": 1,
        "user_id": 1,
        "metal_id": 1,
        "company1_id": 1,
        "company2_id": 2,
    }


class TestRecalculateSafeSupplyBalance:
    """Tests for recalculate_safe_supply_balance method"""

    def test_recalculates_with_only_company_balances(self, db_session, seed_data):
        """Test recalculation with only company deposits, no manufacturer stock"""
        # Setup: Create company balances
        balance1 = CompanyMetalBalance(
            tenant_id=seed_data["tenant_id"],
            company_id=seed_data["company1_id"],
            metal_id=seed_data["metal_id"],
            balance_grams=50.0,
        )
        balance2 = CompanyMetalBalance(
            tenant_id=seed_data["tenant_id"],
            company_id=seed_data["company2_id"],
            metal_id=seed_data["metal_id"],
            balance_grams=30.0,
        )
        db_session.add_all([balance1, balance2])
        db_session.commit()

        # Recalculate
        service = SupplyTrackingService(db_session)
        result = service.recalculate_safe_supply_balance(
            seed_data["metal_id"], seed_data["tenant_id"]
        )

        # Verify: safe supply should equal sum of company balances (50 + 30 = 80)
        assert result == 80.0

        # Verify safe supply record was updated
        safe_supply = db_session.query(SafeSupply).filter(
            SafeSupply.tenant_id == seed_data["tenant_id"],
            SafeSupply.metal_id == seed_data["metal_id"],
            SafeSupply.supply_type == "FINE_METAL",
        ).first()
        assert safe_supply is not None
        assert safe_supply.quantity_grams == 80.0

    def test_recalculates_with_company_balances_and_manufacturer_stock(self, db_session, seed_data):
        """Test recalculation with both company deposits and manufacturer purchases"""
        # Setup: Create company balances
        balance1 = CompanyMetalBalance(
            tenant_id=seed_data["tenant_id"],
            company_id=seed_data["company1_id"],
            metal_id=seed_data["metal_id"],
            balance_grams=50.0,
        )
        db_session.add(balance1)
        db_session.commit()

        # Setup: Create manufacturer purchase transaction
        purchase_txn = MetalTransaction(
            tenant_id=seed_data["tenant_id"],
            transaction_type="SAFE_PURCHASE",
            metal_id=seed_data["metal_id"],
            quantity_grams=100.0,
            notes="Manufacturer purchase",
            created_by=seed_data["user_id"],
        )
        db_session.add(purchase_txn)
        db_session.commit()

        # Recalculate
        service = SupplyTrackingService(db_session)
        result = service.recalculate_safe_supply_balance(
            seed_data["metal_id"], seed_data["tenant_id"]
        )

        # Verify: safe supply should equal company balance + manufacturer stock (50 + 100 = 150)
        assert result == 150.0

        # Verify safe supply record was updated
        safe_supply = db_session.query(SafeSupply).filter(
            SafeSupply.tenant_id == seed_data["tenant_id"],
            SafeSupply.metal_id == seed_data["metal_id"],
            SafeSupply.supply_type == "FINE_METAL",
        ).first()
        assert safe_supply is not None
        assert safe_supply.quantity_grams == 150.0

    def test_recalculates_with_no_company_balances(self, db_session, seed_data):
        """Test recalculation when no company balances exist"""
        # Setup: Create only manufacturer purchase
        purchase_txn = MetalTransaction(
            tenant_id=seed_data["tenant_id"],
            transaction_type="SAFE_PURCHASE",
            metal_id=seed_data["metal_id"],
            quantity_grams=75.0,
            notes="Manufacturer purchase",
            created_by=seed_data["user_id"],
        )
        db_session.add(purchase_txn)
        db_session.commit()

        # Recalculate
        service = SupplyTrackingService(db_session)
        result = service.recalculate_safe_supply_balance(
            seed_data["metal_id"], seed_data["tenant_id"]
        )

        # Verify: safe supply should equal only manufacturer stock (75)
        assert result == 75.0

    def test_recalculation_is_idempotent(self, db_session, seed_data):
        """Test that multiple recalculations produce the same result"""
        # Setup: Create company balance
        balance1 = CompanyMetalBalance(
            tenant_id=seed_data["tenant_id"],
            company_id=seed_data["company1_id"],
            metal_id=seed_data["metal_id"],
            balance_grams=40.0,
        )
        db_session.add(balance1)
        db_session.commit()

        # Recalculate multiple times
        service = SupplyTrackingService(db_session)
        result1 = service.recalculate_safe_supply_balance(
            seed_data["metal_id"], seed_data["tenant_id"]
        )
        result2 = service.recalculate_safe_supply_balance(
            seed_data["metal_id"], seed_data["tenant_id"]
        )
        result3 = service.recalculate_safe_supply_balance(
            seed_data["metal_id"], seed_data["tenant_id"]
        )

        # Verify: all results should be the same
        assert result1 == result2 == result3 == 40.0

        # Verify: no transaction records were created
        transactions = db_session.query(MetalTransaction).filter(
            MetalTransaction.tenant_id == seed_data["tenant_id"],
            MetalTransaction.metal_id == seed_data["metal_id"],
        ).all()
        assert len(transactions) == 0

    def test_recalculates_with_multiple_purchases(self, db_session, seed_data):
        """Test recalculation with multiple manufacturer purchases"""
        # Setup: Create multiple purchase transactions
        purchase1 = MetalTransaction(
            tenant_id=seed_data["tenant_id"],
            transaction_type="SAFE_PURCHASE",
            metal_id=seed_data["metal_id"],
            quantity_grams=50.0,
            notes="Purchase 1",
            created_by=seed_data["user_id"],
        )
        purchase2 = MetalTransaction(
            tenant_id=seed_data["tenant_id"],
            transaction_type="SAFE_PURCHASE",
            metal_id=seed_data["metal_id"],
            quantity_grams=30.0,
            notes="Purchase 2",
            created_by=seed_data["user_id"],
        )
        purchase3 = MetalTransaction(
            tenant_id=seed_data["tenant_id"],
            transaction_type="SAFE_PURCHASE",
            metal_id=seed_data["metal_id"],
            quantity_grams=20.0,
            notes="Purchase 3",
            created_by=seed_data["user_id"],
        )
        db_session.add_all([purchase1, purchase2, purchase3])
        db_session.commit()

        # Recalculate
        service = SupplyTrackingService(db_session)
        result = service.recalculate_safe_supply_balance(
            seed_data["metal_id"], seed_data["tenant_id"]
        )

        # Verify: safe supply should equal sum of all purchases (50 + 30 + 20 = 100)
        assert result == 100.0

"""Tests for order metal_id validation against the metals table.

Validates Requirements 12.1, 12.2, 12.3, 12.4:
- 12.1: Validate metal_id against the metals table instead of metal_type against lookup values
- 12.2: Order creation with valid metal_id succeeds with correct metal reference
- 12.3: Order creation with invalid metal_id returns appropriate error
- 12.4: Ledger entry creation with metal_id verifies fine weight uses Metal's fine_percentage
"""

import pytest
from datetime import date
from sqlalchemy.orm import Session

from app.data.models.tenant import Tenant
from app.data.models.user import User
from app.data.models.department import Department
from app.data.models.company import Company
from app.data.models.contact import Contact
from app.data.models.order import Order
from app.data.models.metal import Metal
from app.data.repositories.metal_repository import MetalRepository
from app.domain.services.ledger_service import LedgerService
from app.domain.exceptions import ValidationError
from app.schemas.ledger import LedgerEntryCreate


@pytest.fixture
def seed_data(db_session):
    """Create the minimal entity graph needed for metal_id validation tests."""
    tenant = Tenant(id=1, name="Test Co", subdomain="test")
    db_session.add(tenant)
    db_session.flush()

    user = User(
        id=1, tenant_id=1, email="u@test.com",
        hashed_password="x", full_name="Test User",
    )
    dept = Department(id=1, tenant_id=1, name="Casting")
    company = Company(id=1, tenant_id=1, name="Acme Jewelry")
    db_session.add_all([user, dept, company])
    db_session.flush()

    gold_24k = Metal(
        id=1, tenant_id=1, code="GOLD_24K",
        name="Gold 24K", fine_percentage=0.999,
    )
    silver_925 = Metal(
        id=2, tenant_id=1, code="SILVER_925",
        name="Silver 925", fine_percentage=0.925,
    )
    inactive_metal = Metal(
        id=3, tenant_id=1, code="PLATINUM",
        name="Platinum", fine_percentage=0.950, is_active=False,
    )
    db_session.add_all([gold_24k, silver_925, inactive_metal])
    db_session.flush()

    contact = Contact(id=1, tenant_id=1, company_id=1, name="John")
    db_session.add(contact)
    db_session.flush()

    order = Order(
        id=1, tenant_id=1, order_number="ORD-001",
        contact_id=1, company_id=1, metal_id=1,
    )
    db_session.add(order)
    db_session.commit()

    return {
        "tenant_id": 1,
        "user_id": 1,
        "department_id": 1,
        "order_id": 1,
        "contact_id": 1,
        "company_id": 1,
        "gold_24k_id": 1,
        "silver_925_id": 2,
        "inactive_metal_id": 3,
    }


class TestOrderMetalIdValidation:
    """Test metal_id validation against the metals table (Requirement 12.1)."""

    def test_valid_metal_id_found_in_metals_table(self, db_session, seed_data):
        """A valid metal_id should be found via MetalRepository (Requirement 12.1)."""
        repo = MetalRepository(db_session)
        metal = repo.get_by_id(seed_data["gold_24k_id"], tenant_id=seed_data["tenant_id"])
        assert metal is not None
        assert metal.code == "GOLD_24K"
        assert metal.is_active is True

    def test_invalid_metal_id_not_found(self, db_session, seed_data):
        """An invalid metal_id should return None from MetalRepository (Requirement 12.1)."""
        repo = MetalRepository(db_session)
        metal = repo.get_by_id(9999, tenant_id=seed_data["tenant_id"])
        assert metal is None

    def test_inactive_metal_id_found_but_inactive(self, db_session, seed_data):
        """An inactive metal_id should be found but flagged as inactive (Requirement 12.1)."""
        repo = MetalRepository(db_session)
        metal = repo.get_by_id(seed_data["inactive_metal_id"], tenant_id=seed_data["tenant_id"])
        assert metal is not None
        assert metal.is_active is False

    def test_metal_id_is_tenant_scoped(self, db_session, seed_data):
        """metal_id lookup should be scoped to the requesting tenant (Requirement 12.1)."""
        repo = MetalRepository(db_session)
        # Metal exists for tenant 1 but not tenant 2
        metal = repo.get_by_id(seed_data["gold_24k_id"], tenant_id=999)
        assert metal is None


class TestOrderCreationWithMetalId:
    """Test order creation with metal_id references (Requirements 12.2, 12.3)."""

    def test_order_created_with_valid_metal_id(self, db_session, seed_data):
        """Order creation with a valid metal_id succeeds with correct metal reference (Requirement 12.2)."""
        order = Order(
            tenant_id=seed_data["tenant_id"],
            order_number="ORD-002",
            contact_id=seed_data["contact_id"],
            company_id=seed_data["company_id"],
            metal_id=seed_data["gold_24k_id"],
        )
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)

        assert order.metal_id == seed_data["gold_24k_id"]
        assert order.metal is not None
        assert order.metal.code == "GOLD_24K"
        assert order.metal.fine_percentage == 0.999

    def test_order_created_without_metal_id(self, db_session, seed_data):
        """Order creation without metal_id succeeds (metal_id is nullable) (Requirement 12.2)."""
        order = Order(
            tenant_id=seed_data["tenant_id"],
            order_number="ORD-003",
            contact_id=seed_data["contact_id"],
            company_id=seed_data["company_id"],
            metal_id=None,
        )
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)

        assert order.metal_id is None
        assert order.metal is None

    def test_order_with_invalid_metal_id_not_found_by_repo(self, db_session, seed_data):
        """Application-level validation: invalid metal_id is not found by MetalRepository (Requirement 12.3)."""
        repo = MetalRepository(db_session)
        metal = repo.get_by_id(9999, tenant_id=seed_data["tenant_id"])
        assert metal is None, "Non-existent metal_id should return None from repository"

    def test_order_with_inactive_metal_id_fails_active_check(self, db_session, seed_data):
        """Application-level validation: inactive metal_id fails the is_active check (Requirement 12.3)."""
        repo = MetalRepository(db_session)
        metal = repo.get_by_id(seed_data["inactive_metal_id"], tenant_id=seed_data["tenant_id"])
        assert metal is not None
        assert metal.is_active is False, "Inactive metal should fail the active check"

    def test_existing_order_has_correct_metal_relationship(self, db_session, seed_data):
        """The seeded order should have the correct metal relationship loaded (Requirement 12.2)."""
        order = db_session.query(Order).filter(Order.id == seed_data["order_id"]).first()
        assert order is not None
        assert order.metal_id == seed_data["gold_24k_id"]
        assert order.metal.name == "Gold 24K"


class TestLedgerEntryFineWeightWithMetalId:
    """Test ledger entry creation with metal_id and fine weight computation (Requirement 12.4)."""

    def test_fine_weight_uses_metal_fine_percentage_for_in(self, db_session, seed_data):
        """Ledger entry IN direction: fine_weight = weight × fine_percentage (Requirement 12.4)."""
        service = LedgerService(db_session)
        data = LedgerEntryCreate(
            date=date(2025, 1, 15),
            department_id=seed_data["department_id"],
            order_id=seed_data["order_id"],
            metal_id=seed_data["gold_24k_id"],
            direction="IN",
            quantity=1.0,
            weight=10.0,
        )
        entry = service.create_entry(data, seed_data["tenant_id"], seed_data["user_id"])

        # Gold 24K fine_percentage = 0.999, weight = 10.0
        expected_fine_weight = 10.0 * 0.999
        assert abs(entry.fine_weight - expected_fine_weight) < 1e-6

    def test_fine_weight_uses_metal_fine_percentage_for_out(self, db_session, seed_data):
        """Ledger entry OUT direction: fine_weight = -(weight × fine_percentage) (Requirement 12.4)."""
        service = LedgerService(db_session)
        # First create an IN entry so balance exists
        in_data = LedgerEntryCreate(
            date=date(2025, 1, 15),
            department_id=seed_data["department_id"],
            order_id=seed_data["order_id"],
            metal_id=seed_data["gold_24k_id"],
            direction="IN",
            quantity=1.0,
            weight=20.0,
        )
        service.create_entry(in_data, seed_data["tenant_id"], seed_data["user_id"])

        out_data = LedgerEntryCreate(
            date=date(2025, 1, 16),
            department_id=seed_data["department_id"],
            order_id=seed_data["order_id"],
            metal_id=seed_data["gold_24k_id"],
            direction="OUT",
            quantity=1.0,
            weight=5.0,
        )
        entry = service.create_entry(out_data, seed_data["tenant_id"], seed_data["user_id"])

        expected_fine_weight = -(5.0 * 0.999)
        assert abs(entry.fine_weight - expected_fine_weight) < 1e-6

    def test_fine_weight_uses_different_metal_percentage(self, db_session, seed_data):
        """Fine weight computation uses the specific metal's fine_percentage (Requirement 12.4)."""
        service = LedgerService(db_session)
        # Create an order with silver
        silver_order = Order(
            tenant_id=seed_data["tenant_id"],
            order_number="ORD-SILVER",
            contact_id=seed_data["contact_id"],
            company_id=seed_data["company_id"],
            metal_id=seed_data["silver_925_id"],
        )
        db_session.add(silver_order)
        db_session.commit()

        data = LedgerEntryCreate(
            date=date(2025, 1, 15),
            department_id=seed_data["department_id"],
            order_id=silver_order.id,
            metal_id=seed_data["silver_925_id"],
            direction="IN",
            quantity=1.0,
            weight=10.0,
        )
        entry = service.create_entry(data, seed_data["tenant_id"], seed_data["user_id"])

        # Silver 925 fine_percentage = 0.925, weight = 10.0
        expected_fine_weight = 10.0 * 0.925
        assert abs(entry.fine_weight - expected_fine_weight) < 1e-6

    def test_ledger_entry_with_invalid_metal_id_raises_error(self, db_session, seed_data):
        """Ledger entry creation with invalid metal_id raises ValidationError (Requirement 12.4)."""
        service = LedgerService(db_session)
        data = LedgerEntryCreate(
            date=date(2025, 1, 15),
            department_id=seed_data["department_id"],
            order_id=seed_data["order_id"],
            metal_id=9999,
            direction="IN",
            quantity=1.0,
            weight=10.0,
        )
        with pytest.raises(ValidationError, match="not found"):
            service.create_entry(data, seed_data["tenant_id"], seed_data["user_id"])

    def test_ledger_entry_with_inactive_metal_id_raises_error(self, db_session, seed_data):
        """Ledger entry creation with inactive metal_id raises ValidationError (Requirement 12.4)."""
        service = LedgerService(db_session)
        data = LedgerEntryCreate(
            date=date(2025, 1, 15),
            department_id=seed_data["department_id"],
            order_id=seed_data["order_id"],
            metal_id=seed_data["inactive_metal_id"],
            direction="IN",
            quantity=1.0,
            weight=10.0,
        )
        with pytest.raises(ValidationError, match="inactive"):
            service.create_entry(data, seed_data["tenant_id"], seed_data["user_id"])

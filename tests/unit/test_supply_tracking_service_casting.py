"""Unit tests for SupplyTrackingService casting consumption methods"""
import pytest
from datetime import date

from app.data.models.tenant import Tenant
from app.data.models.user import User
from app.data.models.department import Department
from app.data.models.company import Company
from app.data.models.contact import Contact
from app.data.models.order import Order
from app.data.models.metal import Metal
from app.data.models.department_ledger_entry import DepartmentLedgerEntry
from app.data.models.company_metal_balance import CompanyMetalBalance
from app.domain.services.supply_tracking_service import SupplyTrackingService


@pytest.fixture
def seed_data(db_session):
    """Create the minimal entity graph needed for casting consumption tests."""
    tenant = Tenant(id=1, name="Test Co", subdomain="test")
    db_session.add(tenant)
    db_session.flush()

    user = User(
        id=1, tenant_id=1, email="u@test.com",
        hashed_password="x", full_name="Test User",
    )
    casting_dept = Department(id=1, tenant_id=1, name="Casting", is_active=True)
    polishing_dept = Department(id=2, tenant_id=1, name="Polishing", is_active=True)
    company = Company(id=1, tenant_id=1, name="Acme Jewelry")
    db_session.add_all([user, casting_dept, polishing_dept, company])
    db_session.flush()

    metal = Metal(
        id=1, tenant_id=1, code="GOLD_22K",
        name="Gold 22K", fine_percentage=0.916, is_active=True,
    )
    db_session.add(metal)
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
        "casting_dept_id": 1,
        "polishing_dept_id": 2,
        "order_id": 1,
        "metal_id": 1,
        "company_id": 1,
    }


class TestProcessCastingLedgerEntry:
    """Tests for process_casting_ledger_entry method"""

    def test_deducts_pure_metal_from_company_balance(self, db_session, seed_data):
        """Test that casting IN entry deducts pure metal from company balance"""
        # Setup: Give company some initial balance
        initial_balance = CompanyMetalBalance(
            tenant_id=seed_data["tenant_id"],
            company_id=seed_data["company_id"],
            metal_id=seed_data["metal_id"],
            balance_grams=100.0,
        )
        db_session.add(initial_balance)
        db_session.commit()

        # Create casting ledger entry
        ledger_entry = DepartmentLedgerEntry(
            tenant_id=seed_data["tenant_id"],
            date=date.today(),
            department_id=seed_data["casting_dept_id"],
            order_id=seed_data["order_id"],
            metal_id=seed_data["metal_id"],
            direction="IN",
            quantity=5.0,
            weight=50.0,  # gross weight
            fine_weight=50.0 * 0.916,  # pure weight
            created_by=seed_data["user_id"],
        )
        db_session.add(ledger_entry)
        db_session.commit()

        # Process the entry
        service = SupplyTrackingService(db_session)
        result = service.process_casting_ledger_entry(
            ledger_entry, seed_data["tenant_id"], seed_data["user_id"]
        )

        # Verify result
        assert result is not None
        assert result.fine_metal_grams == pytest.approx(50.0 * 0.916)
        assert result.company_id == seed_data["company_id"]
        assert result.order_id == seed_data["order_id"]
        assert result.metal_code == "GOLD_22K"

        # Verify balance was deducted
        expected_balance = 100.0 - (50.0 * 0.916)
        assert result.company_balance_after == pytest.approx(expected_balance)

        # Verify balance in database
        db_session.refresh(initial_balance)
        assert initial_balance.balance_grams == pytest.approx(expected_balance)

    def test_allows_negative_balance(self, db_session, seed_data):
        """Test that deduction is allowed even if balance goes negative"""
        # Setup: Give company small initial balance
        initial_balance = CompanyMetalBalance(
            tenant_id=seed_data["tenant_id"],
            company_id=seed_data["company_id"],
            metal_id=seed_data["metal_id"],
            balance_grams=10.0,
        )
        db_session.add(initial_balance)
        db_session.commit()

        # Create casting ledger entry that will make balance negative
        ledger_entry = DepartmentLedgerEntry(
            tenant_id=seed_data["tenant_id"],
            date=date.today(),
            department_id=seed_data["casting_dept_id"],
            order_id=seed_data["order_id"],
            metal_id=seed_data["metal_id"],
            direction="IN",
            quantity=5.0,
            weight=50.0,
            fine_weight=50.0 * 0.916,
            created_by=seed_data["user_id"],
        )
        db_session.add(ledger_entry)
        db_session.commit()

        # Process the entry
        service = SupplyTrackingService(db_session)
        result = service.process_casting_ledger_entry(
            ledger_entry, seed_data["tenant_id"], seed_data["user_id"]
        )

        # Verify negative balance is allowed
        assert result is not None
        expected_balance = 10.0 - (50.0 * 0.916)
        assert expected_balance < 0  # Verify it's actually negative
        assert result.company_balance_after == pytest.approx(expected_balance)

    def test_skips_non_casting_department(self, db_session, seed_data):
        """Test that non-casting department entries are skipped"""
        # Create polishing ledger entry
        ledger_entry = DepartmentLedgerEntry(
            tenant_id=seed_data["tenant_id"],
            date=date.today(),
            department_id=seed_data["polishing_dept_id"],  # Not casting
            order_id=seed_data["order_id"],
            metal_id=seed_data["metal_id"],
            direction="IN",
            quantity=5.0,
            weight=50.0,
            fine_weight=50.0 * 0.916,
            created_by=seed_data["user_id"],
        )
        db_session.add(ledger_entry)
        db_session.commit()

        # Process the entry
        service = SupplyTrackingService(db_session)
        result = service.process_casting_ledger_entry(
            ledger_entry, seed_data["tenant_id"], seed_data["user_id"]
        )

        # Verify it was skipped
        assert result is None

    def test_skips_out_direction(self, db_session, seed_data):
        """Test that OUT direction entries are skipped"""
        ledger_entry = DepartmentLedgerEntry(
            tenant_id=seed_data["tenant_id"],
            date=date.today(),
            department_id=seed_data["casting_dept_id"],
            order_id=seed_data["order_id"],
            metal_id=seed_data["metal_id"],
            direction="OUT",  # OUT direction
            quantity=5.0,
            weight=50.0,
            fine_weight=-50.0 * 0.916,
            created_by=seed_data["user_id"],
        )
        db_session.add(ledger_entry)
        db_session.commit()

        # Process the entry
        service = SupplyTrackingService(db_session)
        result = service.process_casting_ledger_entry(
            ledger_entry, seed_data["tenant_id"], seed_data["user_id"]
        )

        # Verify it was skipped
        assert result is None

    def test_creates_manufacturing_consumption_transaction(self, db_session, seed_data):
        """Test that MANUFACTURING_CONSUMPTION transaction is created"""
        # Setup initial balance
        initial_balance = CompanyMetalBalance(
            tenant_id=seed_data["tenant_id"],
            company_id=seed_data["company_id"],
            metal_id=seed_data["metal_id"],
            balance_grams=100.0,
        )
        db_session.add(initial_balance)
        db_session.commit()

        # Create casting ledger entry
        ledger_entry = DepartmentLedgerEntry(
            tenant_id=seed_data["tenant_id"],
            date=date.today(),
            department_id=seed_data["casting_dept_id"],
            order_id=seed_data["order_id"],
            metal_id=seed_data["metal_id"],
            direction="IN",
            quantity=5.0,
            weight=50.0,
            fine_weight=50.0 * 0.916,
            created_by=seed_data["user_id"],
        )
        db_session.add(ledger_entry)
        db_session.commit()

        # Process the entry
        service = SupplyTrackingService(db_session)
        service.process_casting_ledger_entry(
            ledger_entry, seed_data["tenant_id"], seed_data["user_id"]
        )

        # Verify transaction was created
        transactions = service.get_transactions(
            seed_data["tenant_id"],
            company_id=seed_data["company_id"],
            transaction_type="MANUFACTURING_CONSUMPTION",
        )
        assert len(transactions) == 1
        assert transactions[0].quantity_grams == pytest.approx(-(50.0 * 0.916))
        assert transactions[0].metal_id == seed_data["metal_id"]
        assert transactions[0].order_id == seed_data["order_id"]


class TestReverseCastingLedgerEntry:
    """Tests for reverse_casting_ledger_entry method"""

    def test_reverses_deduction_on_delete(self, db_session, seed_data):
        """Test that deleting a casting entry adds back the deducted amount"""
        # Setup: Create initial balance and process an entry
        initial_balance = CompanyMetalBalance(
            tenant_id=seed_data["tenant_id"],
            company_id=seed_data["company_id"],
            metal_id=seed_data["metal_id"],
            balance_grams=100.0,
        )
        db_session.add(initial_balance)
        db_session.commit()

        ledger_entry = DepartmentLedgerEntry(
            tenant_id=seed_data["tenant_id"],
            date=date.today(),
            department_id=seed_data["casting_dept_id"],
            order_id=seed_data["order_id"],
            metal_id=seed_data["metal_id"],
            direction="IN",
            quantity=5.0,
            weight=50.0,
            fine_weight=50.0 * 0.916,
            created_by=seed_data["user_id"],
        )
        db_session.add(ledger_entry)
        db_session.commit()

        service = SupplyTrackingService(db_session)
        service.process_casting_ledger_entry(
            ledger_entry, seed_data["tenant_id"], seed_data["user_id"]
        )

        # Get balance after deduction
        db_session.refresh(initial_balance)
        balance_after_deduction = initial_balance.balance_grams

        # Now reverse the entry
        result = service.reverse_casting_ledger_entry(
            ledger_entry, seed_data["tenant_id"], seed_data["user_id"]
        )

        # Verify reversal
        assert result is not None
        assert result.company_balance_after == pytest.approx(100.0)  # Back to original

        # Verify balance in database
        db_session.refresh(initial_balance)
        assert initial_balance.balance_grams == pytest.approx(100.0)

    def test_creates_reversal_transaction(self, db_session, seed_data):
        """Test that reversal creates a positive transaction"""
        # Setup
        initial_balance = CompanyMetalBalance(
            tenant_id=seed_data["tenant_id"],
            company_id=seed_data["company_id"],
            metal_id=seed_data["metal_id"],
            balance_grams=100.0,
        )
        db_session.add(initial_balance)
        db_session.commit()

        ledger_entry = DepartmentLedgerEntry(
            tenant_id=seed_data["tenant_id"],
            date=date.today(),
            department_id=seed_data["casting_dept_id"],
            order_id=seed_data["order_id"],
            metal_id=seed_data["metal_id"],
            direction="IN",
            quantity=5.0,
            weight=50.0,
            fine_weight=50.0 * 0.916,
            created_by=seed_data["user_id"],
        )
        db_session.add(ledger_entry)
        db_session.commit()

        service = SupplyTrackingService(db_session)
        service.process_casting_ledger_entry(
            ledger_entry, seed_data["tenant_id"], seed_data["user_id"]
        )
        service.reverse_casting_ledger_entry(
            ledger_entry, seed_data["tenant_id"], seed_data["user_id"]
        )

        # Verify transactions
        transactions = service.get_transactions(
            seed_data["tenant_id"],
            company_id=seed_data["company_id"],
            transaction_type="MANUFACTURING_CONSUMPTION",
        )
        assert len(transactions) == 2
        # Transactions may be in any order, so check both exist
        quantities = [t.quantity_grams for t in transactions]
        assert any(q < 0 for q in quantities), "Should have negative consumption"
        assert any(q > 0 for q in quantities), "Should have positive reversal"
        # Verify they cancel out
        assert abs(quantities[0]) == pytest.approx(abs(quantities[1]))


class TestUpdateCastingLedgerEntry:
    """Tests for update_casting_ledger_entry method"""

    def test_updates_consumption_correctly(self, db_session, seed_data):
        """Test that updating an entry reverses old and applies new deduction"""
        # Setup
        initial_balance = CompanyMetalBalance(
            tenant_id=seed_data["tenant_id"],
            company_id=seed_data["company_id"],
            metal_id=seed_data["metal_id"],
            balance_grams=100.0,
        )
        db_session.add(initial_balance)
        db_session.commit()

        # Create old entry
        old_entry = DepartmentLedgerEntry(
            tenant_id=seed_data["tenant_id"],
            date=date.today(),
            department_id=seed_data["casting_dept_id"],
            order_id=seed_data["order_id"],
            metal_id=seed_data["metal_id"],
            direction="IN",
            quantity=5.0,
            weight=50.0,  # Old weight
            fine_weight=50.0 * 0.916,
            created_by=seed_data["user_id"],
        )
        db_session.add(old_entry)
        db_session.commit()

        service = SupplyTrackingService(db_session)
        service.process_casting_ledger_entry(
            old_entry, seed_data["tenant_id"], seed_data["user_id"]
        )

        # Create new entry with different weight
        new_entry = DepartmentLedgerEntry(
            id=old_entry.id,
            tenant_id=seed_data["tenant_id"],
            date=date.today(),
            department_id=seed_data["casting_dept_id"],
            order_id=seed_data["order_id"],
            metal_id=seed_data["metal_id"],
            direction="IN",
            quantity=5.0,
            weight=30.0,  # New weight (less)
            fine_weight=30.0 * 0.916,
            created_by=seed_data["user_id"],
        )

        # Update the entry
        result = service.update_casting_ledger_entry(
            old_entry, new_entry, seed_data["tenant_id"], seed_data["user_id"]
        )

        # Verify result
        assert result is not None
        expected_balance = 100.0 - (30.0 * 0.916)  # New weight deduction
        assert result.company_balance_after == pytest.approx(expected_balance)

        # Verify balance in database
        db_session.refresh(initial_balance)
        assert initial_balance.balance_grams == pytest.approx(expected_balance)


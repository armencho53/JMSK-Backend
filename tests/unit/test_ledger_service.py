"""Unit tests for LedgerService"""
import pytest
from datetime import date

from app.data.models.tenant import Tenant
from app.data.models.user import User
from app.data.models.department import Department
from app.data.models.company import Company
from app.data.models.contact import Contact
from app.data.models.order import Order
from app.data.models.metal import Metal
from app.data.models.department_balance import DepartmentBalance
from app.domain.services.ledger_service import LedgerService
from app.domain.exceptions import ResourceNotFoundError, ValidationError
from app.schemas.ledger import LedgerEntryCreate, LedgerEntryUpdate


@pytest.fixture
def seed_data(db_session):
    """Create the minimal entity graph needed for ledger tests."""
    tenant = Tenant(id=1, name="Test Co", subdomain="test")
    db_session.add(tenant)
    db_session.flush()

    user = User(
        id=1, tenant_id=1, email="u@test.com",
        hashed_password="x", full_name="Test User",
    )
    dept = Department(id=1, tenant_id=1, name="Casting")
    dept2 = Department(id=2, tenant_id=1, name="Polishing")
    company = Company(id=1, tenant_id=1, name="Acme Jewelry")
    db_session.add_all([user, dept, dept2, company])
    db_session.flush()

    metal = Metal(
        id=1, tenant_id=1, code="GOLD_22K",
        name="Gold 22K", fine_percentage=0.916,
    )
    metal2 = Metal(
        id=2, tenant_id=1, code="SILVER_925",
        name="Silver 925", fine_percentage=0.925,
    )
    db_session.add_all([metal, metal2])
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
        "tenant_id": 1, "user_id": 1,
        "department_id": 1, "department_id_2": 2,
        "order_id": 1, "metal_id": 1,
    }


def _make_create_data(**overrides):
    defaults = dict(
        date=date(2025, 1, 15),
        department_id=1,
        order_id=1,
        metal_id=1,
        direction="IN",
        quantity=5.0,
        weight=28.9,
    )
    defaults.update(overrides)
    return LedgerEntryCreate(**defaults)


# ── create_entry ──────────────────────────────────────────────

class TestCreateEntry:
    def test_creates_in_entry_with_positive_fine_weight(self, db_session, seed_data):
        svc = LedgerService(db_session)
        data = _make_create_data(direction="IN", weight=28.9)
        resp = svc.create_entry(data, seed_data["tenant_id"], seed_data["user_id"])

        assert resp.id is not None
        assert resp.direction == "IN"
        assert resp.qty_in == 5.0
        assert resp.weight_in == 28.9
        assert resp.qty_out is None
        assert resp.weight_out is None
        assert resp.fine_weight == pytest.approx(28.9 * 0.916)

    def test_creates_out_entry_with_negative_fine_weight(self, db_session, seed_data):
        svc = LedgerService(db_session)
        data = _make_create_data(direction="OUT", weight=10.0)
        resp = svc.create_entry(data, seed_data["tenant_id"], seed_data["user_id"])

        assert resp.direction == "OUT"
        assert resp.qty_out == 5.0
        assert resp.weight_out == 10.0
        assert resp.qty_in is None
        assert resp.weight_in is None
        assert resp.fine_weight == pytest.approx(-10.0 * 0.916)

    def test_increases_balance_on_in(self, db_session, seed_data):
        svc = LedgerService(db_session)
        data = _make_create_data(direction="IN", weight=20.0)
        svc.create_entry(data, seed_data["tenant_id"], seed_data["user_id"])

        bal = db_session.query(DepartmentBalance).filter_by(
            department_id=1, metal_id=1
        ).first()
        assert bal is not None
        assert bal.balance_grams == pytest.approx(20.0)

    def test_decreases_balance_on_out(self, db_session, seed_data):
        svc = LedgerService(db_session)
        # First add some stock
        svc.create_entry(
            _make_create_data(direction="IN", weight=50.0),
            seed_data["tenant_id"], seed_data["user_id"],
        )
        # Then take some out
        svc.create_entry(
            _make_create_data(direction="OUT", weight=15.0),
            seed_data["tenant_id"], seed_data["user_id"],
        )

        bal = db_session.query(DepartmentBalance).filter_by(
            department_id=1, metal_id=1
        ).first()
        assert bal.balance_grams == pytest.approx(35.0)

    def test_rejects_invalid_metal_id(self, db_session, seed_data):
        svc = LedgerService(db_session)
        data = _make_create_data(metal_id=9999)
        with pytest.raises(ValidationError, match="Metal with id '9999' not found"):
            svc.create_entry(data, seed_data["tenant_id"], seed_data["user_id"])

    def test_stores_notes_and_created_by(self, db_session, seed_data):
        svc = LedgerService(db_session)
        data = _make_create_data(notes="Test note")
        resp = svc.create_entry(data, seed_data["tenant_id"], seed_data["user_id"])
        assert resp.notes == "Test note"
        assert resp.created_by == seed_data["user_id"]


# ── update_entry ──────────────────────────────────────────────

class TestUpdateEntry:
    def test_updates_weight_and_recomputes_fine_weight(self, db_session, seed_data):
        svc = LedgerService(db_session)
        created = svc.create_entry(
            _make_create_data(direction="IN", weight=20.0),
            seed_data["tenant_id"], seed_data["user_id"],
        )
        updated = svc.update_entry(
            created.id,
            LedgerEntryUpdate(weight=30.0),
            seed_data["tenant_id"],
        )
        assert updated.weight_in == 30.0
        assert updated.fine_weight == pytest.approx(30.0 * 0.916)

    def test_reverses_old_balance_and_applies_new(self, db_session, seed_data):
        svc = LedgerService(db_session)
        created = svc.create_entry(
            _make_create_data(direction="IN", weight=20.0),
            seed_data["tenant_id"], seed_data["user_id"],
        )
        svc.update_entry(
            created.id,
            LedgerEntryUpdate(weight=30.0),
            seed_data["tenant_id"],
        )
        bal = db_session.query(DepartmentBalance).filter_by(
            department_id=1, metal_id=1
        ).first()
        assert bal.balance_grams == pytest.approx(30.0)

    def test_direction_change_updates_balance_correctly(self, db_session, seed_data):
        svc = LedgerService(db_session)
        created = svc.create_entry(
            _make_create_data(direction="IN", weight=20.0),
            seed_data["tenant_id"], seed_data["user_id"],
        )
        # Change from IN to OUT
        svc.update_entry(
            created.id,
            LedgerEntryUpdate(direction="OUT"),
            seed_data["tenant_id"],
        )
        bal = db_session.query(DepartmentBalance).filter_by(
            department_id=1, metal_id=1
        ).first()
        # Was +20, now should be -20
        assert bal.balance_grams == pytest.approx(-20.0)

    def test_raises_not_found_for_missing_entry(self, db_session, seed_data):
        svc = LedgerService(db_session)
        with pytest.raises(ResourceNotFoundError):
            svc.update_entry(999, LedgerEntryUpdate(weight=10.0), seed_data["tenant_id"])

    def test_raises_not_found_for_wrong_tenant(self, db_session, seed_data):
        svc = LedgerService(db_session)
        created = svc.create_entry(
            _make_create_data(), seed_data["tenant_id"], seed_data["user_id"],
        )
        with pytest.raises(ResourceNotFoundError):
            svc.update_entry(created.id, LedgerEntryUpdate(weight=10.0), tenant_id=999)


# ── delete_entry ──────────────────────────────────────────────

class TestDeleteEntry:
    def test_reverses_balance_on_delete(self, db_session, seed_data):
        svc = LedgerService(db_session)
        created = svc.create_entry(
            _make_create_data(direction="IN", weight=25.0),
            seed_data["tenant_id"], seed_data["user_id"],
        )
        svc.delete_entry(created.id, seed_data["tenant_id"])

        bal = db_session.query(DepartmentBalance).filter_by(
            department_id=1, metal_id=1
        ).first()
        assert bal.balance_grams == pytest.approx(0.0)

    def test_raises_not_found_for_missing_entry(self, db_session, seed_data):
        svc = LedgerService(db_session)
        with pytest.raises(ResourceNotFoundError):
            svc.delete_entry(999, seed_data["tenant_id"])


# ── list_entries ──────────────────────────────────────────────

class TestListEntries:
    def test_returns_entries_for_tenant(self, db_session, seed_data):
        svc = LedgerService(db_session)
        svc.create_entry(_make_create_data(), seed_data["tenant_id"], seed_data["user_id"])
        svc.create_entry(_make_create_data(), seed_data["tenant_id"], seed_data["user_id"])

        entries = svc.list_entries(seed_data["tenant_id"])
        assert len(entries) == 2

    def test_filters_by_department(self, db_session, seed_data):
        svc = LedgerService(db_session)
        svc.create_entry(
            _make_create_data(department_id=1),
            seed_data["tenant_id"], seed_data["user_id"],
        )
        svc.create_entry(
            _make_create_data(department_id=2),
            seed_data["tenant_id"], seed_data["user_id"],
        )

        entries = svc.list_entries(seed_data["tenant_id"], department_id=1)
        assert len(entries) == 1
        assert entries[0].department_id == 1

    def test_filters_by_date_range(self, db_session, seed_data):
        svc = LedgerService(db_session)
        svc.create_entry(
            _make_create_data(date=date(2025, 1, 10)),
            seed_data["tenant_id"], seed_data["user_id"],
        )
        svc.create_entry(
            _make_create_data(date=date(2025, 1, 20)),
            seed_data["tenant_id"], seed_data["user_id"],
        )

        entries = svc.list_entries(
            seed_data["tenant_id"],
            date_from=date(2025, 1, 15),
            date_to=date(2025, 1, 25),
        )
        assert len(entries) == 1

    def test_excludes_archived_by_default(self, db_session, seed_data):
        svc = LedgerService(db_session)
        svc.create_entry(_make_create_data(), seed_data["tenant_id"], seed_data["user_id"])
        svc.create_entry(
            _make_create_data(date=date(2025, 1, 15)),
            seed_data["tenant_id"], seed_data["user_id"],
        )
        svc.archive_entries(seed_data["tenant_id"], date(2025, 1, 1), date(2025, 1, 31))

        entries = svc.list_entries(seed_data["tenant_id"])
        assert len(entries) == 0

    def test_includes_archived_when_requested(self, db_session, seed_data):
        svc = LedgerService(db_session)
        svc.create_entry(_make_create_data(), seed_data["tenant_id"], seed_data["user_id"])
        svc.archive_entries(seed_data["tenant_id"], date(2025, 1, 1), date(2025, 1, 31))

        entries = svc.list_entries(seed_data["tenant_id"], include_archived=True)
        assert len(entries) == 1


# ── get_summary ───────────────────────────────────────────────

class TestGetSummary:
    def test_aggregates_qty_and_fine_weight(self, db_session, seed_data):
        svc = LedgerService(db_session)
        svc.create_entry(
            _make_create_data(direction="IN", quantity=10, weight=50.0),
            seed_data["tenant_id"], seed_data["user_id"],
        )
        svc.create_entry(
            _make_create_data(direction="OUT", quantity=3, weight=15.0),
            seed_data["tenant_id"], seed_data["user_id"],
        )

        summary = svc.get_summary(seed_data["tenant_id"])
        assert summary.total_qty_held == pytest.approx(7.0)
        assert summary.total_qty_out == pytest.approx(3.0)
        assert len(summary.balances) == 1
        assert summary.balances[0].metal_id == 1
        assert summary.balances[0].metal_name == "Gold 22K"
        expected_fw = (50.0 * 0.916) + (-15.0 * 0.916)
        assert summary.balances[0].fine_weight_balance == pytest.approx(expected_fw)

    def test_excludes_zero_balance_metals(self, db_session, seed_data):
        svc = LedgerService(db_session)
        # Create IN and matching OUT so fine_weight sums to zero
        svc.create_entry(
            _make_create_data(direction="IN", quantity=5, weight=20.0),
            seed_data["tenant_id"], seed_data["user_id"],
        )
        svc.create_entry(
            _make_create_data(direction="OUT", quantity=5, weight=20.0),
            seed_data["tenant_id"], seed_data["user_id"],
        )

        summary = svc.get_summary(seed_data["tenant_id"])
        assert len(summary.balances) == 0


# ── archive / unarchive ──────────────────────────────────────

class TestArchiveUnarchive:
    def test_archive_marks_entries_in_range(self, db_session, seed_data):
        svc = LedgerService(db_session)
        svc.create_entry(
            _make_create_data(date=date(2025, 1, 10)),
            seed_data["tenant_id"], seed_data["user_id"],
        )
        svc.create_entry(
            _make_create_data(date=date(2025, 2, 10)),
            seed_data["tenant_id"], seed_data["user_id"],
        )

        count = svc.archive_entries(seed_data["tenant_id"], date(2025, 1, 1), date(2025, 1, 31))
        assert count == 1

        entries = svc.list_entries(seed_data["tenant_id"], include_archived=True)
        archived = [e for e in entries if e.is_archived]
        assert len(archived) == 1

    def test_unarchive_restores_entry(self, db_session, seed_data):
        svc = LedgerService(db_session)
        created = svc.create_entry(
            _make_create_data(), seed_data["tenant_id"], seed_data["user_id"],
        )
        svc.archive_entries(seed_data["tenant_id"], date(2025, 1, 1), date(2025, 1, 31))

        restored = svc.unarchive_entry(created.id, seed_data["tenant_id"])
        assert restored.is_archived is False

    def test_unarchive_raises_not_found(self, db_session, seed_data):
        svc = LedgerService(db_session)
        with pytest.raises(ResourceNotFoundError):
            svc.unarchive_entry(999, seed_data["tenant_id"])

"""Unit tests for Contact Pydantic schemas."""
import pytest
from pydantic import ValidationError
from datetime import datetime
from app.schemas.contact import (
    ContactBase, ContactCreate, ContactUpdate, ContactResponse,
    CompanySummary, ContactListResponse,
)


class TestContactCreate:
    def test_valid(self):
        c = ContactCreate(name="John Doe", email="john@example.com", company_id=1)
        assert c.name == "John Doe"

    def test_minimal(self):
        c = ContactCreate(name="Jane", company_id=2)
        assert c.email is None
        assert c.phone is None

    def test_missing_name(self):
        with pytest.raises(ValidationError):
            ContactCreate(company_id=1)

    def test_missing_company_id(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="John")

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="", company_id=1)

    def test_whitespace_name(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="   ", company_id=1)

    def test_name_trimmed(self):
        c = ContactCreate(name="  John Doe  ", company_id=1)
        assert c.name == "John Doe"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="John", email="bad", company_id=1)

    def test_invalid_company_id(self):
        with pytest.raises(ValidationError):
            ContactCreate(name="John", company_id=0)


class TestContactUpdate:
    def test_all_optional(self):
        c = ContactUpdate()
        assert c.name is None

    def test_partial(self):
        c = ContactUpdate(name="Updated")
        assert c.name == "Updated"
        assert c.email is None

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ContactUpdate(name="")

    def test_whitespace_name_rejected(self):
        with pytest.raises(ValidationError):
            ContactUpdate(name="   ")


class TestContactResponse:
    def test_full(self):
        now = datetime.utcnow()
        c = ContactResponse(
            id=1, tenant_id=1, name="John", email="j@test.com",
            phone="555-1234", company_id=1, created_at=now, updated_at=now,
            company=CompanySummary(id=1, name="Acme"),
        )
        assert c.company.name == "Acme"

    def test_without_company(self):
        now = datetime.utcnow()
        c = ContactResponse(
            id=1, tenant_id=1, name="John", company_id=1,
            created_at=now, updated_at=now,
        )
        assert c.company is None


class TestContactListResponse:
    def test_empty(self):
        r = ContactListResponse(contacts=[], total=0)
        assert len(r.contacts) == 0
        assert r.page == 1
        assert r.page_size == 50

"""Tests for order metal_type validation against lookup values.

Validates Requirement 6.1: WHEN an order is created or updated with a metal_type value,
THE Lookup_Service SHALL validate that the value exists as an active Lookup_Value
in the "metal_type" category for the requesting tenant.
"""

import pytest
from sqlalchemy.orm import Session

from app.domain.services.lookup_service import LookupService
from app.domain.exceptions import ValidationError
from app.data.models.lookup_value import LookupValue


class TestMetalTypeValidation:
    """Test metal_type validation via LookupService.validate_lookup_code."""

    def _seed_metal_types(self, db: Session, tenant_id: int):
        """Helper to seed metal_type lookup values for a tenant."""
        values = [
            ("metal_type", "GOLD_24K", "Gold 24K", 0),
            ("metal_type", "GOLD_18K", "Gold 18K", 1),
            ("metal_type", "SILVER_925", "Silver 925", 2),
        ]
        for category, code, label, sort_order in values:
            lv = LookupValue(
                tenant_id=tenant_id,
                category=category,
                code=code,
                display_label=label,
                sort_order=sort_order,
            )
            db.add(lv)
        db.commit()

    def test_valid_metal_type_accepted(self, db: Session):
        """A valid metal_type code should pass validation."""
        self._seed_metal_types(db, tenant_id=1)
        service = LookupService(db)
        assert service.validate_lookup_code(1, "metal_type", "GOLD_24K") is True

    def test_invalid_metal_type_rejected(self, db: Session):
        """An invalid metal_type code should raise ValidationError."""
        self._seed_metal_types(db, tenant_id=1)
        service = LookupService(db)
        with pytest.raises(ValidationError) as exc_info:
            service.validate_lookup_code(1, "metal_type", "INVALID_METAL")
        assert "Invalid metal_type value 'INVALID_METAL'" in exc_info.value.message
        assert "GOLD_24K" in exc_info.value.message

    def test_no_lookup_values_skips_validation(self, db: Session):
        """When no lookup values exist for the category, validation should pass."""
        service = LookupService(db)
        # No lookup values seeded — should not raise
        assert service.validate_lookup_code(1, "metal_type", "ANY_VALUE") is True

    def test_inactive_metal_type_rejected(self, db: Session):
        """An inactive metal_type code should not pass validation."""
        lv = LookupValue(
            tenant_id=1,
            category="metal_type",
            code="GOLD_24K",
            display_label="Gold 24K",
            sort_order=0,
            is_active=False,
        )
        db.add(lv)
        # Add one active value so the category isn't empty
        lv_active = LookupValue(
            tenant_id=1,
            category="metal_type",
            code="SILVER_925",
            display_label="Silver 925",
            sort_order=1,
            is_active=True,
        )
        db.add(lv_active)
        db.commit()

        service = LookupService(db)
        with pytest.raises(ValidationError):
            service.validate_lookup_code(1, "metal_type", "GOLD_24K")

    def test_validation_is_tenant_scoped(self, db: Session):
        """Validation should only check lookup values for the requesting tenant."""
        # Seed for tenant 1
        self._seed_metal_types(db, tenant_id=1)
        service = LookupService(db)

        # Tenant 1 should validate fine
        assert service.validate_lookup_code(1, "metal_type", "GOLD_24K") is True

        # Tenant 2 has no lookup values — should skip validation
        assert service.validate_lookup_code(2, "metal_type", "GOLD_24K") is True

    def test_validation_error_lists_valid_options(self, db: Session):
        """The error message should list all valid options."""
        self._seed_metal_types(db, tenant_id=1)
        service = LookupService(db)
        with pytest.raises(ValidationError) as exc_info:
            service.validate_lookup_code(1, "metal_type", "BAD_VALUE")
        msg = exc_info.value.message
        assert "GOLD_24K" in msg
        assert "GOLD_18K" in msg
        assert "SILVER_925" in msg

"""Tests for supply type validation against lookup values.

Validates Requirement 6.3: WHEN a supply is created or updated with a type value,
THE Lookup_Service SHALL validate that the value exists as an active Lookup_Value
in the "supply_type" category for the requesting tenant.
"""

import pytest
from sqlalchemy.orm import Session

from app.domain.services.lookup_service import LookupService
from app.domain.exceptions import ValidationError
from app.data.models.lookup_value import LookupValue


class TestSupplyTypeValidation:
    """Test supply type validation via LookupService.validate_lookup_code."""

    def _seed_supply_types(self, db: Session, tenant_id: int):
        """Helper to seed supply_type lookup values for a tenant."""
        values = [
            ("supply_type", "METAL", "Metal", 0),
            ("supply_type", "GEMSTONE", "Gemstone", 1),
            ("supply_type", "TOOL", "Tool", 2),
            ("supply_type", "PACKAGING", "Packaging", 3),
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

    def test_valid_supply_type_accepted(self, db: Session):
        """A valid supply_type code should pass validation."""
        self._seed_supply_types(db, tenant_id=1)
        service = LookupService(db)
        assert service.validate_lookup_code(1, "supply_type", "METAL") is True

    def test_all_seeded_supply_types_accepted(self, db: Session):
        """All seeded supply_type codes should pass validation."""
        self._seed_supply_types(db, tenant_id=1)
        service = LookupService(db)
        for code in ["METAL", "GEMSTONE", "TOOL", "PACKAGING"]:
            assert service.validate_lookup_code(1, "supply_type", code) is True

    def test_invalid_supply_type_rejected(self, db: Session):
        """An invalid supply_type code should raise ValidationError."""
        self._seed_supply_types(db, tenant_id=1)
        service = LookupService(db)
        with pytest.raises(ValidationError) as exc_info:
            service.validate_lookup_code(1, "supply_type", "INVALID_TYPE")
        assert "Invalid supply_type value 'INVALID_TYPE'" in exc_info.value.message
        assert "METAL" in exc_info.value.message

    def test_no_lookup_values_skips_validation(self, db: Session):
        """When no lookup values exist for the category, validation should pass."""
        service = LookupService(db)
        assert service.validate_lookup_code(1, "supply_type", "ANY_VALUE") is True

    def test_inactive_supply_type_rejected(self, db: Session):
        """An inactive supply_type code should not pass validation."""
        lv_inactive = LookupValue(
            tenant_id=1,
            category="supply_type",
            code="METAL",
            display_label="Metal",
            sort_order=0,
            is_active=False,
        )
        db.add(lv_inactive)
        lv_active = LookupValue(
            tenant_id=1,
            category="supply_type",
            code="GEMSTONE",
            display_label="Gemstone",
            sort_order=1,
            is_active=True,
        )
        db.add(lv_active)
        db.commit()

        service = LookupService(db)
        with pytest.raises(ValidationError):
            service.validate_lookup_code(1, "supply_type", "METAL")

    def test_validation_is_tenant_scoped(self, db: Session):
        """Validation should only check lookup values for the requesting tenant."""
        self._seed_supply_types(db, tenant_id=1)
        service = LookupService(db)

        assert service.validate_lookup_code(1, "supply_type", "METAL") is True
        # Tenant 2 has no lookup values — should skip validation
        assert service.validate_lookup_code(2, "supply_type", "METAL") is True

    def test_validation_error_lists_valid_options(self, db: Session):
        """The error message should list all valid options."""
        self._seed_supply_types(db, tenant_id=1)
        service = LookupService(db)
        with pytest.raises(ValidationError) as exc_info:
            service.validate_lookup_code(1, "supply_type", "BAD_VALUE")
        msg = exc_info.value.message
        assert "METAL" in msg
        assert "GEMSTONE" in msg
        assert "TOOL" in msg
        assert "PACKAGING" in msg

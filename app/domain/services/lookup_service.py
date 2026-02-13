"""Lookup value business logic service"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.data.repositories.lookup_repository import LookupRepository
from app.data.models.lookup_value import LookupValue
from app.schemas.lookup_value import (
    LookupValueCreate,
    LookupValueUpdate,
    LookupValueResponse,
)
from app.domain.exceptions import (
    ResourceNotFoundError,
    DuplicateResourceError,
    ValidationError,
)

# Default seed data for new tenants
# Each tuple: (category, code, display_label, sort_order)
DEFAULT_LOOKUP_VALUES = [
    ("metal_type", "GOLD_24K", "Gold 24K", 0),
    ("metal_type", "GOLD_22K", "Gold 22K", 1),
    ("metal_type", "GOLD_18K", "Gold 18K", 2),
    ("metal_type", "GOLD_14K", "Gold 14K", 3),
    ("metal_type", "SILVER_925", "Silver 925", 4),
    ("metal_type", "PLATINUM", "Platinum", 5),
    ("metal_type", "OTHER", "Other", 6),
    ("step_type", "DESIGN", "Design", 0),
    ("step_type", "CASTING", "Casting", 1),
    ("step_type", "STONE_SETTING", "Stone Setting", 2),
    ("step_type", "POLISHING", "Polishing", 3),
    ("step_type", "ENGRAVING", "Engraving", 4),
    ("step_type", "QUALITY_CHECK", "Quality Check", 5),
    ("step_type", "FINISHING", "Finishing", 6),
    ("step_type", "OTHER", "Other", 7),
    ("supply_type", "METAL", "Metal", 0),
    ("supply_type", "GEMSTONE", "Gemstone", 1),
    ("supply_type", "TOOL", "Tool", 2),
    ("supply_type", "PACKAGING", "Packaging", 3),
    ("supply_type", "OTHER", "Other", 4),
]


class LookupService:
    """
    Service for lookup value business logic.

    Implements business logic for tenant-scoped configurable enum values
    including CRUD operations, validation, and default seeding.
    All operations enforce multi-tenant isolation.

    Requirements: 3.2, 4.1-4.6, 5.3-5.7, 6.1-6.4
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = LookupRepository(db)

    def get_by_category(
        self,
        tenant_id: int,
        category: str,
        include_inactive: bool = False,
    ) -> List[LookupValueResponse]:
        """
        Get lookup values for a category, ordered by sort_order.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            category: Category to filter by (e.g., "metal_type")
            include_inactive: If True, include inactive values

        Returns:
            List of LookupValueResponse ordered by sort_order

        Requirements: 5.1, 5.8
        """
        if include_inactive:
            values = self.repository.get_all_by_category(
                tenant_id, category, include_inactive=True
            )
        else:
            values = self.repository.get_active_by_category(tenant_id, category)
        return [LookupValueResponse.model_validate(v) for v in values]

    def get_all_grouped(
        self,
        tenant_id: int,
        include_inactive: bool = False,
    ) -> Dict[str, List[LookupValueResponse]]:
        """
        Get all lookup values grouped by category.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            include_inactive: If True, include inactive values

        Returns:
            Dict mapping category names to lists of LookupValueResponse

        Requirements: 5.2
        """
        grouped = self.repository.get_all_grouped(tenant_id, include_inactive)
        return {
            category: [LookupValueResponse.model_validate(v) for v in values]
            for category, values in grouped.items()
        }

    def create_lookup_value(
        self,
        data: LookupValueCreate,
        tenant_id: int,
    ) -> LookupValueResponse:
        """
        Create a new lookup value for a tenant.

        Normalizes code to UPPER_CASE and checks for duplicates
        within the same tenant+category.

        Args:
            data: Lookup value creation data
            tenant_id: Tenant ID from authenticated user's JWT

        Returns:
            Created LookupValueResponse

        Raises:
            DuplicateResourceError: If code already exists in category for tenant

        Requirements: 3.2, 5.3, 5.4
        """
        # Code is already auto-uppercased by the Pydantic schema validator
        normalized_code = data.code

        if self.repository.code_exists(tenant_id, data.category, normalized_code):
            raise DuplicateResourceError(
                "LookupValue",
                f"code '{normalized_code}' already exists in category",
                data.category,
            )

        lookup_value = LookupValue(
            tenant_id=tenant_id,
            category=data.category,
            code=normalized_code,
            display_label=data.display_label,
            sort_order=data.sort_order,
        )
        lookup_value = self.repository.create(lookup_value)
        return LookupValueResponse.model_validate(lookup_value)

    def update_lookup_value(
        self,
        lookup_id: int,
        data: LookupValueUpdate,
        tenant_id: int,
    ) -> LookupValueResponse:
        """
        Update an existing lookup value.

        Only display_label, sort_order, and is_active can be modified.
        Code and category are immutable after creation.

        Args:
            lookup_id: ID of the lookup value to update
            data: Update data (only mutable fields)
            tenant_id: Tenant ID for multi-tenant isolation

        Returns:
            Updated LookupValueResponse

        Raises:
            ResourceNotFoundError: If lookup value not found for tenant

        Requirements: 5.5, 5.6
        """
        lookup_value = self.repository.get_by_id(lookup_id, tenant_id)
        if not lookup_value:
            raise ResourceNotFoundError("LookupValue", lookup_id)

        # Update only mutable fields that were provided
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(lookup_value, field, value)

        lookup_value = self.repository.update(lookup_value)
        return LookupValueResponse.model_validate(lookup_value)

    def deactivate_lookup_value(
        self,
        lookup_id: int,
        tenant_id: int,
    ) -> LookupValueResponse:
        """
        Soft delete a lookup value by setting is_active to false.

        Args:
            lookup_id: ID of the lookup value to deactivate
            tenant_id: Tenant ID for multi-tenant isolation

        Returns:
            Deactivated LookupValueResponse

        Raises:
            ResourceNotFoundError: If lookup value not found for tenant

        Requirements: 5.7
        """
        lookup_value = self.repository.get_by_id(lookup_id, tenant_id)
        if not lookup_value:
            raise ResourceNotFoundError("LookupValue", lookup_id)

        lookup_value.is_active = False
        lookup_value = self.repository.update(lookup_value)
        return LookupValueResponse.model_validate(lookup_value)

    def validate_lookup_code(
        self,
        tenant_id: int,
        category: str,
        code: str,
    ) -> bool:
        """
        Validate that a code exists as an active lookup value for a tenant+category.

        Used by other services (orders, manufacturing, supplies) to validate
        configurable enum field values against the lookup_values table.

        If no lookup values exist for the tenant+category, validation is skipped
        to maintain backward compatibility with tenants that haven't been seeded.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            category: Category to validate against (e.g., "metal_type")
            code: Code value to validate

        Returns:
            True if the code is valid

        Raises:
            ValidationError: If code does not match any active lookup value,
                with a message listing valid options

        Requirements: 6.1, 6.2, 6.3, 6.4
        """
        active_values = self.repository.get_active_by_category(tenant_id, category)
        active_codes = [v.code for v in active_values]

        # Skip validation if no lookup values exist for this tenant+category
        # (backward compatibility for tenants that haven't been seeded)
        if not active_codes:
            return True

        if code in active_codes:
            return True

        valid_options = ", ".join(active_codes)
        raise ValidationError(
            f"Invalid {category} value '{code}'. Valid options: {valid_options}"
        )

    def seed_defaults(self, tenant_id: int) -> None:
        """
        Seed default lookup values for a tenant. Idempotent.

        Creates the standard set of lookup values (metal_type, step_type,
        supply_type) for a tenant. Skips any values that already exist,
        making it safe to call multiple times.

        Args:
            tenant_id: Tenant ID to seed defaults for

        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
        """
        for category, code, display_label, sort_order in DEFAULT_LOOKUP_VALUES:
            if not self.repository.code_exists(tenant_id, category, code):
                lookup_value = LookupValue(
                    tenant_id=tenant_id,
                    category=category,
                    code=code,
                    display_label=display_label,
                    sort_order=sort_order,
                )
                self.repository.create(lookup_value)

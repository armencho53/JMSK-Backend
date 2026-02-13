"""Lookup value repository for data access"""
from typing import Dict, List, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from app.data.repositories.base import BaseRepository
from app.data.models.lookup_value import LookupValue


class LookupRepository(BaseRepository[LookupValue]):
    """
    Repository for lookup value data access operations.

    Provides CRUD operations and specialized queries for tenant-scoped
    configurable enum values. All operations enforce multi-tenant isolation
    through tenant_id filtering.

    Requirements: 3.1, 3.4
    """

    def __init__(self, db: Session):
        super().__init__(LookupValue, db)

    def get_active_by_category(
        self,
        tenant_id: int,
        category: str,
    ) -> List[LookupValue]:
        """
        Get all active lookup values for a category, ordered by sort_order.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            category: Category to filter by (e.g., "metal_type")

        Returns:
            List of active LookupValue records ordered by sort_order ascending

        Requirements: 3.1, 3.4
        """
        return (
            self.db.query(LookupValue)
            .filter(
                LookupValue.tenant_id == tenant_id,
                LookupValue.category == category,
                LookupValue.is_active == True,
            )
            .order_by(LookupValue.sort_order.asc())
            .all()
        )

    def get_all_by_category(
        self,
        tenant_id: int,
        category: str,
        include_inactive: bool = False,
    ) -> List[LookupValue]:
        """
        Get all lookup values for a category, optionally including inactive.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            category: Category to filter by
            include_inactive: If True, include inactive values

        Returns:
            List of LookupValue records ordered by sort_order ascending

        Requirements: 3.1, 3.4
        """
        query = self.db.query(LookupValue).filter(
            LookupValue.tenant_id == tenant_id,
            LookupValue.category == category,
        )
        if not include_inactive:
            query = query.filter(LookupValue.is_active == True)
        return query.order_by(LookupValue.sort_order.asc()).all()

    def get_by_code(
        self,
        tenant_id: int,
        category: str,
        code: str,
    ) -> Optional[LookupValue]:
        """
        Find a specific lookup value by its unique key (tenant_id, category, code).

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            category: Category of the lookup value
            code: UPPER_CASE code identifier

        Returns:
            LookupValue if found, None otherwise

        Requirements: 3.1, 3.4
        """
        return (
            self.db.query(LookupValue)
            .filter(
                LookupValue.tenant_id == tenant_id,
                LookupValue.category == category,
                LookupValue.code == code,
            )
            .first()
        )

    def get_all_grouped(
        self,
        tenant_id: int,
        include_inactive: bool = False,
    ) -> Dict[str, List[LookupValue]]:
        """
        Get all lookup values grouped by category.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            include_inactive: If True, include inactive values

        Returns:
            Dict mapping category names to lists of LookupValue records,
            each list ordered by sort_order ascending

        Requirements: 3.1, 3.4
        """
        query = self.db.query(LookupValue).filter(
            LookupValue.tenant_id == tenant_id,
        )
        if not include_inactive:
            query = query.filter(LookupValue.is_active == True)
        values = query.order_by(
            LookupValue.category.asc(),
            LookupValue.sort_order.asc(),
        ).all()

        grouped: Dict[str, List[LookupValue]] = defaultdict(list)
        for value in values:
            grouped[value.category].append(value)
        return dict(grouped)

    def code_exists(
        self,
        tenant_id: int,
        category: str,
        code: str,
    ) -> bool:
        """
        Check if a code already exists within a tenant+category combination.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            category: Category to check within
            code: Code to check for existence

        Returns:
            True if the code exists, False otherwise

        Requirements: 3.1, 3.4
        """
        count = (
            self.db.query(LookupValue)
            .filter(
                LookupValue.tenant_id == tenant_id,
                LookupValue.category == category,
                LookupValue.code == code,
            )
            .count()
        )
        return count > 0

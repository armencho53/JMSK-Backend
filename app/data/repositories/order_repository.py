"""Order repository for data access"""
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.data.repositories.base import BaseRepository
from app.data.models.order import Order


class OrderRepository(BaseRepository[Order]):
    """
    Repository for order data access operations.
    
    Provides CRUD operations and specialized queries for orders.
    All operations enforce multi-tenant isolation through tenant_id filtering.
    
    Methods:
        get_by_id: Get order by ID with optional line items
        get_with_line_items: Get order with all line items eagerly loaded
        create: Create a new order (inherited from BaseRepository)
        update: Update an existing order (inherited from BaseRepository)
        delete: Delete an order (inherited from BaseRepository)
    
    Requirements: 3.6, 3.9
    """
    
    def __init__(self, db: Session):
        super().__init__(Order, db)
    
    def get_with_line_items(
        self,
        order_id: int,
        tenant_id: int
    ) -> Optional[Order]:
        """
        Get order with all line items eagerly loaded.
        
        Uses joinedload to efficiently fetch the order and all its line items
        in a single query, avoiding N+1 query problems.
        
        Args:
            order_id: ID of the order
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Order object with line_items relationship loaded, or None if not found
        
        Requirements: 3.9
        """
        return self.db.query(Order).options(
            joinedload(Order.line_items),
            joinedload(Order.contact),
            joinedload(Order.company),
            joinedload(Order.metal)
        ).filter(
            Order.id == order_id,
            Order.tenant_id == tenant_id
        ).first()

"""Order repository for data access"""
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload, subqueryload
from app.data.repositories.base import BaseRepository
from app.data.models.order import Order
from app.data.models.order_line_item import OrderLineItem


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
            subqueryload(Order.line_items).joinedload(OrderLineItem.metal),
            joinedload(Order.contact),
            joinedload(Order.company),
            joinedload(Order.metal)
        ).filter(
            Order.id == order_id,
            Order.tenant_id == tenant_id
        ).first()
    def get_all(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Order]:
        """
        Get all orders with relationships eagerly loaded.

        Overrides base get_all to include eager loading of:
        - contact
        - company
        - metal
        - line_items

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of Order objects with relationships loaded
        """
        return self.db.query(Order).options(
            joinedload(Order.contact),
            joinedload(Order.company),
            joinedload(Order.metal),
            subqueryload(Order.line_items).joinedload(OrderLineItem.metal)
        ).filter(
            Order.tenant_id == tenant_id
        ).offset(skip).limit(limit).all()


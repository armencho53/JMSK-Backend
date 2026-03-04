"""OrderLineItem repository for data access"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.data.repositories.base import BaseRepository
from app.data.models.order_line_item import OrderLineItem


class OrderLineItemRepository(BaseRepository[OrderLineItem]):
    """
    Repository for order line item data access operations.
    
    Provides CRUD operations and specialized queries for order line items.
    All operations enforce multi-tenant isolation through tenant_id filtering.
    
    Methods:
        get_by_order: Get all line items for a specific order
        delete_by_order: Delete all line items for a specific order
        create: Create a new line item (inherited from BaseRepository)
        update: Update an existing line item (inherited from BaseRepository)
    
    Requirements: 3.6, 3.9
    """
    
    def __init__(self, db: Session):
        super().__init__(OrderLineItem, db)
    
    def get_by_order(
        self,
        order_id: int,
        tenant_id: int
    ) -> List[OrderLineItem]:
        """
        Get all line items for a specific order.
        
        Returns all line items associated with the given order ID,
        filtered by tenant for multi-tenant isolation.
        
        Args:
            order_id: ID of the parent order
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            List of OrderLineItem objects for the order
        
        Requirements: 3.6
        """
        return self.db.query(OrderLineItem).filter(
            OrderLineItem.order_id == order_id,
            OrderLineItem.tenant_id == tenant_id
        ).all()
    
    def delete_by_order(
        self,
        order_id: int,
        tenant_id: int
    ) -> None:
        """
        Delete all line items for a specific order.
        
        Removes all line items associated with the given order ID.
        Enforces tenant isolation to prevent cross-tenant deletions.
        
        Args:
            order_id: ID of the parent order
            tenant_id: Tenant ID for multi-tenant isolation
        
        Requirements: 3.9
        """
        self.db.query(OrderLineItem).filter(
            OrderLineItem.order_id == order_id,
            OrderLineItem.tenant_id == tenant_id
        ).delete()
        self.db.commit()

"""OrderLineItem data model for tracking individual products within an order"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base


class OrderLineItem(Base):
    """
    OrderLineItem model representing individual products within an order.
    
    This model supports multi-line orders where each line item can have its own
    metal type, quantity, weight specifications, and pricing. This enables orders
    with multiple products of different metals within a single order transaction.
    
    Attributes:
        id: Primary key
        tenant_id: Foreign key to tenant for multi-tenant isolation
        order_id: Foreign key to parent order
        product_description: Description of the jewelry product (required)
        specifications: Detailed product specifications (optional)
        metal_id: Foreign key to metals table (nullable for items without metal)
        quantity: Number of pieces to manufacture (default: 1)
        target_weight_per_piece: Expected final weight per piece in grams
        initial_total_weight: Total raw material weight in grams
        price: Line item price
        labor_cost: Manual labor cost for this line item
        created_at: Timestamp when line item was created
        updated_at: Timestamp when line item was last updated
    
    Relationships:
        tenant: The tenant this line item belongs to
        order: The parent order (with cascade delete)
        metal: The metal type for this line item
    
    Constraints:
        - product_description is required (NOT NULL)
        - quantity must be at least 1
        - Cascade delete: deleting an order deletes all its line items
    
    Requirements: 3.7, 3.8, 4.3
    """
    __tablename__ = "order_line_items"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_description = Column(Text, nullable=False)
    specifications = Column(Text, nullable=True)
    metal_id = Column(Integer, ForeignKey("metals.id"), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    target_weight_per_piece = Column(Float, nullable=True)
    initial_total_weight = Column(Float, nullable=True)
    price = Column(Float, nullable=True)
    labor_cost = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    order = relationship("Order", back_populates="line_items")
    metal = relationship("Metal")

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base
from app.domain.enums import OrderStatus

class Order(Base):
    """
    Order model representing a business transaction in the jewelry manufacturing system.
    
    Orders are placed by contacts on behalf of their companies. Each order must reference
    both a contact (the individual who placed the order) and a company (the organization
    the contact represents). This dual relationship enables:
    - Individual contact order history tracking
    - Company-wide order aggregation across all contacts
    - Accurate balance calculations at the company level
    
    Attributes:
        id: Primary key
        tenant_id: Foreign key to tenant for multi-tenant isolation
        order_number: Unique order identifier
        contact_id: Foreign key to contact who placed the order (required)
        company_id: Foreign key to company the order belongs to (required)
        product_description: Description of the jewelry product
        specifications: Detailed product specifications
        quantity: Number of pieces to manufacture
        price: Order price
        status: Current order status (PENDING, IN_PROGRESS, COMPLETED, SHIPPED, CANCELLED)
        due_date: Expected completion date
        metal_type: Type of metal used (gold, silver, platinum, etc.)
        target_weight_per_piece: Expected final weight per piece in grams
        initial_total_weight: Total raw material weight in grams
        created_at: Timestamp when order was created
        updated_at: Timestamp when order was last updated
    
    Relationships:
        tenant: The tenant this order belongs to
        contact: The contact (individual) who placed this order
        company: The company this order belongs to (must match contact's company)
        manufacturing_steps: All manufacturing steps for this order
        shipments: All shipments for this order
    
    Constraints:
        - contact_id and company_id are both required (NOT NULL)
        - Database trigger ensures company_id matches contact's company_id
        - Foreign key constraints ensure referential integrity
    
    Requirements: 1.5, 1.6
    """
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    order_number = Column(String, unique=True, nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    product_description = Column(Text)
    specifications = Column(Text)
    quantity = Column(Integer, default=1)
    price = Column(Float)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    due_date = Column(DateTime)

    # Metal and weight tracking
    metal_type = Column(String(50))
    target_weight_per_piece = Column(Float)  # Expected final weight per piece in grams
    initial_total_weight = Column(Float)  # Total raw material weight in grams
    labor_cost = Column(Float, nullable=True)  # Manual labor cost entry

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="orders")
    contact = relationship("Contact", back_populates="orders", foreign_keys="[Order.contact_id]")
    company = relationship("Company", back_populates="orders", foreign_keys="[Order.company_id]")
    manufacturing_steps = relationship("ManufacturingStep", back_populates="order")
    shipments = relationship("Shipment", back_populates="order")

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.data.database import Base

class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"

class MetalType(str, enum.Enum):
    GOLD_24K = "GOLD_24K"
    GOLD_22K = "GOLD_22K"
    GOLD_18K = "GOLD_18K"
    GOLD_14K = "GOLD_14K"
    SILVER_925 = "SILVER_925"
    PLATINUM = "PLATINUM"
    OTHER = "OTHER"

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    order_number = Column(String, unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String)
    customer_phone = Column(String)
    product_description = Column(Text)
    specifications = Column(Text)
    quantity = Column(Integer, default=1)
    price = Column(Float)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    due_date = Column(DateTime)

    # Metal and weight tracking
    metal_type = Column(Enum(MetalType))
    target_weight_per_piece = Column(Float)  # Expected final weight per piece in grams
    initial_total_weight = Column(Float)  # Total raw material weight in grams

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    manufacturing_steps = relationship("ManufacturingStep", back_populates="order")
    shipments = relationship("Shipment", back_populates="order")

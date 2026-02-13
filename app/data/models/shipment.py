from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base
from app.domain.enums import ShipmentStatus

class Shipment(Base):
    __tablename__ = "shipments"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    tracking_number = Column(String, unique=True, index=True)
    carrier = Column(String)
    shipping_address = Column(Text)
    status = Column(Enum(ShipmentStatus), default=ShipmentStatus.PREPARING)
    shipping_cost = Column(Float)
    shipped_at = Column(DateTime)
    delivered_at = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="shipments")
    order = relationship("Order", back_populates="shipments")

"""Metal transaction model for audit trail of all metal balance changes"""
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base


class MetalTransaction(Base):
    __tablename__ = "metal_transactions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    transaction_type = Column(String(30), nullable=False)
    # "COMPANY_DEPOSIT", "MANUFACTURING_CONSUMPTION", "SAFE_PURCHASE", "SAFE_ADJUSTMENT"
    metal_id = Column(Integer, ForeignKey("metals.id"), nullable=True)  # NULL for alloy
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    quantity_grams = Column(Float, nullable=False)  # positive=deposit/purchase, negative=consumption
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    metal = relationship("Metal")
    company = relationship("Company")
    order = relationship("Order")
    user = relationship("User")

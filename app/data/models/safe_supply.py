"""Safe supply model for tracking manufacturer's metal and alloy inventory"""
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base


class SafeSupply(Base):
    __tablename__ = "safe_supplies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "metal_id", "supply_type", name="uq_safe_supply"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    metal_id = Column(Integer, ForeignKey("metals.id"), nullable=True)  # NULL for alloy
    supply_type = Column(String(20), nullable=False)  # "FINE_METAL" or "ALLOY"
    quantity_grams = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant")
    metal = relationship("Metal")

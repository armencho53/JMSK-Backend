"""Metal data model for tracking metal types with fine percentage and cost"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base


class Metal(Base):
    __tablename__ = "metals"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_metal_code_per_tenant"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False)
    name = Column(String, nullable=False)
    fine_percentage = Column(Float, nullable=False)
    average_cost_per_gram = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="metals")

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base
from app.data.models.order import MetalType

class DepartmentBalance(Base):
    __tablename__ = "department_balances"
    __table_args__ = (
        UniqueConstraint('department_id', 'metal_type', name='uq_department_metal_type'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    metal_type = Column(Enum(MetalType), nullable=False)
    balance_grams = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="department_balances")
    department = relationship("Department", back_populates="balances")

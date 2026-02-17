"""Company metal balance model for tracking per-company metal deposits and consumption"""
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base


class CompanyMetalBalance(Base):
    __tablename__ = "company_metal_balances"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'company_id', 'metal_id', name='uq_company_metal_balance'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    metal_id = Column(Integer, ForeignKey("metals.id"), nullable=False, index=True)
    balance_grams = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant")
    company = relationship("Company", back_populates="metal_balances")
    metal = relationship("Metal")

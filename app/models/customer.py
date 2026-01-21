from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    phone = Column(String)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint on email per tenant
    __table_args__ = (
        UniqueConstraint('tenant_id', 'email', name='uq_customer_email_per_tenant'),
    )
    
    # Relationships
    tenant = relationship("Tenant", back_populates="customers")
    company = relationship("Company", back_populates="customers")
    orders = relationship("Order", back_populates="customer")

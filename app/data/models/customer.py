from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base

# DEPRECATED: This model is being phased out in favor of Contact model
# Use app.data.models.contact.Contact for new code
# This model is kept for backward compatibility during migration
class Customer(Base):
    """
    DEPRECATED: Legacy customer model.
    
    This model is being replaced by the Contact model as part of the
    hierarchical contact system migration. Use Contact model for all new code.
    
    Migration path: customers table -> contacts table
    See: alembic/versions/003_hierarchical_contact_system.py
    """
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
    # Note: orders relationship removed as Customer model is legacy
    # Orders now reference Contact model via contact_id field

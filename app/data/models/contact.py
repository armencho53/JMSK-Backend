"""Contact model for hierarchical contact system"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base


class Contact(Base):
    """
    Contact model representing an individual person who works for a company.
    
    Formerly known as "Customer" in the legacy system. Contacts are individuals
    who can place orders on behalf of their company. Every contact must belong
    to exactly one company.
    
    Attributes:
        id: Primary key
        tenant_id: Foreign key to tenant for multi-tenant isolation
        company_id: Foreign key to company (required) - every contact belongs to a company
        name: Contact's full name (required)
        email: Contact's email address (optional)
        phone: Contact's phone number (optional)
        created_at: Timestamp when contact was created
        updated_at: Timestamp when contact was last updated
    
    Relationships:
        tenant: The tenant this contact belongs to
        company: The company this contact works for
        orders: All orders placed by this contact
    
    Constraints:
        - Unique constraint on (tenant_id, company_id, email) to prevent duplicate
          contacts within the same company
        - Foreign key constraints ensure referential integrity
        - Database triggers validate tenant consistency between contact and company
    
    Requirements: 1.1, 1.3, 1.4
    """
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True, index=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: same email can exist across companies but not within same company
    __table_args__ = (
        UniqueConstraint('tenant_id', 'company_id', 'email', name='uq_contact_email_per_company'),
    )
    
    # Relationships
    tenant = relationship("Tenant", back_populates="contacts")
    company = relationship("Company", back_populates="contacts")
    orders = relationship("Order", back_populates="contact", foreign_keys="Order.contact_id")

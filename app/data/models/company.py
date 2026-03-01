"""Company model for hierarchical contact system"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base


class Company(Base):
    """
    Company model representing an organization in the hierarchical contact system.
    
    Companies are the parent entities in the company-contact hierarchy. Each company
    can have multiple contacts (individuals who work for the company) and multiple
    orders (placed by those contacts). The company serves as the primary business
    entity for aggregating balances and tracking overall business relationships.
    
    Attributes:
        id: Primary key
        tenant_id: Foreign key to tenant for multi-tenant isolation
        name: Company name (required, unique per tenant)
        address: Company address (optional, text field for flexibility)
        phone: Company phone number (optional)
        email: Company email address (optional)
        created_at: Timestamp when company was created
        updated_at: Timestamp when company was last updated
    
    Relationships:
        tenant: The tenant this company belongs to
        contacts: All contacts (individuals) associated with this company
        orders: All orders placed by contacts of this company
        addresses: All addresses associated with this company
    
    Constraints:
        - Unique constraint on (tenant_id, name) to prevent duplicate company names
        - Foreign key constraints ensure referential integrity
    
    Balance Calculation:
        Company balance is calculated by aggregating all order values from all
        associated contacts. This is handled by the CompanyRepository.get_balance()
        method rather than being stored as a field.
    
    Requirements: 1.3, 2.1, 2.2, 4.1, 4.3
    """
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    address = Column(Text)
    phone = Column(String)
    email = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint on name per tenant
    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='uq_company_name_per_tenant'),
    )
    
    # Relationships
    tenant = relationship("Tenant", back_populates="companies")
    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="company", foreign_keys="Order.company_id")
    addresses = relationship("Address", back_populates="company", foreign_keys="[Address.company_id]", cascade="all, delete-orphan")
    metal_balances = relationship("CompanyMetalBalance", back_populates="company")

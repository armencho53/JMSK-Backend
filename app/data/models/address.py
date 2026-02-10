"""Address model for hierarchical contact system"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base


class Address(Base):
    """
    Address model representing a physical location associated with a company.
    
    Companies can have multiple addresses for different purposes (shipping, billing, etc.).
    One address can be marked as the default address, which is automatically populated
    during shipment creation. The default address can be modified for individual shipments
    without affecting the company's default.
    
    Attributes:
        id: Primary key
        tenant_id: Foreign key to tenant for multi-tenant isolation
        company_id: Foreign key to company (required) - every address belongs to a company
        street_address: Street address line (required)
        city: City name (required)
        state: State or province (required)
        zip_code: Postal/ZIP code (required)
        country: Country name (defaults to 'USA')
        is_default: Whether this is the default address for the company
        created_at: Timestamp when address was created
    
    Relationships:
        tenant: The tenant this address belongs to
        company: The company this address is associated with
    
    Constraints:
        - Foreign key constraints ensure referential integrity
        - Check constraint validates zip_code has minimum 5 characters
        - Database trigger ensures only one default address per company
        - Database trigger automatically sets first address as default
        - Database trigger prevents deletion of default address in use
    
    Business Rules:
        - First address created for a company is automatically set as default
        - Setting an address as default unsets other defaults for that company
        - Default address cannot be deleted if referenced by company.default_address_id
        - Shipments use company's default address but can be modified per shipment
        - Updating company's default address only affects future shipments
    
    Requirements: 5.1, 5.2, 5.3, 5.4
    """
    __tablename__ = "addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    street_address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    zip_code = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False, default="USA")
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="addresses")
    company = relationship("Company", back_populates="addresses", foreign_keys=[company_id])

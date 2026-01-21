from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    subdomain = Column(String, unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="tenant")
    roles = relationship("Role", back_populates="tenant")
    supplies = relationship("Supply", back_populates="tenant")
    companies = relationship("Company", back_populates="tenant")
    customers = relationship("Customer", back_populates="tenant")
    orders = relationship("Order", back_populates="tenant")
    manufacturing_steps = relationship("ManufacturingStep", back_populates="tenant")
    shipments = relationship("Shipment", back_populates="tenant")
    departments = relationship("Department", back_populates="tenant")
    department_balances = relationship("DepartmentBalance", back_populates="tenant")

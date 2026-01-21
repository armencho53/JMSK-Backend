from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.data.database import Base

class SupplyType(str, enum.Enum):
    METAL = "metal"
    GEMSTONE = "gemstone"
    TOOL = "tool"
    PACKAGING = "packaging"
    OTHER = "other"

class Supply(Base):
    __tablename__ = "supplies"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    type = Column(Enum(SupplyType), nullable=False)
    quantity = Column(Float, default=0)
    unit = Column(String)  # grams, pieces, carats, etc.
    cost_per_unit = Column(Float)
    supplier = Column(String)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="supplies")

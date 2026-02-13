from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.data.database import Base


class LookupValue(Base):
    __tablename__ = "lookup_values"
    __table_args__ = (
        UniqueConstraint("tenant_id", "category", "code", name="uq_tenant_category_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    display_label = Column(String, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="lookup_values")

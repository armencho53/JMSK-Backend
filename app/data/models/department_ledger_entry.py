from sqlalchemy import Column, Integer, String, DateTime, Date, Float, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.data.database import Base


class DepartmentLedgerEntry(Base):
    __tablename__ = "department_ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, default=date.today)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    metal_id = Column(Integer, ForeignKey("metals.id"), nullable=False)
    direction = Column(String(3), nullable=False)  # "IN" or "OUT"
    quantity = Column(Float, nullable=False)
    weight = Column(Float, nullable=False)          # gross weight in grams
    fine_weight = Column(Float, nullable=False)      # computed: weight × purity_factor, signed
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="ledger_entries")
    department = relationship("Department")
    order = relationship("Order")
    metal = relationship("Metal")
    creator = relationship("User")

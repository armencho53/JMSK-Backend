# ARCHIVED: This model is kept for reference only.
# The manufacturing_steps table has been renamed to manufacturing_steps_archive
# via Alembic migration. The Department Ledger system replaces this functionality.
# See app/data/models/department_ledger_entry.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship, backref
from datetime import datetime
from app.data.database import Base


class ManufacturingStep(Base):
    __tablename__ = "manufacturing_steps_archive"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    parent_step_id = Column(Integer, ForeignKey("manufacturing_steps_archive.id"), nullable=True, index=True)
    step_type = Column(String(50), nullable=True)
    description = Column(Text)
    status = Column(String(20))

    # Department and Worker tracking
    department = Column(String)
    worker_name = Column(String)

    # Tracking timestamps
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    received_at = Column(DateTime)

    # Transfer tracking
    transferred_by = Column(String)
    received_by = Column(String)

    # Enhanced quantity tracking
    quantity_received = Column(Float)
    quantity_returned = Column(Float)

    # Enhanced weight tracking
    weight_received = Column(Float)
    weight_returned = Column(Float)

    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Self-referential relationship for parent/child steps
    children = relationship("ManufacturingStep", backref=backref("parent", remote_side=[id]))

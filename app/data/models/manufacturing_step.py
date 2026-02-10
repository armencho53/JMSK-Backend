from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, Float
from sqlalchemy.orm import relationship, backref
from datetime import datetime
import enum
from app.data.database import Base

class StepType(str, enum.Enum):
    DESIGN = "DESIGN"
    CASTING = "CASTING"
    STONE_SETTING = "STONE_SETTING"
    POLISHING = "POLISHING"
    ENGRAVING = "ENGRAVING"
    QUALITY_CHECK = "QUALITY_CHECK"
    FINISHING = "FINISHING"
    OTHER = "OTHER"

class StepStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ManufacturingStep(Base):
    __tablename__ = "manufacturing_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    parent_step_id = Column(Integer, ForeignKey("manufacturing_steps.id"), nullable=True, index=True)
    step_type = Column(Enum(StepType), nullable=True)
    description = Column(Text)
    status = Column(Enum(StepStatus, name='stepstatus',  values_callable=lambda x: [e.value for e in x]), default=StepStatus.IN_PROGRESS)

    # Department and Worker tracking
    department = Column(String)
    worker_name = Column(String)

    # Tracking timestamps
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    received_at = Column(DateTime)  # When worker received pieces

    # Transfer tracking
    transferred_by = Column(String)  # Worker who sent pieces
    received_by = Column(String)  # Worker who received pieces

    # Enhanced quantity tracking
    quantity_received = Column(Float)
    quantity_returned = Column(Float)

    # Enhanced weight tracking
    weight_received = Column(Float)  # Weight when received in grams
    weight_returned = Column(Float)  # Weight when returned in grams

    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="manufacturing_steps")
    order = relationship("Order", back_populates="manufacturing_steps")
    children = relationship("ManufacturingStep", backref=backref("parent", remote_side=[id]))

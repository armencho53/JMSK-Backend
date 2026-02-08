from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.data.models.manufacturing_step import StepType, StepStatus

class ManufacturingStepBase(BaseModel):
    order_id: int
    step_type: Optional[StepType] = None
    description: Optional[str] = None
    department: Optional[str] = None
    worker_name: Optional[str] = None

class ManufacturingStepCreate(ManufacturingStepBase):
    quantity_received: Optional[float] = None
    quantity_returned: Optional[float] = None
    weight_received: Optional[float] = None
    weight_returned: Optional[float] = None

class ManufacturingStepUpdate(BaseModel):
    step_type: Optional[StepType] = None
    description: Optional[str] = None
    status: Optional[StepStatus] = None
    department: Optional[str] = None
    worker_name: Optional[str] = None
    parent_step_id: Optional[int] = None

    # Transfer tracking
    transferred_by: Optional[str] = None
    received_by: Optional[str] = None

    # Quantity tracking
    quantity_received: Optional[float] = None
    quantity_returned: Optional[float] = None

    # Weight tracking
    weight_received: Optional[float] = None
    weight_returned: Optional[float] = None

    notes: Optional[str] = None

class TransferStepRequest(BaseModel):
    """Request schema for transferring a portion of a manufacturing step to create a child step"""
    quantity: float
    weight: float
    next_step_type: StepType
    received_by: str
    department: Optional[str] = None

class ManufacturingStepResponse(ManufacturingStepBase):
    id: int
    tenant_id: int
    status: StepStatus
    parent_step_id: Optional[int] = None

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    received_at: Optional[datetime] = None

    # Transfer tracking
    transferred_by: Optional[str] = None
    received_by: Optional[str] = None

    # Quantity tracking
    quantity_received: Optional[float] = None
    quantity_returned: Optional[float] = None

    # Weight tracking
    weight_received: Optional[float] = None
    weight_returned: Optional[float] = None

    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    children: List['ManufacturingStepResponse'] = []

    class Config:
        from_attributes = True

# Update forward references for recursive model
ManufacturingStepResponse.model_rebuild()

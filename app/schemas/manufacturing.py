from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.data.models.manufacturing_step import StepType, StepStatus

class ManufacturingStepBase(BaseModel):
    order_id: int
    step_type: StepType
    step_name: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    sequence_order: Optional[int] = None
    department: Optional[str] = None
    worker_name: Optional[str] = None
    parent_step_id: Optional[int] = None

class ManufacturingStepCreate(ManufacturingStepBase):
    # Legacy fields (kept for backward compatibility)
    goods_given_quantity: Optional[float] = None
    goods_given_weight: Optional[float] = None
    # New enhanced fields
    quantity_received: Optional[float] = None
    quantity_returned: Optional[float] = None
    weight_received: Optional[float] = None
    # Note: expected_loss_percentage removed - now tracked via department balances

class ManufacturingStepUpdate(BaseModel):
    step_type: Optional[StepType] = None
    step_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[StepStatus] = None
    assigned_to: Optional[str] = None
    sequence_order: Optional[int] = None
    department: Optional[str] = None
    worker_name: Optional[str] = None
    parent_step_id: Optional[int] = None

    # Transfer tracking
    transferred_by: Optional[str] = None
    received_by: Optional[str] = None

    # Legacy fields (kept for backward compatibility)
    goods_given_quantity: Optional[float] = None
    goods_given_weight: Optional[float] = None
    goods_returned_quantity: Optional[float] = None
    goods_returned_weight: Optional[float] = None

    # Enhanced quantity tracking
    quantity_received: Optional[float] = None
    quantity_returned: Optional[float] = None
    quantity_completed: Optional[float] = None  # Deprecated
    quantity_failed: Optional[float] = None  # Deprecated
    quantity_rework: Optional[float] = None  # Deprecated

    # Enhanced weight tracking
    weight_received: Optional[float] = None
    weight_returned: Optional[float] = None
    # Note: expected_loss_percentage removed - now tracked via department balances

    notes: Optional[str] = None

class TransferStepRequest(BaseModel):
    """Request schema for transferring a portion of a manufacturing step to create a child step"""
    quantity: float
    weight: float
    next_step_type: StepType
    next_step_name: str
    received_by: str
    department: Optional[str] = None

class ManufacturingStepResponse(ManufacturingStepBase):
    id: int
    tenant_id: int
    status: StepStatus

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    received_at: Optional[datetime] = None

    # Transfer tracking
    transferred_by: Optional[str] = None
    received_by: Optional[str] = None

    # Legacy fields
    goods_given_quantity: Optional[float] = None
    goods_given_weight: Optional[float] = None
    goods_given_at: Optional[datetime] = None
    goods_returned_quantity: Optional[float] = None
    goods_returned_weight: Optional[float] = None
    goods_returned_at: Optional[datetime] = None

    # Enhanced quantity tracking
    quantity_received: Optional[float] = None
    quantity_returned: Optional[float] = None
    quantity_completed: Optional[float] = None  # Deprecated
    quantity_failed: Optional[float] = None  # Deprecated
    quantity_rework: Optional[float] = None  # Deprecated

    # Enhanced weight tracking
    weight_received: Optional[float] = None
    weight_returned: Optional[float] = None
    # Note: weight_loss, weight_loss_percentage, and expected_loss_percentage
    # were removed from the model - now tracked via department balances

    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    children: List['ManufacturingStepResponse'] = []

    class Config:
        from_attributes = True

# Update forward references for recursive model
ManufacturingStepResponse.model_rebuild()

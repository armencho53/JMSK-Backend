from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from datetime import datetime
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.data.models.manufacturing_step import ManufacturingStep
from app.domain.enums import StepStatus
from app.data.models.department import Department
from app.data.models.department_balance import DepartmentBalance
from app.data.models.order import Order
from app.schemas.manufacturing import ManufacturingStepCreate, ManufacturingStepUpdate, ManufacturingStepResponse, TransferStepRequest
from app.domain.services.lookup_service import LookupService
from app.domain.exceptions import ValidationError

router = APIRouter()

# Helper functions for department balance management

def get_or_create_department_balance(
    db: Session,
    tenant_id: int,
    department_name: str,
    metal_type: str
) -> DepartmentBalance:
    """Get or create a department balance for a specific metal type."""
    # Get department by name
    department = db.query(Department).filter(
        Department.tenant_id == tenant_id,
        Department.name == department_name
    ).first()

    if not department:
        raise HTTPException(status_code=404, detail=f"Department '{department_name}' not found")

    # Get or create balance
    balance = db.query(DepartmentBalance).filter(
        DepartmentBalance.department_id == department.id,
        DepartmentBalance.metal_type == metal_type
    ).first()

    if not balance:
        balance = DepartmentBalance(
            tenant_id=tenant_id,
            department_id=department.id,
            metal_type=metal_type,
            balance_grams=0.0
        )
        db.add(balance)
        db.flush()

    return balance

def update_department_balance(
    db: Session,
    tenant_id: int,
    department_name: str,
    metal_type: str,
    amount_grams: float,
    operation: str = "add"
) -> DepartmentBalance:
    """
    Update department balance by adding or subtracting weight.
    operation: "add" or "subtract"
    """
    balance = get_or_create_department_balance(db, tenant_id, department_name, metal_type)

    if operation == "subtract":
        if balance.balance_grams < amount_grams:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance in {department_name}. Available: {balance.balance_grams}g, Required: {amount_grams}g"
            )
        balance.balance_grams -= amount_grams
    elif operation == "add":
        balance.balance_grams += amount_grams
    else:
        raise ValueError(f"Invalid operation: {operation}")

    balance.updated_at = datetime.utcnow()
    return balance

# Weight loss calculation removed - now tracked implicitly via department balances
# def calculate_weight_loss(step: ManufacturingStep) -> None:
#     """
#     Calculate and set weight loss and weight loss percentage for a manufacturing step.
#     This should be called whenever a step is completed.
#     """
#     if step.weight_received is not None and step.weight_returned is not None:
#         step.weight_loss = step.weight_received - step.weight_returned
#         if step.weight_received > 0:
#             step.weight_loss_percentage = (step.weight_loss / step.weight_received) * 100
#         else:
#             step.weight_loss_percentage = 0.0

@router.get("/steps", response_model=List[ManufacturingStepResponse])
def list_steps(
    order_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(ManufacturingStep).filter(
        ManufacturingStep.tenant_id == current_user.tenant_id
    )

    if order_id:
        query = query.filter(ManufacturingStep.order_id == order_id)

    # Order by created_at DESC (newest first)
    steps = query.order_by(ManufacturingStep.created_at.desc()).offset(skip).limit(limit).all()
    return steps

@router.post("/steps", response_model=ManufacturingStepResponse)
def create_step(
    step: ManufacturingStepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Debug: Log current user info
    print(f"DEBUG: Creating step for user_id={current_user.id}, tenant_id={current_user.tenant_id}")
    
    # Create the manufacturing step with explicit tenant_id
    step_data = step.dict()
    step_data['tenant_id'] = current_user.tenant_id

    # Validate step_type against lookup values if provided (Requirement 6.2)
    step_type = step_data.get('step_type')
    if step_type:
        lookup_service = LookupService(db)
        try:
            lookup_service.validate_lookup_code(current_user.tenant_id, "step_type", step_type)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=e.message)
    
    # Debug: Verify tenant_id is in the data
    print(f"DEBUG: step_data tenant_id = {step_data.get('tenant_id')}")
    
    db_step = ManufacturingStep(**step_data)
    
    # Debug: Verify tenant_id is on the object
    print(f"DEBUG: db_step.tenant_id = {db_step.tenant_id}")
    
    db.add(db_step)
    db.flush()  # Flush to get the ID but don't commit yet
    
    # Debug: Verify after flush
    print(f"DEBUG: After flush, db_step.id={db_step.id}, tenant_id={db_step.tenant_id}")

    # Handle department balance tracking (optional - only if Inventory department exists)
    if db_step.weight_received and db_step.weight_received > 0 and db_step.department:
        # Get the order to determine metal type
        order = db.query(Order).filter(Order.id == db_step.order_id).first()
        if order and order.metal_type:
            # For first step (no parent), try to allocate from Inventory
            if not db_step.parent_step_id:
                # Check if Inventory department exists
                inventory_dept = db.query(Department).filter(
                    Department.tenant_id == current_user.tenant_id,
                    Department.name == "Inventory"
                ).first()
                
                if inventory_dept:
                    # Subtract from Inventory department
                    update_department_balance(
                        db=db,
                        tenant_id=current_user.tenant_id,
                        department_name="Inventory",
                        metal_type=order.metal_type,
                        amount_grams=db_step.weight_received,
                        operation="subtract"
                    )
                # Add to the step's department (always do this)
                update_department_balance(
                    db=db,
                    tenant_id=current_user.tenant_id,
                    department_name=db_step.department,
                    metal_type=order.metal_type,
                    amount_grams=db_step.weight_received,
                    operation="add"
                )

    db.commit()
    db.refresh(db_step)
    return db_step

@router.get("/steps/{step_id}", response_model=ManufacturingStepResponse)
def get_step(
    step_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    step = db.query(ManufacturingStep).filter(
        ManufacturingStep.id == step_id,
        ManufacturingStep.tenant_id == current_user.tenant_id
    ).first()

    if not step:
        raise HTTPException(status_code=404, detail="Manufacturing step not found")

    return step

@router.put("/steps/{step_id}", response_model=ManufacturingStepResponse)
def update_step(
    step_id: int,
    step_update: ManufacturingStepUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    step = db.query(ManufacturingStep).filter(
        ManufacturingStep.id == step_id,
        ManufacturingStep.tenant_id == current_user.tenant_id
    ).first()

    if not step:
        raise HTTPException(status_code=404, detail="Manufacturing step not found")

    update_data = step_update.dict(exclude_unset=True)

    # Validate step_type against lookup values if provided (Requirement 6.2)
    step_type = update_data.get('step_type')
    if step_type:
        lookup_service = LookupService(db)
        try:
            lookup_service.validate_lookup_code(current_user.tenant_id, "step_type", step_type)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=e.message)

    for key, value in update_data.items():
        setattr(step, key, value)

    # Auto-set timestamps based on status
    if step_update.status == StepStatus.IN_PROGRESS and not step.started_at:
        step.started_at = datetime.utcnow()
    elif step_update.status == StepStatus.COMPLETED and not step.completed_at:
        step.completed_at = datetime.utcnow()

    # Auto-set received timestamp for weight tracking
    if step_update.weight_received is not None and not step.received_at:
        step.received_at = datetime.utcnow()

    # Weight loss calculation removed - now tracked implicitly via department balances

    db.commit()
    db.refresh(step)
    return step

@router.delete("/steps/{step_id}")
def delete_step(
    step_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    step = db.query(ManufacturingStep).filter(
        ManufacturingStep.id == step_id,
        ManufacturingStep.tenant_id == current_user.tenant_id
    ).first()

    if not step:
        raise HTTPException(status_code=404, detail="Manufacturing step not found")

    db.delete(step)
    db.commit()
    return {"message": "Manufacturing step deleted successfully"}

@router.get("/steps/{step_id}/remaining", response_model=Dict[str, Any])
def get_remaining_quantities(
    step_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get remaining quantity and weight available for transfer from a parent step.
    """
    parent_step = db.query(ManufacturingStep).filter(
        ManufacturingStep.id == step_id,
        ManufacturingStep.tenant_id == current_user.tenant_id
    ).first()

    if not parent_step:
        raise HTTPException(status_code=404, detail="Manufacturing step not found")

    # Calculate already transferred amounts from existing children
    children = db.query(ManufacturingStep).filter(
        ManufacturingStep.parent_step_id == step_id
    ).all()

    total_transferred_qty = sum(child.quantity_received or 0 for child in children)
    total_transferred_weight = sum(child.weight_received or 0 for child in children)

    # Calculate remaining amounts based on quantity_returned and weight_returned
    # These are the amounts available to transfer (what was returned from the parent step)
    # Fallback to quantity_received if quantity_returned is None
    parent_qty = parent_step.quantity_returned or parent_step.quantity_received or 0
    parent_weight = parent_step.weight_returned or parent_step.weight_received or 0
    remaining_qty = parent_qty - total_transferred_qty
    remaining_weight = parent_weight - total_transferred_weight

    return {
        "step_id": step_id,
        "total_quantity": parent_qty,
        "total_weight": parent_weight,
        "transferred_quantity": total_transferred_qty,
        "transferred_weight": total_transferred_weight,
        "remaining_quantity": remaining_qty,
        "remaining_weight": remaining_weight,
        "children_count": len(children)
    }

@router.post("/steps/{step_id}/transfer", response_model=Dict[str, Any])
def transfer_step(
    step_id: int,
    transfer_request: TransferStepRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Transfer a portion of a manufacturing step to create a new child step.
    The parent step tracks all transfers and auto-completes when fully transferred.
    """
    # Get the parent step
    parent_step = db.query(ManufacturingStep).filter(
        ManufacturingStep.id == step_id,
        ManufacturingStep.tenant_id == current_user.tenant_id
    ).first()

    if not parent_step:
        raise HTTPException(status_code=404, detail="Manufacturing step not found")

    # Validate next_step_type against lookup values (Requirement 6.2)
    if transfer_request.next_step_type:
        lookup_service = LookupService(db)
        try:
            lookup_service.validate_lookup_code(current_user.tenant_id, "step_type", transfer_request.next_step_type)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=e.message)

    # Calculate already transferred amounts from existing children
    children = db.query(ManufacturingStep).filter(
        ManufacturingStep.parent_step_id == step_id
    ).all()

    total_transferred_qty = sum(child.quantity_received or 0 for child in children)
    total_transferred_weight = sum(child.weight_received or 0 for child in children)

    # Calculate remaining amounts based on quantity_returned and weight_returned
    # These are the amounts available to transfer (what was returned from the parent step)
    parent_qty = parent_step.quantity_returned or parent_step.quantity_received or 0
    parent_weight = parent_step.weight_returned or parent_step.weight_received or 0
    remaining_qty = parent_qty - total_transferred_qty
    remaining_weight = parent_weight - total_transferred_weight

    # Validate transfer doesn't exceed remaining amounts
    if transfer_request.quantity > remaining_qty:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transfer {transfer_request.quantity} pieces. Only {remaining_qty} remaining."
        )

    if transfer_request.weight > remaining_weight:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transfer {transfer_request.weight}g. Only {remaining_weight}g remaining."
        )

    # Validate minimum transfer amount
    if transfer_request.quantity <= 0:
        raise HTTPException(status_code=400, detail="Transfer quantity must be greater than 0")

    if transfer_request.weight <= 0:
        raise HTTPException(status_code=400, detail="Transfer weight must be greater than 0")

    # Create child step
    child_step = ManufacturingStep(
        tenant_id=current_user.tenant_id,
        order_id=parent_step.order_id,
        parent_step_id=parent_step.id,
        step_type=transfer_request.next_step_type,
        status=StepStatus.IN_PROGRESS,
        department=transfer_request.department,
        worker_name=transfer_request.received_by,
        quantity_received=transfer_request.quantity,
        weight_received=transfer_request.weight,
        received_at=datetime.utcnow(),
        received_by=transfer_request.received_by,
        transferred_by=parent_step.worker_name
    )

    db.add(child_step)
    db.flush()  # Flush to get IDs before balance operations

    # Handle department balance tracking for transfer
    if parent_step.department and transfer_request.department and transfer_request.weight > 0:
        # Get the order to determine metal type
        order = db.query(Order).filter(Order.id == parent_step.order_id).first()
        if order and order.metal_type:
            # Subtract from parent department
            update_department_balance(
                db=db,
                tenant_id=current_user.tenant_id,
                department_name=parent_step.department,
                metal_type=order.metal_type,
                amount_grams=transfer_request.weight,
                operation="subtract"
            )
            # Add to receiving department (child step)
            update_department_balance(
                db=db,
                tenant_id=current_user.tenant_id,
                department_name=transfer_request.department,
                metal_type=order.metal_type,
                amount_grams=transfer_request.weight,
                operation="add"
            )
            # Weight loss is implicit: if parent_weight_returned < parent_weight_received,
            # the difference remains in parent's department as loss

    # Update parent step: set transferred_by if this is the first transfer
    if not parent_step.transferred_by:
        parent_step.transferred_by = parent_step.worker_name

    # Calculate new totals after this transfer
    new_total_transferred_qty = total_transferred_qty + transfer_request.quantity
    new_total_transferred_weight = total_transferred_weight + transfer_request.weight

    # Calculate remaining amounts
    remaining_qty = parent_qty - new_total_transferred_qty
    remaining_weight = parent_weight - new_total_transferred_weight

    # Auto-complete parent step when available items reach 0
    # Complete if EITHER quantity or weight reaches 0 (within tolerance)
    tolerance = 0.01  # Small tolerance for floating point precision

    qty_depleted = parent_qty > 0 and remaining_qty <= tolerance
    weight_depleted = parent_weight > 0 and remaining_weight <= tolerance

    # If either metric is being tracked and is depleted, complete the step
    if qty_depleted or weight_depleted:
        parent_step.status = StepStatus.COMPLETED
        if not parent_step.completed_at:
            parent_step.completed_at = datetime.utcnow()

        # Set returned quantities if not already set
        # The "returned" amount is the amount that was processed and transferred to children
        if parent_step.quantity_returned is None:
            parent_step.quantity_returned = new_total_transferred_qty
        if parent_step.weight_returned is None:
            parent_step.weight_returned = new_total_transferred_weight

        # Weight loss calculation removed - now tracked implicitly via department balances

    db.commit()
    db.refresh(child_step)
    db.refresh(parent_step)

    return {
        "message": "Transfer completed successfully",
        "parent_step_id": parent_step.id,
        "parent_step_status": parent_step.status.value,
        "child_step_id": child_step.id,
        "remaining_quantity": remaining_qty,
        "remaining_weight": remaining_weight
    }

# Dashboard endpoints

@router.get("/dashboard/by-step", response_model=Dict[str, Any])
def get_dashboard_by_step(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get manufacturing steps grouped by step type for Kanban view
    """
    steps = db.query(ManufacturingStep).filter(
        ManufacturingStep.tenant_id == current_user.tenant_id
    ).all()

    # Group steps by step_type
    grouped_steps = {}
    for step in steps:
        step_type_value = step.step_type
        if step_type_value:
            if step_type_value not in grouped_steps:
                grouped_steps[step_type_value] = {
                    "step_type": step_type_value,
                    "label": step_type_value.replace('_', ' ').title(),
                    "steps": []
                }
            grouped_steps[step_type_value]["steps"].append(step)

    return {"groups": list(grouped_steps.values())}

@router.get("/dashboard/by-department", response_model=Dict[str, Any])
def get_dashboard_by_department(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get manufacturing steps grouped by department
    """
    steps = db.query(ManufacturingStep).filter(
        ManufacturingStep.tenant_id == current_user.tenant_id,
        ManufacturingStep.department.isnot(None)
    ).all()

    # Group steps by department
    departments = {}
    for step in steps:
        dept = step.department or "Unassigned"
        if dept not in departments:
            departments[dept] = {
                "department": dept,
                "steps": [],
                "workers": set()
            }
        departments[dept]["steps"].append(step)
        if step.worker_name:
            departments[dept]["workers"].add(step.worker_name)

    # Convert sets to lists for JSON serialization
    result = []
    for dept_name, dept_data in departments.items():
        result.append({
            "department": dept_name,
            "steps": dept_data["steps"],
            "workers": list(dept_data["workers"]),
            "total_steps": len(dept_data["steps"])
        })

    return {"groups": result}

@router.get("/dashboard/by-worker", response_model=Dict[str, Any])
def get_dashboard_by_worker(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get manufacturing steps grouped by worker
    """
    steps = db.query(ManufacturingStep).filter(
        ManufacturingStep.tenant_id == current_user.tenant_id,
        ManufacturingStep.worker_name.isnot(None)
    ).all()

    # Group steps by worker_name
    workers = {}
    for step in steps:
        worker = step.worker_name or "Unassigned"
        if worker not in workers:
            workers[worker] = {
                "worker_name": worker,
                "steps": [],
                "in_progress_count": 0
            }
        workers[worker]["steps"].append(step)
        if step.status == StepStatus.IN_PROGRESS:
            workers[worker]["in_progress_count"] += 1

    result = []
    for worker_name, worker_data in workers.items():
        result.append({
            "worker_name": worker_name,
            "steps": worker_data["steps"],
            "in_progress_count": worker_data["in_progress_count"],
            "total_steps": len(worker_data["steps"])
        })

    return {"groups": result}

@router.get("/stats", response_model=Dict[str, Any])
def get_manufacturing_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get manufacturing statistics for dashboard summary
    """
    steps = db.query(ManufacturingStep).filter(
        ManufacturingStep.tenant_id == current_user.tenant_id
    ).all()

    # Calculate statistics
    total_steps = len(steps)
    status_counts = {
        "in_progress": 0,
        "completed": 0,
        "failed": 0
    }

    # Weight loss tracking removed - now tracked via department balances
    total_duration = 0
    completed_steps = 0

    for step in steps:
        # Count by status
        status_counts[step.status.value] = status_counts.get(step.status.value, 0) + 1

        # Calculate average duration for completed steps
        if step.status == StepStatus.COMPLETED and step.started_at and step.completed_at:
            duration = (step.completed_at - step.started_at).total_seconds() / 3600  # hours
            total_duration += duration
            completed_steps += 1

    avg_duration = total_duration / completed_steps if completed_steps > 0 else 0

    return {
        "total_steps": total_steps,
        "status_counts": status_counts,
        "average_duration_hours": round(avg_duration, 2),
        "completed_steps": completed_steps
    }

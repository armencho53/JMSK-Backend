# Manufacturing Step Creation Fixes

## Issues Fixed

### Issue 1: tenant_id Not Being Inserted
**Problem**: When creating a manufacturing step, the tenant_id was not being properly inserted into the database.

**Root Cause**: The way the step data was being passed to the ManufacturingStep constructor might have caused the tenant_id to be overridden or not properly set.

**Solution**: Modified the `create_step` endpoint to:
1. Explicitly set tenant_id in the step data dictionary before creating the model instance
2. Add validation to ensure tenant_id is set correctly
3. Raise clear errors if tenant_id is missing

```python
# After fix
def create_step(step, db, current_user):
    # Validate that current_user has tenant_id
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User does not have a tenant_id")
    
    # Create the manufacturing step with explicit tenant_id
    step_data = step.dict()
    step_data['tenant_id'] = current_user.tenant_id
    
    # Verify tenant_id is set before creating the object
    if 'tenant_id' not in step_data or step_data['tenant_id'] is None:
        raise HTTPException(status_code=500, detail="Failed to set tenant_id")
    
    db_step = ManufacturingStep(**step_data)
    
    # Double-check tenant_id is set on the object
    if not db_step.tenant_id:
        raise HTTPException(status_code=500, detail="tenant_id not set on ManufacturingStep object")
    
    db.add(db_step)
    db.flush()
```

This ensures tenant_id is always set correctly from the authenticated user and provides clear error messages if something goes wrong.

### Issue 2: parent_step_id Should Be Null for New Steps
**Problem**: When adding a new manufacturing step (not a transfer), the parent_step_id field was being included in the create schema, which could lead to confusion or incorrect data.

**Root Cause**: The `parent_step_id` field was in the `ManufacturingStepBase` schema, which is inherited by `ManufacturingStepCreate`. This meant users could (and might accidentally) set parent_step_id when creating a new step.

**Solution**: 
1. Removed `parent_step_id` from `ManufacturingStepBase`
2. Added `parent_step_id` only to `ManufacturingStepResponse` where it's needed for display
3. The transfer endpoint explicitly sets `parent_step_id` when creating child steps

**Schema Changes**:

```python
# ManufacturingStepBase - No parent_step_id
class ManufacturingStepBase(BaseModel):
    order_id: int
    step_type: Optional[StepType] = None
    description: Optional[str] = None
    department: Optional[str] = None
    worker_name: Optional[str] = None
    # parent_step_id removed from here

# ManufacturingStepResponse - Includes parent_step_id
class ManufacturingStepResponse(ManufacturingStepBase):
    id: int
    tenant_id: int
    status: StepStatus
    parent_step_id: Optional[int] = None  # Added here
    # ... rest of fields
```

## How It Works Now

### Creating a New Step (POST /steps)
```json
{
  "order_id": 1,
  "step_type": "casting",
  "description": "Cast ring base",
  "department": "Casting",
  "worker_name": "John Doe",
  "quantity_received": 1,
  "weight_received": 15.5
}
```

Result:
- ✓ `tenant_id` is automatically set from authenticated user
- ✓ `parent_step_id` is NULL (this is a new step, not a transfer)
- ✓ User cannot accidentally set parent_step_id

### Transferring a Step (POST /steps/{step_id}/transfer)
```json
{
  "quantity": 1,
  "weight": 14.8,
  "next_step_type": "polishing",
  "next_description": "Polish the ring",
  "received_by": "Jane Smith",
  "department": "Polishing"
}
```

Result:
- ✓ `tenant_id` is automatically set from authenticated user
- ✓ `parent_step_id` is automatically set to the source step's ID
- ✓ Creates a proper parent-child relationship

## Testing

Run the test script to verify the fixes:

```bash
python3 test_manufacturing_fixes.py
```

Expected output:
```
✓ ManufacturingStepCreate accepts data without parent_step_id
✓ parent_step_id is NOT included in ManufacturingStepCreate
✓ ManufacturingStepResponse accepts data with parent_step_id=None
✓ parent_step_id is correctly None for new steps
✓ TransferStepRequest created successfully
✓ parent_step_id will be set by the transfer endpoint
```

## API Examples

### Example 1: Create a New Manufacturing Step

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/manufacturing/steps" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1,
    "step_type": "casting",
    "description": "Cast 18K gold ring",
    "department": "Casting",
    "worker_name": "Maria Garcia",
    "quantity_received": 1,
    "weight_received": 15.5
  }'
```

**Response**:
```json
{
  "id": 1,
  "tenant_id": 1,
  "order_id": 1,
  "parent_step_id": null,
  "step_type": "casting",
  "description": "Cast 18K gold ring",
  "department": "Casting",
  "worker_name": "Maria Garcia",
  "status": "in_progress",
  "quantity_received": 1.0,
  "weight_received": 15.5,
  "created_at": "2026-01-31T10:00:00",
  "updated_at": "2026-01-31T10:00:00",
  "children": []
}
```

### Example 2: Transfer to Next Step

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/manufacturing/steps/1/transfer" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "quantity": 1,
    "weight": 14.8,
    "next_step_type": "polishing",
    "next_description": "Polish ring to mirror finish",
    "received_by": "Sarah Johnson",
    "department": "Polishing"
  }'
```

**Response**:
```json
{
  "message": "Transfer completed successfully",
  "parent_step_id": 1,
  "parent_step_status": "completed",
  "child_step_id": 2,
  "remaining_quantity": 0,
  "remaining_weight": 0
}
```

The child step (ID 2) will have:
- `parent_step_id`: 1
- `tenant_id`: Same as parent (from authenticated user)

## Files Modified

1. **app/schemas/manufacturing.py**
   - Removed `parent_step_id` from `ManufacturingStepBase`
   - Added `parent_step_id` to `ManufacturingStepResponse`

2. **app/api/v1/endpoints/manufacturing.py**
   - Modified `create_step` to explicitly set tenant_id in step data

## Benefits

1. **Cleaner API**: Users can't accidentally set parent_step_id when creating new steps
2. **Data Integrity**: tenant_id is always correctly set from authentication
3. **Clear Separation**: New steps vs. transferred steps are handled differently
4. **Better UX**: API is more intuitive - parent_step_id is only relevant for transfers

## Migration Impact

No database migration needed - these are API/schema-level fixes only.

## Troubleshooting

### If tenant_id is still NULL in database:

1. **Check Authentication**: Ensure the user is properly authenticated and has a tenant_id
   ```bash
   # Test with a valid JWT token
   curl -X GET "http://localhost:8000/api/v1/auth/me" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```
   
   Response should include `tenant_id`:
   ```json
   {
     "id": 1,
     "tenant_id": 1,
     "email": "user@example.com",
     ...
   }
   ```

2. **Run the test script**:
   ```bash
   python3 test_tenant_id_insertion.py
   ```
   
   This will check:
   - If the table structure is correct
   - If existing records have tenant_id
   - If there are any NULL tenant_id records

3. **Check application logs**: Look for error messages like:
   - "User does not have a tenant_id"
   - "Failed to set tenant_id"
   - "tenant_id not set on ManufacturingStep object"

4. **Fix existing NULL records**:
   ```sql
   -- Update NULL tenant_id from related order
   UPDATE manufacturing_steps
   SET tenant_id = (
     SELECT tenant_id FROM orders 
     WHERE orders.id = manufacturing_steps.order_id
   )
   WHERE tenant_id IS NULL;
   ```

### Enum Value Mismatch

The enum values in the model have been updated to use lowercase with underscores:
- ✓ Use: `"casting"`, `"stone_setting"`, `"in_progress"`
- ✗ Don't use: `"CASTING"`, `"STONE_SETTING"`, `"IN_PROGRESS"`

If you get enum validation errors, make sure you're using the correct lowercase format.

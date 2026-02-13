# Implementation Plan: Tenant Lookup Values

## Overview

Implement a hybrid enum management system: centralize system enums in code, move configurable enums to a tenant-scoped `lookup_values` database table, create CRUD API endpoints, update frontend forms to fetch options dynamically, and build an admin UI for managing lookup values.

## Tasks

- [x] 1. Centralize system enums and create lookup value data model
  - [x] 1.1 Create `app/domain/enums.py` with OrderStatus, StepStatus, and ShipmentStatus enum classes
    - Move enum definitions from `app/data/models/order.py`, `app/data/models/manufacturing_step.py`, and `app/data/models/shipment.py`
    - Update imports in all model files to reference `app.domain.enums`
    - Remove the old inline enum class definitions from model files (keep the imports)
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  - [x] 1.2 Create `app/data/models/lookup_value.py` with the LookupValue SQLAlchemy model
    - Define all fields: id, tenant_id, category, code, display_label, sort_order (default 0), is_active (default True), created_at, updated_at
    - Add UniqueConstraint on (tenant_id, category, code)
    - Add ForeignKey to tenants.id
    - Add relationship to Tenant model
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  - [x] 1.3 Create `app/schemas/lookup_value.py` with Pydantic schemas
    - LookupValueCreate: category, code (validated non-empty, auto-uppercased), display_label (validated non-empty), sort_order
    - LookupValueUpdate: optional display_label, sort_order, is_active
    - LookupValueResponse: all fields with `from_attributes = True`
    - _Requirements: 5.9, 5.10_
  - [ ]* 1.4 Write property test for unique constraint enforcement
    - **Property 5: Duplicate Code Rejection**
    - **Validates: Requirements 1.2, 5.4**

- [x] 2. Create Alembic migration for lookup_values table and column conversions
  - [x] 2.1 Create Alembic migration file
    - Create `lookup_values` table with all columns and unique constraint
    - Convert `orders.metal_type` from Enum to String(50)
    - Convert `manufacturing_steps.step_type` from Enum to String(50)
    - Convert `supplies.type` from Enum to String(50)
    - Leave status columns (orders.status, manufacturing_steps.status, shipments.status) as Enum type
    - Implement downgrade to reverse all changes
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 10.7_
  - [x] 2.2 Update SQLAlchemy model column definitions
    - Change `orders.metal_type` from `Column(Enum(MetalType))` to `Column(String(50))`
    - Change `manufacturing_steps.step_type` from `Column(Enum(StepType))` to `Column(String(50))`
    - Change `supplies.type` from `Column(Enum(SupplyType))` to `Column(String(50))`
    - Remove MetalType, StepType, SupplyType Python enum classes from model files
    - _Requirements: 2.2, 2.3, 2.4_

- [x] 3. Implement lookup value repository and service
  - [x] 3.1 Create `app/data/repositories/lookup_repository.py`
    - Extend BaseRepository[LookupValue]
    - Implement get_active_by_category(tenant_id, category)
    - Implement get_all_by_category(tenant_id, category, include_inactive)
    - Implement get_by_code(tenant_id, category, code)
    - Implement get_all_grouped(tenant_id, include_inactive)
    - Implement code_exists(tenant_id, category, code)
    - All methods must filter by tenant_id
    - _Requirements: 3.1, 3.4_
  - [x] 3.2 Create `app/domain/services/lookup_service.py`
    - Implement get_by_category, get_all_grouped, create_lookup_value, update_lookup_value, deactivate_lookup_value
    - Implement validate_lookup_code for validating configurable enum values
    - Implement seed_defaults with idempotent seeding logic
    - Code normalization: auto-uppercase code on create
    - Prevent modification of code/category on update
    - Raise DuplicateResourceError on duplicate code
    - Raise ValidationError on invalid lookup code
    - _Requirements: 3.2, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.3, 5.4, 5.5, 5.6, 5.7, 6.1, 6.2, 6.3, 6.4_
  - [ ]* 3.3 Write property tests for tenant isolation
    - **Property 1: Tenant Isolation**
    - **Validates: Requirements 3.1, 3.3**
  - [ ]* 3.4 Write property test for seeding idempotence
    - **Property 3: Seeding Idempotence**
    - **Validates: Requirements 4.6**
  - [ ]* 3.5 Write property test for lookup validation consistency
    - **Property 10: Lookup Validation Consistency**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

- [x] 4. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement lookup value API controller
  - [x] 5.1 Create `app/presentation/api/v1/controllers/lookup_controller.py`
    - GET /lookup-values with optional category and include_inactive query params
    - POST /lookup-values to create a new lookup value (returns 201)
    - PUT /lookup-values/{id} to update display_label, sort_order, is_active
    - DELETE /lookup-values/{id} for soft delete
    - POST /lookup-values/seed to seed defaults for current tenant
    - All endpoints require authentication via get_current_active_user
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_
  - [x] 5.2 Register the lookup controller in `app/presentation/api/v1/router.py`
    - Add import for lookup_controller
    - Include router with prefix "/lookup-values" and tags ["lookup-values"]
    - _Requirements: 5.1_
  - [ ]* 5.3 Write property tests for API endpoints
    - **Property 4: Category Filtering Returns Active Values in Sort Order**
    - **Validates: Requirements 5.1**
  - [ ]* 5.4 Write property test for update immutability
    - **Property 6: Update Preserves Immutable Fields**
    - **Validates: Requirements 5.5, 5.6**
  - [ ]* 5.5 Write property test for soft delete
    - **Property 7: Soft Delete Preserves Record**
    - **Validates: Requirements 5.7**
  - [ ]* 5.6 Write property test for include_inactive filter
    - **Property 8: Include Inactive Filter**
    - **Validates: Requirements 5.8**
  - [ ]* 5.7 Write property test for whitespace input rejection
    - **Property 9: Whitespace-Only Input Rejection**
    - **Validates: Requirements 5.9, 5.10**

- [x] 6. Integrate lookup validation into existing entity services
  - [x] 6.1 Update order creation/update endpoints to validate metal_type against lookup values
    - Import LookupService in the orders endpoint/service
    - Call validate_lookup_code(tenant_id, "metal_type", metal_type) before saving
    - _Requirements: 6.1_
  - [x] 6.2 Update manufacturing step creation/update endpoints to validate step_type against lookup values
    - Import LookupService in the manufacturing endpoint/service
    - Call validate_lookup_code(tenant_id, "step_type", step_type) before saving
    - _Requirements: 6.2_
  - [x] 6.3 Update supply creation/update endpoints to validate type against lookup values
    - Import LookupService in the supplies endpoint/service
    - Call validate_lookup_code(tenant_id, "supply_type", type) before saving
    - _Requirements: 6.3_

- [x] 7. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Frontend: Create constants file and lookup values hook
  - [x] 8.1 Create `src/lib/constants.ts` with centralized system enum option arrays
    - Export ORDER_STATUS_OPTIONS, STEP_STATUS_OPTIONS, SHIPMENT_STATUS_OPTIONS
    - _Requirements: 10.5, 10.6_
  - [x] 8.2 Add LookupValue TypeScript types to `src/types/`
    - Define LookupValue, LookupValueCreate, LookupValueUpdate interfaces
    - _Requirements: 7.1_
  - [x] 8.3 Add lookup value API functions to `src/lib/api.ts`
    - fetchLookupValues(category?, includeInactive?)
    - createLookupValue(data)
    - updateLookupValue(id, data)
    - deleteLookupValue(id)
    - seedLookupDefaults()
    - _Requirements: 7.1_
  - [x] 8.4 Create `src/lib/useLookupValues.ts` custom hook
    - Use React Query with queryKey ['lookup-values', category]
    - Set staleTime to 5 minutes
    - Return { data, isLoading, isError, refetch }
    - Map API response to { value: code, label: display_label } format
    - _Requirements: 7.1, 7.2, 8.2_
  - [ ]* 8.5 Write property test for dropdown option mapping
    - **Property 11: Dropdown Option Mapping**
    - **Validates: Requirements 8.1, 8.2**

- [x] 9. Frontend: Update form components to use dynamic lookup values
  - [x] 9.1 Update OrderFormModal to use dynamic metal type options
    - Replace hardcoded metalTypeOptions with useLookupValues("metal_type")
    - Import ORDER_STATUS_OPTIONS from constants.ts for status dropdown (system enum stays hardcoded)
    - Add loading and error states for the metal type dropdown
    - _Requirements: 7.3, 7.6, 7.7_
  - [x] 9.2 Update ManufacturingFormModal to use dynamic step type options
    - Replace hardcoded stepTypeOptions with useLookupValues("step_type")
    - Import STEP_STATUS_OPTIONS from constants.ts for status dropdown (system enum stays hardcoded)
    - Add loading and error states for the step type dropdown
    - _Requirements: 7.4, 7.6, 7.7_
  - [x] 9.3 Update SupplyFormModal to use dynamic supply type options and fix case mismatch
    - Replace hardcoded SUPPLY_TYPES with useLookupValues("supply_type")
    - Values now come from API as UPPER_CASE codes, fixing the case mismatch bug
    - Add loading and error states for the supply type dropdown
    - _Requirements: 7.5, 7.6, 7.7, 8.1, 8.3_
  - [x] 9.4 Update ShipmentFormModal to import status options from constants.ts
    - Replace inline statusOptions with import from constants.ts (SHIPMENT_STATUS_OPTIONS)
    - _Requirements: 10.5, 10.6_

- [x] 10. Frontend: Build admin UI for managing lookup values
  - [x] 10.1 Create `src/pages/LookupValues.tsx` admin page
    - Display all categories with their lookup values
    - Support add, edit, deactivate, and reactivate operations
    - Show deactivated values with visual distinction (e.g., grayed out, strikethrough)
    - Display error messages from API (e.g., duplicate code)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_
  - [x] 10.2 Create `src/components/LookupValueFormModal.tsx` form modal
    - Form fields: code (disabled in edit mode), display_label, sort_order
    - Validation for required fields
    - _Requirements: 9.2, 9.3, 9.4_
  - [x] 10.3 Add route and navigation for the lookup values page
    - Add route in App.tsx
    - Add navigation item in sidebar (under Settings or similar section)
    - _Requirements: 9.1_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis (Python) and fast-check (TypeScript)
- Unit tests validate specific examples and edge cases
- The backend tasks (1–7) can be completed independently before frontend tasks (8–10)

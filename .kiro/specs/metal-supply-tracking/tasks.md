# Implementation Plan: Metal Supply Tracking

## Overview

Implementation is broken into 5 deployable phases. After each phase, the system can be deployed and tested independently. Each phase builds on the previous one.

- **Phase 1**: Metal entity + CRUD API (standalone, no dependencies on other phases)
- **Phase 2**: Safe supply + purchase API
- **Phase 3**: Company metal balance + deposit API
- **Phase 4**: Casting consumption calculation + auto-adjustments
- **Phase 5**: Frontend screens (Metal management, company balances)

## Tasks

### Phase 1: Metal Entity & CRUD API

- [x] 1. Create Metal data model and migration
  - [x] 1.1 Create `app/data/models/metal.py` with Metal SQLAlchemy model (id, tenant_id, code, name, fine_percentage, average_cost_per_gram, is_active, timestamps, unique constraint on tenant_id+code)
    - Register model in `app/data/models/__init__.py`
    - Add `metals` relationship to Tenant model
    - _Requirements: 1.1, 1.2, 1.3_
  - [x] 1.2 Create Alembic migration for the `metals` table
    - Run `alembic revision --autogenerate -m "add metals table"`
    - _Requirements: 13.1_
  - [x] 1.3 Create Pydantic schemas in `app/schemas/metal.py` (MetalCreate, MetalUpdate, MetalResponse)
    - MetalCreate: code (auto-uppercase, non-empty), name, fine_percentage (0-1 validated), average_cost_per_gram (optional)
    - MetalUpdate: name, fine_percentage, average_cost_per_gram, is_active (all optional)
    - MetalResponse: all fields including id, tenant_id, timestamps
    - _Requirements: 1.4, 9.5_
  - [ ]* 1.4 Write property test for fine_percentage validation (Property 1)
    - **Property 1: Fine percentage range validation**
    - **Validates: Requirements 1.4, 9.7**

- [x] 2. Create Metal repository and service
  - [x] 2.1 Create `app/data/repositories/metal_repository.py` extending BaseRepository
    - Methods: get_by_code, code_exists, get_active (ordered by name), get_all_with_inactive
    - All queries filtered by tenant_id
    - _Requirements: 9.1, 9.8_
  - [x] 2.2 Create `app/domain/services/metal_service.py` with MetalService
    - CRUD methods: get_all, get_by_id, get_by_code, create, update, deactivate
    - seed_defaults() for default metals (GOLD_24K, GOLD_22K, GOLD_18K, GOLD_14K, SILVER_925, PLATINUM)
    - Duplicate code check on create, immutable code on update
    - _Requirements: 1.5, 1.6, 9.1-9.8_
  - [ ]* 2.3 Write property test for metal code uniqueness (Property 2)
    - **Property 2: Metal code uniqueness per tenant**
    - **Validates: Requirements 1.2, 9.3**
  - [ ]* 2.4 Write property test for seed idempotence (Property 3)
    - **Property 3: Metal seed idempotence**
    - **Validates: Requirements 1.6**

- [x] 3. Create Metal controller and wire routes
  - [x] 3.1 Create `app/presentation/api/v1/controllers/metal_controller.py`
    - GET / (list active, optional include_inactive), POST / (create), GET /{id}, PUT /{id} (update), DELETE /{id} (soft delete)
    - Role check: write operations require manager+ role
    - Follow existing controller pattern (DomainException → HTTPException)
    - _Requirements: 9.1-9.8, 10.1-10.3_
  - [x] 3.2 Register metal controller in `app/presentation/api/v1/router.py` at prefix `/metals`
    - _Requirements: 9.1_
  - [x] 3.3 Add role-checking dependency function in `app/presentation/api/dependencies.py`
    - `require_manager_role(current_user)` that raises ForbiddenError if role is not manager/admin
    - _Requirements: 10.1, 10.2_
  - [ ]* 3.4 Write property test for role-based access (Property 12)
    - **Property 12: Role-based write access on metals**
    - **Validates: Requirements 10.1, 10.2, 10.3**
  - [ ]* 3.5 Write property test for soft delete behavior (Property 11)
    - **Property 11: Soft delete preserves record**
    - **Validates: Requirements 9.6, 9.8**

- [x] 4. Phase 1 Checkpoint
  - Ensure all tests pass, ask the user if questions arise.
  - At this point: Metal CRUD API is fully functional, metals can be created/read/updated/deactivated, role-based access enforced.

### Phase 2: Safe Supply & Purchase API

- [x] 5. Create Safe Supply data model and migration
  - [x] 5.1 Create `app/data/models/safe_supply.py` with SafeSupply model (id, tenant_id, metal_id nullable, supply_type, quantity_grams, timestamps, unique constraint on tenant_id+metal_id+supply_type)
    - Register model in `app/data/models/__init__.py`
    - _Requirements: 2.1, 2.2_
  - [x] 5.2 Create `app/data/models/metal_transaction.py` with MetalTransaction model (id, tenant_id, transaction_type, metal_id nullable, company_id nullable, order_id nullable, quantity_grams, notes, created_at, created_by)
    - Register model in `app/data/models/__init__.py`
    - _Requirements: 4.1_
  - [x] 5.3 Create Alembic migration for `safe_supplies` and `metal_transactions` tables
    - _Requirements: 13.2, 13.4_

- [x] 6. Create Safe Supply repository, schemas, and service
  - [x] 6.1 Create `app/data/repositories/safe_supply_repository.py` extending BaseRepository
    - Methods: get_or_create(tenant_id, metal_id, supply_type), get_all_for_tenant(tenant_id)
    - _Requirements: 2.1_
  - [x] 6.2 Create `app/data/repositories/metal_transaction_repository.py` extending BaseRepository
    - Methods: get_filtered(tenant_id, filters)
    - _Requirements: 4.1_
  - [x] 6.3 Create Pydantic schemas in `app/schemas/supply_tracking.py` (SafePurchaseCreate, SafeSupplyResponse, MetalTransactionResponse)
    - SafePurchaseCreate: metal_id (optional), supply_type ("FINE_METAL"/"ALLOY"), quantity_grams (>0), cost_per_gram (>=0)
    - _Requirements: 8.1, 8.4_
  - [x] 6.4 Create `app/domain/services/supply_tracking_service.py` with SupplyTrackingService
    - Implement record_safe_purchase(): increase safe supply, update weighted average cost on Metal, create SAFE_PURCHASE transaction
    - Implement get_safe_supplies()
    - Implement get_transactions()
    - _Requirements: 2.3, 2.4, 8.1, 8.2, 8.3_
  - [ ]* 6.5 Write property test for purchase increases safe supply (Property 6)
    - **Property 6: Purchase increases safe supply**
    - **Validates: Requirements 2.3, 2.4, 8.1**
  - [ ]* 6.6 Write property test for weighted average cost (Property 9)
    - **Property 9: Weighted average cost calculation**
    - **Validates: Requirements 8.2**
  - [ ]* 6.7 Write property test for non-positive quantity rejection (Property 10)
    - **Property 10: Non-positive quantity rejection**
    - **Validates: Requirements 7.3, 8.4**

- [x] 7. Create Safe Supply controller and wire routes
  - [x] 7.1 Create supply tracking controller routes for safe purchases
    - POST /api/v1/safe/purchases, GET /api/v1/safe/supplies, GET /api/v1/metal-transactions
    - _Requirements: 8.1, 8.4_
  - [x] 7.2 Register supply tracking controller in router.py
    - _Requirements: 8.1_

- [x] 8. Phase 2 Checkpoint
  - Ensure all tests pass, ask the user if questions arise.
  - At this point: Safe supply tracking works, purchases can be recorded, transaction ledger is active.

### Phase 3: Company Metal Balance & Deposit API

- [x] 9. Create Company Metal Balance model and migration
  - [x] 9.1 Create `app/data/models/company_metal_balance.py` with CompanyMetalBalance model (id, tenant_id, company_id, metal_id, balance_grams, timestamps, unique constraint on tenant_id+company_id+metal_id)
    - Register model in `app/data/models/__init__.py`
    - Add relationship to Company model
    - _Requirements: 3.1, 3.2_
  - [x] 9.2 Create Alembic migration for `company_metal_balances` table
    - _Requirements: 13.3_

- [x] 10. Create Company Metal Balance repository, schemas, and deposit logic
  - [x] 10.1 Create `app/data/repositories/company_metal_balance_repository.py` extending BaseRepository
    - Methods: get_or_create(tenant_id, company_id, metal_id), get_by_company(tenant_id, company_id)
    - _Requirements: 3.1_
  - [x] 10.2 Add deposit schemas to `app/schemas/supply_tracking.py` (MetalDepositCreate, CompanyMetalBalanceResponse)
    - MetalDepositCreate: metal_id, quantity_grams (>0)
    - _Requirements: 7.1, 7.3_
  - [x] 10.3 Add record_company_deposit() and get_company_balances() to SupplyTrackingService
    - Deposit increases both Company_Metal_Balance and Safe_Supply (FINE_METAL)
    - Creates COMPANY_DEPOSIT transaction
    - Validates company_id and metal_id exist
    - _Requirements: 3.3, 3.4, 4.2, 7.1-7.5_
  - [ ]* 10.4 Write property test for deposit dual-update (Property 5)
    - **Property 5: Deposit dual-update invariant**
    - **Validates: Requirements 3.3, 3.4, 7.1**
  - [ ]* 10.5 Write property test for transaction ledger completeness (Property 8)
    - **Property 8: Transaction ledger completeness and sign convention**
    - **Validates: Requirements 4.2, 4.3, 4.4, 4.5**

- [x] 11. Create deposit and balance API endpoints
  - [x] 11.1 Add company deposit and balance routes to supply tracking controller
    - POST /api/v1/companies/{company_id}/metal-deposits
    - GET /api/v1/companies/{company_id}/metal-balances
    - _Requirements: 7.1-7.5_
  - [x] 11.2 Wire new routes in router.py
    - _Requirements: 7.1_

- [x] 12. Phase 3 Checkpoint
  - Ensure all tests pass, ask the user if questions arise.
  - At this point: Company deposits work, balances are tracked, safe supply updates on deposit.

### Phase 4: Casting Consumption & Order Labor Cost

- [ ] 13. Add labor_cost to Order model
  - [ ] 13.1 Add `labor_cost = Column(Float, nullable=True)` to Order model in `app/data/models/order.py`
    - _Requirements: 5.1_
  - [ ] 13.2 Update Order schemas in `app/schemas/order.py` to include labor_cost in OrderCreate, OrderUpdate, and OrderResponse
    - _Requirements: 5.2, 5.3_
  - [ ] 13.3 Create Alembic migration to add labor_cost column to orders table
    - _Requirements: 13.5_

- [ ] 14. Implement casting consumption logic
  - [ ] 14.1 Add `_calculate_casting_consumption(total_weight, fine_percentage)` method to SupplyTrackingService
    - Returns (fine_metal_grams, alloy_grams) where fine_metal = total_weight * fine_percentage, alloy = total_weight - fine_metal
    - _Requirements: 6.1, 6.2_
  - [ ] 14.2 Add `process_casting_consumption(tenant_id, order_id, user_id)` method to SupplyTrackingService
    - Fetch order, validate metal_type exists as active Metal, calculate consumption
    - Subtract fine_metal from company balance, subtract alloy from safe
    - If company balance goes negative, subtract deficit from fine metal safe supply
    - Create MANUFACTURING_CONSUMPTION transactions
    - Skip if order missing metal_type or target_weight_per_piece
    - _Requirements: 6.1-6.9, 3.5, 2.5, 2.6_
  - [ ] 14.3 Add CastingConsumptionResult schema to `app/schemas/supply_tracking.py`
    - _Requirements: 6.1_
  - [ ]* 14.4 Write property test for conservation of mass (Property 4)
    - **Property 4: Conservation of mass in casting calculation**
    - **Validates: Requirements 6.1, 6.2**
  - [ ]* 14.5 Write property test for casting consumption balance adjustments (Property 7)
    - **Property 7: Casting consumption balance adjustments**
    - **Validates: Requirements 3.5, 2.5, 2.6, 6.5, 6.6, 6.7**

- [ ] 15. Integrate casting consumption with manufacturing step completion
  - [ ] 15.1 Modify the manufacturing step completion flow to call `process_casting_consumption()` when a step with step_type "CASTING" is completed
    - Check if step_type == "CASTING" and status is being set to COMPLETED
    - Call SupplyTrackingService.process_casting_consumption()
    - This integrates with the existing manufacturing endpoint (legacy or clean architecture)
    - _Requirements: 6.1-6.9_
  - [ ]* 15.2 Write unit tests for casting integration
    - Test casting step triggers consumption
    - Test non-casting steps do not trigger consumption
    - Test order with missing metal_type skips calculation
    - _Requirements: 6.8, 6.9_

- [ ] 16. Phase 4 Checkpoint
  - Ensure all tests pass, ask the user if questions arise.
  - At this point: Full backend is complete. Casting auto-calculates consumption, labor cost on orders, all balance adjustments work.

### Phase 5: Frontend Screens

- [ ] 17. Create Metal management page
  - [ ] 17.1 Create `useMetals()` hook in `src/hooks/useMetals.ts`
    - CRUD operations via React Query: list, create, update, deactivate
    - _Requirements: 11.1_
  - [ ] 17.2 Create `src/pages/Metals.tsx` page
    - Table with code, name, fine_percentage (as %), average_cost_per_gram
    - Add/Edit/Deactivate controls visible only to manager+ roles
    - Fine percentage displayed as percentage (e.g., 58.5%)
    - _Requirements: 11.1-11.6_
  - [ ] 17.3 Create `src/components/MetalFormModal.tsx`
    - Form for creating/editing metals
    - Code field disabled on edit
    - Fine percentage input as percentage (user enters 58.5, stored as 0.585)
    - _Requirements: 11.2, 11.3_
  - [ ] 17.4 Add Metals page to navigation in `src/components/Layout.tsx` and router
    - _Requirements: 11.1_

- [ ] 18. Create Company Metal Balance view and deposit flow
  - [ ] 18.1 Create `useCompanyMetalBalances(companyId)` hook in `src/hooks/useCompanyMetalBalances.ts`
    - Fetch balances, record deposit
    - _Requirements: 12.1_
  - [ ] 18.2 Create `src/components/CompanyMetalBalances.tsx` component
    - Table of per-metal balances, negative balances highlighted in red
    - "Record Deposit" button for manager+ roles
    - _Requirements: 12.1-12.3_
  - [ ] 18.3 Create `src/components/MetalDepositModal.tsx`
    - Form: select metal (from useMetals), enter quantity in grams
    - Validates positive quantity
    - _Requirements: 12.3_
  - [ ] 18.4 Integrate CompanyMetalBalances into company detail page
    - _Requirements: 12.1_

- [ ] 19. Update Order form with labor cost field
  - [ ] 19.1 Add labor_cost field to `src/components/OrderFormModal.tsx`
    - Optional numeric input for labor cost
    - _Requirements: 5.3_

- [ ] 20. Final Checkpoint
  - Ensure all tests pass, ask the user if questions arise.
  - Full feature is complete: backend API, frontend screens, casting calculations, balance tracking.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each phase (1-5) is independently deployable and testable
- Phase 1-4 are backend-only; Phase 5 is frontend-only
- Property tests use Hypothesis (Python) and fast-check (TypeScript)
- Checkpoints at phases 1-4 ensure incremental validation before building on top

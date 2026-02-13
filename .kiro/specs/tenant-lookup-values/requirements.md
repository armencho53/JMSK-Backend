    # Requirements Document

    ## Introduction

    This feature introduces a hybrid enum management system for the JMSK multi-tenant jewelry manufacturing SaaS. Enums are split into two categories: system enums that drive application logic (OrderStatus, StepStatus, ShipmentStatus) remain as Python enums in code, while configurable enums that serve as labels/categories (MetalType, StepType, SupplyType) are moved to a tenant-scoped database table called `lookup_values`. Each tenant can customize their own set of lookup values, with sensible defaults seeded from the current hardcoded values. The frontend fetches these values from the API instead of using hardcoded arrays, and an admin UI allows tenants to manage their lookup values.

    ## Glossary

    - **Lookup_Value**: A tenant-scoped configurable enum entry stored in the database, consisting of a category, code, display label, sort order, and active status.
    - **Category**: A grouping identifier for lookup values (e.g., "metal_type", "step_type", "supply_type"). Categories use snake_case naming.
    - **System_Enum**: An enum that drives application branching logic (if/switch statements) and remains hardcoded in Python and TypeScript code. Examples: OrderStatus, StepStatus, ShipmentStatus.
    - **Configurable_Enum**: An enum that serves only as a label or category tag with no branching logic depending on specific values. These are migrated to the lookup_values table.
    - **Lookup_API**: The set of backend REST endpoints for CRUD operations on Lookup_Values.
    - **Lookup_Service**: The domain layer service responsible for business logic around Lookup_Values.
    - **Lookup_Repository**: The data layer repository responsible for database operations on Lookup_Values.
    - **Seed_Data**: The default set of Lookup_Values created for a new tenant, derived from the current hardcoded enum values.
    - **Tenant**: An isolated organizational unit in the system. Each jewelry manufacturer is a Tenant.
    - **Admin_UI**: The frontend page where administrators manage Lookup_Values for their tenant.

    ## Requirements

    ### Requirement 1: Lookup Value Data Model

    **User Story:** As a system architect, I want a database table that stores configurable enum values per tenant, so that tenants can customize their own categories without code changes.

    #### Acceptance Criteria

    1. THE Lookup_Value model SHALL have the following fields: id (primary key), tenant_id (foreign key to tenants), category (string, not null), code (string, not null, UPPER_CASE), display_label (string, not null), sort_order (integer, default 0), is_active (boolean, default true), created_at (datetime), and updated_at (datetime).
    2. THE Lookup_Value model SHALL enforce a unique constraint on the combination of tenant_id, category, and code.
    3. THE Lookup_Value model SHALL enforce a foreign key constraint from tenant_id to the tenants table.
    4. WHEN a Lookup_Value is created without a sort_order, THE Lookup_Value model SHALL default sort_order to 0.
    5. WHEN a Lookup_Value is created without an is_active value, THE Lookup_Value model SHALL default is_active to true.

    ### Requirement 2: Database Migration

    **User Story:** As a developer, I want an Alembic migration that creates the lookup_values table and converts existing enum columns to string type, so that the database supports dynamic lookup values.

    #### Acceptance Criteria

    1. WHEN the migration runs, THE Migration SHALL create the lookup_values table with all fields defined in Requirement 1.
    2. WHEN the migration runs, THE Migration SHALL convert the metal_type column in the orders table from SQLAlchemy Enum type to String type.
    3. WHEN the migration runs, THE Migration SHALL convert the step_type column in the manufacturing_steps table from SQLAlchemy Enum type to String type.
    4. WHEN the migration runs, THE Migration SHALL convert the type column in the supplies table from SQLAlchemy Enum type to String type.
    5. WHEN the migration runs, THE Migration SHALL preserve all existing data in the converted columns.
    6. WHEN the migration is rolled back, THE Migration SHALL restore the original Enum column types and drop the lookup_values table.

    ### Requirement 3: Tenant Isolation for Lookup Values

    **User Story:** As a tenant administrator, I want lookup values to be scoped to my tenant, so that my customizations do not affect other tenants.

    #### Acceptance Criteria

    1. WHEN a Lookup_Value is queried, THE Lookup_Repository SHALL filter results by the requesting tenant_id.
    2. WHEN a Lookup_Value is created, THE Lookup_Service SHALL associate the Lookup_Value with the authenticated tenant_id from the JWT token.
    3. WHEN a tenant attempts to access a Lookup_Value belonging to a different tenant, THE Lookup_API SHALL return a 404 Not Found response.
    4. THE Lookup_Repository SHALL include tenant_id in all query filters for Lookup_Values.

    ### Requirement 4: Seed Default Lookup Values

    **User Story:** As a new tenant, I want default lookup values pre-populated when my tenant is created, so that the system is immediately usable with standard jewelry manufacturing categories.

    #### Acceptance Criteria

    1. WHEN a new tenant is created, THE Lookup_Service SHALL seed default Lookup_Values for the "metal_type" category with codes: GOLD_24K, GOLD_22K, GOLD_18K, GOLD_14K, SILVER_925, PLATINUM, OTHER.
    2. WHEN a new tenant is created, THE Lookup_Service SHALL seed default Lookup_Values for the "step_type" category with codes: DESIGN, CASTING, STONE_SETTING, POLISHING, ENGRAVING, QUALITY_CHECK, FINISHING, OTHER.
    3. WHEN a new tenant is created, THE Lookup_Service SHALL seed default Lookup_Values for the "supply_type" category with codes: METAL, GEMSTONE, TOOL, PACKAGING, OTHER.
    4. WHEN default Lookup_Values are seeded, THE Lookup_Service SHALL assign human-readable display_labels (e.g., code "GOLD_24K" gets display_label "Gold 24K").
    5. WHEN default Lookup_Values are seeded, THE Lookup_Service SHALL assign sequential sort_order values starting from 0.
    6. THE Seed_Data function SHALL be idempotent so that running the seed operation multiple times for the same tenant does not create duplicate Lookup_Values.

    ### Requirement 5: Lookup Value CRUD API

    **User Story:** As a tenant administrator, I want API endpoints to create, read, update, and deactivate lookup values, so that I can manage my tenant's configurable categories.

    #### Acceptance Criteria

    1. WHEN a GET request is made to the list endpoint with a category query parameter, THE Lookup_API SHALL return all active Lookup_Values for the authenticated tenant filtered by that category, ordered by sort_order.
    2. WHEN a GET request is made to the list endpoint without a category parameter, THE Lookup_API SHALL return all active Lookup_Values for the authenticated tenant, grouped by category.
    3. WHEN a POST request is made with valid Lookup_Value data, THE Lookup_API SHALL create a new Lookup_Value for the authenticated tenant and return the created resource with a 201 status code.
    4. WHEN a POST request is made with a duplicate category and code combination for the same tenant, THE Lookup_API SHALL return a 409 Conflict response.
    5. WHEN a PUT request is made with valid update data, THE Lookup_API SHALL update the display_label, sort_order, or is_active fields of the specified Lookup_Value.
    6. WHEN a PUT request is made, THE Lookup_API SHALL prevent modification of the category and code fields.
    7. WHEN a DELETE request is made for a Lookup_Value, THE Lookup_API SHALL set is_active to false (soft delete) rather than removing the record.
    8. WHEN a GET request is made with an include_inactive query parameter set to true, THE Lookup_API SHALL return both active and inactive Lookup_Values.
    9. IF a POST request is made with an empty or whitespace-only code, THEN THE Lookup_API SHALL return a 422 Validation Error response.
    10. IF a POST request is made with an empty or whitespace-only display_label, THEN THE Lookup_API SHALL return a 422 Validation Error response.

    ### Requirement 6: Backend Validation Against Lookup Values

    **User Story:** As a developer, I want the backend to validate configurable enum fields against the lookup_values table instead of Python enums, so that tenant-specific values are accepted.

    #### Acceptance Criteria

    1. WHEN an order is created or updated with a metal_type value, THE Lookup_Service SHALL validate that the value exists as an active Lookup_Value in the "metal_type" category for the requesting tenant.
    2. WHEN a manufacturing step is created or updated with a step_type value, THE Lookup_Service SHALL validate that the value exists as an active Lookup_Value in the "step_type" category for the requesting tenant.
    3. WHEN a supply is created or updated with a type value, THE Lookup_Service SHALL validate that the value exists as an active Lookup_Value in the "supply_type" category for the requesting tenant.
    4. IF a configurable enum field value does not match any active Lookup_Value for the tenant and category, THEN THE Lookup_Service SHALL raise a validation error with a descriptive message indicating the invalid value and the valid options.

    ### Requirement 7: Frontend Lookup Value Fetching

    **User Story:** As a frontend developer, I want to fetch lookup values from the API and cache them with React Query, so that form dropdowns display tenant-specific options.

    #### Acceptance Criteria

    1. WHEN a form component that uses a configurable enum mounts, THE Frontend SHALL fetch the relevant Lookup_Values from the Lookup_API.
    2. THE Frontend SHALL cache fetched Lookup_Values using React Query with a stale time of 5 minutes.
    3. WHEN the OrderFormModal renders the metal type dropdown, THE Frontend SHALL populate options from the "metal_type" Lookup_Values instead of the hardcoded metalTypeOptions array.
    4. WHEN the ManufacturingFormModal renders the step type dropdown, THE Frontend SHALL populate options from the "step_type" Lookup_Values instead of the hardcoded stepTypeOptions array.
    5. WHEN the SupplyFormModal renders the supply type dropdown, THE Frontend SHALL populate options from the "supply_type" Lookup_Values instead of the hardcoded SUPPLY_TYPES array.
    6. WHILE Lookup_Values are loading, THE Frontend SHALL display a loading indicator in the dropdown.
    7. IF fetching Lookup_Values fails, THEN THE Frontend SHALL display an error message and allow the user to retry.

    ### Requirement 8: Fix Supply Type Case Mismatch

    **User Story:** As a developer, I want the supply type values to use consistent UPPER_CASE format between frontend and backend, so that supply creation and editing works correctly.

    #### Acceptance Criteria

    1. THE Frontend SupplyFormModal SHALL send supply type values in UPPER_CASE format (e.g., "METAL", "GEMSTONE") matching the backend expectation.
    2. WHEN Lookup_Values are fetched for the "supply_type" category, THE Frontend SHALL use the code field (UPPER_CASE) as the option value and the display_label field as the option label.
    3. WHEN existing supplies are loaded for editing, THE Frontend SHALL correctly match the UPPER_CASE type value from the backend to the corresponding Lookup_Value.

    ### Requirement 9: Admin UI for Managing Lookup Values

    **User Story:** As a tenant administrator, I want a settings page to manage lookup values, so that I can add, edit, reorder, and deactivate configurable enum values for my organization.

    #### Acceptance Criteria

    1. WHEN an administrator navigates to the lookup values management page, THE Admin_UI SHALL display all categories with their Lookup_Values listed under each category.
    2. WHEN an administrator clicks "Add Value" for a category, THE Admin_UI SHALL display a form to enter the code, display_label, and sort_order for the new Lookup_Value.
    3. WHEN an administrator edits a Lookup_Value, THE Admin_UI SHALL allow modification of the display_label and sort_order fields.
    4. WHEN an administrator edits a Lookup_Value, THE Admin_UI SHALL prevent modification of the code field.
    5. WHEN an administrator deactivates a Lookup_Value, THE Admin_UI SHALL visually distinguish the deactivated value from active values.
    6. WHEN an administrator reactivates a deactivated Lookup_Value, THE Admin_UI SHALL restore the value to active status.
    7. IF an administrator attempts to add a Lookup_Value with a duplicate code within the same category, THEN THE Admin_UI SHALL display an error message from the API response.

### Requirement 10: System Enums Centralized and Unchanged

**User Story:** As a developer, I want system enums (OrderStatus, StepStatus, ShipmentStatus) centralized in a single file per project and retained as code-level enums, so that application branching logic continues to work correctly and enum definitions are easy to find.

#### Acceptance Criteria

1. THE Backend SHALL consolidate all system enum definitions (OrderStatus, StepStatus, ShipmentStatus) into a single central file (e.g., app/domain/enums.py) and all model files SHALL import from that central location.
2. THE Backend SHALL retain OrderStatus as a Python enum class with values: PENDING, IN_PROGRESS, COMPLETED, SHIPPED, CANCELLED.
3. THE Backend SHALL retain StepStatus as a Python enum class with values: IN_PROGRESS, COMPLETED, FAILED.
4. THE Backend SHALL retain ShipmentStatus as a Python enum class with values: PREPARING, SHIPPED, IN_TRANSIT, DELIVERED, RETURNED.
5. THE Frontend SHALL consolidate all system enum option arrays (statusOptions for orders, statusOptions for manufacturing steps, statusOptions for shipments) into a single central constants file (e.g., src/lib/constants.ts) and all form components SHALL import from that central location.
6. THE Frontend SHALL continue to use hardcoded status option arrays for OrderStatus, StepStatus, and ShipmentStatus dropdowns.
7. WHEN the configurable enum columns are migrated to String type, THE Migration SHALL leave the status columns (order status, step status, shipment status) as SQLAlchemy Enum type.

# Requirements Document

## Introduction

This feature introduces comprehensive metal supply tracking for the JMSK jewelry manufacturing SaaS. It replaces the simple string-based metal_type lookup with a dedicated Metal entity that tracks fine percentage, metal code, and average cost per gram. The system tracks two pools of metal: the "safe" (the manufacturer's own supply of fine metals and alloy) and per-company metal balances (metal deposited by companies for their orders). During manufacturing (specifically the casting step), the system calculates fine metal and alloy consumption based on target karat purity and item weight, automatically adjusting both company balances and safe supply. Companies pay for orders with fine metal (which they deposit) and cash for labor. Company metal balances can go negative, indicating the manufacturer's own supply was consumed. The feature also adds labor cost tracking to orders and provides a frontend Metal management screen accessible to manager-level roles and above.

## Glossary

- **Metal**: A dedicated database entity representing a type of metal with its fine percentage, code, and average cost per gram. Replaces the simple metal_type lookup for metal-specific tracking.
- **Fine_Percentage**: The purity of a metal expressed as a decimal between 0 and 1 (e.g., 0.999 for 24K gold, 0.585 for 14K gold, 0.925 for Silver 925).
- **Fine_Metal**: Pure metal content (e.g., pure gold at 99.9%). Companies deposit fine metal for their orders.
- **Alloy**: Non-precious metal mixed with fine metal to achieve a target karat. Companies do not provide alloy; the manufacturer purchases and tracks alloy separately.
- **Safe**: The manufacturer's own inventory of fine metals and alloy, tracked per metal type per tenant. Represents what is physically stored in the safe/vault.
- **Company_Metal_Balance**: A per-company, per-metal-type ledger tracking how much fine metal a company has deposited minus how much has been consumed during manufacturing. Can go negative.
- **Metal_Transaction**: A record of any change to a company's metal balance or the safe supply, including deposits, manufacturing consumption, and purchases.
- **Casting_Step**: The manufacturing step where raw metal is melted and formed. This is the step where fine metal and alloy consumption is calculated and balances are adjusted.
- **Labor_Cost**: A monetary amount (in the tenant's currency) charged for the work performed on an order, entered manually during order creation or update.
- **Metal_Service**: The domain layer service responsible for metal CRUD operations and fine percentage calculations.
- **Supply_Tracking_Service**: The domain layer service responsible for safe supply and company balance adjustments during manufacturing and deposits.
- **Tenant**: An isolated organizational unit in the system. Each jewelry manufacturer is a Tenant.

## Requirements

### Requirement 1: Metal Entity Data Model

**User Story:** As a system architect, I want a dedicated Metal database table that stores metal types with their fine percentage and cost information, so that the system can perform accurate purity-based calculations during manufacturing.

#### Acceptance Criteria

1. THE Metal model SHALL have the following fields: id (primary key), tenant_id (foreign key to tenants), code (string, not null, UPPER_CASE, unique per tenant), name (string, not null), fine_percentage (float, not null, between 0 and 1 inclusive), average_cost_per_gram (float, nullable), is_active (boolean, default true), created_at (datetime), and updated_at (datetime).
2. THE Metal model SHALL enforce a unique constraint on the combination of tenant_id and code.
3. WHEN a Metal record is created without an average_cost_per_gram, THE Metal model SHALL default average_cost_per_gram to null.
4. WHEN a Metal record is created, THE Metal model SHALL validate that fine_percentage is between 0 and 1 inclusive.
5. WHEN a new tenant is created, THE Metal_Service SHALL seed default Metal records: GOLD_24K (0.999), GOLD_22K (0.916), GOLD_18K (0.750), GOLD_14K (0.585), SILVER_925 (0.925), PLATINUM (0.950).
6. THE Seed function for Metal records SHALL be idempotent so that running the seed operation multiple times for the same tenant does not create duplicate Metal records.

### Requirement 2: Safe Supply Tracking

**User Story:** As a jewelry manufacturer, I want to track my own inventory of fine metals and alloy in a "safe," so that I know how much material I have available for manufacturing.

#### Acceptance Criteria

1. THE Safe_Supply model SHALL have the following fields: id (primary key), tenant_id (foreign key to tenants), metal_id (foreign key to metals, nullable for alloy), supply_type (string, either "FINE_METAL" or "ALLOY"), quantity_grams (float, not null, default 0), created_at (datetime), and updated_at (datetime).
2. THE Safe_Supply model SHALL enforce a unique constraint on the combination of tenant_id, metal_id, and supply_type.
3. WHEN a manufacturer purchases fine metal, THE Supply_Tracking_Service SHALL increase the corresponding Safe_Supply quantity_grams.
4. WHEN a manufacturer purchases alloy, THE Supply_Tracking_Service SHALL increase the alloy Safe_Supply quantity_grams.
5. WHEN fine metal is consumed during a casting step, THE Supply_Tracking_Service SHALL decrease the corresponding fine metal Safe_Supply quantity_grams if the company balance goes negative.
6. WHEN alloy is consumed during a casting step, THE Supply_Tracking_Service SHALL decrease the alloy Safe_Supply quantity_grams.
7. THE Safe_Supply quantity_grams SHALL be allowed to go negative to indicate a deficit.

### Requirement 3: Company Metal Balance Tracking

**User Story:** As a jewelry manufacturer, I want to track how much fine metal each company has deposited and how much has been consumed, so that I can maintain accurate per-company metal accounts.

#### Acceptance Criteria

1. THE Company_Metal_Balance model SHALL have the following fields: id (primary key), tenant_id (foreign key to tenants), company_id (foreign key to companies), metal_id (foreign key to metals), balance_grams (float, not null, default 0), created_at (datetime), and updated_at (datetime).
2. THE Company_Metal_Balance model SHALL enforce a unique constraint on the combination of tenant_id, company_id, and metal_id.
3. WHEN a company deposits fine metal, THE Supply_Tracking_Service SHALL increase the corresponding Company_Metal_Balance balance_grams.
4. WHEN a company deposits fine metal, THE Supply_Tracking_Service SHALL also increase the corresponding fine metal Safe_Supply quantity_grams.
5. WHEN fine metal is consumed during a casting step for a company's order, THE Supply_Tracking_Service SHALL decrease the corresponding Company_Metal_Balance balance_grams.
6. THE Company_Metal_Balance balance_grams SHALL be allowed to go negative to indicate the company has consumed more metal than deposited.
7. WHEN a Company_Metal_Balance goes negative, THE Supply_Tracking_Service SHALL decrease the corresponding fine metal Safe_Supply quantity_grams by the deficit amount.

### Requirement 4: Metal Transaction Ledger

**User Story:** As a jewelry manufacturer, I want a complete audit trail of all metal balance changes, so that I can trace every deposit, consumption, and purchase.

#### Acceptance Criteria

1. THE Metal_Transaction model SHALL have the following fields: id (primary key), tenant_id (foreign key to tenants), transaction_type (string: "COMPANY_DEPOSIT", "MANUFACTURING_CONSUMPTION", "SAFE_PURCHASE", "SAFE_ADJUSTMENT"), metal_id (foreign key to metals, nullable for alloy transactions), company_id (foreign key to companies, nullable), order_id (foreign key to orders, nullable), quantity_grams (float, not null), notes (text, nullable), created_at (datetime), and created_by (integer, foreign key to users).
2. WHEN a company deposits fine metal, THE Supply_Tracking_Service SHALL create a Metal_Transaction with transaction_type "COMPANY_DEPOSIT".
3. WHEN fine metal or alloy is consumed during casting, THE Supply_Tracking_Service SHALL create a Metal_Transaction with transaction_type "MANUFACTURING_CONSUMPTION".
4. WHEN the manufacturer purchases metal or alloy for the safe, THE Supply_Tracking_Service SHALL create a Metal_Transaction with transaction_type "SAFE_PURCHASE".
5. THE Metal_Transaction quantity_grams SHALL be positive for deposits and purchases, and negative for consumption.

### Requirement 5: Labor Cost on Orders

**User Story:** As a jewelry manufacturer, I want to record labor cost on each order, so that I can track the monetary charge for manufacturing work separately from metal costs.

#### Acceptance Criteria

1. WHEN an order is created, THE Order model SHALL accept an optional labor_cost field (float, nullable, default null).
2. WHEN an order is updated, THE Order model SHALL allow the labor_cost field to be modified.
3. THE Order API SHALL include labor_cost in order creation, update, and response schemas.

### Requirement 6: Casting Step Metal Calculation

**User Story:** As a jewelry manufacturer, I want the system to automatically calculate fine metal and alloy consumption when a casting step is processed, so that material usage is accurately tracked based on the target karat and item weight.

#### Acceptance Criteria

1. WHEN a casting step is completed for an order, THE Supply_Tracking_Service SHALL calculate the total fine metal required using the formula: fine_metal_grams = total_weight * target_metal_fine_percentage.
2. WHEN a casting step is completed for an order, THE Supply_Tracking_Service SHALL calculate the total alloy required using the formula: alloy_grams = total_weight - fine_metal_grams.
3. WHEN calculating metal consumption, THE Supply_Tracking_Service SHALL retrieve the target metal's fine_percentage from the Metal entity referenced by the order's metal_type.
4. WHEN calculating metal consumption, THE Supply_Tracking_Service SHALL use the order's total weight (quantity multiplied by target_weight_per_piece) as the total_weight input.
5. WHEN a casting step is completed, THE Supply_Tracking_Service SHALL subtract the calculated fine_metal_grams from the company's Company_Metal_Balance for the order's metal type.
6. WHEN a casting step is completed, THE Supply_Tracking_Service SHALL subtract the calculated alloy_grams from the alloy Safe_Supply.
7. WHEN a casting step is completed and the company's metal balance goes negative, THE Supply_Tracking_Service SHALL subtract the deficit from the corresponding fine metal Safe_Supply.
8. IF the order does not have a metal_type or target_weight_per_piece defined, THEN THE Supply_Tracking_Service SHALL skip metal consumption calculation and log a warning.
9. IF the metal_type on the order does not match any active Metal record for the tenant, THEN THE Supply_Tracking_Service SHALL raise a validation error.

### Requirement 7: Company Metal Deposit API

**User Story:** As a jewelry manufacturer, I want an API endpoint to record when a company deposits fine metal, so that I can update both the company's balance and the safe supply.

#### Acceptance Criteria

1. WHEN a POST request is made to the company metal deposit endpoint with a valid company_id, metal_id, and quantity_grams, THE Supply_Tracking_Service SHALL increase the Company_Metal_Balance and the Safe_Supply by the specified quantity.
2. WHEN a deposit is recorded, THE Supply_Tracking_Service SHALL create a Metal_Transaction record with transaction_type "COMPANY_DEPOSIT".
3. IF the quantity_grams in a deposit request is zero or negative, THEN THE API SHALL return a 422 Validation Error response.
4. IF the metal_id does not reference an active Metal record for the tenant, THEN THE API SHALL return a 404 Not Found response.
5. IF the company_id does not reference a valid company for the tenant, THEN THE API SHALL return a 404 Not Found response.

### Requirement 8: Safe Supply Purchase API

**User Story:** As a jewelry manufacturer, I want an API endpoint to record when I purchase metal or alloy for my safe, so that I can update my inventory.

#### Acceptance Criteria

1. WHEN a POST request is made to the safe purchase endpoint with a valid metal_id (or alloy indicator), quantity_grams, and cost_per_gram, THE Supply_Tracking_Service SHALL increase the corresponding Safe_Supply quantity_grams.
2. WHEN a fine metal purchase is recorded, THE Supply_Tracking_Service SHALL update the Metal record's average_cost_per_gram using a weighted average of the existing cost and the new purchase cost.
3. WHEN a purchase is recorded, THE Supply_Tracking_Service SHALL create a Metal_Transaction record with transaction_type "SAFE_PURCHASE".
4. IF the quantity_grams in a purchase request is zero or negative, THEN THE API SHALL return a 422 Validation Error response.

### Requirement 9: Metal CRUD API

**User Story:** As a tenant administrator, I want API endpoints to manage Metal records, so that I can add new metal types, update fine percentages, and deactivate metals no longer in use.

#### Acceptance Criteria

1. WHEN a GET request is made to the metals list endpoint, THE Metal API SHALL return all active Metal records for the authenticated tenant, ordered by name.
2. WHEN a POST request is made with valid Metal data, THE Metal API SHALL create a new Metal record for the authenticated tenant and return the created resource with a 201 status code.
3. WHEN a POST request is made with a duplicate code for the same tenant, THE Metal API SHALL return a 409 Conflict response.
4. WHEN a PUT request is made with valid update data, THE Metal API SHALL allow modification of name, fine_percentage, average_cost_per_gram, and is_active fields.
5. WHEN a PUT request is made, THE Metal API SHALL prevent modification of the code field.
6. WHEN a DELETE request is made for a Metal record, THE Metal API SHALL set is_active to false (soft delete) rather than removing the record.
7. IF a POST request is made with a fine_percentage outside the range 0 to 1, THEN THE Metal API SHALL return a 422 Validation Error response.
8. WHEN a GET request is made with an include_inactive query parameter set to true, THE Metal API SHALL return both active and inactive Metal records.

### Requirement 10: Role-Based Access for Metal Management

**User Story:** As a system administrator, I want only users with manager role or above to be able to create, update, or deactivate Metal records and lookup values, so that critical configuration data is protected.

#### Acceptance Criteria

1. WHEN a user with a role below manager attempts to create, update, or deactivate a Metal record, THE Metal API SHALL return a 403 Forbidden response.
2. WHEN a user with manager role or above attempts to create, update, or deactivate a Metal record, THE Metal API SHALL allow the operation.
3. THE Metal API SHALL allow all authenticated users to read (GET) Metal records regardless of role.

### Requirement 11: Frontend Metal Management Screen

**User Story:** As a tenant administrator, I want a dedicated Metal management page in the frontend, so that I can view, add, edit, and deactivate metal types with their fine percentages and costs.

#### Acceptance Criteria

1. WHEN a user with manager role or above navigates to the Metal management page, THE Frontend SHALL display a table of all active Metal records showing code, name, fine_percentage (as percentage), and average_cost_per_gram.
2. WHEN a manager clicks "Add Metal," THE Frontend SHALL display a form to enter code, name, fine_percentage, and average_cost_per_gram.
3. WHEN a manager edits a Metal record, THE Frontend SHALL allow modification of name, fine_percentage, and average_cost_per_gram but prevent modification of code.
4. WHEN a manager deactivates a Metal record, THE Frontend SHALL visually distinguish the deactivated metal from active metals.
5. WHEN a user with a role below manager navigates to the Metal management page, THE Frontend SHALL hide the add, edit, and deactivate controls.
6. WHEN the fine_percentage field is displayed, THE Frontend SHALL show it as a percentage (e.g., 0.585 displayed as "58.5%").

### Requirement 12: Frontend Company Metal Balance View

**User Story:** As a jewelry manufacturer, I want to see each company's metal balance on the company detail page, so that I can quickly check how much metal a company has deposited versus consumed.

#### Acceptance Criteria

1. WHEN a user views a company detail page, THE Frontend SHALL display a table of Company_Metal_Balance records showing metal name, balance_grams, and whether the balance is negative.
2. WHEN a balance is negative, THE Frontend SHALL visually highlight the negative balance (e.g., red text).
3. WHEN a manager views the company detail page, THE Frontend SHALL display a "Record Deposit" button to add a metal deposit for that company.

### Requirement 13: Alembic Migration for New Models

**User Story:** As a developer, I want Alembic migrations that create the new Metal, Safe_Supply, Company_Metal_Balance, and Metal_Transaction tables and add the labor_cost column to orders, so that the database schema supports metal supply tracking.

#### Acceptance Criteria

1. WHEN the migration runs, THE Migration SHALL create the metals table with all fields defined in Requirement 1.
2. WHEN the migration runs, THE Migration SHALL create the safe_supplies table with all fields defined in Requirement 2.
3. WHEN the migration runs, THE Migration SHALL create the company_metal_balances table with all fields defined in Requirement 3.
4. WHEN the migration runs, THE Migration SHALL create the metal_transactions table with all fields defined in Requirement 4.
5. WHEN the migration runs, THE Migration SHALL add a labor_cost column (float, nullable) to the orders table.
6. WHEN the migration is rolled back, THE Migration SHALL drop the new tables and remove the labor_cost column from orders.

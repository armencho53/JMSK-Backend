# Migration 003: Hierarchical Contact System

## Overview
This migration implements the hierarchical contact system by restructuring the customer-company relationship into a parent-child hierarchy where companies are the primary entity and contacts (formerly customers) are associated with companies.

## Changes Summary

### 1. New Tables Created

#### `addresses` Table
- Stores multiple addresses per company
- Fields: `id`, `tenant_id`, `company_id`, `street_address`, `city`, `state`, `zip_code`, `country`, `is_default`, `created_at`
- Foreign keys: `tenant_id` → `tenants.id`, `company_id` → `companies.id`
- Indexes: Standard indexes plus composite index on `(company_id, is_default)`

### 2. Table Modifications

#### `companies` Table - Added Columns
- `fax` (VARCHAR(50), nullable) - Fax number for company
- `default_address_id` (INTEGER, nullable) - Foreign key to `addresses.id`

#### `customers` → `contacts` Table - Renamed and Modified
- **Table renamed** from `customers` to `contacts`
- `company_id` changed from nullable to **NOT NULL** (required relationship)
- Unique constraint changed from `(tenant_id, email)` to `(tenant_id, company_id, email)`
  - This allows same email across different companies but not within same company
- All indexes renamed to reflect new table name

#### `orders` Table - Added Columns and Renamed
- `company_id` (INTEGER, NOT NULL) - Foreign key to `companies.id`
- `customer_id` renamed to `contact_id`
- Foreign key constraint renamed from `orders_customer_id_fkey` to `fk_orders_contact`
- New foreign key constraint `fk_orders_company` added

### 3. Performance Indexes Added

#### Composite Indexes for Common Query Patterns
- `ix_contacts_tenant_company` on `contacts(tenant_id, company_id)` - For fetching all contacts of a company
- `ix_orders_tenant_company` on `orders(tenant_id, company_id)` - For fetching all orders for a company
- `ix_orders_tenant_contact` on `orders(tenant_id, contact_id)` - For fetching all orders for a contact

### 4. Data Migration Logic

#### Handling Orphaned Contacts
The migration includes logic to handle contacts without a company_id:
1. Identifies tenants with contacts that have NULL `company_id`
2. Creates a "Default Company" for each affected tenant
3. Associates orphaned contacts with the default company
4. Only then makes `company_id` NOT NULL

#### Populating Orders.company_id
- Automatically populates `company_id` in orders table from the associated contact's company
- Uses SQL UPDATE with JOIN to efficiently populate all records

## Requirements Addressed

This migration addresses the following requirements from the hierarchical contact system spec:

- **Requirement 1.1**: Rename "Client" entities to "Contact" entities in database schema
- **Requirement 1.3**: Establish one-to-many relationship (Company → Contacts)
- **Requirement 1.4**: Require contact association with exactly one company
- **Requirement 1.6**: Maintain referential integrity between Companies, Contacts, and Orders
- **Requirement 8.1**: Restructure database to support contact-company hierarchy
- **Requirement 8.2**: Include tables for Companies, Contacts, Orders, and relationships
- **Requirement 8.4**: Ensure data integrity through constraints and indexes

## Database Constraints

### Foreign Key Constraints
- `addresses.tenant_id` → `tenants.id` (CASCADE DELETE)
- `addresses.company_id` → `companies.id` (CASCADE DELETE)
- `companies.default_address_id` → `addresses.id` (SET NULL on delete)
- `contacts.tenant_id` → `tenants.id` (existing)
- `contacts.company_id` → `companies.id` (existing, now NOT NULL)
- `orders.tenant_id` → `tenants.id` (existing)
- `orders.contact_id` → `contacts.id` (SET NULL on delete)
- `orders.company_id` → `companies.id` (CASCADE DELETE)

### Unique Constraints
- `contacts`: `(tenant_id, company_id, email)` - Prevents duplicate contacts within same company
- `companies`: `(tenant_id, name)` - Prevents duplicate company names per tenant (existing)

### NOT NULL Constraints
- `contacts.company_id` - Every contact must belong to a company
- `orders.company_id` - Every order must be associated with a company
- All address fields except `is_default` are required

## Migration Safety

### Upgrade Safety
- ✅ Handles orphaned contacts by creating default companies
- ✅ Automatically populates `orders.company_id` from contact relationships
- ✅ Uses transactions to ensure atomicity
- ✅ Creates indexes for query performance
- ✅ Maintains referential integrity throughout

### Downgrade Considerations
⚠️ **WARNING**: Downgrading this migration may result in data loss:
- Multiple contacts with same email across different companies will conflict
- Address data will be lost
- Company default address references will be lost

## Testing Recommendations

### Pre-Migration Validation
1. Backup database before running migration
2. Verify all customers have valid tenant_id
3. Check for customers with NULL company_id (will get default company)
4. Verify orders reference valid customers

### Post-Migration Validation
1. Verify all contacts have non-NULL company_id
2. Verify all orders have both contact_id and company_id
3. Check that orders.company_id matches contacts.company_id
4. Verify indexes were created successfully
5. Test query performance with new indexes

### SQL Validation Queries

```sql
-- Verify all contacts have company_id
SELECT COUNT(*) FROM contacts WHERE company_id IS NULL;
-- Expected: 0

-- Verify all orders have company_id
SELECT COUNT(*) FROM orders WHERE company_id IS NULL;
-- Expected: 0

-- Verify order-contact-company consistency
SELECT COUNT(*) 
FROM orders o
JOIN contacts c ON o.contact_id = c.id
WHERE o.company_id != c.company_id;
-- Expected: 0

-- Check indexes exist
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('contacts', 'orders', 'addresses')
ORDER BY tablename, indexname;
```

## Rollback Plan

If issues occur after migration:

1. **Immediate Rollback**: Run `alembic downgrade -1`
2. **Restore from Backup**: If data corruption occurs
3. **Fix and Retry**: Address specific issues and re-run migration

## Next Steps

After this migration is applied:

1. Update SQLAlchemy ORM models to reflect new schema
2. Update API endpoints to use "contact" terminology
3. Update frontend to use "Contact" instead of "Client"
4. Create/update repositories for contacts and addresses
5. Implement balance calculation logic for companies
6. Update tests to reflect new schema

## Migration File Location

`JMSK-Backend/alembic/versions/003_hierarchical_contact_system.py`

## Revision Chain

```
001_initial_complete_schema
  ↓
fa63140935ab (sync_manufacturing_steps_schema)
  ↓
002_remove_deprecated
  ↓
003_hierarchical_contact_system (this migration)
```

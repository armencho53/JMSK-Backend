# Address Model and Repository Implementation

## Overview

This document summarizes the implementation of the Address model and AddressRepository for the hierarchical contact system, completing task 2.3.

## Implementation Date

January 2025

## Requirements Addressed

- **Requirement 5.1**: Store default address for each company
- **Requirement 5.2**: Automatically populate company's default address during shipment creation
- **Requirement 5.3**: Allow modification of address for individual shipments without changing company default
- **Requirement 5.4**: Apply default address updates only to future shipments

## Files Created

### 1. Address Model
**File**: `JMSK-Backend/app/data/models/address.py`

**Description**: SQLAlchemy ORM model representing physical addresses associated with companies.

**Key Features**:
- Multi-tenant isolation via `tenant_id`
- Required association with a company via `company_id`
- Required fields: street_address, city, state, zip_code
- Optional country field (defaults to "USA")
- Boolean `is_default` flag for marking default addresses
- Relationships with Tenant and Company models

**Database Constraints**:
- Foreign key constraints for referential integrity
- Cascade delete when company or tenant is deleted
- Check constraint validates zip_code has minimum 5 characters
- Database triggers ensure only one default address per company

### 2. Address Repository
**File**: `JMSK-Backend/app/data/repositories/address_repository.py`

**Description**: Repository pattern implementation for address data access operations.

**Key Methods**:
- `get_by_company()`: Retrieve all addresses for a specific company
- `get_default_address()`: Get the default address for a company
- `set_default_address()`: Set an address as default (unsets others)
- `unset_default_addresses()`: Remove default status from all addresses
- `has_default_address()`: Check if company has a default address
- `count_by_company()`: Count addresses for a company
- `is_referenced_as_default()`: Check if address is referenced by company

**Features**:
- Multi-tenant isolation enforced on all queries
- Pagination support for large address lists
- Explicit default address management
- CRUD operations inherited from BaseRepository

### 3. Unit Tests
**Files**: 
- `JMSK-Backend/tests/unit/test_address_repository.py` (17 tests)
- `JMSK-Backend/tests/unit/test_address_default_logic.py` (6 tests)

**Test Coverage**:
- Address model creation and validation
- Company-address relationships
- Default address logic and business rules
- Multi-tenant isolation
- CRUD operations (create, read, update, delete)
- Pagination functionality
- Edge cases (missing required fields, no default address, etc.)

**Total Tests**: 23 address-specific tests, all passing

## Model Updates

### Updated Models

1. **Company Model** (`app/data/models/company.py`)
   - Added `addresses` relationship with cascade delete
   - Supports one-to-many relationship with Address model

2. **Tenant Model** (`app/data/models/tenant.py`)
   - Added `addresses` relationship
   - Maintains multi-tenant isolation

3. **Models __init__.py** (`app/data/models/__init__.py`)
   - Added Address model import and export

## Database Schema

The Address table structure (already defined in migration `003_hierarchical_contact_system.py`):

```sql
CREATE TABLE addresses (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    street_address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    zip_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) DEFAULT 'USA' NOT NULL,
    is_default BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);
```

**Indexes**:
- Primary key on `id`
- Index on `tenant_id` for multi-tenant queries
- Index on `company_id` for company-address lookups
- Composite index on `(company_id, is_default)` for default address queries

## Business Logic

### Default Address Handling

1. **Setting Default Address**:
   - When an address is set as default, all other addresses for that company are automatically unmarked
   - Only one address can be default per company
   - Different companies can each have their own default address

2. **Shipment Creation**:
   - System retrieves company's default address using `get_default_address()`
   - Address is populated in shipment form
   - User can modify address for individual shipment
   - Modification doesn't affect company's default address

3. **Updating Default Address**:
   - Changes to company's default address only affect future shipments
   - Existing shipments retain their original addresses
   - Implemented via `set_default_address()` method

### Multi-Tenant Isolation

All address operations enforce tenant isolation:
- Queries filter by `tenant_id`
- Prevents cross-tenant data access
- Maintains data security in multi-tenant SaaS architecture

## Testing Results

All unit tests pass successfully:

```
49 total unit tests passed
├── 6 address default logic tests
├── 17 address repository tests
├── 26 existing tests (company, contact)
└── 0 failures
```

## Integration Points

### Current Integration
- ✅ Address model integrated with Company model
- ✅ Address model integrated with Tenant model
- ✅ Repository pattern follows existing conventions
- ✅ Multi-tenant isolation implemented
- ✅ Database migration already exists

### Future Integration (Next Tasks)
- [ ] Create Address Pydantic schemas (Task 3.3)
- [ ] Create AddressService for business logic (Task 4.3)
- [ ] Implement address API endpoints (Task 7.1)
- [ ] Frontend address management components (Task 14)

## Usage Example

```python
from app.data.repositories.address_repository import AddressRepository
from app.data.models.address import Address

# Create repository
address_repo = AddressRepository(db_session)

# Create new address
address = Address(
    tenant_id=1,
    company_id=5,
    street_address="123 Main St",
    city="New York",
    state="NY",
    zip_code="10001",
    country="USA",
    is_default=True
)
created_address = address_repo.create(address)

# Get default address for shipment
default_address = address_repo.get_default_address(
    company_id=5,
    tenant_id=1
)

# Get all addresses for a company
addresses = address_repo.get_by_company(
    company_id=5,
    tenant_id=1,
    skip=0,
    limit=10
)

# Set different address as default
address_repo.set_default_address(
    address_id=10,
    company_id=5,
    tenant_id=1
)
```

## Notes

- The database migration (003_hierarchical_contact_system.py) already includes the addresses table creation and triggers
- Database triggers in PostgreSQL will enforce additional constraints:
  - Automatic setting of first address as default
  - Prevention of default address deletion if referenced by company
  - Enforcement of one default address per company
- SQLite (used in tests) doesn't support all triggers, so application logic handles these cases

## Next Steps

1. Create Address Pydantic schemas for API validation (Task 3.3)
2. Implement AddressService for business logic layer (Task 4.3)
3. Create API endpoints for address management (Task 7.1)
4. Implement frontend components for address management (Task 14)

## Conclusion

Task 2.3 is complete. The Address model and AddressRepository have been successfully implemented with:
- ✅ Full CRUD operations
- ✅ Default address handling logic
- ✅ Multi-tenant isolation
- ✅ Comprehensive unit tests (23 tests, all passing)
- ✅ Integration with existing Company and Tenant models
- ✅ Documentation and usage examples

The implementation follows the established patterns in the codebase and is ready for integration with the service and API layers.

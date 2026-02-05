# Deprecation Notice: Customer to Contact Migration

## Overview

As part of the hierarchical contact system implementation, the following components have been marked as deprecated and will be removed in a future version.

## Deprecated Backend Components

### Models
- **`app/data/models/customer.py`** - Customer model
  - **Replacement**: `app/data/models/contact.py` - Contact model
  - **Status**: Deprecated, kept for backward compatibility
  - **Migration**: See `alembic/versions/003_hierarchical_contact_system.py`

### Repositories
- **`app/data/repositories/customer_repository.py`** - CustomerRepository
  - **Replacement**: `app/data/repositories/contact_repository.py` - ContactRepository
  - **Status**: Deprecated, kept for backward compatibility

### Services
- **`app/domain/services/customer_service.py`** - CustomerService
  - **Replacement**: `app/domain/services/contact_service.py` - ContactService
  - **Status**: Deprecated, kept for backward compatibility

### Schemas
- **`app/schemas/customer.py`** - All customer schemas
  - **Replacement**: `app/schemas/contact.py` - Contact schemas
  - **Status**: Deprecated, kept for backward compatibility

### Controllers
- **`app/presentation/api/v1/controllers/customer_controller.py`** - CustomerController
  - **Replacement**: `app/presentation/api/v1/controllers/contact_controller.py` - ContactController
  - **Status**: Deprecated, all routes marked as deprecated in OpenAPI
  - **API Endpoints**: All `/api/v1/customers/*` endpoints

## Deprecated Frontend Components

### Types
- **`src/types/customer.ts`** - All customer-related types
  - **Replacement**: `src/types/contact.ts` - Contact types
  - **Status**: Deprecated with JSDoc annotations

## Migration Path

### For Backend Developers

1. **New Code**: Use Contact model, ContactRepository, ContactService, and ContactController
2. **Existing Code**: Can continue using Customer components during transition period
3. **API Clients**: Should migrate to `/api/v1/contacts/*` endpoints

### For Frontend Developers

1. **New Code**: Use Contact types from `src/types/contact.ts`
2. **Existing Code**: Can continue using Customer types during transition period
3. **API Calls**: Should migrate to contact-related API functions

### For API Consumers

1. **Deprecated Endpoints**: All `/api/v1/customers/*` endpoints are marked as deprecated
2. **New Endpoints**: Use `/api/v1/contacts/*` endpoints instead
3. **Backward Compatibility**: Deprecated endpoints will remain functional during transition period

## Database Migration

The database migration script `003_hierarchical_contact_system.py` handles:
- Creating new `contacts` table
- Creating new `addresses` table
- Updating `orders` table with `contact_id` and `company_id` columns
- Maintaining `customers` table for backward compatibility

To migrate existing customer data to contacts, use:
```bash
python scripts/migrate_customers_to_contacts.py
```

## Timeline

- **Current**: Deprecated components marked and documented
- **Transition Period**: Both old and new systems functional
- **Future**: Deprecated components will be removed (TBD)

## Support

For questions or issues during migration, please refer to:
- Design document: `.kiro/specs/hierarchical-contact-system/design.md`
- Requirements: `.kiro/specs/hierarchical-contact-system/requirements.md`
- Tasks: `.kiro/specs/hierarchical-contact-system/tasks.md`

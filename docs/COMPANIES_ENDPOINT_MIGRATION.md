# Companies Endpoint Migration

## Summary

The companies endpoint has been migrated from the legacy structure to clean architecture. The new endpoint is now available at `/api/v1/companies` and the old endpoint has been moved to `/api/v1/companies-legacy` with deprecation warnings.

## Changes Made

### 1. Backend Router Configuration (`app/presentation/api/v1/router.py`)

- **New companies endpoint**: `/api/v1/companies` now points to the clean architecture controller
  - Uses `company_controller` from `app.presentation.api.v1.controllers`
  - Tags: `["companies"]`
  
- **Legacy companies endpoint**: Moved to `/api/v1/companies-legacy`
  - Uses legacy `companies` module from `app.api.v1.endpoints`
  - Tags: `["companies-legacy"]`
  - Marked as `deprecated=True` in FastAPI
  - Will show deprecation warning in API documentation

### 2. Legacy Endpoint (`app/api/v1/endpoints/companies.py`)

- Added deprecation warning that displays when the module is imported
- Warning message: "The /companies-legacy endpoint is deprecated and will be removed in a future version. Please use /companies endpoint instead."

### 3. Frontend API Layer (`JMSK-Frontend/src/lib/api.ts`)

Updated all company API functions to use `/companies` instead of `/companies-v2`:

- `fetchCompanies()` - GET `/companies`
- `fetchCompanyById()` - GET `/companies/{id}`
- `createCompany()` - POST `/companies`
- `updateCompany()` - PUT `/companies/{id}`
- `deleteCompany()` - DELETE `/companies/{id}`
- `fetchCompanyContacts()` - GET `/companies/{id}/contacts`
- `fetchCompanyOrders()` - GET `/companies/{id}/orders`
- `fetchCompanyBalance()` - GET `/companies/{id}/balance`
- `fetchCompanyStatistics()` - GET `/companies/{id}/statistics`

## API Endpoints

### New Clean Architecture Endpoints (Active)

```
GET    /api/v1/companies                      - List companies with filters
POST   /api/v1/companies                      - Create company
GET    /api/v1/companies/{id}                 - Get company details
PUT    /api/v1/companies/{id}                 - Update company
DELETE /api/v1/companies/{id}                 - Delete company
GET    /api/v1/companies/{id}/contacts        - Get company contacts
GET    /api/v1/companies/{id}/orders          - Get company orders
GET    /api/v1/companies/{id}/balance         - Get company balance
GET    /api/v1/companies/{id}/statistics      - Get company statistics
```

### Legacy Endpoints (Deprecated)

```
GET    /api/v1/companies-legacy/              - List companies
POST   /api/v1/companies-legacy/              - Create company (old format)
GET    /api/v1/companies-legacy/{id}          - Get company
PUT    /api/v1/companies-legacy/{id}          - Update company
DELETE /api/v1/companies-legacy/{id}          - Delete company
```

## Migration Guide for Frontend/API Consumers

### Breaking Changes

1. **Endpoint URL**: Change from `/api/v1/companies-v2/` to `/api/v1/companies/`
2. **Request/Response Format**: The new endpoint uses enhanced schemas
   - Supports nested relationships (contacts, orders)
   - Includes balance and statistics endpoints
   - See API documentation at `/docs` for full schema details

### Migration Steps

1. Update all API calls from `/api/v1/companies-v2/` to `/api/v1/companies/`
2. Update request payloads to match new schemas (if needed)
3. Test thoroughly in development environment
4. The legacy endpoint at `/api/v1/companies-legacy/` will remain available temporarily for backward compatibility

### Timeline

- **Now**: Both endpoints are available
  - `/api/v1/companies/` - New clean architecture (recommended)
  - `/api/v1/companies-legacy/` - Legacy endpoint (deprecated)
  
- **Future**: Legacy endpoint will be removed in a future version
  - Exact timeline TBD
  - Deprecation warnings will be shown in API documentation

## Testing

All tests pass successfully:

```bash
pytest tests/unit/test_controller_routes.py -v
```

Results:
- ✅ test_order_controller_routes_registered
- ✅ test_metal_price_controller_routes_registered
- ✅ test_supply_tracking_metal_balances_endpoint
- ✅ test_openapi_schema_includes_new_routes

## Features of New Endpoint

The new clean architecture endpoint provides enhanced functionality:

1. **Nested Relationships**: Companies include nested contact data
2. **Balance Tracking**: Get aggregated balance per company
3. **Statistics**: Comprehensive company statistics endpoint
4. **Order History**: Fetch all orders for a company
5. **Contact Management**: Manage company contacts through nested routes
6. **Search & Filtering**: Enhanced search and filtering capabilities

## Documentation

- API documentation available at: `http://localhost:8000/docs`
- Legacy endpoints are marked as deprecated in Swagger UI
- New endpoints are tagged as "companies"
- Legacy endpoints are tagged as "companies-legacy"

## Related Migrations

- [Orders Endpoint Migration](./ORDERS_ENDPOINT_MIGRATION.md) - Similar migration for orders
- [Frontend API Verification](./FRONTEND_API_VERIFICATION.md) - Frontend API alignment

## Next Steps

1. ✅ Update frontend to use new `/api/v1/companies/` endpoint
2. Monitor usage of legacy endpoint
3. Plan removal of legacy endpoint after migration period
4. Update any external integrations or documentation

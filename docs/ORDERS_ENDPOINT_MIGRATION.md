# Orders Endpoint Migration

## Summary

The orders endpoint has been migrated from the legacy structure to clean architecture. The new endpoint is now available at `/api/v1/orders` and the old endpoint has been moved to `/api/v1/orders-legacy` with deprecation warnings.

## Changes Made

### 1. Router Configuration (`app/presentation/api/v1/router.py`)

- **New orders endpoint**: `/api/v1/orders` now points to the clean architecture controller
  - Uses `order_controller` from `app.presentation.api.v1.controllers`
  - Tags: `["orders"]`
  
- **Legacy orders endpoint**: Moved to `/api/v1/orders-legacy`
  - Uses legacy `orders` module from `app.api.v1.endpoints`
  - Tags: `["orders-legacy"]`
  - Marked as `deprecated=True` in FastAPI
  - Will show deprecation warning in API documentation

### 2. Legacy Endpoint (`app/api/v1/endpoints/orders.py`)

- Added deprecation warning that displays when the module is imported
- Warning message: "The /orders-legacy endpoint is deprecated and will be removed in a future version. Please use /orders endpoint instead."

### 3. Configuration (`app/infrastructure/config.py`)

- Updated Pydantic Settings to allow extra environment variables
- Added `extra = "allow"` to Config class
- This allows multiple database connection strings (DATABASE_URL_LOCAL, DATABASE_URL_DEV, etc.) without validation errors

### 4. Tests (`tests/unit/test_controller_routes.py`)

- Updated all test assertions to use `/api/v1/orders/` instead of `/api/v1/orders-v2/`
- Tests verify:
  - POST `/api/v1/orders/` - Order creation
  - GET `/api/v1/orders/{order_id}` - Order retrieval
  - PUT `/api/v1/orders/{order_id}` - Order update
  - OpenAPI schema includes new routes

## API Endpoints

### New Clean Architecture Endpoints (Active)

```
POST   /api/v1/orders/              - Create order with line items and optional deposit
GET    /api/v1/orders/{order_id}    - Get order with line items
PUT    /api/v1/orders/{order_id}    - Update order
```

### Legacy Endpoints (Deprecated)

```
GET    /api/v1/orders-legacy/                  - List orders
POST   /api/v1/orders-legacy/                  - Create order (old format)
GET    /api/v1/orders-legacy/{order_id}        - Get order
PUT    /api/v1/orders-legacy/{order_id}        - Update order
DELETE /api/v1/orders-legacy/{order_id}        - Delete order
GET    /api/v1/orders-legacy/{order_id}/timeline - Get order timeline
```

## Migration Guide for Frontend/API Consumers

### Breaking Changes

1. **Endpoint URL**: Change from `/api/v1/orders-v2/` to `/api/v1/orders/`
2. **Request/Response Format**: The new endpoint uses different schemas
   - New: `OrderCreateWithDeposit`, `OrderUpdate`, `OrderResponse`
   - Supports line items and metal deposits
   - See API documentation at `/docs` for full schema details

### Migration Steps

1. Update all API calls from `/api/v1/orders-v2/` to `/api/v1/orders/`
2. Update request payloads to match new schemas (if needed)
3. Test thoroughly in development environment
4. The legacy endpoint at `/api/v1/orders-legacy/` will remain available temporarily for backward compatibility

### Timeline

- **Now**: Both endpoints are available
  - `/api/v1/orders/` - New clean architecture (recommended)
  - `/api/v1/orders-legacy/` - Legacy endpoint (deprecated)
  
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

## Documentation

- API documentation available at: `http://localhost:8000/docs`
- Legacy endpoints are marked as deprecated in Swagger UI
- New endpoints are tagged as "orders"
- Legacy endpoints are tagged as "orders-legacy"

## Next Steps

1. Update frontend to use new `/api/v1/orders/` endpoint
2. Monitor usage of legacy endpoint
3. Plan removal of legacy endpoint after migration period
4. Update any external integrations or documentation

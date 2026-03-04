# Integration Tests

Integration tests run against actual database connections to verify the full stack works correctly with real PostgreSQL databases.

## Purpose

- Verify database migrations are applied correctly
- Test actual database operations and queries
- Validate multi-tenant isolation
- Ensure data integrity constraints
- Test full API endpoints with real database

## Running Integration Tests

### Locally

```bash
# Set DATABASE_URL to your test database
export DATABASE_URL="postgresql://user:password@localhost:5432/testdb"

# Run integration tests only
pytest tests/integration/ -v

# Run specific integration test
pytest tests/integration/test_database_connection.py -v
```

### In CI/CD

Integration tests automatically run in GitHub Actions after migrations:

1. **Migrations** are applied to the target database (dev/prod)
2. **Integration tests** run against the same database
3. **Deployment** proceeds if tests pass

The workflow uses GitHub secrets:
- `DATABASE_URL_DEV` - Development database connection string
- `DATABASE_URL_PROD` - Production database connection string

## Test Organization

```
tests/integration/
├── __init__.py                      # Package marker
├── conftest.py                      # Integration test fixtures
├── README.md                        # This file
├── test_database_connection.py      # Database connectivity tests
└── api/                            # API integration tests (future)
    ├── test_auth_integration.py
    ├── test_orders_integration.py
    └── ...
```

## Writing Integration Tests

Integration tests should:

1. **Use real database connections** via `integration_db_session` fixture
2. **Use transactions** that rollback after each test (no data pollution)
3. **Test actual database operations** not mocked behavior
4. **Verify data integrity** and constraints
5. **Test multi-tenant isolation** where applicable

### Example

```python
def test_order_creation_with_line_items(integration_db_session):
    """Test creating an order with line items in real database."""
    # Create test data
    order = Order(
        tenant_id=1,
        order_number="TEST-001",
        contact_id=1,
        company_id=1,
        status=OrderStatus.PENDING
    )
    integration_db_session.add(order)
    integration_db_session.flush()
    
    # Create line item
    line_item = OrderLineItem(
        tenant_id=1,
        order_id=order.id,
        product_description="Test Product",
        quantity=10
    )
    integration_db_session.add(line_item)
    integration_db_session.commit()
    
    # Verify
    assert order.id is not None
    assert line_item.id is not None
    assert line_item.order_id == order.id
```

## Differences from Unit Tests

| Aspect | Unit Tests | Integration Tests |
|--------|-----------|-------------------|
| Database | SQLite in-memory | Real PostgreSQL |
| Speed | Fast (milliseconds) | Slower (seconds) |
| Isolation | Complete | Transaction-based |
| Purpose | Test logic | Test integration |
| When to run | Every commit | Before deployment |

## Best Practices

1. **Keep tests independent** - Each test should work in isolation
2. **Use transactions** - Tests should not leave data behind
3. **Test edge cases** - Verify constraints, foreign keys, etc.
4. **Don't test business logic** - That's for unit tests
5. **Focus on integration** - Test how components work together

## Troubleshooting

### Tests are skipped

```
SKIPPED [1] tests/integration/conftest.py:23: DATABASE_URL not set
```

**Solution**: Set the `DATABASE_URL` environment variable

### Connection refused

```
Cannot connect to database: connection refused
```

**Solution**: Ensure PostgreSQL is running and accessible

### Permission denied

```
permission denied for table X
```

**Solution**: Ensure database user has appropriate permissions

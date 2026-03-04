# Backend Tests

## Quick Reference

### Run All Tests (Unit Only)

```bash
# Default: runs unit tests only, skips integration tests
pytest

# Or explicitly
pytest -m "not integration"
```

### Run Unit Tests Only

```bash
pytest tests/unit/ -v
```

### Run Integration Tests Only

```bash
# Requires PostgreSQL DATABASE_URL
export DATABASE_URL="postgresql://user:pass@host:5432/db"
pytest -m integration -v
```

### Run Specific Test File

```bash
pytest tests/unit/test_order_service.py -v
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Organization

```
tests/
├── unit/                          # Unit tests (SQLite, fast)
│   ├── test_order_service.py
│   ├── test_customer_repository.py
│   └── ...
├── integration/                   # Integration tests (PostgreSQL, slower)
│   ├── test_database_connection.py
│   └── ...
├── conftest.py                    # Unit test fixtures
└── test_api.py                    # Legacy API tests
```

## Test Types

### Unit Tests
- **Database**: SQLite in-memory
- **Speed**: Fast (< 100ms per test)
- **Purpose**: Test business logic in isolation
- **Run by default**: Yes
- **Coverage requirement**: 80%

### Integration Tests
- **Database**: Real PostgreSQL
- **Speed**: Slower (seconds per test)
- **Purpose**: Test full stack with real database
- **Run by default**: No (skipped unless DATABASE_URL is PostgreSQL)
- **Coverage requirement**: None (not counted)

## CI/CD Behavior

### Local Development
```bash
# Only unit tests run
pytest
```

### GitHub Actions
```bash
# Step 1: Unit tests (always)
pytest -m "not integration"

# Step 2: Integration tests (after migrations)
export DATABASE_URL=${{ secrets.DATABASE_URL_DEV }}
pytest -m integration
```

## Common Commands

```bash
# Run tests with verbose output
pytest -v

# Run tests and stop at first failure
pytest -x

# Run tests matching a pattern
pytest -k "order"

# Run tests with print statements visible
pytest -s

# Run specific test function
pytest tests/unit/test_order_service.py::test_create_order -v

# List all available tests
pytest --collect-only

# List all markers
pytest --markers
```

## Troubleshooting

### Integration tests running locally

**Problem**: Integration tests try to run but fail with SQLite errors

**Solution**: Integration tests are now automatically skipped unless DATABASE_URL points to PostgreSQL

### Tests are slow

**Problem**: Tests take a long time to run

**Solution**: Make sure you're only running unit tests locally:
```bash
pytest -m "not integration"
```

### Coverage too low

**Problem**: Coverage below 80%

**Solution**: Add unit tests for uncovered code:
```bash
# See what's not covered
pytest --cov=app --cov-report=term-missing

# Focus on specific module
pytest tests/unit/test_order_service.py --cov=app.domain.services.order_service
```

### Import errors

**Problem**: `ModuleNotFoundError` when running tests

**Solution**: Install test dependencies:
```bash
pip install -r requirements-test.txt
```

## Writing Tests

### Unit Test Template

```python
# tests/unit/test_my_service.py
import pytest
from app.domain.services.my_service import MyService

def test_my_function(db_session):
    """Test description."""
    service = MyService(db_session)
    
    result = service.do_something()
    
    assert result is not None
```

### Integration Test Template

```python
# tests/integration/test_my_integration.py
import pytest
from sqlalchemy import text

@pytest.mark.integration
def test_database_constraint(integration_db_session):
    """Test description."""
    result = integration_db_session.execute(text("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'my_table'
    """))
    
    constraints = [row.constraint_name for row in result.fetchall()]
    assert len(constraints) > 0
```

## More Information

- [Testing Strategy](../docs/TESTING_STRATEGY.md) - Complete testing documentation
- [Integration Tests](integration/README.md) - Integration test guide

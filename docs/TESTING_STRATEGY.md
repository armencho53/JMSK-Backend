# Testing Strategy

## Overview

The backend uses a two-tier testing strategy:

1. **Unit Tests** - Fast tests using SQLite in-memory database
2. **Integration Tests** - Real database tests using PostgreSQL

## Test Types

### Unit Tests (`tests/unit/`)

**Purpose**: Test business logic, services, and repositories in isolation

**Database**: SQLite in-memory (`:memory:`)

**When to run**: On every commit, before any deployment

**Characteristics**:
- Fast execution (milliseconds)
- Complete isolation
- No external dependencies
- Mock external services

**Example**:
```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=app --cov-report=term-missing
```

### Integration Tests (`tests/integration/`)

**Purpose**: Test full stack integration with real database

**Database**: Real PostgreSQL (dev/prod)

**When to run**: After migrations, before deployment

**Characteristics**:
- Slower execution (seconds)
- Transaction-based isolation
- Real database operations
- Verify migrations and constraints

**Example**:
```bash
# Set database URL
export DATABASE_URL="postgresql://user:pass@host:5432/db"

# Run integration tests
pytest tests/integration/ -v
```

## CI/CD Pipeline

### GitHub Actions Workflow

```mermaid
graph TD
    A[Push to main/develop] --> B[Run Unit Tests]
    B --> C[Build Lambda Package]
    C --> D[Determine Environment]
    D --> E[Run Migrations]
    E --> F[Run Integration Tests]
    F --> G[Deploy to Lambda]
    G --> H[Validate Deployment]
```

### Test Execution Flow

1. **Unit Tests** (always run)
   - Uses SQLite in-memory
   - Must pass before proceeding
   - Enforces 80% code coverage

2. **Build** (after unit tests pass)
   - Creates Lambda deployment package
   - Caches build artifacts

3. **Migrations** (environment-specific)
   - Uses `DATABASE_URL_DEV` or `DATABASE_URL_PROD`
   - Applies pending migrations
   - Stamps version if needed

4. **Integration Tests** (after migrations)
   - Uses same database as migrations
   - Verifies migrations applied correctly
   - Tests database operations
   - Non-blocking (warnings only)

5. **Deployment** (after all tests)
   - Deploys to AWS Lambda
   - Updates API Gateway
   - Tags repository

## GitHub Secrets Configuration

### Required Secrets

Add these secrets to your GitHub repository:

1. **DATABASE_URL_DEV**
   ```
   postgresql://user:password@dev-host:5432/jewelry_dev
   ```
   - Development database connection string
   - Used for develop branch deployments

2. **DATABASE_URL_PROD**
   ```
   postgresql://user:password@prod-host:5432/jewelry_prod
   ```
   - Production database connection string
   - Used for main branch deployments

### Setting Secrets

1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add `DATABASE_URL_DEV` with your development database URL
4. Add `DATABASE_URL_PROD` with your production database URL

**Security Note**: These secrets are masked in logs and never exposed in workflow output.

## Local Development

### Running Unit Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_order_service.py -v
```

### Running Integration Tests

```bash
# Set up local PostgreSQL database
createdb jewelry_test

# Set DATABASE_URL
export DATABASE_URL="postgresql://localhost:5432/jewelry_test"

# Run migrations
alembic upgrade head

# Run integration tests
pytest tests/integration/ -v

# Clean up
dropdb jewelry_test
```

## Test Organization

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures (unit tests)
├── test_api.py                    # Legacy API tests
├── test_main.py                   # Main app tests
├── unit/                          # Unit tests
│   ├── __init__.py
│   ├── test_order_service.py
│   ├── test_customer_repository.py
│   └── ...
└── integration/                   # Integration tests
    ├── __init__.py
    ├── conftest.py               # Integration fixtures
    ├── README.md
    ├── test_database_connection.py
    └── api/                      # API integration tests
        └── ...
```

## Writing Tests

### Unit Test Example

```python
# tests/unit/test_customer_service.py
import pytest
from unittest.mock import Mock
from app.domain.services.customer_service import CustomerService

def test_create_customer(db_session):
    """Test customer creation logic."""
    service = CustomerService(db_session)
    
    customer_data = {
        "name": "Test Customer",
        "email": "test@example.com"
    }
    
    customer = service.create_customer(customer_data, tenant_id=1)
    
    assert customer.id is not None
    assert customer.name == "Test Customer"
    assert customer.tenant_id == 1
```

### Integration Test Example

```python
# tests/integration/test_order_integration.py
import pytest
from sqlalchemy import text

def test_order_line_items_foreign_key(integration_db_session):
    """Test that order_line_items has proper foreign key to orders."""
    # This tests actual database constraints
    result = integration_db_session.execute(text("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'order_line_items' 
        AND constraint_type = 'FOREIGN KEY'
    """))
    
    constraints = [row.constraint_name for row in result.fetchall()]
    assert any('order_id' in c for c in constraints)
```

## Best Practices

### Unit Tests

1. ✅ Test business logic in isolation
2. ✅ Mock external dependencies
3. ✅ Use SQLite in-memory database
4. ✅ Keep tests fast (< 100ms each)
5. ✅ Aim for 80%+ code coverage

### Integration Tests

1. ✅ Test database operations
2. ✅ Verify migrations and constraints
3. ✅ Use real PostgreSQL database
4. ✅ Use transactions (rollback after test)
5. ✅ Test multi-tenant isolation

### What NOT to Test

1. ❌ Don't test framework code (FastAPI, SQLAlchemy)
2. ❌ Don't test external APIs (mock them)
3. ❌ Don't duplicate unit tests in integration tests
4. ❌ Don't leave test data in database

## Troubleshooting

### Unit Tests Failing

```bash
# Check syntax errors
python -m py_compile app/domain/services/order_service.py

# Run single test with verbose output
pytest tests/unit/test_order_service.py::test_create_order -vv

# Check coverage
pytest --cov=app --cov-report=term-missing
```

### Integration Tests Skipped

```
SKIPPED [1] DATABASE_URL not set
```

**Solution**: Set `DATABASE_URL` environment variable

### Migration Conflicts

```
ERROR: Can't locate revision identified by 'abc123'
```

**Solution**: The workflow automatically handles this by stamping to consolidated version

## Continuous Improvement

- Add more integration tests as features are added
- Maintain 80%+ code coverage for unit tests
- Review test failures in CI/CD pipeline
- Update this document as testing strategy evolves

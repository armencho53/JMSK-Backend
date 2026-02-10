# Project Structure

## Repository Organization

This is a multi-workspace repository with separate frontend and backend folders:

```
workspace/
├── JMSK-Frontend/    # React TypeScript frontend
└── JMSK-Backend/     # FastAPI Python backend
```

## Backend Structure (JMSK-Backend/)

```
JMSK-Backend/
├── app/
│   ├── presentation/           # Presentation Layer (HTTP)
│   │   └── api/
│   │       ├── dependencies.py # FastAPI dependencies (auth, DI)
│   │       └── v1/
│   │           ├── router.py   # Main API router
│   │           └── controllers/ # HTTP endpoint handlers
│   │               ├── customer_controller.py
│   │               └── ...
│   ├── domain/                 # Domain Layer (Business Logic)
│   │   ├── services/           # Business logic services
│   │   │   ├── customer_service.py
│   │   │   └── ...
│   │   └── exceptions.py       # Domain exceptions
│   ├── data/                   # Data Layer (Persistence)
│   │   ├── repositories/       # Repository pattern
│   │   │   ├── base.py        # Base CRUD repository
│   │   │   ├── customer_repository.py
│   │   │   └── ...
│   │   ├── models/            # SQLAlchemy ORM models
│   │   │   ├── customer.py
│   │   │   ├── order.py
│   │   │   ├── user.py
│   │   │   └── ...
│   │   └── database.py        # Database configuration
│   ├── infrastructure/         # Infrastructure Layer
│   │   ├── config.py          # Application settings
│   │   └── security.py        # JWT, password hashing
│   ├── schemas/               # Pydantic schemas (shared)
│   │   ├── customer.py
│   │   ├── auth.py
│   │   └── ...
│   ├── api/                   # LEGACY: Old endpoint structure
│   │   └── v1/endpoints/      # Being migrated to clean architecture
│   │       ├── auth.py
│   │       ├── orders.py
│   │       └── ...
│   └── main.py                # FastAPI application entry point
├── alembic/                   # Database migrations
│   ├── versions/              # Migration files
│   └── env.py                 # Alembic configuration
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests (planned)
│   │   ├── services/
│   │   └── repositories/
│   ├── integration/           # Integration tests (planned)
│   │   └── api/
│   ├── test_api.py           # Current API tests
│   └── conftest.py           # Pytest fixtures
├── aws-infrastructure/        # AWS SAM templates
│   └── github-oidc-setup.yaml
├── docs/                      # Documentation
│   └── deployment/
├── lambda_handler.py          # AWS Lambda entry point
├── requirements.txt           # Production dependencies
├── requirements-test.txt      # Test dependencies
├── alembic.ini               # Alembic configuration
├── pytest.ini                # Pytest configuration
└── ARCHITECTURE.md           # Architecture documentation
```

## Clean Architecture Layers

### 1. Presentation Layer (`presentation/`)
**Responsibility**: Handle HTTP requests and responses

- Controllers handle HTTP endpoints
- Call domain services
- Convert domain exceptions to HTTP responses
- Use Pydantic schemas for validation
- No business logic or direct database access

### 2. Domain Layer (`domain/`)
**Responsibility**: Implement business logic and rules

- Services orchestrate business operations
- Contain all business logic
- Call data repositories
- Raise domain exceptions
- No HTTP or database dependencies

### 3. Data Layer (`data/`)
**Responsibility**: Manage data persistence and retrieval

- Repositories encapsulate database queries
- SQLAlchemy ORM models
- Database session management
- No business logic
- Returns ORM models

### 4. Infrastructure Layer (`infrastructure/`)
**Responsibility**: Cross-cutting concerns and external integrations

- Application configuration
- JWT and password utilities
- Database connection management
- Reusable utilities

## Naming Conventions

### Python Files and Functions
- **snake_case** for all Python files, functions, and variables
- **PascalCase** for class names
- **UPPER_CASE** for constants

### Database Models
- Singular names (e.g., `Customer`, `Order`, not `Customers`, `Orders`)
- Table names automatically pluralized by SQLAlchemy

### API Endpoints
- RESTful conventions
- Plural resource names (e.g., `/customers`, `/orders`)
- Version prefix (e.g., `/api/v1/`)

### Schemas
- Suffix with purpose: `CustomerCreate`, `CustomerUpdate`, `CustomerResponse`
- Base schema without suffix for shared fields

## Design Patterns

### Repository Pattern
Encapsulates data access logic:
```python
class BaseRepository(Generic[ModelType]):
    def get_by_id(self, id: int, tenant_id: int) -> Optional[ModelType]
    def get_all(self, tenant_id: int) -> List[ModelType]
    def create(self, obj: ModelType) -> ModelType
    def update(self, obj: ModelType) -> ModelType
    def delete(self, obj: ModelType) -> None
```

### Service Pattern
Encapsulates business logic:
```python
class CustomerService:
    def __init__(self, db: Session):
        self.repository = CustomerRepository(db)
    
    def create_customer(self, data, tenant_id) -> CustomerResponse
    def update_customer(self, id, data, tenant_id) -> CustomerResponse
```

### Dependency Injection
FastAPI's dependency system:
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    # Validate token and return user
```

## Multi-Tenant Architecture

Every layer enforces tenant isolation:

1. **Presentation**: Extracts `tenant_id` from authenticated user (JWT token)
2. **Domain**: Passes `tenant_id` to repositories
3. **Data**: Filters all queries by `tenant_id`

```python
# Presentation
current_user.tenant_id  # From JWT token

# Domain
service.get_customers(tenant_id=current_user.tenant_id)

# Data
repository.get_all(tenant_id=tenant_id)
```

## Migration Status

### ✅ Completed
- Layered directory structure
- Base repository pattern
- Domain exceptions
- Customer module (full clean architecture)
- Import consolidation
- Codebase cleanup

### 🔄 In Progress
- Legacy endpoints in `app/api/v1/endpoints/` (functional but need refactoring)

### 📋 Next Steps
1. Refactor Auth module to clean architecture
2. Refactor remaining CRUD modules (orders, supplies, companies, etc.)
3. Organize tests by layer
4. Remove deprecated `app/api/` directory

## Key Files

### Application Entry Points
- `app/main.py` - FastAPI app initialization, CORS, middleware
- `lambda_handler.py` - AWS Lambda adapter using Mangum

### Database
- `app/data/database.py` - Database session management and engine configuration
- `alembic/env.py` - Migration configuration
- `alembic/versions/` - Migration files

### Authentication & Security
- `app/infrastructure/security.py` - JWT creation/validation, password hashing
- `app/presentation/api/dependencies.py` - FastAPI auth dependencies

### Configuration
- `app/infrastructure/config.py` - Application settings using Pydantic
- `.env` - Environment variables (not in git)
- `.env.example` - Environment variable template

## Testing Organization

### Test Structure
```
tests/
├── unit/              # Unit tests (planned)
│   ├── services/      # Service layer tests
│   └── repositories/  # Repository layer tests
├── integration/       # Integration tests (planned)
│   └── api/          # Full API tests
├── test_api.py       # Current API tests
└── conftest.py       # Pytest fixtures and configuration
```

### Testing Strategy
- **Unit Tests**: Mock repositories, test business logic in isolation
- **Repository Tests**: Use in-memory SQLite, test queries
- **Integration Tests**: Test full stack with test database
- **API Tests**: End-to-end API testing

### Test Configuration
- `pytest.ini` - Pytest settings
- `conftest.py` - Shared fixtures (database, test client)
- Tests automatically use SQLite in-memory database
- No PostgreSQL required for testing

## API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Deployment Structure

### AWS Lambda
- `lambda_handler.py` - Entry point using Mangum adapter
- `template.yaml` - AWS SAM template
- `samconfig.toml` - SAM deployment configuration

### GitHub Actions
- `.github/workflows/` - CI/CD pipelines
- Environment-specific deployments
- Automated testing and deployment

# Backend Architecture - Layered Design

## Overview

The backend follows a clean, layered architecture with strict separation of concerns. Each layer has specific responsibilities and dependencies flow in one direction.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│  (Controllers, Routes, HTTP Request/Response Handling)       │
│                                                               │
│  • FastAPI routers and controllers                           │
│  • Request validation (Pydantic schemas)                     │
│  • Response formatting                                       │
│  • Exception to HTTP error mapping                           │
└────────────────────┬────────────────────────────────────────┘
                     │ depends on
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      Domain Layer                            │
│         (Business Logic, Services, Domain Rules)             │
│                                                               │
│  • Business logic services                                   │
│  • Domain exceptions                                         │
│  • Business rule validation                                  │
│  • Multi-tenant isolation logic                              │
└────────────────────┬────────────────────────────────────────┘
                     │ depends on
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                       Data Layer                             │
│      (Repositories, ORM Models, Database Access)             │
│                                                               │
│  • Repository pattern (CRUD operations)                      │
│  • SQLAlchemy ORM models                                     │
│  • Database queries                                          │
│  • Data persistence                                          │
└────────────────────┬────────────────────────────────────────┘
                     │ uses
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                        │
│    (Configuration, Security, External Integrations)          │
│                                                               │
│  • Application configuration                                 │
│  • JWT authentication & password hashing                     │
│  • Database connection management                            │
│  • External API clients (future)                             │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
backend/app/
│
├── presentation/              # Presentation Layer
│   └── api/
│       ├── dependencies.py    # FastAPI dependencies (auth, DI)
│       └── v1/
│           ├── router.py      # Main API router
│           └── controllers/   # HTTP endpoint handlers
│               ├── customer_controller.py
│               ├── auth_controller.py (TODO)
│               └── ...
│
├── domain/                    # Domain Layer
│   ├── services/              # Business logic services
│   │   ├── customer_service.py
│   │   ├── auth_service.py (TODO)
│   │   └── ...
│   └── exceptions.py          # Domain-specific exceptions
│
├── data/                      # Data Layer
│   ├── repositories/          # Data access patterns
│   │   ├── base.py           # Base repository with common CRUD
│   │   ├── customer_repository.py
│   │   └── ...
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── customer.py
│   │   ├── order.py
│   │   ├── user.py
│   │   └── ...
│   └── database.py           # Database configuration & session
│
├── infrastructure/            # Infrastructure Layer
│   ├── config.py             # Application settings
│   └── security.py           # JWT, password hashing
│
├── schemas/                   # Pydantic schemas (shared)
│   ├── customer.py
│   ├── auth.py
│   └── ...
│
└── main.py                    # FastAPI application entry point
```

## Layer Details

### 1. Presentation Layer (`presentation/`)

**Responsibility**: Handle HTTP requests and responses

**Components**:
- **Controllers**: Handle HTTP endpoints, call services
- **Dependencies**: FastAPI dependency injection (auth, DB session)
- **Routers**: Group related endpoints

**Rules**:
- ✅ Can call Domain services
- ✅ Can use Pydantic schemas for validation
- ✅ Can convert domain exceptions to HTTP responses
- ❌ No business logic
- ❌ No direct database access
- ❌ No direct model manipulation

**Example**:
```python
@router.get("/", response_model=List[CustomerResponse])
def list_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        service = CustomerService(db)
        return service.get_all_customers(current_user.tenant_id)
    except DomainException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
```

### 2. Domain Layer (`domain/`)

**Responsibility**: Implement business logic and rules

**Components**:
- **Services**: Orchestrate business operations
- **Exceptions**: Domain-specific errors

**Rules**:
- ✅ Can call Data repositories
- ✅ Can raise domain exceptions
- ✅ Contains all business logic
- ❌ No HTTP/FastAPI dependencies
- ❌ No direct database queries
- ❌ No ORM model creation (use repositories)

**Example**:
```python
class CustomerService:
    def __init__(self, db: Session):
        self.repository = CustomerRepository(db)
    
    def create_customer(self, data: CustomerCreate, tenant_id: int):
        # Business rule: Check for duplicate email
        if self.repository.get_by_email(data.email, tenant_id):
            raise DuplicateResourceError("Customer", "email", data.email)
        
        customer = Customer(**data.dict(), tenant_id=tenant_id)
        return self.repository.create(customer)
```

### 3. Data Layer (`data/`)

**Responsibility**: Manage data persistence and retrieval

**Components**:
- **Repositories**: Encapsulate database queries
- **Models**: SQLAlchemy ORM models
- **Database**: Connection and session management

**Rules**:
- ✅ Can query database
- ✅ Can create/update/delete models
- ✅ Returns ORM models
- ❌ No business logic
- ❌ No HTTP dependencies
- ❌ No validation (use schemas in presentation)

**Example**:
```python
class CustomerRepository(BaseRepository[Customer]):
    def get_by_email(self, email: str, tenant_id: int) -> Optional[Customer]:
        return self.db.query(Customer).filter(
            Customer.email == email,
            Customer.tenant_id == tenant_id
        ).first()
    
    def search(self, tenant_id: int, term: str) -> List[Customer]:
        return self.db.query(Customer).filter(
            Customer.tenant_id == tenant_id,
            or_(
                Customer.name.ilike(f"%{term}%"),
                Customer.email.ilike(f"%{term}%")
            )
        ).all()
```

### 4. Infrastructure Layer (`infrastructure/`)

**Responsibility**: Provide cross-cutting concerns and external integrations

**Components**:
- **Config**: Application settings
- **Security**: JWT, password hashing
- **Database**: Connection management

**Rules**:
- ✅ Reusable utilities
- ✅ No business logic
- ✅ Can be used by any layer
- ❌ No layer-specific logic

**Example**:
```python
# config.py
class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

# security.py
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY)
```

## Design Patterns

### Repository Pattern
Encapsulates data access logic, provides clean interface for domain layer.

```python
class BaseRepository(Generic[ModelType]):
    def get_by_id(self, id: int, tenant_id: int) -> Optional[ModelType]
    def get_all(self, tenant_id: int) -> List[ModelType]
    def create(self, obj: ModelType) -> ModelType
    def update(self, obj: ModelType) -> ModelType
    def delete(self, obj: ModelType) -> None
```

### Service Pattern
Encapsulates business logic, orchestrates repositories and domain rules.

```python
class CustomerService:
    def __init__(self, db: Session):
        self.repository = CustomerRepository(db)
    
    def create_customer(self, data, tenant_id) -> CustomerResponse
    def update_customer(self, id, data, tenant_id) -> CustomerResponse
    def delete_customer(self, id, tenant_id) -> None
```

### Dependency Injection
FastAPI's dependency system provides clean DI for database sessions and auth.

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

1. **Presentation**: Extracts `tenant_id` from authenticated user
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

## Testing Strategy

### Unit Tests
- **Services**: Mock repositories, test business logic in isolation
- **Repositories**: Use in-memory SQLite, test queries
- **Controllers**: Mock services, test HTTP handling

### Integration Tests
- Test full stack with test database
- Verify layer interactions
- End-to-end API tests

### Test Structure
```
tests/
├── unit/
│   ├── services/
│   ├── repositories/
│   └── controllers/
├── integration/
│   └── api/
└── conftest.py
```

## Migration Status

### ✅ Completed
- Layered directory structure
- Base repository pattern
- Domain exceptions
- Customer module (full clean architecture stack)
- Import consolidation (removed app/core, app/models duplicates)
- Codebase cleanup (removed duplicates and unused code)

### 🔄 In Progress
- Legacy endpoints in `app/api/v1/endpoints/` (auth, orders, supplies, etc.)
- These are functional but need refactoring to clean architecture

### 📋 Next Steps
1. Refactor Auth module to clean architecture
2. Refactor remaining CRUD modules (orders, supplies, companies, etc.)
3. Organize tests by layer (unit/services, unit/repositories, integration/api)
4. Remove deprecated `app/api/` directory once all endpoints migrated

## Benefits

1. **Maintainability**: Changes isolated to specific layers
2. **Testability**: Business logic testable without HTTP/DB
3. **Scalability**: Easy to add features following patterns
4. **Clarity**: Clear responsibilities and dependencies
5. **Reusability**: Services and repositories reusable
6. **Type Safety**: Strong typing between layers

## References

- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [Service Layer Pattern](https://martinfowler.com/eaaCatalog/serviceLayer.html)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/bigger-applications/)

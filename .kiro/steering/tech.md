# Technology Stack

## Backend

**Framework**: FastAPI (Python 3.11+)
**Database**: PostgreSQL (production), SQLite (testing)
**ORM**: SQLAlchemy 2.0
**Authentication**: JWT with python-jose
**Password Hashing**: Passlib with bcrypt
**Migrations**: Alembic
**Deployment**: AWS Lambda with Mangum adapter
**Testing**: Pytest with coverage reporting

### Architecture Pattern
Clean Architecture with layered design:
- **Presentation Layer**: FastAPI controllers and routes
- **Domain Layer**: Business logic services
- **Data Layer**: Repositories and ORM models
- **Infrastructure Layer**: Config, security, database

### Key Libraries
- `fastapi` - Modern async web framework
- `sqlalchemy` - ORM and database toolkit
- `psycopg2-binary` - PostgreSQL adapter
- `pydantic` - Data validation
- `python-jose` - JWT implementation
- `passlib` - Password hashing
- `mangum` - AWS Lambda ASGI adapter
- `alembic` - Database migrations

## Common Commands

### Development
```bash
# Virtual Environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Dependencies
pip install -r requirements.txt       # Production dependencies
pip install -r requirements-test.txt  # Test dependencies

# Start Development Server
uvicorn app.main:app --reload --port 8000

# API Documentation
# Available at http://localhost:8000/docs (Swagger UI)
# Available at http://localhost:8000/redoc (ReDoc)
```

### Database Management
```bash
# Run Migrations
alembic upgrade head

# Create New Migration
alembic revision --autogenerate -m "description"

# Rollback Migration
alembic downgrade -1

# View Migration History
alembic history

# Seed Database (if script exists)
python scripts/seed_database.py
```

### Testing
```bash
# Run All Tests
pytest

# Run with Coverage
pytest --cov=app --cov-report=term-missing

# Run Specific Test File
pytest tests/test_api.py

# Run with Verbose Output
pytest -v

# Run Specific Test
pytest tests/test_api.py::test_function_name

# Generate HTML Coverage Report
pytest --cov=app --cov-report=html
# View at htmlcov/index.html
```

### Code Quality
```bash
# Format Code
black app/ tests/

# Sort Imports
isort app/ tests/

# Type Checking
mypy app/

# Linting
flake8 app/ tests/
```

## Deployment

### GitHub Actions (Recommended)
- Automatic deployment on push to main/develop/staging branches
- Manual deployment via workflow dispatch
- Environment-specific configurations
- OIDC authentication with AWS
- Automated testing in CI/CD pipeline

### Manual Deployment (Legacy)
```bash
# Deploy to AWS Lambda
./deploy.sh

# Run migrations on deployed database
alembic upgrade head
```

## Environment Variables

**Required**:
- `DATABASE_URL` - PostgreSQL connection string (e.g., `postgresql://user:pass@host:5432/dbname`)
- `SECRET_KEY` - JWT secret key (generate with `openssl rand -hex 32`)

**Optional**:
- `ALGORITHM` - JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration (default: 30)

**Testing**:
- Tests automatically use SQLite in-memory database
- No PostgreSQL required for running tests

## Database Configuration

### Connection Pooling
- **Lambda (Production)**: NullPool for serverless connection management
- **Local Development**: Connection pooling (pool_size=5, max_overflow=10)
- **Testing**: StaticPool with SQLite in-memory database

### Multi-Tenant Isolation
All database queries automatically filtered by `tenant_id` from JWT token.

## Development Notes

- Backend runs on port 8000 by default
- CORS configured for localhost:5173, 5174, 3000
- API documentation auto-generated at `/docs` and `/redoc`
- Tests use in-memory SQLite for fast execution
- Minimum 80% code coverage enforced
- All endpoints require JWT authentication except `/auth/login` and `/auth/register`

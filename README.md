# Jewelry Manufacturing System - Backend

FastAPI backend for the Jewelry Manufacturing Tracking System.

## Prerequisites

- Python 3.11+
- PostgreSQL database
- AWS CLI configured (for AWS deployment)
- AWS SAM CLI (for AWS deployment)

## Local Development

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database URL and secret key
```

4. Run migrations:
```bash
alembic upgrade head
```

5. Seed initial data:
```bash
python seed_roles.py
python seed_data.py
```

6. Start development server:
```bash
uvicorn app.main:app --reload --port 8000
```

API will be available at http://localhost:8000
API docs at http://localhost:8000/docs

**CORS Configuration**: The backend automatically allows requests from:
- `http://localhost:5173` (default Vite dev server)
- `http://localhost:5174` (alternative Vite dev server port)
- `http://localhost:3000` (alternative dev server port)
- All origins when deployed to AWS Lambda

## Testing

The backend includes comprehensive test coverage with automatic SQLite configuration:

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v
```

**Test Database Configuration:**
- Tests automatically use in-memory SQLite for fast execution
- No PostgreSQL required for running tests
- Database schema created/destroyed for each test
- StaticPool ensures thread-safe in-memory database access

**Test Coverage Requirements:**
- Minimum 80% code coverage enforced
- Coverage reports generated in `htmlcov/` directory
- XML coverage report for CI/CD integration

## AWS Lambda Deployment

### Recommended: GitHub Actions (Automated)

The preferred deployment method is GitHub Actions workflows:

**Automatic Deployment:**
- Push to `main` branch → Deploys to production
- Create pull request → Runs tests only

**Manual Deployment:**
```bash
# Deploy to specific environment
gh workflow run deploy-backend.yml -f environment=prod
gh workflow run deploy-backend.yml -f environment=staging
gh workflow run deploy-backend.yml -f environment=dev
```

**Setup Requirements:**
- AWS OIDC identity provider configured
- GitHub repository secrets configured
- See [docs/deployment/deployment-guide.md](../docs/deployment/deployment-guide.md) for complete setup

### Legacy: Manual Deployment (Deprecated)

⚠️ **Deprecated**: Manual deployment script is maintained for backup only.

1. Ensure AWS credentials are configured:
```bash
aws configure
```

2. Deploy (with deprecation warnings):
```bash
./deploy.sh
```

3. Run migrations on deployed database:
```bash
# Connect to your RDS/Supabase database and run:
alembic upgrade head
```

**Migration Guide**: See [MIGRATION-GUIDE.md](../MIGRATION-GUIDE.md) for migrating to GitHub Actions.

## Environment Variables

- `DATABASE_URL`: Database connection string
  - **Production/Development**: PostgreSQL connection string (e.g., `postgresql://user:pass@host:5432/dbname`)
  - **Testing**: SQLite in-memory database (e.g., `sqlite:///:memory:`) - automatically configured in tests
- `SECRET_KEY`: JWT secret key (generate with `openssl rand -hex 32`)
- `ALGORITHM`: JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration (default: 30)

**Database Configuration:**
- **Lambda (Production)**: Uses NullPool for serverless connection management
- **Local Development**: Uses connection pooling (pool_size=5, max_overflow=10)
- **Testing**: Uses StaticPool with SQLite in-memory database for fast, isolated tests

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/refresh` - Refresh access token

### Customers (Clean Architecture ✨)
- `GET /api/v1/customers` - List customers (with search)
- `POST /api/v1/customers` - Create customer
- `GET /api/v1/customers/{id}` - Get customer details
- `PUT /api/v1/customers/{id}` - Update customer
- `DELETE /api/v1/customers/{id}` - Delete customer
- `GET /api/v1/customers/{id}/balance` - Get balance breakdown
- `GET /api/v1/customers/{id}/orders` - Get customer orders
- `GET /api/v1/customers/{id}/shipments` - Get customer shipments

### Other Resources
- Orders, Supplies, Companies, Manufacturing, Shipments, Departments, Roles, Tenants
- See `/docs` for complete API documentation

## Architecture

The backend is transitioning to a **Clean Architecture** pattern with clear separation of concerns:

- **Presentation Layer** (`app/presentation/`): HTTP controllers and request handling
- **Domain Layer** (`app/domain/`): Business logic and use cases
- **Data Layer** (`app/data/`): Database access and repositories

**Current Status**: Hybrid architecture with customer endpoints refactored to clean architecture pattern.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed architecture documentation.

## Project Structure

```
backend/
├── app/
│   ├── presentation/      # NEW: Presentation layer (controllers)
│   │   └── api/v1/controllers/
│   ├── domain/           # NEW: Domain layer (services, business logic)
│   │   ├── services/
│   │   └── exceptions.py
│   ├── data/             # NEW: Data layer (repositories, models)
│   │   ├── repositories/
│   │   ├── models/
│   │   └── database.py
│   ├── api/              # LEGACY: Old endpoint structure
│   │   └── v1/endpoints/
│   ├── core/             # Core functionality (auth, config)
│   └── schemas/          # Pydantic schemas (shared)
├── alembic/              # Database migrations
├── lambda_handler.py     # AWS Lambda entry point
├── requirements.txt      # Python dependencies
└── deploy.sh             # Deployment script
```

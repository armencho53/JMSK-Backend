# Database Migration Scripts

## Quick Start

### Method 1: Using the Migration Script (Recommended)

```bash
# Run migrations against local database
./scripts/migrate.sh local upgrade head

# Run migrations against development
./scripts/migrate.sh dev upgrade head

# Run migrations against staging
./scripts/migrate.sh staging upgrade head

# Run migrations against production (with confirmation prompt)
./scripts/migrate.sh prod upgrade head

# Create a new migration
./scripts/migrate.sh local revision --autogenerate -m "add new column"

# Rollback one migration
./scripts/migrate.sh dev downgrade -1

# View migration history
./scripts/migrate.sh local history
```

### Method 2: Using Environment Variables

```bash
# Set the environment variable directly
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
alembic upgrade head

# Or use inline
DATABASE_URL="postgresql://user:pass@host:5432/dbname" alembic upgrade head
```

### Method 3: Edit .env File

1. Open `.env` file
2. Change the `DATABASE_URL` line to point to your desired environment:
   ```bash
   DATABASE_URL=${DATABASE_URL_PROD}  # Switch to production
   ```
3. Run alembic normally:
   ```bash
   alembic upgrade head
   ```

## Environment Configuration

All database URLs are stored in `.env`:

```bash
DATABASE_URL_LOCAL=postgresql+psycopg://jewelry_user:jewelry_pass@localhost:5432/jewelry_db
DATABASE_URL_DEV=postgresql://user:pass@dev-host:5432/jewelry_dev
DATABASE_URL_STAGING=postgresql://user:pass@staging-host:5432/jewelry_staging
DATABASE_URL_PROD=postgresql://user:pass@production-host:5432/jewelry_production

# Active database (used by default)
DATABASE_URL=${DATABASE_URL_LOCAL}
```

## Common Alembic Commands

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade abc123

# Downgrade one revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade abc123

# Create new migration (auto-detect changes)
alembic revision --autogenerate -m "description"

# Create empty migration
alembic revision -m "description"

# View current revision
alembic current

# View migration history
alembic history

# View SQL without executing
alembic upgrade head --sql
```

## Safety Features

- Production migrations require explicit confirmation
- Database credentials are masked in output
- Script validates environment exists before running
- Uses `set -e` to exit on any error

## CI/CD Integration

For GitHub Actions or other CI/CD:

```yaml
- name: Run migrations
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL_PROD }}
  run: alembic upgrade head
```

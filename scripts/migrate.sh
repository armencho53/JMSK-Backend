#!/bin/bash
set -e

echo "🔄 Running database migrations..."

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL environment variable is not set"
    echo ""
    echo "Usage:"
    echo "  export DATABASE_URL='postgresql://user:pass@host:port/db'"
    echo "  ./migrate.sh"
    echo ""
    echo "Or:"
    echo "  DATABASE_URL='postgresql://user:pass@host:port/db' ./migrate.sh"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
fi

# Check if alembic is available
if ! command -v alembic &> /dev/null; then
    echo "❌ ERROR: alembic not found"
    echo ""
    echo "Please install dependencies first:"
    echo "  pip3 install -r requirements.txt"
    echo ""
    echo "Or activate your virtual environment:"
    echo "  source venv/bin/activate"
    exit 1
fi

# Show current migration status
echo "📊 Current migration status:"
alembic current || echo "No migrations applied yet"

# Run migrations
echo "⬆️  Upgrading to latest schema..."
alembic upgrade head

# Show final status
echo "✅ Migrations completed successfully!"
echo "📊 Current version:"
alembic current

echo ""
echo "🎉 Database is now up to date!"

#!/bin/bash
set -e

echo "🔄 Waiting for database to be ready..."
until pg_isready -h db -U jewelry_user; do
  echo "⏳ Database is unavailable - sleeping"
  sleep 2
done

echo "✅ Database is ready!"

echo "🔄 Running database migrations..."
# Check if tenants table exists to determine if this is a fresh database
if ! PGPASSWORD=jewelry_pass psql -h db -U jewelry_user -d jewelry_db -c "SELECT 1 FROM tenants LIMIT 1;" > /dev/null 2>&1; then
  echo "📊 Fresh database detected, running initial migration..."
  alembic upgrade head
else
  echo "📊 Existing database detected, marking as current version..."
  # Mark the database as being at the current migration version without running migrations
  alembic stamp head
fi

echo "🌱 Seeding database (if needed)..."
python seed_database.py

echo "🚀 Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

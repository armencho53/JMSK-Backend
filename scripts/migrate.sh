#!/bin/bash

# Migration helper script for different environments
# Usage: ./scripts/migrate.sh [environment] [command]
# Example: ./scripts/migrate.sh prod upgrade head
# Example: ./scripts/migrate.sh staging revision --autogenerate -m "add column"

set -e

ENVIRONMENT=${1:-local}
COMMAND=${2:-upgrade}
ARGS="${@:3}"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔧 Running Alembic against ${ENVIRONMENT} environment${NC}"

case $ENVIRONMENT in
  local)
    export DATABASE_URL=$(grep "^DATABASE_URL_LOCAL=" .env | cut -d '=' -f2-)
    ;;
  dev|development)
    export DATABASE_URL=$(grep "^DATABASE_URL_DEV=" .env | cut -d '=' -f2-)
    ;;
  staging)
    export DATABASE_URL=$(grep "^DATABASE_URL_STAGING=" .env | cut -d '=' -f2-)
    ;;
  prod|production)
    export DATABASE_URL=$(grep "^DATABASE_URL_PROD=" .env | cut -d '=' -f2-)
    echo -e "${RED}⚠️  WARNING: Running against PRODUCTION database!${NC}"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
      echo "Aborted."
      exit 1
    fi
    ;;
  *)
    echo -e "${RED}❌ Unknown environment: $ENVIRONMENT${NC}"
    echo "Valid options: local, dev, staging, prod"
    exit 1
    ;;
esac

if [ -z "$DATABASE_URL" ]; then
  echo -e "${RED}❌ DATABASE_URL not found for environment: $ENVIRONMENT${NC}"
  echo "Make sure DATABASE_URL_${ENVIRONMENT^^} is set in .env"
  exit 1
fi

echo -e "${GREEN}📊 Database: ${DATABASE_URL%%@*}@***${NC}"
echo -e "${GREEN}🚀 Command: alembic $COMMAND $ARGS${NC}"
echo ""

alembic $COMMAND $ARGS

echo -e "${GREEN}✅ Migration completed successfully!${NC}"

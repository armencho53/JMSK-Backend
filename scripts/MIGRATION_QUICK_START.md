# Migration Quick Start Guide

## TL;DR - How to Migrate

### Step 1: Test First (Dry Run)
```bash
cd JMSK-Backend
python scripts/migrate_customers_to_contacts.py --dry-run
```

### Step 2: Run Migration
```bash
python scripts/migrate_customers_to_contacts.py
```

Type `yes` when prompted.

### Step 3: Verify
The script automatically verifies the migration. Check the output for any errors.

## What Gets Migrated

| Before | After |
|--------|-------|
| `customers` table | `contacts` table |
| `orders.customer_id` | `orders.contact_id` |
| No `orders.company_id` | `orders.company_id` (auto-populated) |
| No `addresses` table | `addresses` table (created) |

## Safety Features

✅ **Automatic Backup**: Creates backup before migration  
✅ **Pre-validation**: Checks data integrity before starting  
✅ **Post-verification**: Validates migration success  
✅ **Detailed Report**: Generates migration report  
✅ **Rollback Support**: Can be reversed with `alembic downgrade -1`

## Common Commands

```bash
# Dry run (no changes)
python scripts/migrate_customers_to_contacts.py --dry-run

# Full migration with backup
python scripts/migrate_customers_to_contacts.py

# Migration without backup (if you have external backup)
python scripts/migrate_customers_to_contacts.py --skip-backup

# Verify existing migration
python scripts/migrate_customers_to_contacts.py --verify-only

# Rollback migration
alembic downgrade -1
```

## Expected Duration

- Small database (<1000 records): ~30 seconds
- Medium database (1000-10000 records): ~2-5 minutes
- Large database (>10000 records): ~5-15 minutes

## When to Run

- ✅ During maintenance window
- ✅ After backing up database
- ✅ After testing on staging
- ❌ During peak hours
- ❌ Without backup
- ❌ Without testing first

## Troubleshooting

### Migration fails?
1. Check error message
2. Restore from backup
3. Fix issue
4. Try again

### Need to rollback?
```bash
alembic downgrade -1
```

### Need help?
See `README_MIGRATION.md` for detailed guide.

## Post-Migration Checklist

- [ ] Verify migration report shows all checks passed
- [ ] Test application functionality
- [ ] Check that contacts display correctly
- [ ] Verify order relationships are intact
- [ ] Monitor application logs for errors
- [ ] Update API endpoints (if needed)
- [ ] Update frontend (if needed)

## Files Generated

- `backups/migration_TIMESTAMP/` - Table backups
- `migration_report_TIMESTAMP.txt` - Detailed report

## Support

For detailed information, see:
- `README_MIGRATION.md` - Complete migration guide
- `../alembic/versions/003_hierarchical_contact_system_README.md` - Technical details
- `../alembic/versions/003_hierarchical_contact_system_CONSTRAINTS.md` - Constraint details

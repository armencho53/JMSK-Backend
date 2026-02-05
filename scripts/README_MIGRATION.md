# Customer to Contact Migration Guide

## Overview

This guide explains how to migrate from the legacy customer-company structure to the new hierarchical contact system using the provided migration script.

## What This Migration Does

The migration transforms your database schema to support a hierarchical contact system:

1. **Renames** `customers` table to `contacts`
2. **Makes** `company_id` required for all contacts (creates default companies for orphaned contacts)
3. **Adds** `company_id` column to `orders` table
4. **Creates** `addresses` table for company addresses
5. **Adds** database constraints, indexes, and triggers for data integrity
6. **Preserves** all existing order relationships

## Requirements Addressed

- **Requirement 1.5**: Preserve all existing order relationships during restructuring
- **Requirement 8.1**: Migrate existing customer data to contacts
- **Requirement 8.2**: Ensure all orders are properly linked to contacts and companies
- **Requirement 8.3**: Verify data integrity after migration

## Pre-Migration Checklist

Before running the migration, ensure:

- [ ] You have a **full database backup** (the script creates a logical backup, but a full backup is recommended)
- [ ] You have tested the migration on a **staging/development environment** first
- [ ] All users are **logged out** and the application is in maintenance mode
- [ ] You have reviewed the **pre-migration validation checks** (run with `--dry-run`)
- [ ] You understand that this operation **cannot be easily reversed**

## Migration Script Usage

### 1. Dry Run (Recommended First Step)

Run validation checks without making any changes:

```bash
cd JMSK-Backend
python scripts/migrate_customers_to_contacts.py --dry-run
```

This will:
- Check if the database is ready for migration
- Identify any potential issues
- Show statistics about data to be migrated
- **NOT make any changes** to the database

### 2. Full Migration with Backup

Execute the migration with automatic backup:

```bash
python scripts/migrate_customers_to_contacts.py
```

This will:
1. Run pre-migration validation checks
2. Create a logical backup of critical tables
3. Ask for confirmation before proceeding
4. Execute the Alembic migration
5. Run post-migration verification checks
6. Generate a detailed migration report

### 3. Migration Without Backup (Not Recommended)

If you already have a backup and want to skip the script's backup:

```bash
python scripts/migrate_customers_to_contacts.py --skip-backup
```

⚠️ **Warning**: Only use this if you have a reliable external backup!

### 4. Verify Existing Migration

If the migration has already been run and you want to verify data integrity:

```bash
python scripts/migrate_customers_to_contacts.py --verify-only
```

This will:
- Skip pre-migration checks
- Run all post-migration verification checks
- Generate a verification report

## What the Script Checks

### Pre-Migration Validation

1. ✓ Customers table exists
2. ✓ Count of customers to migrate
3. ✓ Orphaned customers (without company_id)
4. ✓ Valid tenant_id for all customers
5. ✓ Orders linked to customers
6. ✓ Order-customer relationship integrity
7. ✓ Duplicate emails within companies

### Post-Migration Verification

1. ✓ Contacts table exists
2. ✓ Customers table was renamed
3. ✓ Count of contacts after migration
4. ✓ All contacts have company_id (NOT NULL)
5. ✓ Orders have contact_id column
6. ✓ Orders have company_id column
7. ✓ Order-contact-company consistency
8. ✓ Addresses table exists
9. ✓ Required indexes created
10. ✓ Foreign key constraints verified

## Expected Output

### Successful Migration

```
============================================================
PRE-MIGRATION VALIDATION CHECKS
============================================================

✓ Checking if 'customers' table exists...
  ✓ PASSED: customers table found

✓ Counting total customers...
  ✓ Found 150 customers

...

============================================================
✓ PRE-MIGRATION VALIDATION PASSED
  Database is ready for migration
============================================================

============================================================
READY TO MIGRATE
============================================================

Proceed with migration? (yes/no): yes

============================================================
CREATING DATABASE BACKUP
============================================================

✓ Backing up customers table...
  ✓ Backed up 150 rows to backups/migration_20250123_143022/customers.sql

...

============================================================
EXECUTING DATABASE MIGRATION
============================================================

Running: alembic upgrade head

✓ Migration completed successfully!

============================================================
POST-MIGRATION VERIFICATION CHECKS
============================================================

✓ Checking if 'contacts' table exists...
  ✓ PASSED: contacts table found

...

============================================================
✓ POST-MIGRATION VERIFICATION PASSED
  Migration completed successfully!
  All data integrity checks passed.
============================================================

✓ MIGRATION COMPLETED SUCCESSFULLY!

Next steps:
  1. Review the migration report above
  2. Test the application with the new schema
  3. Update API endpoints to use 'contact' terminology
  4. Update frontend to use 'Contact' instead of 'Client'
```

## Handling Common Issues

### Issue: Orphaned Customers (No company_id)

**Symptom**: Pre-migration check shows customers without company_id

**Solution**: The migration automatically handles this by:
1. Creating a "Default Company" for each affected tenant
2. Assigning orphaned customers to the default company
3. You can later reassign these contacts to proper companies

### Issue: Invalid tenant_id

**Symptom**: Pre-migration check fails with invalid tenant_id

**Solution**: 
1. Identify the problematic records
2. Fix or remove them before migration
3. Run dry-run again to verify

```sql
-- Find customers with invalid tenant_id
SELECT * FROM customers c
WHERE c.tenant_id IS NULL 
OR NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = c.tenant_id);
```

### Issue: Duplicate Emails Within Companies

**Symptom**: Warning about duplicate emails

**Solution**: This is usually not a blocker. The migration will:
1. Keep all contacts (no data loss)
2. The unique constraint `(tenant_id, company_id, email)` will be enforced
3. You may need to update duplicate emails after migration

### Issue: Migration Fails Midway

**Symptom**: Migration script reports failure

**Solution**:
1. Check the error message for details
2. Restore from backup if needed
3. Fix the underlying issue
4. Run the migration again

```bash
# Check current migration status
cd JMSK-Backend
alembic current

# If needed, downgrade to previous version
alembic downgrade -1

# Restore from backup (if needed)
# Use your database's restore tools with the backup files
```

## Rollback Procedure

If you need to rollback the migration:

### Option 1: Alembic Downgrade (Immediate)

```bash
cd JMSK-Backend
alembic downgrade -1
```

⚠️ **Warning**: This may result in data loss if:
- Multiple contacts have the same email across different companies
- Addresses have been created
- The schema has been modified after migration

### Option 2: Restore from Backup (Safest)

1. Stop the application
2. Restore database from backup
3. Verify data integrity
4. Restart application

## Post-Migration Tasks

After successful migration:

1. **Test the Application**
   - Verify contacts are displayed correctly
   - Check order relationships
   - Test company-contact hierarchy

2. **Update API Endpoints**
   - Endpoints should use "contact" terminology
   - Update API documentation

3. **Update Frontend**
   - Change "Customer" to "Contact" in UI
   - Update navigation and routes
   - Test all contact-related features

4. **Monitor Performance**
   - Check query performance with new indexes
   - Monitor for any errors in logs

5. **Clean Up**
   - Remove old backup files after verification
   - Update documentation

## Verification Queries

After migration, you can manually verify data integrity:

```sql
-- Verify all contacts have company_id
SELECT COUNT(*) FROM contacts WHERE company_id IS NULL;
-- Expected: 0

-- Verify all orders have company_id
SELECT COUNT(*) FROM orders WHERE company_id IS NULL;
-- Expected: 0

-- Verify order-contact-company consistency
SELECT COUNT(*) 
FROM orders o
JOIN contacts c ON o.contact_id = c.id
WHERE o.company_id != c.company_id;
-- Expected: 0

-- Check contact count matches original customer count
SELECT 
  (SELECT COUNT(*) FROM contacts) as contact_count,
  'Should match original customer count' as note;

-- Verify indexes exist
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('contacts', 'orders', 'addresses')
ORDER BY tablename, indexname;
```

## Support

If you encounter issues during migration:

1. Check the migration report for detailed error messages
2. Review the backup files in `backups/migration_TIMESTAMP/`
3. Check Alembic migration logs
4. Consult the database migration documentation

## Files Created by Migration

- `backups/migration_TIMESTAMP/` - Logical backup of tables
  - `customers.sql` - Backup of customers table
  - `companies.sql` - Backup of companies table
  - `orders.sql` - Backup of orders table

- `migration_report_TIMESTAMP.txt` - Detailed migration report with all checks

## Technical Details

### Database Changes

See `JMSK-Backend/alembic/versions/003_hierarchical_contact_system_README.md` for complete technical details about:
- Schema changes
- Constraints added
- Triggers created
- Indexes added

### Migration Script

The migration script (`migrate_customers_to_contacts.py`) is a wrapper around Alembic that:
- Provides validation and verification
- Creates backups
- Generates reports
- Ensures data integrity

The actual schema changes are defined in:
`JMSK-Backend/alembic/versions/003_hierarchical_contact_system.py`

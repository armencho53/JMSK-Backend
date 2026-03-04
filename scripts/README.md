# Data Migration Scripts

This directory contains standalone data migration scripts for the JMSK Backend.

## Order Line Items Migration

### Overview

The `migrate_orders_to_line_items.py` script migrates existing single-line orders to the new multi-line order system by creating `order_line_items` records.

### Prerequisites

1. Apply the schema migration first:
   ```bash
   alembic upgrade head
   ```

2. Ensure the `order_line_items` table exists in your database

### Usage

#### Dry Run (Recommended First)

Preview what the migration will do without making changes:

```bash
python scripts/migrate_orders_to_line_items.py --dry-run
```

#### Run Migration

Execute the actual migration:

```bash
python scripts/migrate_orders_to_line_items.py
```

#### Verify Migration

Check migration status without running it:

```bash
python scripts/migrate_orders_to_line_items.py --verify
```

#### Custom Database URL

Override the default database connection:

```bash
python scripts/migrate_orders_to_line_items.py --database-url "postgresql://user:pass@host:5432/dbname"
```

### What It Does

1. **Finds eligible orders**: Selects all orders with `product_description` populated that don't already have line items
2. **Creates line items**: For each order, creates a corresponding `order_line_items` record with:
   - `product_description`
   - `specifications`
   - `metal_id`
   - `quantity`
   - `target_weight_per_piece`
   - `initial_total_weight`
   - `price`
   - `labor_cost`
   - Timestamps (`created_at`, `updated_at`)
3. **Preserves data**: All existing order data is copied without modification
4. **Idempotent**: Can be run multiple times safely - skips orders that already have line items

### Safety Features

- **Idempotent**: Running multiple times won't create duplicate line items
- **Transaction-based**: All changes are wrapped in a database transaction
- **Dry-run mode**: Test the migration without making changes
- **Verification**: Built-in verification to check migration status
- **Rollback on error**: Automatically rolls back if any error occurs

### Output

The script provides detailed output:

```
Starting order migration...
Database: localhost:5432/jmsk_db
--------------------------------------------------------------------------------
Found 150 orders to migrate

✓ Created line item for order ORD-2024-001 (ID: 1)
✓ Created line item for order ORD-2024-002 (ID: 2)
...

================================================================================
✓ Migration completed successfully!

Summary:
  Orders processed: 150
  Line items created: 150
  Orders skipped (already migrated): 0

Verifying migration...
--------------------------------------------------------------------------------
Total line items in database: 150
Orders with line items: 150
Orders still needing migration: 0

✓ All orders have been successfully migrated!
```

### Troubleshooting

**Error: "No module named 'app'"**
- Make sure you're running from the JMSK-Backend directory
- The script automatically adds the parent directory to the Python path

**Error: "relation 'order_line_items' does not exist"**
- Run the schema migration first: `alembic upgrade head`

**Orders skipped during migration**
- This is normal if you've run the migration before
- The script skips orders that already have line items

**Migration shows 0 orders found**
- All orders may already be migrated
- Or no orders have `product_description` populated
- Run with `--verify` to check current status

### Rollback

If you need to rollback the migration:

```sql
-- Delete all line items (be careful!)
DELETE FROM order_line_items;

-- Or delete for specific orders
DELETE FROM order_line_items WHERE order_id IN (1, 2, 3);
```

Then you can re-run the migration script.

### Related Files

- Schema migration: `alembic/versions/003_add_order_line_items_table.py`
- Order model: `app/data/models/order.py`
- Requirements: `.kiro/specs/orders-metal-refactoring/requirements.md` (3.6, 3.7)
- Design: `.kiro/specs/orders-metal-refactoring/design.md`

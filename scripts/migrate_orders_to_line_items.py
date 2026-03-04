#!/usr/bin/env python3
"""
Data migration script to convert existing single-line orders to order_line_items records.

This script:
1. Finds all existing orders that have product_description populated
2. Creates corresponding OrderLineItem records with all order data
3. Preserves all existing order data without loss
4. Is idempotent (can be run multiple times safely)

Requirements: 3.6, 3.7

Usage:
    python scripts/migrate_orders_to_line_items.py

Note: Run this AFTER applying the schema migration 003_add_order_line_items_table.py
"""

import sys
import os
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.infrastructure.config import settings
from app.data.database import Base


def migrate_orders_to_line_items(database_url: str = None, dry_run: bool = False):
    """
    Migrate existing single-line orders to order_line_items table.
    
    Args:
        database_url: Database connection string (defaults to settings.DATABASE_URL)
        dry_run: If True, only print what would be done without making changes
    
    Returns:
        Tuple of (orders_processed, line_items_created, orders_skipped)
    """
    # Use provided database URL or fall back to settings
    db_url = database_url or settings.DATABASE_URL
    
    # Create engine and session
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    orders_processed = 0
    line_items_created = 0
    orders_skipped = 0
    
    try:
        print(f"{'[DRY RUN] ' if dry_run else ''}Starting order migration...")
        print(f"Database: {db_url.split('@')[-1] if '@' in db_url else 'local'}")
        print("-" * 80)
        
        # Find all orders with product_description that don't already have line items
        query = text("""
            SELECT 
                o.id,
                o.tenant_id,
                o.order_number,
                o.product_description,
                o.specifications,
                o.metal_id,
                o.quantity,
                o.target_weight_per_piece,
                o.initial_total_weight,
                o.price,
                o.labor_cost,
                o.created_at,
                o.updated_at,
                COUNT(oli.id) as existing_line_items
            FROM orders o
            LEFT JOIN order_line_items oli ON oli.order_id = o.id
            WHERE o.product_description IS NOT NULL 
                AND o.product_description != ''
            GROUP BY o.id
            HAVING COUNT(oli.id) = 0
            ORDER BY o.id
        """)
        
        result = session.execute(query)
        orders = result.fetchall()
        
        if not orders:
            print("No orders found that need migration.")
            return 0, 0, 0
        
        print(f"Found {len(orders)} orders to migrate\n")
        
        # Process each order
        for order in orders:
            order_id = order.id
            tenant_id = order.tenant_id
            order_number = order.order_number
            
            # Check if this order already has line items (safety check)
            check_query = text("""
                SELECT COUNT(*) as count 
                FROM order_line_items 
                WHERE order_id = :order_id
            """)
            existing_count = session.execute(
                check_query, 
                {"order_id": order_id}
            ).scalar()
            
            if existing_count > 0:
                print(f"⚠️  Order {order_number} (ID: {order_id}) already has {existing_count} line items - SKIPPING")
                orders_skipped += 1
                continue
            
            # Create line item from order data
            insert_query = text("""
                INSERT INTO order_line_items (
                    tenant_id,
                    order_id,
                    product_description,
                    specifications,
                    metal_id,
                    quantity,
                    target_weight_per_piece,
                    initial_total_weight,
                    price,
                    labor_cost,
                    created_at,
                    updated_at
                ) VALUES (
                    :tenant_id,
                    :order_id,
                    :product_description,
                    :specifications,
                    :metal_id,
                    :quantity,
                    :target_weight_per_piece,
                    :initial_total_weight,
                    :price,
                    :labor_cost,
                    :created_at,
                    :updated_at
                )
            """)
            
            params = {
                "tenant_id": tenant_id,
                "order_id": order_id,
                "product_description": order.product_description,
                "specifications": order.specifications,
                "metal_id": order.metal_id,
                "quantity": order.quantity or 1,
                "target_weight_per_piece": order.target_weight_per_piece,
                "initial_total_weight": order.initial_total_weight,
                "price": order.price,
                "labor_cost": order.labor_cost,
                "created_at": order.created_at or datetime.utcnow(),
                "updated_at": order.updated_at or datetime.utcnow()
            }
            
            if dry_run:
                print(f"[DRY RUN] Would create line item for order {order_number} (ID: {order_id})")
                print(f"  Product: {order.product_description[:50]}...")
                print(f"  Metal ID: {order.metal_id}, Quantity: {order.quantity or 1}")
            else:
                session.execute(insert_query, params)
                print(f"✓ Created line item for order {order_number} (ID: {order_id})")
            
            orders_processed += 1
            line_items_created += 1
        
        # Commit transaction if not dry run
        if not dry_run:
            session.commit()
            print("\n" + "=" * 80)
            print("✓ Migration completed successfully!")
        else:
            print("\n" + "=" * 80)
            print("[DRY RUN] No changes were made to the database")
        
        print(f"\nSummary:")
        print(f"  Orders processed: {orders_processed}")
        print(f"  Line items created: {line_items_created}")
        print(f"  Orders skipped (already migrated): {orders_skipped}")
        
        return orders_processed, line_items_created, orders_skipped
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error during migration: {str(e)}")
        raise
    finally:
        session.close()
        engine.dispose()


def verify_migration(database_url: str = None):
    """
    Verify that the migration was successful by checking data integrity.
    
    Args:
        database_url: Database connection string (defaults to settings.DATABASE_URL)
    """
    db_url = database_url or settings.DATABASE_URL
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        print("\nVerifying migration...")
        print("-" * 80)
        
        # Check orders with product_description but no line items
        query = text("""
            SELECT COUNT(*) as count
            FROM orders o
            LEFT JOIN order_line_items oli ON oli.order_id = o.id
            WHERE o.product_description IS NOT NULL 
                AND o.product_description != ''
            GROUP BY o.id
            HAVING COUNT(oli.id) = 0
        """)
        
        unmigrated_count = len(session.execute(query).fetchall())
        
        # Check total line items created
        total_line_items = session.execute(
            text("SELECT COUNT(*) FROM order_line_items")
        ).scalar()
        
        # Check orders with line items
        orders_with_line_items = session.execute(
            text("""
                SELECT COUNT(DISTINCT order_id) 
                FROM order_line_items
            """)
        ).scalar()
        
        print(f"Total line items in database: {total_line_items}")
        print(f"Orders with line items: {orders_with_line_items}")
        print(f"Orders still needing migration: {unmigrated_count}")
        
        if unmigrated_count == 0:
            print("\n✓ All orders have been successfully migrated!")
        else:
            print(f"\n⚠️  Warning: {unmigrated_count} orders still need migration")
        
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate existing single-line orders to order_line_items table"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no changes will be made)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify migration status without running migration"
    )
    parser.add_argument(
        "--database-url",
        type=str,
        help="Database connection string (overrides settings.DATABASE_URL)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.verify:
            verify_migration(args.database_url)
        else:
            migrate_orders_to_line_items(
                database_url=args.database_url,
                dry_run=args.dry_run
            )
            
            # Run verification after migration
            if not args.dry_run:
                verify_migration(args.database_url)
                
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        sys.exit(1)

#!/usr/bin/env python3
"""
Test script to verify tenant_id is properly inserted when creating manufacturing steps
"""
import os
import sys

# Set database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_7SxAlHGEB4vd@ep-noisy-credit-ah4w8p9r-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"
)

print("=" * 60)
print("Testing tenant_id Insertion in Manufacturing Steps")
print("=" * 60)

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("\n✓ Database connection established")
    
    # Test 1: Check if manufacturing_steps table exists
    print("\n" + "=" * 60)
    print("Test 1: Check Table Structure")
    print("=" * 60)
    
    result = session.execute(text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'manufacturing_steps'
        AND column_name IN ('id', 'tenant_id', 'order_id', 'parent_step_id')
        ORDER BY ordinal_position
    """))
    
    columns = result.fetchall()
    if columns:
        print("✓ manufacturing_steps table exists")
        print("\nKey columns:")
        for col in columns:
            nullable = "NULL" if col[2] == "YES" else "NOT NULL"
            print(f"  - {col[0]}: {col[1]} ({nullable})")
    else:
        print("✗ manufacturing_steps table not found")
        sys.exit(1)
    
    # Test 2: Check existing records
    print("\n" + "=" * 60)
    print("Test 2: Check Existing Records")
    print("=" * 60)
    
    result = session.execute(text("""
        SELECT id, tenant_id, order_id, parent_step_id, description
        FROM manufacturing_steps
        ORDER BY id DESC
        LIMIT 5
    """))
    
    records = result.fetchall()
    if records:
        print(f"✓ Found {len(records)} recent records:")
        for rec in records:
            tenant_status = "✓" if rec[1] is not None else "✗ MISSING"
            parent_status = "NULL" if rec[3] is None else f"→ {rec[3]}"
            print(f"  ID: {rec[0]}, tenant_id: {rec[1]} {tenant_status}, order_id: {rec[2]}, parent: {parent_status}")
            if rec[4]:
                print(f"    Description: {rec[4][:50]}...")
    else:
        print("⚠ No records found in manufacturing_steps table")
    
    # Test 3: Check for records with NULL tenant_id
    print("\n" + "=" * 60)
    print("Test 3: Check for NULL tenant_id")
    print("=" * 60)
    
    result = session.execute(text("""
        SELECT COUNT(*) FROM manufacturing_steps WHERE tenant_id IS NULL
    """))
    
    null_count = result.fetchone()[0]
    if null_count > 0:
        print(f"✗ Found {null_count} records with NULL tenant_id!")
        print("\nThese records need to be fixed:")
        
        result = session.execute(text("""
            SELECT id, order_id, description
            FROM manufacturing_steps
            WHERE tenant_id IS NULL
            LIMIT 10
        """))
        
        for rec in result.fetchall():
            print(f"  - ID: {rec[0]}, order_id: {rec[1]}, description: {rec[2][:50] if rec[2] else 'N/A'}...")
    else:
        print("✓ No records with NULL tenant_id found")
    
    # Test 4: Verify tenant_id constraint
    print("\n" + "=" * 60)
    print("Test 4: Check Foreign Key Constraint")
    print("=" * 60)
    
    result = session.execute(text("""
        SELECT
            tc.constraint_name,
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name = 'manufacturing_steps'
        AND kcu.column_name = 'tenant_id'
    """))
    
    fk = result.fetchone()
    if fk:
        print(f"✓ Foreign key constraint exists:")
        print(f"  {fk[1]}.{fk[2]} → {fk[3]}.{fk[4]}")
    else:
        print("⚠ No foreign key constraint found for tenant_id")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    if null_count == 0:
        print("✓ All manufacturing steps have tenant_id set correctly")
        print("\nThe endpoint should be working correctly.")
        print("If you're still seeing issues, check:")
        print("  1. Authentication is working (current_user is set)")
        print("  2. The user has a valid tenant_id")
        print("  3. Check application logs for errors")
    else:
        print(f"✗ Found {null_count} records with NULL tenant_id")
        print("\nTo fix existing records, you can run:")
        print("  UPDATE manufacturing_steps")
        print("  SET tenant_id = (SELECT tenant_id FROM orders WHERE orders.id = manufacturing_steps.order_id)")
        print("  WHERE tenant_id IS NULL;")
    
    session.close()
    
except ImportError as e:
    print(f"\n✗ Missing required package: {e}")
    print("\nPlease install:")
    print("  pip install sqlalchemy psycopg2-binary")
    sys.exit(1)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

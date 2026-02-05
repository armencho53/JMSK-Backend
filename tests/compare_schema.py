#!/usr/bin/env python3
"""
Compare SQLAlchemy models against PostgreSQL database
Usage: python compare_schema.py "your_database_url"
"""
import os
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    if len(sys.argv) < 2:
        print("Usage: python compare_schema.py 'DATABASE_URL'")
        print("Example: python compare_schema.py 'postgresql://user:pass@host/db'")
        sys.exit(1)
    
    DATABASE_URL = sys.argv[1]
    
    print("=" * 80)
    print("Testing Database Connection")
    print("=" * 80)
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected successfully!")
            print(f"PostgreSQL Version: {version[:80]}...")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)
    
    # Get database tables
    print("\n" + "=" * 80)
    print("Database Tables")
    print("=" * 80)
    inspector = inspect(engine)
    db_tables = inspector.get_table_names()
    print(f"\nFound {len(db_tables)} tables:")
    for table in sorted(db_tables):
        print(f"  - {table}")
    
    # Check manufacturing_steps
    if 'manufacturing_steps' not in db_tables:
        print("\n❌ manufacturing_steps table NOT FOUND in database!")
        print("   Run manufacturing_steps_table.sql to create it.")
        return
    
    print("\n" + "=" * 80)
    print("Manufacturing Steps Table Schema")
    print("=" * 80)
    
    columns = inspector.get_columns('manufacturing_steps')
    print(f"\nFound {len(columns)} columns:")
    print(f"\n{'Column Name':<30} {'Type':<25} {'Nullable':<10} {'Default':<20}")
    print("-" * 90)
    for col in columns:
        default = str(col.get('default', ''))[:18] if col.get('default') else ''
        print(f"{col['name']:<30} {str(col['type']):<25} {str(col['nullable']):<10} {default:<20}")
    
    # Check enum values
    print("\n" + "=" * 80)
    print("Enum Values in Database")
    print("=" * 80)
    
    query = text("""
    SELECT 
        t.typname as enum_name,
        e.enumlabel as enum_value
    FROM pg_type t 
    JOIN pg_enum e ON t.oid = e.enumtypid
    WHERE t.typname IN ('steptype', 'stepstatus')
    ORDER BY t.typname, e.enumsortorder;
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()
        
        if rows:
            current_enum = None
            for row in rows:
                if row[0] != current_enum:
                    current_enum = row[0]
                    print(f"\n{current_enum}:")
                print(f"  - {row[1]}")
        else:
            print("\n⚠️  No enum types found")
    
    # Compare with model
    print("\n" + "=" * 80)
    print("Model Enum Values (Expected)")
    print("=" * 80)
    
    from app.data.models.manufacturing_step import StepType, StepStatus
    
    print("\nsteptype:")
    for e in StepType:
        print(f"  - {e.value}")
    
    print("\nstepstatus:")
    for e in StepStatus:
        print(f"  - {e.value}")
    
    # Check indexes
    print("\n" + "=" * 80)
    print("Indexes")
    print("=" * 80)
    
    indexes = inspector.get_indexes('manufacturing_steps')
    if indexes:
        print(f"\nFound {len(indexes)} indexes:")
        for idx in indexes:
            print(f"  - {idx['name']}: {', '.join(idx['column_names'])}")
    else:
        print("\n⚠️  No indexes found")
    
    print("\n" + "=" * 80)
    print("Comparison Complete")
    print("=" * 80)

if __name__ == "__main__":
    main()

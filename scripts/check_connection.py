#!/usr/bin/env python3
"""
Test database connection to verify the connection string works
"""
import os
import sys
from sqlalchemy import create_engine, text

def test_connection(database_url):
    """Test database connection"""
    print("🔍 Testing database connection...")
    print(f"📍 Host: {database_url.split('@')[1].split(':')[0] if '@' in database_url else 'unknown'}")
    
    try:
        # Create engine
        engine = create_engine(database_url, pool_pre_ping=True)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ Connection successful!")
            print(f"📊 PostgreSQL version: {version[:50]}...")
            
            # Check if tables exist
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                print(f"📋 Found {len(tables)} tables:")
                for table in tables:
                    print(f"   - {table}")
            else:
                print("⚠️  No tables found. You may need to run migrations.")
            
            return True
            
    except Exception as e:
        print(f"❌ Connection failed!")
        print(f"Error: {str(e)}")
        print()
        print("Common issues:")
        print("1. Wrong connection string format")
        print("2. Using direct connection (port 5432) instead of pooler (port 6543)")
        print("3. Incorrect password")
        print("4. Database not accessible from your IP")
        print()
        print("For Lambda/serverless, use the CONNECTION POOLING string:")
        print("  postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres")
        return False

if __name__ == "__main__":
    # Get DATABASE_URL from environment or command line
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url and len(sys.argv) > 1:
        database_url = sys.argv[1]
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not provided")
        print()
        print("Usage:")
        print("  export DATABASE_URL='postgresql://...'")
        print("  python test_connection.py")
        print()
        print("Or:")
        print("  python test_connection.py 'postgresql://...'")
        sys.exit(1)
    
    # Hide password in output
    safe_url = database_url.split('@')[0].split(':')[0] + ':****@' + database_url.split('@')[1] if '@' in database_url else database_url
    print(f"🔗 Using: {safe_url}")
    print()
    
    success = test_connection(database_url)
    sys.exit(0 if success else 1)

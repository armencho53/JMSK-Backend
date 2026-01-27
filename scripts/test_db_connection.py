#!/usr/bin/env python3
"""
Test database connection and help with URL encoding
Run with: python -m scripts.test_db_connection <command>
Or activate venv first: source venv/bin/activate (or venv\Scripts\activate on Windows)
"""
import sys
from urllib.parse import quote_plus

try:
    from sqlalchemy import create_engine, text
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    print("⚠️  Warning: SQLAlchemy not installed. Connection testing disabled.")
    print("   To enable testing, run: pip install sqlalchemy psycopg2-binary")
    print("   Or activate your virtual environment: source venv/bin/activate\n")

def encode_password(password):
    """URL encode a password for use in connection strings"""
    return quote_plus(password)

def build_connection_string(host, port, database, user, password):
    """Build a properly encoded connection string"""
    encoded_password = encode_password(password)
    return f"postgresql://{user}:{encoded_password}@{host}:{port}/{database}"

def test_connection(connection_string):
    """Test if a connection string works"""
    if not SQLALCHEMY_AVAILABLE:
        print("❌ Cannot test connection: SQLAlchemy not installed")
        print("   Run: pip install sqlalchemy psycopg2-binary")
        print("   Or activate your virtual environment")
        return False
    
    try:
        print("Connecting to database...")
        engine = create_engine(connection_string, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Connection successful!")
            print("   Database is reachable and credentials are correct.")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nCommon issues:")
        print("  1. Wrong password or special characters not encoded")
        print("  2. Wrong user format (should be postgres.PROJECT_REF)")
        print("  3. Network/firewall blocking connection")
        print("  4. Database not accessible from your IP")
        return False

if __name__ == "__main__":
    print("=== Supabase Connection String Helper ===\n")
    
    # Example usage
    print("Usage examples:")
    print("\n1. Encode a password:")
    print("   python scripts/test_db_connection.py encode 'your-password-here'")
    print("\n2. Test a connection string:")
    print("   python scripts/test_db_connection.py test 'postgresql://user:pass@host:5432/db'")
    print("\n3. Build and test a connection string:")
    print("   python scripts/test_db_connection.py build")
    
    if len(sys.argv) < 2:
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "encode":
        if len(sys.argv) < 3:
            print("\nError: Please provide a password to encode")
            print("Usage: python scripts/test_db_connection.py encode 'your-password'")
            sys.exit(1)
        
        password = sys.argv[2]
        encoded = encode_password(password)
        print(f"\nOriginal password: {password}")
        print(f"Encoded password:  {encoded}")
        print("\nUse the encoded password in your connection string:")
        print(f"postgresql://user:{encoded}@host:5432/database")
    
    elif command == "test":
        if not SQLALCHEMY_AVAILABLE:
            print("\n❌ Cannot test: SQLAlchemy not installed")
            print("Run: source venv/bin/activate && pip install sqlalchemy psycopg2-binary")
            sys.exit(1)
        
        if len(sys.argv) < 3:
            print("\nError: Please provide a connection string to test")
            print("Usage: python scripts/test_db_connection.py test 'postgresql://...'")
            sys.exit(1)
        
        connection_string = sys.argv[2]
        print(f"\nTesting connection...")
        print(f"Host: {connection_string.split('@')[1].split('/')[0] if '@' in connection_string else 'unknown'}")
        test_connection(connection_string)
    
    elif command == "build":
        if not SQLALCHEMY_AVAILABLE:
            print("\n⚠️  SQLAlchemy not installed - will build connection string but cannot test")
            print("To enable testing: source venv/bin/activate\n")
        
        print("\n=== Build Connection String ===")
        print("\nFor Supabase Session Pooler:")
        print("Host format: aws-0-REGION.pooler.supabase.com")
        print("Port: 5432")
        print("User format: postgres.PROJECT_REF (e.g., postgres.esdjwyvwhpuknjtqfzzb)")
        print("Database: postgres")
        
        print("\nEnter your details:")
        user = input("User (e.g., postgres.esdjwyvwhpuknjtqfzzb): ").strip()
        password = input("Password: ").strip()
        host = input("Host (e.g., aws-0-us-east-1.pooler.supabase.com): ").strip()
        port = input("Port [5432]: ").strip() or "5432"
        database = input("Database [postgres]: ").strip() or "postgres"
        
        connection_string = build_connection_string(host, port, database, user, password)
        
        print(f"\n=== Generated Connection String ===")
        print(connection_string)
        
        if SQLALCHEMY_AVAILABLE:
            print("\n=== Testing Connection ===")
            test_connection(connection_string)
        else:
            print("\n⚠️  Skipping connection test (SQLAlchemy not available)")
            print("To test: source venv/bin/activate && python scripts/test_db_connection.py test '<connection_string>'")
    
    else:
        print(f"\nUnknown command: {command}")
        print("Valid commands: encode, test, build")

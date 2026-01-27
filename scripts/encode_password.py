#!/usr/bin/env python3
"""
Simple password encoder for database connection strings
No dependencies required - uses only Python standard library
"""
import sys
from urllib.parse import quote_plus

def encode_password(password):
    """URL encode a password for use in connection strings"""
    return quote_plus(password)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=== Database Password Encoder ===\n")
        print("Usage: python scripts/encode_password.py 'your-password-here'\n")
        print("This will encode special characters in your password for use in connection strings.")
        print("\nExample:")
        print("  Password: my@pass#123")
        print("  Encoded:  my%40pass%23123")
        sys.exit(0)
    
    password = sys.argv[1]
    encoded = encode_password(password)
    
    print(f"\nOriginal password: {password}")
    print(f"Encoded password:  {encoded}")
    
    print("\n=== Supabase Session Pooler Connection String ===")
    print(f"postgresql://postgres.esdjwyvwhpuknjtqfzzb:{encoded}@aws-1-us-east-1.pooler.supabase.com:5432/postgres")
    
    print("\n✅ Copy the connection string above and update it in AWS Secrets Manager")

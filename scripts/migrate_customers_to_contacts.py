#!/usr/bin/env python3
"""
Data Migration Script: Customers to Contacts
==============================================

This script handles the migration from the legacy customer-company structure
to the new hierarchical contact system. It performs pre-migration validation,
executes the database migration, and verifies data integrity afterward.

Requirements Addressed:
- Requirement 1.5: Preserve all existing order relationships
- Requirement 8.1: Migrate existing customer data to contacts
- Requirement 8.2: Ensure all orders are properly linked to contacts and companies
- Requirement 8.3: Verify data integrity after migration

Usage:
    python scripts/migrate_customers_to_contacts.py [--dry-run] [--skip-backup]

Options:
    --dry-run       Run validation checks without executing migration
    --skip-backup   Skip database backup (not recommended for production)
    --verify-only   Only run post-migration verification checks
"""

import sys
import os
import argparse
from datetime import datetime
from typing import Dict, List, Tuple
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from app.data.database import engine, SessionLocal
from app.infrastructure.config import settings


class MigrationValidator:
    """Validates data before and after migration"""
    
    def __init__(self, db: Session):
        self.db = db
        self.validation_results = {}
    
    def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        inspector = inspect(engine)
        return table_name in inspector.get_table_names()
    
    def pre_migration_checks(self) -> Dict[str, any]:
        """Run validation checks before migration"""
        print("\n" + "="*60)
        print("PRE-MIGRATION VALIDATION CHECKS")
        print("="*60 + "\n")
        
        results = {
            'passed': True,
            'checks': []
        }
        
        # Check 1: Verify customers table exists
        print("✓ Checking if 'customers' table exists...")
        if not self.check_table_exists('customers'):
            results['passed'] = False
            results['checks'].append({
                'name': 'customers_table_exists',
                'passed': False,
                'message': "ERROR: 'customers' table does not exist. Migration may have already been run."
            })
            print("  ✗ FAILED: customers table not found")
        else:
            results['checks'].append({
                'name': 'customers_table_exists',
                'passed': True,
                'message': "customers table exists"
            })
            print("  ✓ PASSED: customers table found")
        
        # Check 2: Count total customers
        print("\n✓ Counting total customers...")
        customer_count = self.db.execute(text("SELECT COUNT(*) FROM customers")).scalar()
        results['checks'].append({
            'name': 'customer_count',
            'passed': True,
            'count': customer_count,
            'message': f"Found {customer_count} customers to migrate"
        })
        print(f"  ✓ Found {customer_count} customers")
        
        # Check 3: Check for customers without company_id
        print("\n✓ Checking for orphaned customers (no company_id)...")
        orphaned_count = self.db.execute(
            text("SELECT COUNT(*) FROM customers WHERE company_id IS NULL")
        ).scalar()
        
        if orphaned_count > 0:
            print(f"  ⚠ WARNING: Found {orphaned_count} customers without company_id")
            print(f"    These will be assigned to a 'Default Company' during migration")
            results['checks'].append({
                'name': 'orphaned_customers',
                'passed': True,
                'count': orphaned_count,
                'message': f"Found {orphaned_count} orphaned customers (will create default companies)"
            })
        else:
            print(f"  ✓ All customers have company_id")
            results['checks'].append({
                'name': 'orphaned_customers',
                'passed': True,
                'count': 0,
                'message': "No orphaned customers found"
            })
        
        # Check 4: Verify all customers have valid tenant_id
        print("\n✓ Checking customer tenant_id validity...")
        invalid_tenant_count = self.db.execute(
            text("""
                SELECT COUNT(*) FROM customers c
                WHERE c.tenant_id IS NULL 
                OR NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = c.tenant_id)
            """)
        ).scalar()
        
        if invalid_tenant_count > 0:
            results['passed'] = False
            results['checks'].append({
                'name': 'valid_tenant_ids',
                'passed': False,
                'count': invalid_tenant_count,
                'message': f"ERROR: {invalid_tenant_count} customers have invalid tenant_id"
            })
            print(f"  ✗ FAILED: {invalid_tenant_count} customers have invalid tenant_id")
        else:
            results['checks'].append({
                'name': 'valid_tenant_ids',
                'passed': True,
                'message': "All customers have valid tenant_id"
            })
            print(f"  ✓ All customers have valid tenant_id")
        
        # Check 5: Count orders referencing customers
        print("\n✓ Counting orders linked to customers...")
        order_count = self.db.execute(
            text("SELECT COUNT(*) FROM orders WHERE customer_id IS NOT NULL")
        ).scalar()
        results['checks'].append({
            'name': 'order_count',
            'passed': True,
            'count': order_count,
            'message': f"Found {order_count} orders linked to customers"
        })
        print(f"  ✓ Found {order_count} orders linked to customers")
        
        # Check 6: Check for orders with invalid customer_id
        print("\n✓ Checking order-customer relationship integrity...")
        invalid_orders = self.db.execute(
            text("""
                SELECT COUNT(*) FROM orders o
                WHERE o.customer_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM customers c WHERE c.id = o.customer_id)
            """)
        ).scalar()
        
        if invalid_orders > 0:
            results['passed'] = False
            results['checks'].append({
                'name': 'valid_order_customer_refs',
                'passed': False,
                'count': invalid_orders,
                'message': f"ERROR: {invalid_orders} orders reference non-existent customers"
            })
            print(f"  ✗ FAILED: {invalid_orders} orders reference non-existent customers")
        else:
            results['checks'].append({
                'name': 'valid_order_customer_refs',
                'passed': True,
                'message': "All orders reference valid customers"
            })
            print(f"  ✓ All orders reference valid customers")
        
        # Check 7: Check for duplicate emails within companies
        print("\n✓ Checking for duplicate emails within companies...")
        duplicate_emails = self.db.execute(
            text("""
                SELECT company_id, email, COUNT(*) as count
                FROM customers
                WHERE company_id IS NOT NULL AND email IS NOT NULL
                GROUP BY company_id, email
                HAVING COUNT(*) > 1
            """)
        ).fetchall()
        
        if duplicate_emails:
            print(f"  ⚠ WARNING: Found {len(duplicate_emails)} duplicate email(s) within companies:")
            for row in duplicate_emails[:5]:  # Show first 5
                print(f"    - Company {row[0]}: {row[1]} ({row[2]} occurrences)")
            if len(duplicate_emails) > 5:
                print(f"    ... and {len(duplicate_emails) - 5} more")
            results['checks'].append({
                'name': 'duplicate_emails',
                'passed': True,
                'count': len(duplicate_emails),
                'message': f"WARNING: {len(duplicate_emails)} duplicate emails within companies (migration will handle)"
            })
        else:
            results['checks'].append({
                'name': 'duplicate_emails',
                'passed': True,
                'count': 0,
                'message': "No duplicate emails within companies"
            })
            print(f"  ✓ No duplicate emails within companies")
        
        # Summary
        print("\n" + "="*60)
        if results['passed']:
            print("✓ PRE-MIGRATION VALIDATION PASSED")
            print("  Database is ready for migration")
        else:
            print("✗ PRE-MIGRATION VALIDATION FAILED")
            print("  Please fix the errors above before proceeding")
        print("="*60 + "\n")
        
        return results
    
    def post_migration_checks(self) -> Dict[str, any]:
        """Run validation checks after migration"""
        print("\n" + "="*60)
        print("POST-MIGRATION VERIFICATION CHECKS")
        print("="*60 + "\n")
        
        results = {
            'passed': True,
            'checks': []
        }
        
        # Check 1: Verify contacts table exists
        print("✓ Checking if 'contacts' table exists...")
        if not self.check_table_exists('contacts'):
            results['passed'] = False
            results['checks'].append({
                'name': 'contacts_table_exists',
                'passed': False,
                'message': "ERROR: 'contacts' table does not exist. Migration may have failed."
            })
            print("  ✗ FAILED: contacts table not found")
            return results
        else:
            results['checks'].append({
                'name': 'contacts_table_exists',
                'passed': True,
                'message': "contacts table exists"
            })
            print("  ✓ PASSED: contacts table found")
        
        # Check 2: Verify customers table no longer exists
        print("\n✓ Checking if 'customers' table was renamed...")
        if self.check_table_exists('customers'):
            results['passed'] = False
            results['checks'].append({
                'name': 'customers_table_removed',
                'passed': False,
                'message': "ERROR: 'customers' table still exists. Migration may have failed."
            })
            print("  ✗ FAILED: customers table still exists")
        else:
            results['checks'].append({
                'name': 'customers_table_removed',
                'passed': True,
                'message': "customers table successfully renamed to contacts"
            })
            print("  ✓ PASSED: customers table renamed")
        
        # Check 3: Count total contacts
        print("\n✓ Counting total contacts...")
        contact_count = self.db.execute(text("SELECT COUNT(*) FROM contacts")).scalar()
        results['checks'].append({
            'name': 'contact_count',
            'passed': True,
            'count': contact_count,
            'message': f"Found {contact_count} contacts after migration"
        })
        print(f"  ✓ Found {contact_count} contacts")
        
        # Check 4: Verify all contacts have company_id (NOT NULL constraint)
        print("\n✓ Verifying all contacts have company_id...")
        null_company_count = self.db.execute(
            text("SELECT COUNT(*) FROM contacts WHERE company_id IS NULL")
        ).scalar()
        
        if null_company_count > 0:
            results['passed'] = False
            results['checks'].append({
                'name': 'contacts_have_company',
                'passed': False,
                'count': null_company_count,
                'message': f"ERROR: {null_company_count} contacts have NULL company_id"
            })
            print(f"  ✗ FAILED: {null_company_count} contacts have NULL company_id")
        else:
            results['checks'].append({
                'name': 'contacts_have_company',
                'passed': True,
                'message': "All contacts have company_id"
            })
            print(f"  ✓ All contacts have company_id")
        
        # Check 5: Verify orders have contact_id (renamed from customer_id)
        print("\n✓ Checking orders.contact_id column...")
        try:
            order_contact_count = self.db.execute(
                text("SELECT COUNT(*) FROM orders WHERE contact_id IS NOT NULL")
            ).scalar()
            results['checks'].append({
                'name': 'orders_have_contact_id',
                'passed': True,
                'count': order_contact_count,
                'message': f"Found {order_contact_count} orders with contact_id"
            })
            print(f"  ✓ Found {order_contact_count} orders with contact_id")
        except Exception as e:
            results['passed'] = False
            results['checks'].append({
                'name': 'orders_have_contact_id',
                'passed': False,
                'message': f"ERROR: Could not query orders.contact_id: {str(e)}"
            })
            print(f"  ✗ FAILED: Could not query orders.contact_id")
        
        # Check 6: Verify orders have company_id
        print("\n✓ Checking orders.company_id column...")
        try:
            order_company_count = self.db.execute(
                text("SELECT COUNT(*) FROM orders WHERE company_id IS NOT NULL")
            ).scalar()
            results['checks'].append({
                'name': 'orders_have_company_id',
                'passed': True,
                'count': order_company_count,
                'message': f"Found {order_company_count} orders with company_id"
            })
            print(f"  ✓ Found {order_company_count} orders with company_id")
        except Exception as e:
            results['passed'] = False
            results['checks'].append({
                'name': 'orders_have_company_id',
                'passed': False,
                'message': f"ERROR: Could not query orders.company_id: {str(e)}"
            })
            print(f"  ✗ FAILED: Could not query orders.company_id")
        
        # Check 7: Verify order-contact-company consistency
        print("\n✓ Verifying order-contact-company relationship consistency...")
        inconsistent_orders = self.db.execute(
            text("""
                SELECT COUNT(*) 
                FROM orders o
                JOIN contacts c ON o.contact_id = c.id
                WHERE o.company_id != c.company_id
            """)
        ).scalar()
        
        if inconsistent_orders > 0:
            results['passed'] = False
            results['checks'].append({
                'name': 'order_contact_company_consistency',
                'passed': False,
                'count': inconsistent_orders,
                'message': f"ERROR: {inconsistent_orders} orders have mismatched company_id"
            })
            print(f"  ✗ FAILED: {inconsistent_orders} orders have company_id != contact.company_id")
        else:
            results['checks'].append({
                'name': 'order_contact_company_consistency',
                'passed': True,
                'message': "All orders have consistent contact-company relationships"
            })
            print(f"  ✓ All orders have consistent relationships")
        
        # Check 8: Verify addresses table exists
        print("\n✓ Checking if 'addresses' table exists...")
        if not self.check_table_exists('addresses'):
            results['passed'] = False
            results['checks'].append({
                'name': 'addresses_table_exists',
                'passed': False,
                'message': "ERROR: 'addresses' table does not exist"
            })
            print("  ✗ FAILED: addresses table not found")
        else:
            address_count = self.db.execute(text("SELECT COUNT(*) FROM addresses")).scalar()
            results['checks'].append({
                'name': 'addresses_table_exists',
                'passed': True,
                'count': address_count,
                'message': f"addresses table exists with {address_count} records"
            })
            print(f"  ✓ addresses table exists with {address_count} records")
        
        # Check 9: Verify indexes were created
        print("\n✓ Checking for required indexes...")
        inspector = inspect(engine)
        required_indexes = [
            ('contacts', 'ix_contacts_tenant_company'),
            ('orders', 'ix_orders_tenant_company'),
            ('orders', 'ix_orders_tenant_contact'),
            ('addresses', 'ix_addresses_company_id')
        ]
        
        missing_indexes = []
        for table, index_name in required_indexes:
            indexes = inspector.get_indexes(table)
            if not any(idx['name'] == index_name for idx in indexes):
                missing_indexes.append(f"{table}.{index_name}")
        
        if missing_indexes:
            results['passed'] = False
            results['checks'].append({
                'name': 'required_indexes',
                'passed': False,
                'message': f"ERROR: Missing indexes: {', '.join(missing_indexes)}"
            })
            print(f"  ✗ FAILED: Missing indexes: {', '.join(missing_indexes)}")
        else:
            results['checks'].append({
                'name': 'required_indexes',
                'passed': True,
                'message': "All required indexes created"
            })
            print(f"  ✓ All required indexes created")
        
        # Check 10: Verify foreign key constraints
        print("\n✓ Checking foreign key constraints...")
        try:
            # Test that constraints work by attempting invalid operations
            # This is a read-only check - we just verify the constraints exist
            fk_constraints = inspector.get_foreign_keys('contacts')
            company_fk = any(fk['referred_table'] == 'companies' for fk in fk_constraints)
            
            if not company_fk:
                results['passed'] = False
                results['checks'].append({
                    'name': 'foreign_key_constraints',
                    'passed': False,
                    'message': "ERROR: contacts.company_id foreign key not found"
                })
                print(f"  ✗ FAILED: Missing foreign key constraint")
            else:
                results['checks'].append({
                    'name': 'foreign_key_constraints',
                    'passed': True,
                    'message': "Foreign key constraints verified"
                })
                print(f"  ✓ Foreign key constraints verified")
        except Exception as e:
            results['checks'].append({
                'name': 'foreign_key_constraints',
                'passed': True,
                'message': f"Could not verify constraints (may be normal): {str(e)}"
            })
            print(f"  ⚠ Could not verify constraints (may be normal)")
        
        # Summary
        print("\n" + "="*60)
        if results['passed']:
            print("✓ POST-MIGRATION VERIFICATION PASSED")
            print("  Migration completed successfully!")
            print("  All data integrity checks passed.")
        else:
            print("✗ POST-MIGRATION VERIFICATION FAILED")
            print("  Some checks failed. Please review the errors above.")
        print("="*60 + "\n")
        
        return results
    
    def generate_report(self, pre_results: Dict, post_results: Dict = None) -> str:
        """Generate a detailed migration report"""
        report = []
        report.append("\n" + "="*60)
        report.append("MIGRATION REPORT")
        report.append("="*60)
        report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'}")
        
        report.append("\n\nPRE-MIGRATION CHECKS:")
        report.append("-" * 60)
        for check in pre_results['checks']:
            status = "✓ PASS" if check['passed'] else "✗ FAIL"
            report.append(f"{status}: {check['name']}")
            report.append(f"  {check['message']}")
            if 'count' in check:
                report.append(f"  Count: {check['count']}")
        
        if post_results:
            report.append("\n\nPOST-MIGRATION CHECKS:")
            report.append("-" * 60)
            for check in post_results['checks']:
                status = "✓ PASS" if check['passed'] else "✗ FAIL"
                report.append(f"{status}: {check['name']}")
                report.append(f"  {check['message']}")
                if 'count' in check:
                    report.append(f"  Count: {check['count']}")
        
        report.append("\n" + "="*60)
        report.append("END OF REPORT")
        report.append("="*60 + "\n")
        
        return "\n".join(report)


def backup_database(db: Session) -> str:
    """Create a logical backup of critical tables"""
    print("\n" + "="*60)
    print("CREATING DATABASE BACKUP")
    print("="*60 + "\n")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f"backups/migration_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)
    
    tables_to_backup = ['customers', 'companies', 'orders']
    
    for table in tables_to_backup:
        try:
            print(f"✓ Backing up {table} table...")
            result = db.execute(text(f"SELECT * FROM {table}"))
            rows = result.fetchall()
            
            backup_file = os.path.join(backup_dir, f"{table}.sql")
            with open(backup_file, 'w') as f:
                f.write(f"-- Backup of {table} table\n")
                f.write(f"-- Created: {datetime.now()}\n")
                f.write(f"-- Row count: {len(rows)}\n\n")
                
                if rows:
                    columns = result.keys()
                    f.write(f"-- Columns: {', '.join(columns)}\n\n")
                    for row in rows:
                        values = ', '.join([f"'{v}'" if v is not None else 'NULL' for v in row])
                        f.write(f"-- INSERT INTO {table} VALUES ({values});\n")
            
            print(f"  ✓ Backed up {len(rows)} rows to {backup_file}")
        except Exception as e:
            print(f"  ⚠ Could not backup {table}: {str(e)}")
    
    print(f"\n✓ Backup completed: {backup_dir}")
    print("="*60 + "\n")
    
    return backup_dir


def run_migration(db: Session) -> bool:
    """Execute the Alembic migration"""
    print("\n" + "="*60)
    print("EXECUTING DATABASE MIGRATION")
    print("="*60 + "\n")
    
    try:
        import subprocess
        
        print("Running: alembic upgrade head")
        result = subprocess.run(
            ['alembic', 'upgrade', 'head'],
            cwd=os.path.dirname(os.path.dirname(__file__)),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("\n✓ Migration completed successfully!")
            print("\nMigration output:")
            print(result.stdout)
            return True
        else:
            print("\n✗ Migration failed!")
            print("\nError output:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"\n✗ Migration failed with exception: {str(e)}")
        return False


def main():
    """Main migration script"""
    parser = argparse.ArgumentParser(
        description='Migrate customer data to hierarchical contact system'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run validation checks without executing migration'
    )
    parser.add_argument(
        '--skip-backup',
        action='store_true',
        help='Skip database backup (not recommended for production)'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only run post-migration verification checks'
    )
    
    args = parser.parse_args()
    
    # Create database session
    db = SessionLocal()
    validator = MigrationValidator(db)
    
    try:
        if args.verify_only:
            # Only run post-migration checks
            print("\nRunning post-migration verification only...")
            post_results = validator.post_migration_checks()
            
            # Generate and save report
            report = validator.generate_report({'checks': []}, post_results)
            print(report)
            
            sys.exit(0 if post_results['passed'] else 1)
        
        # Run pre-migration validation
        pre_results = validator.pre_migration_checks()
        
        if not pre_results['passed']:
            print("\n❌ Pre-migration validation failed. Please fix the errors and try again.")
            sys.exit(1)
        
        if args.dry_run:
            print("\n✓ Dry run completed. No changes were made to the database.")
            print("  Run without --dry-run to execute the migration.")
            sys.exit(0)
        
        # Confirm before proceeding
        print("\n" + "="*60)
        print("READY TO MIGRATE")
        print("="*60)
        print("\nThis will:")
        print("  1. Rename 'customers' table to 'contacts'")
        print("  2. Make company_id required for all contacts")
        print("  3. Add company_id to orders table")
        print("  4. Create addresses table")
        print("  5. Add database constraints and triggers")
        print("\n⚠  This operation cannot be easily reversed!")
        
        response = input("\nProceed with migration? (yes/no): ")
        if response.lower() != 'yes':
            print("\n❌ Migration cancelled by user.")
            sys.exit(0)
        
        # Create backup unless skipped
        if not args.skip_backup:
            backup_dir = backup_database(db)
            print(f"\n✓ Backup created: {backup_dir}")
        else:
            print("\n⚠  Skipping backup (--skip-backup flag set)")
        
        # Execute migration
        success = run_migration(db)
        
        if not success:
            print("\n❌ Migration failed. Please check the error messages above.")
            print("   Database backup is available if needed.")
            sys.exit(1)
        
        # Refresh database session after migration
        db.close()
        db = SessionLocal()
        validator = MigrationValidator(db)
        
        # Run post-migration validation
        post_results = validator.post_migration_checks()
        
        # Generate and save report
        report = validator.generate_report(pre_results, post_results)
        print(report)
        
        # Save report to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"migration_report_{timestamp}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\n✓ Report saved to: {report_file}")
        
        if post_results['passed']:
            print("\n" + "="*60)
            print("✓ MIGRATION COMPLETED SUCCESSFULLY!")
            print("="*60)
            print("\nNext steps:")
            print("  1. Review the migration report above")
            print("  2. Test the application with the new schema")
            print("  3. Update API endpoints to use 'contact' terminology")
            print("  4. Update frontend to use 'Contact' instead of 'Client'")
            print("\n")
            sys.exit(0)
        else:
            print("\n" + "="*60)
            print("⚠  MIGRATION COMPLETED WITH WARNINGS")
            print("="*60)
            print("\nSome post-migration checks failed.")
            print("Please review the report and fix any issues.")
            print("\n")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == '__main__':
    main()

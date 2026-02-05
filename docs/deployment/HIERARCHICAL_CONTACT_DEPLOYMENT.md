# Hierarchical Contact System Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the hierarchical contact system to staging and production environments.

## Prerequisites

- Access to staging/production database
- Alembic installed and configured
- Database backup completed
- All code changes merged to deployment branch

## Deployment Steps

### Step 1: Database Migration (Task 18.1)

#### 1.1 Backup Database

**CRITICAL**: Always backup the database before running migrations.

```bash
# For PostgreSQL
pg_dump -h <host> -U <user> -d <database> > backup_$(date +%Y%m%d_%H%M%S).sql

# Or use your cloud provider's backup tools
```

#### 1.2 Run Migration on Staging

```bash
# Set environment to staging
export DATABASE_URL="<staging_database_url>"

# Run migration
cd JMSK-Backend
alembic upgrade head

# Verify migration
alembic current
```

#### 1.3 Verify Migration Success

Run these verification queries:

```sql
-- Check that new tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('contacts', 'addresses');

-- Check that orders table has new columns
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'orders' 
AND column_name IN ('contact_id', 'company_id');

-- Check constraints
SELECT constraint_name, constraint_type 
FROM information_schema.table_constraints 
WHERE table_name IN ('contacts', 'addresses', 'orders');

-- Check indexes
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('contacts', 'addresses', 'orders');
```

#### 1.4 Migrate Existing Data

If you have existing customer data, run the migration script:

```bash
# Review the script first
cat scripts/migrate_customers_to_contacts.py

# Run migration (dry-run first)
python scripts/migrate_customers_to_contacts.py --dry-run

# Run actual migration
python scripts/migrate_customers_to_contacts.py

# Verify data migration
python scripts/migrate_customers_to_contacts.py --verify
```

#### 1.5 Run on Production

Only after successful staging deployment:

```bash
# Set environment to production
export DATABASE_URL="<production_database_url>"

# Run migration
alembic upgrade head

# Verify
alembic current

# Run data migration if needed
python scripts/migrate_customers_to_contacts.py
```

### Step 2: Deploy Backend Changes (Task 18.2)

#### 2.1 Deploy Backend Application

Using GitHub Actions (Recommended):

```bash
# Push to deployment branch
git push origin main  # or develop/staging

# Monitor GitHub Actions workflow
# Check: https://github.com/<org>/<repo>/actions
```

Manual deployment (if needed):

```bash
# Build and deploy using SAM
cd JMSK-Backend
sam build
sam deploy --config-env production
```

#### 2.2 Verify Backend Deployment

```bash
# Check API health
curl https://<api-url>/health

# Test new contact endpoints
curl -H "Authorization: Bearer <token>" https://<api-url>/api/v1/contacts

# Test company endpoints
curl -H "Authorization: Bearer <token>" https://<api-url>/api/v1/companies

# Test address endpoints
curl -H "Authorization: Bearer <token>" https://<api-url>/api/v1/companies/1/addresses
```

#### 2.3 Check Logs

```bash
# For AWS Lambda
aws logs tail /aws/lambda/<function-name> --follow

# Check for errors
aws logs filter-pattern /aws/lambda/<function-name> --filter-pattern "ERROR"
```

### Step 3: Deploy Frontend Changes (Task 18.3)

#### 3.1 Build Frontend

```bash
cd JMSK-Frontend

# Install dependencies
npm install

# Build for production
npm run build

# Preview build locally (optional)
npm run preview
```

#### 3.2 Deploy Frontend

Using GitHub Actions (Recommended):

```bash
# Push to deployment branch
git push origin main

# Monitor deployment in GitHub Actions
```

Manual deployment to S3/CloudFront:

```bash
# Deploy to S3
aws s3 sync dist/ s3://<bucket-name>/ --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id <distribution-id> \
  --paths "/*"
```

#### 3.3 Verify Frontend Deployment

1. Open application in browser
2. Check that new pages load:
   - `/contacts` - Contacts list page
   - `/companies` - Companies list page
   - `/contacts/:id` - Contact detail page
   - `/companies/:id` - Company detail page
3. Verify navigation menu shows "Contacts" and "Companies"
4. Test creating a new contact
5. Test creating a new company
6. Test address management

### Step 4: Production Verification (Task 18.4)

#### 4.1 Functional Testing

Test these complete workflows:

1. **Contact Management**
   - Create a new company
   - Add a contact to the company
   - View contact details
   - Update contact information
   - View contact order history

2. **Company Management**
   - View company list with balances
   - View company detail page
   - See all contacts for a company
   - View aggregated orders
   - Add/edit company addresses

3. **Order Creation**
   - Create order with contact selection
   - Verify contact and company are linked
   - Check order appears in contact history
   - Check order appears in company aggregation

4. **Address Management**
   - Add address to company
   - Set default address
   - Create shipment (verify address auto-populates)
   - Modify shipment address

5. **Navigation**
   - Click contact name in order list
   - Navigate to contact detail
   - Navigate to parent company
   - Use breadcrumb navigation

#### 4.2 Multi-Tenant Isolation

Verify tenant isolation:

```bash
# Login as different tenants
# Verify each tenant only sees their own:
# - Companies
# - Contacts
# - Orders
# - Addresses
```

#### 4.3 Performance Monitoring

Monitor these metrics:

- API response times for new endpoints
- Database query performance
- Frontend page load times
- Error rates in logs

#### 4.4 Error Monitoring

Check for errors:

```bash
# Backend errors
aws logs filter-pattern /aws/lambda/<function-name> --filter-pattern "ERROR" --start-time 1h

# Check CloudWatch metrics
# - Lambda errors
# - API Gateway 4xx/5xx errors
# - Database connection errors
```

## Rollback Procedure

If issues are encountered:

### Database Rollback

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision>

# Restore from backup (if needed)
psql -h <host> -U <user> -d <database> < backup_file.sql
```

### Application Rollback

```bash
# Revert to previous deployment
# Using GitHub Actions: redeploy previous commit
# Using SAM: deploy previous version

# For frontend
aws s3 sync <previous-build>/ s3://<bucket-name>/ --delete
aws cloudfront create-invalidation --distribution-id <id> --paths "/*"
```

## Post-Deployment

### 1. Monitor for 24-48 Hours

- Check error logs regularly
- Monitor user feedback
- Track performance metrics
- Watch for database issues

### 2. Gather User Feedback

- Survey users on new interface
- Track feature usage
- Identify pain points
- Document improvement requests

### 3. Update Documentation

- Update API documentation
- Update user guides
- Document any issues encountered
- Share lessons learned

## Troubleshooting

### Migration Fails

```bash
# Check current migration state
alembic current

# Check migration history
alembic history

# View specific migration
alembic show <revision>

# Manually fix and retry
alembic upgrade head
```

### API Endpoints Not Working

1. Check Lambda logs for errors
2. Verify environment variables
3. Check database connectivity
4. Verify IAM permissions
5. Test endpoints with curl

### Frontend Not Loading

1. Check browser console for errors
2. Verify API URL configuration
3. Check CORS settings
4. Clear browser cache
5. Check CloudFront distribution

### Data Migration Issues

1. Check migration script logs
2. Verify data integrity queries
3. Check for orphaned records
4. Verify foreign key relationships
5. Run verification queries

## Support Contacts

- Backend Issues: [Backend Team]
- Frontend Issues: [Frontend Team]
- Database Issues: [Database Team]
- Infrastructure: [DevOps Team]

## Checklist

Use this checklist during deployment:

- [ ] Database backup completed
- [ ] Migration tested on staging
- [ ] Data migration script tested
- [ ] Backend deployed to staging
- [ ] Frontend deployed to staging
- [ ] Staging verification complete
- [ ] Production database backup
- [ ] Production migration executed
- [ ] Production backend deployed
- [ ] Production frontend deployed
- [ ] Functional testing complete
- [ ] Multi-tenant isolation verified
- [ ] Performance monitoring active
- [ ] Error monitoring active
- [ ] User feedback collected
- [ ] Documentation updated

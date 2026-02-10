# AWS GitHub Secrets and Environment Setup for Production

This guide covers setting up GitHub secrets, variables, and AWS environment configuration for automated production deployment.

## Prerequisites

- AWS Account with appropriate permissions
- GitHub repository with Actions enabled
- AWS CLI installed and configured locally
- OIDC provider configured in AWS (see `aws-infrastructure/github-oidc-setup.yaml`)

## GitHub Secrets Setup

### Required Secrets

Navigate to your GitHub repository: **Settings → Secrets and variables → Actions → New repository secret**

**Only AWS credentials are stored in GitHub. All application secrets (database, JWT keys) are stored in AWS Secrets Manager.**

#### AWS Deployment Secrets

```
AWS_ROLE_ARN
```
- **Description**: IAM role ARN for GitHub Actions OIDC authentication
- **Format**: `arn:aws:iam::ACCOUNT_ID:role/GitHubActionsDeploymentRole`
- **How to get**: After deploying OIDC CloudFormation stack, find in stack outputs
- **Example**: `arn:aws:iam::123456789012:role/GitHubActionsDeploymentRole`

```
AWS_REGION
```
- **Description**: AWS region for deployment
- **Value**: `us-east-1` (or your preferred region)

### Setting Secrets via GitHub CLI

```bash
# Install GitHub CLI if not already installed
brew install gh  # macOS
# or download from https://cli.github.com/

# Authenticate
gh auth login

# Set AWS secrets only
gh secret set AWS_ROLE_ARN --body "arn:aws:iam::123456789012:role/GitHubActionsDeploymentRole"
gh secret set AWS_REGION --body "us-east-1"
```

## GitHub Variables Setup

Navigate to: **Settings → Secrets and variables → Actions → Variables tab → New repository variable**

### Required Variables

```
LAMBDA_FUNCTION_NAME_PROD
```
- **Description**: Name of the Lambda function for production
- **Value**: `jmsk-backend-prod`

```
S3_BUCKET_PROD
```
- **Description**: S3 bucket for Lambda deployment packages
- **Value**: `jmsk-lambda-deployments-prod`

```
STACK_NAME_PROD
```
- **Description**: CloudFormation/SAM stack name
- **Value**: `jmsk-backend-stack-prod`

### Optional Variables

```
LOG_LEVEL_PROD
```
- **Description**: Application log level
- **Value**: `INFO` or `WARNING`

```
ACCESS_TOKEN_EXPIRE_MINUTES
```
- **Description**: JWT token expiration time
- **Value**: `30` (default)

## GitHub Environment Setup

### Create Production Environment

1. Navigate to: **Settings → Environments → New environment**
2. Name: `production`
3. Configure protection rules:

#### Protection Rules

**Required reviewers**:
- Add 1-2 team members who must approve production deployments
- Prevents accidental deployments

**Wait timer**:
- Optional: Add 5-10 minute delay before deployment
- Allows time to cancel if needed

**Deployment branches**:
- Select "Selected branches"
- Add rule: `main` (only main branch can deploy to production)

#### Environment Variables

```
ENVIRONMENT
```
- Value: `production`

```
API_BASE_URL
```
- Value: `https://api.yourdomain.com` (your production API URL)

## AWS Secrets Manager Setup

All sensitive application secrets are stored in AWS Secrets Manager and accessed by Lambda at runtime.

### Create Secrets in AWS Secrets Manager

#### 1. Database Connection Secret

```bash
# Create database credentials secret
aws secretsmanager create-secret \
  --name jmsk/prod/database \
  --description "JMSK Production Database Credentials" \
  --secret-string '{
    "username": "jmsk_admin",
    "password": "YourSecurePassword123!",
    "host": "jmsk-prod.abc123.us-east-1.rds.amazonaws.com",
    "port": 5432,
    "dbname": "jmsk_production",
    "engine": "postgres"
  }' \
  --region us-east-1
```

**Alternative: Store as connection string**:
```bash
aws secretsmanager create-secret \
  --name jmsk/prod/database-url \
  --description "JMSK Production Database URL" \
  --secret-string "postgresql://jmsk_admin:YourSecurePassword123!@jmsk-prod.abc123.us-east-1.rds.amazonaws.com:5432/jmsk_production" \
  --region us-east-1
```

#### 2. JWT Secret Key

```bash
# Generate and store JWT secret
aws secretsmanager create-secret \
  --name jmsk/prod/jwt-secret \
  --description "JMSK Production JWT Secret Key" \
  --secret-string "$(openssl rand -hex 32)" \
  --region us-east-1
```

#### 3. Optional Application Secrets

```bash
# Sentry DSN (if using error tracking)
aws secretsmanager create-secret \
  --name jmsk/prod/sentry-dsn \
  --description "Sentry Error Tracking DSN" \
  --secret-string "https://public_key@sentry.io/project_id" \
  --region us-east-1

# API Keys or third-party credentials
aws secretsmanager create-secret \
  --name jmsk/prod/api-keys \
  --description "Third-party API Keys" \
  --secret-string '{
    "stripe_key": "sk_live_...",
    "sendgrid_key": "SG..."
  }' \
  --region us-east-1
```

### Enable Automatic Secret Rotation

```bash
# Enable rotation for database credentials (recommended)
aws secretsmanager rotate-secret \
  --secret-id jmsk/prod/database \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:SecretsManagerRDSRotation \
  --rotation-rules AutomaticallyAfterDays=30
```

### Retrieve Secrets in Lambda

Update your Lambda function to retrieve secrets at runtime:

```python
# app/infrastructure/secrets.py
import json
import boto3
from functools import lru_cache

@lru_cache()
def get_secret(secret_name: str, region: str = "us-east-1") -> dict:
    """Retrieve secret from AWS Secrets Manager with caching."""
    client = boto3.client('secretsmanager', region_name=region)
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        raise Exception(f"Failed to retrieve secret {secret_name}: {str(e)}")

def get_database_url() -> str:
    """Get database connection URL from Secrets Manager."""
    secret = get_secret("jmsk/prod/database-url")
    return secret if isinstance(secret, str) else construct_url(secret)

def construct_url(db_config: dict) -> str:
    """Construct database URL from config dict."""
    return (
        f"postgresql://{db_config['username']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    )

def get_jwt_secret() -> str:
    """Get JWT secret key from Secrets Manager."""
    return get_secret("jmsk/prod/jwt-secret")
```

Update configuration to use Secrets Manager:

```python
# app/infrastructure/config.py
from pydantic_settings import BaseSettings
from .secrets import get_database_url, get_jwt_secret
import os

class Settings(BaseSettings):
    # Use Secrets Manager in production, env vars in development
    @property
    def database_url(self) -> str:
        if os.getenv("ENVIRONMENT") == "production":
            return get_database_url()
        return os.getenv("DATABASE_URL", "sqlite:///./test.db")
    
    @property
    def secret_key(self) -> str:
        if os.getenv("ENVIRONMENT") == "production":
            return get_jwt_secret()
        return os.getenv("SECRET_KEY", "dev-secret-key")
    
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
```

## AWS Environment Setup

### 1. RDS PostgreSQL Database

```bash
# Create RDS instance via AWS Console or CLI
aws rds create-db-instance \
  --db-instance-identifier jmsk-prod \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username jmsk_admin \
  --master-user-password "YourSecurePassword123!" \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-xxxxxxxxx \
  --db-subnet-group-name your-subnet-group \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "mon:04:00-mon:05:00" \
  --storage-encrypted \
  --publicly-accessible false \
  --tags Key=Environment,Value=production Key=Project,Value=JMSK
```

**Important RDS Settings**:
- Enable automated backups (7-30 days retention)
- Enable encryption at rest
- Use private subnets (not publicly accessible)
- Configure security groups to allow Lambda access only
- Enable Performance Insights for monitoring

### 2. Lambda Function Configuration

**Environment Variables** (set in Lambda console or SAM template):

```yaml
Environment:
  Variables:
    # Secrets Manager references (not actual secrets)
    DATABASE_SECRET_NAME: jmsk/prod/database-url
    JWT_SECRET_NAME: jmsk/prod/jwt-secret
    
    # Non-sensitive configuration
    ALGORITHM: HS256
    ACCESS_TOKEN_EXPIRE_MINUTES: 30
    ENVIRONMENT: production
    LOG_LEVEL: INFO
    AWS_REGION: us-east-1
```

**Note**: Lambda retrieves actual secrets from Secrets Manager at runtime, not from environment variables.

**Lambda Settings**:
- Memory: 512 MB (adjust based on load)
- Timeout: 30 seconds
- Reserved concurrency: 10-50 (based on expected traffic)
- VPC: Same VPC as RDS for private connectivity

### 3. API Gateway Configuration

```bash
# Create custom domain (optional but recommended)
aws apigatewayv2 create-domain-name \
  --domain-name api.yourdomain.com \
  --domain-name-configurations CertificateArn=arn:aws:acm:region:account:certificate/xxx
```

**API Gateway Settings**:
- Enable CloudWatch logging
- Set throttling limits (rate: 1000, burst: 2000)
- Enable CORS for frontend domain
- Configure custom domain with SSL certificate

### 4. S3 Bucket for Deployments

```bash
# Create S3 bucket for Lambda deployment packages
aws s3 mb s3://jmsk-lambda-deployments-prod --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket jmsk-lambda-deployments-prod \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket jmsk-lambda-deployments-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

### 5. CloudWatch Alarms

```bash
# Lambda error alarm
aws cloudwatch put-metric-alarm \
  --alarm-name jmsk-lambda-errors-prod \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=FunctionName,Value=jmsk-backend-prod

# RDS CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name jmsk-rds-cpu-prod \
  --alarm-description "Alert on high RDS CPU" \
  --metric-name CPUUtilization \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=DBInstanceIdentifier,Value=jmsk-prod
```

## IAM Roles and Permissions

### GitHub Actions OIDC Role

Deploy the OIDC CloudFormation stack:

```bash
aws cloudformation create-stack \
  --stack-name github-oidc-provider \
  --template-body file://aws-infrastructure/github-oidc-setup.yaml \
  --parameters ParameterKey=GitHubOrg,ParameterValue=your-org \
               ParameterKey=GitHubRepo,ParameterValue=your-repo \
  --capabilities CAPABILITY_IAM
```

**Required Permissions**:
- `lambda:UpdateFunctionCode`
- `lambda:UpdateFunctionConfiguration`
- `lambda:GetFunction`
- `s3:PutObject`
- `s3:GetObject`
- `cloudformation:*` (for SAM deployments)
- `iam:PassRole` (for Lambda execution role)
- `secretsmanager:GetSecretValue` (for deployment-time secret access if needed)

### Lambda Execution Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:*:secret:jmsk/prod/*"
      ]
    }
  ]
}
```

**Critical**: Lambda execution role must have `secretsmanager:GetSecretValue` permission to retrieve secrets at runtime.

## Database Migration Strategy

### Initial Setup

```bash
# Retrieve database URL from Secrets Manager
export DATABASE_URL=$(aws secretsmanager get-secret-value \
  --secret-id jmsk/prod/database-url \
  --query SecretString \
  --output text)

# Run migrations
alembic upgrade head

# Verify
alembic current
```

### Automated Migrations in CI/CD

Add to GitHub Actions workflow:

```yaml
- name: Run Database Migrations
  run: |
    # Retrieve database URL from Secrets Manager
    export DATABASE_URL=$(aws secretsmanager get-secret-value \
      --secret-id jmsk/prod/database-url \
      --query SecretString \
      --output text)
    
    # Install dependencies and run migrations
    pip install alembic psycopg2-binary
    alembic upgrade head
```

**⚠️ Important**: 
- Always test migrations in staging first!
- GitHub Actions workflow must have permission to access Secrets Manager
- Consider using a dedicated migration Lambda or ECS task for production

## Security Checklist

- [ ] Only AWS credentials stored in GitHub Secrets (never application secrets)
- [ ] All application secrets stored in AWS Secrets Manager
- [ ] Lambda execution role has minimal Secrets Manager permissions (specific secret ARNs only)
- [ ] Automatic secret rotation enabled for database credentials
- [ ] RDS in private subnet with security group restrictions
- [ ] Lambda in VPC with access to RDS only
- [ ] SSL/TLS enabled for all connections (RDS, API Gateway)
- [ ] CloudWatch logging enabled for audit trail
- [ ] Secrets Manager access logged in CloudTrail
- [ ] API Gateway throttling configured
- [ ] CORS restricted to frontend domain only
- [ ] Environment protection rules enabled in GitHub
- [ ] MFA required for AWS console access
- [ ] Backup and disaster recovery plan documented
- [ ] Secrets Manager KMS encryption enabled

## Monitoring and Alerts

### CloudWatch Dashboards

Create a production dashboard monitoring:
- Lambda invocations, errors, duration
- RDS CPU, memory, connections
- API Gateway requests, latency, 4xx/5xx errors
- Custom application metrics

### Log Aggregation

```python
# Add structured logging in application
import logging
import json

logger = logging.getLogger(__name__)

def log_event(event_type: str, data: dict):
    logger.info(json.dumps({
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        **data
    }))
```

## Rollback Procedure

### Lambda Rollback

```bash
# List versions
aws lambda list-versions-by-function --function-name jmsk-backend-prod

# Rollback to previous version
aws lambda update-alias \
  --function-name jmsk-backend-prod \
  --name prod \
  --function-version <previous-version>
```

### Database Rollback

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision>
```

## Testing Production Setup

### Smoke Tests

```bash
# Health check
curl https://api.yourdomain.com/health

# Authentication test
curl -X POST https://api.yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.com","password":"admin123"}'

# Database connectivity
curl https://api.yourdomain.com/api/v1/customers \
  -H "Authorization: Bearer <token>"
```

### Load Testing

```bash
# Install Apache Bench
brew install httpd

# Run load test
ab -n 1000 -c 10 https://api.yourdomain.com/health
```

## Cost Optimization

- Use Lambda reserved concurrency to control costs
- Enable RDS auto-scaling for storage
- Set up CloudWatch billing alarms
- Review and delete old Lambda versions
- Use S3 lifecycle policies for deployment artifacts
- Consider Aurora Serverless for variable workloads

## Support and Troubleshooting

### Common Issues

**Issue**: Lambda timeout connecting to RDS
- **Solution**: Ensure Lambda is in same VPC as RDS, check security groups

**Issue**: GitHub Actions deployment fails with permission error
- **Solution**: Verify OIDC role has correct permissions, check trust policy

**Issue**: Database migration fails
- **Solution**: Check DATABASE_URL format, verify network connectivity, review migration logs

### Useful Commands

```bash
# View Lambda logs
aws logs tail /aws/lambda/jmsk-backend-prod --follow

# Check RDS status
aws rds describe-db-instances --db-instance-identifier jmsk-prod

# Retrieve secret from Secrets Manager
aws secretsmanager get-secret-value --secret-id jmsk/prod/database-url

# Test database connection
export DB_URL=$(aws secretsmanager get-secret-value \
  --secret-id jmsk/prod/database-url \
  --query SecretString --output text)
psql "$DB_URL" -c "SELECT version();"

# View CloudFormation stack events
aws cloudformation describe-stack-events --stack-name jmsk-backend-stack-prod

# List all secrets
aws secretsmanager list-secrets --filters Key=name,Values=jmsk/prod/

# Update a secret
aws secretsmanager update-secret \
  --secret-id jmsk/prod/jwt-secret \
  --secret-string "$(openssl rand -hex 32)"
```

## Additional Resources

- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [GitHub Actions OIDC with AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)

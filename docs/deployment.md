# Deployment

## GitHub Actions CI/CD

Push to `main` deploys to production automatically. PRs run tests only.

Workflow: `.github/workflows/deploy-backend.yml`
- Runs tests → builds Lambda package → determines environment → migrates DB → deploys

Manual deploy: Actions tab → Deploy Backend → Run workflow → select branch/environment.

## GitHub Secrets & Variables

### Secrets (Settings → Secrets and variables → Actions → Secrets)

| Secret | Description |
|--------|-------------|
| `AWS_ROLE_ARN` | IAM role ARN for OIDC authentication |
| `AWS_REGION` | AWS region (e.g., `us-east-1`) |

### Variables (Settings → Secrets and variables → Actions → Variables)

| Variable | Description |
|----------|-------------|
| `LAMBDA_FUNCTION_NAME_PROD` | Lambda function name (e.g., `jmsk-backend-prod`) |
| `S3_BUCKET_PROD` | S3 bucket for deployment packages |
| `STACK_NAME_PROD` | CloudFormation/SAM stack name |

## AWS Secrets Manager

Application secrets are stored in AWS Secrets Manager, not GitHub:

```bash
# Database URL
aws secretsmanager create-secret --name jmsk/prod/database-url \
  --secret-string "postgresql://user:pass@host:5432/dbname"

# JWT secret
aws secretsmanager create-secret --name jmsk/prod/jwt-secret \
  --secret-string "$(openssl rand -hex 32)"
```

Lambda retrieves these at runtime via `secretsmanager:GetSecretValue` permission.

## AWS Infrastructure

- OIDC provider: deploy `aws-infrastructure/github-oidc-setup.yaml`
- Lambda: 512MB memory, 30s timeout, in VPC with RDS access
- RDS: PostgreSQL in private subnet, encrypted, automated backups
- API Gateway: throttling enabled, CORS for frontend domain

## Database Migrations

```bash
# Run migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

## Rollback

```bash
# Option 1: Git revert (triggers auto-redeploy)
git revert COMMIT_SHA && git push origin main

# Option 2: Lambda version rollback
aws lambda list-versions-by-function --function-name jmsk-backend-prod
aws lambda update-alias --function-name jmsk-backend-prod --name prod --function-version PREV
```

## Useful Commands

```bash
# View Lambda logs
aws logs tail /aws/lambda/jmsk-backend-prod --follow

# Check RDS status
aws rds describe-db-instances --db-instance-identifier jmsk-prod

# Workflow status
gh run list --workflow="deploy-backend.yml"
```

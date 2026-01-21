# GitHub Actions Workflows

## Status: ACTIVE

Automated CI/CD workflows for the jewelry manufacturing system.

## Available Workflows

### Backend Deployment (`deploy-backend.yml`)
- **Triggers**: Push to main/develop/staging, pull requests, manual dispatch
- **Features**: 
  - Automated testing with pytest
  - SAM-based Lambda deployment
  - OIDC authentication with AWS
  - Environment-specific deployments (dev/staging/prod)
  - Secrets management via AWS Secrets Manager
  - Automatic repository tagging

### Environment Configuration

The workflows support three environments with automatic branch-based deployment:

- **Development (`dev`)**: Triggered by pushes to `develop` branch
- **Staging (`staging`)**: Triggered by pushes to `staging` branch  
- **Production (`prod`)**: Triggered by pushes to `main` branch
- **Manual**: Use workflow dispatch to deploy any branch to any environment

## Required Repository Configuration

### GitHub Repository Variables

Configure these in your repository settings under **Settings > Secrets and variables > Actions > Variables**:

#### AWS OIDC Role ARNs (per environment)
```
AWS_ROLE_ARN_DEV=arn:aws:iam::ACCOUNT:role/github-actions-dev
AWS_ROLE_ARN_STAGING=arn:aws:iam::ACCOUNT:role/github-actions-staging
AWS_ROLE_ARN_PROD=arn:aws:iam::ACCOUNT:role/github-actions-prod
```

#### AWS Secrets Manager Secret Names (per environment)
```
SECRET_NAME_DEV=jewelry-manufacturing-dev
SECRET_NAME_STAGING=jewelry-manufacturing-staging
SECRET_NAME_PROD=jewelry-manufacturing-prod
```

### AWS Infrastructure Prerequisites

Before using these workflows, you must set up:

1. **OIDC Identity Provider**: Use `aws-infrastructure/github-oidc-setup.yaml`
2. **IAM Roles**: Environment-specific roles with deployment permissions
3. **Secrets Manager**: Secrets containing DATABASE_URL, JWT_SECRET_KEY, etc.

See the `aws-infrastructure/` directory for CloudFormation templates.

### AWS Secrets Manager Structure

Each environment secret should contain:
```json
{
  "DATABASE_URL": "postgresql://user:pass@host:5432/db",
  "JWT_SECRET_KEY": "your-jwt-secret-key",
  "CORS_ORIGINS": "https://your-domain.com",
  "ENVIRONMENT": "prod"
}
```

## Usage

### Automatic Deployments
- Push to `main` → deploys to production
- Push to `develop` → deploys to development
- Push to `staging` → deploys to staging
- Pull requests → runs tests only (no deployment)

### Manual Deployments
1. Go to **Actions** tab in GitHub
2. Select **Deploy Backend** workflow
3. Click **Run workflow**
4. Choose environment and branch
5. Click **Run workflow**

### Monitoring Deployments
- View workflow progress in the **Actions** tab
- Check deployment summaries in workflow run details
- Monitor AWS CloudFormation stacks for infrastructure changes
- View Lambda logs via AWS CloudWatch

## Troubleshooting

### Common Issues

1. **OIDC Authentication Failures**
   - Verify IAM role trust policy includes correct GitHub repository
   - Check that role ARN variables are correctly configured

2. **Secrets Manager Access Denied**
   - Ensure IAM role has `secretsmanager:GetSecretValue` permission
   - Verify secret names match the configured variables

3. **SAM Deployment Failures**
   - Check that `samconfig.toml` has environment-specific configurations
   - Verify CloudFormation stack permissions

4. **API Validation Failures**
   - API may take time to become available after deployment
   - Check Lambda function logs in CloudWatch

### Getting Help

- Check workflow logs in the Actions tab
- Review AWS CloudFormation events for deployment issues
- Monitor Lambda function logs in CloudWatch
- Verify AWS IAM permissions and policies

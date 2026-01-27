"""
AWS Lambda handler for FastAPI application using Mangum
Optimized for cold start performance
"""
import os

# Set environment for Lambda
os.environ.setdefault("ENVIRONMENT", "production")

# Import app (lazy loading happens in app.main)
from app.main import app
from mangum import Mangum

# Mangum adapter - lifespan off for faster cold starts
# API Gateway strips the stage prefix before invoking Lambda
handler = Mangum(app, lifespan="off")

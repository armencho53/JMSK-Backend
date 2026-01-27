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
# api_gateway_base_path tells Mangum to strip the stage prefix
stage = os.environ.get("STAGE", "prod")
handler = Mangum(app, lifespan="off", api_gateway_base_path=f"/{stage}")

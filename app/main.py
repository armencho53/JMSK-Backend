import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Lazy imports for faster cold starts
IS_LAMBDA = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
STAGE = os.getenv("STAGE", "prod")

# Minimal FastAPI config for Lambda
# Set root_path for proper OpenAPI URL generation behind API Gateway
root_path = f"/{STAGE}" if IS_LAMBDA else ""
app = FastAPI(
    title="Jewelry Manufacturing API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,  # Disable ReDoc to reduce bundle size
    openapi_url="/openapi.json",
    swagger_ui_oauth2_redirect_url=None,  # Disable OAuth2 redirect for docs
    root_path=root_path,
    lifespan=None,  # Disable lifespan for faster Lambda startup
)

# Custom CORS middleware to ensure headers are always present
# This is critical for Lambda/API Gateway where standard CORSMiddleware
# may not cover all edge cases (e.g., unhandled exceptions, streaming responses)
class CORSHeaderMiddleware(BaseHTTPMiddleware):
    CORS_HEADERS = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Max-Age": "3600",
    }

    async def dispatch(self, request: Request, call_next):
        # Handle preflight OPTIONS requests directly
        if request.method == "OPTIONS":
            return JSONResponse(content={}, headers=self.CORS_HEADERS)
        
        # Process the request and add CORS headers
        response = await call_next(request)
        for key, value in self.CORS_HEADERS.items():
            response.headers[key] = value
        return response

# Single CORS middleware — handles both preflight and actual requests
app.add_middleware(CORSHeaderMiddleware)

# Using new layered architecture router
from app.presentation.api.v1.router import api_router
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "lambda": IS_LAMBDA}

@app.get("/health/db")
def health_check_db():
    """Check database connectivity"""
    from app.data.database import SessionLocal
    from sqlalchemy import text
    try:
        db = SessionLocal()
        # Simple query to test connection
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

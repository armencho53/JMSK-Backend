import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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
class CORSHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Handle preflight OPTIONS requests
        if request.method == "OPTIONS":
            return JSONResponse(
                content={},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Max-Age": "3600",
                }
            )
        
        # Process the request
        response = await call_next(request)
        
        # Add CORS headers to all responses
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "3600"
        
        return response

# Add custom CORS middleware first
app.add_middleware(CORSHeaderMiddleware)

# Add standard CORS middleware as backup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# Load routes at module level (required for Lambda with lifespan="off")
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

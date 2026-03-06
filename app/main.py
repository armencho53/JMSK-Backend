import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

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
    redirect_slashes=True,  # Default behavior — frontend uses trailing slashes to avoid redirects
)

# Standard CORS middleware — handles preflight and adds headers to all responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)


# Global exception handler to ensure CORS headers on unhandled errors
# Only catches non-HTTP exceptions (HTTPException is handled by FastAPI's built-in handler)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        # Let FastAPI's default handler deal with HTTPExceptions
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
                **(exc.headers or {}),
            },
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
        },
    )


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

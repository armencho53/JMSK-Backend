import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Lazy imports for faster cold starts
IS_LAMBDA = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None

# Minimal FastAPI config for Lambda
app = FastAPI(
    title="Jewelry Manufacturing API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,  # Disable ReDoc to reduce bundle size
    openapi_url="/openapi.json",
)

# Optimized CORS - minimal overhead
allowed_origins = ["*"] if IS_LAMBDA else ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,  # Cache preflight requests
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

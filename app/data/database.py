import os
from sqlalchemy import create_engine, pool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.infrastructure.config import settings

# Lambda-optimized database configuration
IS_LAMBDA = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None

def clean_database_url(url: str) -> str:
    """
    Clean database URL by removing unsupported query parameters.
    Some database providers (Supabase, Neon) add parameters like ?pgbouncer=true
    that SQLAlchemy doesn't recognize.
    """
    if "?" in url:
        base_url, params = url.split("?", 1)
        # Parse parameters
        param_pairs = params.split("&")
        # Filter out unsupported parameters
        supported_params = []
        unsupported = ["pgbouncer", "supa"]  # Add more if needed
        
        for param in param_pairs:
            param_name = param.split("=")[0]
            if param_name not in unsupported:
                supported_params.append(param)
        
        # Reconstruct URL
        if supported_params:
            return f"{base_url}?{'&'.join(supported_params)}"
        return base_url
    return url

# Clean the database URL
database_url = clean_database_url(settings.DATABASE_URL)

# Use psycopg (v3) driver for PostgreSQL — handles Neon + SSL natively
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

# Detect database type
is_sqlite = database_url.startswith("sqlite")

# Use NullPool for Lambda to avoid connection pooling issues
# Lambda containers are reused, but connections should be short-lived
engine_config = {
    "echo": False,          # Disable SQL logging in production
}

# SQLite doesn't support connection pooling parameters
if not is_sqlite:
    engine_config["pool_pre_ping"] = True  # Verify connections before using
    engine_config["pool_recycle"] = 3600   # Recycle connections after 1 hour

if IS_LAMBDA:
    # NullPool: No connection pooling, create new connection per request
    # This prevents connection exhaustion in Lambda
    engine_config["poolclass"] = pool.NullPool
elif not is_sqlite:
    # Local development with PostgreSQL: Use connection pooling
    engine_config["pool_size"] = 5
    engine_config["max_overflow"] = 10
else:
    # SQLite in tests: Use StaticPool for in-memory databases
    if ":memory:" in database_url:
        engine_config["poolclass"] = pool.StaticPool
        engine_config["connect_args"] = {"check_same_thread": False}

engine = create_engine(database_url, **engine_config)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Database session dependency with automatic cleanup"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

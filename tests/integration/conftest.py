"""
Pytest configuration for integration tests.

Integration tests use the actual DATABASE_URL from environment variables
to test against real PostgreSQL databases (dev/prod).

These tests are SKIPPED locally unless DATABASE_URL points to PostgreSQL.
"""

import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.data.database import get_db, Base
from app.infrastructure.config import settings


def is_postgresql_url(url):
    """Check if the database URL is PostgreSQL."""
    if not url:
        return False
    return url.startswith("postgresql://") or url.startswith("postgresql+psycopg")


@pytest.fixture(scope="session")
def integration_db_engine():
    """
    Create a database engine for integration tests.
    Uses the actual DATABASE_URL from environment.
    
    SKIPS if DATABASE_URL is not set or not PostgreSQL.
    """
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        pytest.skip("DATABASE_URL not set - skipping integration tests")
    
    if not is_postgresql_url(database_url):
        pytest.skip("DATABASE_URL is not PostgreSQL - integration tests require PostgreSQL")
    
    # Handle PostgreSQL URL format
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql+psycopg2://"):
        database_url = database_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    
    engine = create_engine(database_url)
    
    # Verify connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.skip(f"Cannot connect to database: {e}")
    
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def integration_db_session(integration_db_engine):
    """
    Create a database session for each integration test.
    Uses transactions that are rolled back after each test.
    """
    connection = integration_db_engine.connect()
    transaction = connection.begin()
    
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def integration_client(integration_db_session):
    """
    Create a test client with real database dependency override.
    """
    def override_get_db():
        try:
            yield integration_db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

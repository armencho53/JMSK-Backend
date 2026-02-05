"""Pytest configuration and fixtures for backend tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.data.database import get_db, Base
from app.infrastructure.config import settings


# Test database URL - use in-memory SQLite for fast tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(db_session):
    """Alias for db_session to match common naming convention."""
    return db_session


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_tenant_data():
    """Sample tenant data for testing."""
    return {
        "name": "Test Jewelry Co",
        "email": "admin@testjewelry.com",
        "phone": "+1234567890"
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "testuser@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
        "is_active": True
    }


@pytest.fixture
def sample_tenant(db_session):
    """Create a sample tenant for testing."""
    from app.data.models.tenant import Tenant
    tenant = Tenant(
        name="Test Tenant",
        subdomain="test-tenant",
        is_active=True
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def other_tenant(db_session):
    """Create another tenant for multi-tenant isolation testing."""
    from app.data.models.tenant import Tenant
    tenant = Tenant(
        name="Other Tenant",
        subdomain="other-tenant",
        is_active=True
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant
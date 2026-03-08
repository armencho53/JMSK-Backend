"""Unit tests for MetalPriceRepository."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.data.database import Base
from app.data.models.metal_price import MetalPrice
from app.data.repositories.metal_price_repository import MetalPriceRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def repo(db_session):
    return MetalPriceRepository(db_session)


class TestGetCurrentPrice:
    def test_returns_none_when_not_exists(self, repo):
        assert repo.get_current_price("GOLD") is None

    def test_returns_existing_price(self, repo, db_session):
        db_session.add(MetalPrice(
            metal_category="GOLD", price_per_gram=65.50,
            fetched_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=15),
        ))
        db_session.commit()
        result = repo.get_current_price("GOLD")
        assert result.price_per_gram == 65.50

    def test_case_sensitive(self, repo, db_session):
        db_session.add(MetalPrice(
            metal_category="GOLD", price_per_gram=65.50,
            fetched_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=15),
        ))
        db_session.commit()
        assert repo.get_current_price("gold") is None


class TestSavePrice:
    def test_creates_new(self, repo):
        result = repo.save_price("GOLD", 65.50, ttl_minutes=15)
        assert result.metal_category == "GOLD"
        assert result.price_per_gram == 65.50

    def test_updates_existing(self, repo, db_session):
        db_session.add(MetalPrice(
            metal_category="PLATINUM", price_per_gram=30.00,
            fetched_at=datetime.utcnow() - timedelta(hours=1),
            expires_at=datetime.utcnow() - timedelta(minutes=30),
        ))
        db_session.commit()
        initial_id = db_session.query(MetalPrice).first().id

        updated = repo.save_price("PLATINUM", 32.50, ttl_minutes=15)
        assert updated.id == initial_id
        assert updated.price_per_gram == 32.50

    def test_multiple_categories(self, repo):
        gold = repo.save_price("GOLD", 65.50)
        silver = repo.save_price("SILVER", 0.85)
        assert gold.id != silver.id


class TestIsExpired:
    def test_not_expired(self, repo):
        price = MetalPrice(
            metal_category="GOLD", price_per_gram=65.50,
            fetched_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=15),
        )
        assert repo.is_expired(price) is False

    def test_expired(self, repo):
        price = MetalPrice(
            metal_category="GOLD", price_per_gram=65.50,
            fetched_at=datetime.utcnow() - timedelta(hours=1),
            expires_at=datetime.utcnow() - timedelta(minutes=30),
        )
        assert repo.is_expired(price) is True

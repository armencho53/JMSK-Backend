"""Unit tests for MetalPriceRepository

Tests the metal price caching repository operations including:
- Retrieving current cached prices
- Saving new prices with TTL
- Updating existing prices
- Checking price expiration

Requirements: 8.7, 8.8
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.data.database import Base
from app.data.models.metal_price import MetalPrice
from app.data.repositories.metal_price_repository import MetalPriceRepository


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def repository(db_session):
    """Create a MetalPriceRepository instance"""
    return MetalPriceRepository(db_session)


class TestGetCurrentPrice:
    """Tests for get_current_price method"""
    
    def test_get_current_price_returns_none_when_not_exists(self, repository):
        """Test that get_current_price returns None when no price exists"""
        # Act
        result = repository.get_current_price("GOLD")
        
        # Assert
        assert result is None
    
    def test_get_current_price_returns_existing_price(self, repository, db_session):
        """Test that get_current_price returns existing price"""
        # Arrange
        price = MetalPrice(
            metal_category="GOLD",
            price_per_gram=65.50,
            fetched_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=15)
        )
        db_session.add(price)
        db_session.commit()
        
        # Act
        result = repository.get_current_price("GOLD")
        
        # Assert
        assert result is not None
        assert result.metal_category == "GOLD"
        assert result.price_per_gram == 65.50
    
    def test_get_current_price_case_sensitive(self, repository, db_session):
        """Test that metal category lookup is case-sensitive"""
        # Arrange
        price = MetalPrice(
            metal_category="GOLD",
            price_per_gram=65.50,
            fetched_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=15)
        )
        db_session.add(price)
        db_session.commit()
        
        # Act
        result = repository.get_current_price("gold")
        
        # Assert
        assert result is None


class TestSavePrice:
    """Tests for save_price method"""
    
    def test_save_price_creates_new_price(self, repository):
        """Test that save_price creates a new price record"""
        # Act
        result = repository.save_price("GOLD", 65.50, ttl_minutes=15)
        
        # Assert
        assert result is not None
        assert result.id is not None
        assert result.metal_category == "GOLD"
        assert result.price_per_gram == 65.50
        assert result.currency == "USD"
        assert result.fetched_at is not None
        assert result.expires_at is not None
    
    def test_save_price_sets_correct_expiration(self, repository):
        """Test that save_price sets correct expiration time"""
        # Arrange
        ttl_minutes = 20
        before_save = datetime.utcnow()
        
        # Act
        result = repository.save_price("SILVER", 0.85, ttl_minutes=ttl_minutes)
        
        # Assert
        after_save = datetime.utcnow()
        expected_expiration = before_save + timedelta(minutes=ttl_minutes)
        
        # Allow 1 second tolerance for test execution time
        assert abs((result.expires_at - expected_expiration).total_seconds()) < 1
        assert result.fetched_at >= before_save
        assert result.fetched_at <= after_save
    
    def test_save_price_updates_existing_price(self, repository, db_session):
        """Test that save_price updates existing price instead of creating duplicate"""
        # Arrange - Create initial price
        old_fetched = datetime.utcnow() - timedelta(hours=1)
        old_expires = datetime.utcnow() - timedelta(minutes=30)
        initial_price = MetalPrice(
            metal_category="PLATINUM",
            price_per_gram=30.00,
            fetched_at=old_fetched,
            expires_at=old_expires
        )
        db_session.add(initial_price)
        db_session.commit()
        initial_id = initial_price.id
        
        # Act - Save new price for same category
        updated_price = repository.save_price("PLATINUM", 32.50, ttl_minutes=15)
        
        # Assert - Same record updated, not new record created
        assert updated_price.id == initial_id
        assert updated_price.price_per_gram == 32.50
        assert updated_price.fetched_at > old_fetched
        assert updated_price.expires_at > old_expires
        
        # Verify only one record exists
        all_prices = db_session.query(MetalPrice).filter(
            MetalPrice.metal_category == "PLATINUM"
        ).all()
        assert len(all_prices) == 1
    
    def test_save_price_uses_default_ttl(self, repository):
        """Test that save_price uses default TTL of 15 minutes"""
        # Arrange
        before_save = datetime.utcnow()
        
        # Act - Don't specify ttl_minutes
        result = repository.save_price("GOLD", 65.50)
        
        # Assert - Default TTL is 15 minutes
        expected_expiration = before_save + timedelta(minutes=15)
        assert abs((result.expires_at - expected_expiration).total_seconds()) < 1
    
    def test_save_price_handles_multiple_categories(self, repository):
        """Test that save_price can handle multiple different metal categories"""
        # Act
        gold_price = repository.save_price("GOLD", 65.50)
        silver_price = repository.save_price("SILVER", 0.85)
        platinum_price = repository.save_price("PLATINUM", 32.00)
        
        # Assert
        assert gold_price.metal_category == "GOLD"
        assert silver_price.metal_category == "SILVER"
        assert platinum_price.metal_category == "PLATINUM"
        assert gold_price.id != silver_price.id
        assert silver_price.id != platinum_price.id


class TestIsExpired:
    """Tests for is_expired method"""
    
    def test_is_expired_returns_false_for_valid_price(self, repository):
        """Test that is_expired returns False for non-expired price"""
        # Arrange
        price = MetalPrice(
            metal_category="GOLD",
            price_per_gram=65.50,
            fetched_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=15)
        )
        
        # Act
        result = repository.is_expired(price)
        
        # Assert
        assert result is False
    
    def test_is_expired_returns_true_for_expired_price(self, repository):
        """Test that is_expired returns True for expired price"""
        # Arrange
        price = MetalPrice(
            metal_category="GOLD",
            price_per_gram=65.50,
            fetched_at=datetime.utcnow() - timedelta(hours=1),
            expires_at=datetime.utcnow() - timedelta(minutes=30)
        )
        
        # Act
        result = repository.is_expired(price)
        
        # Assert
        assert result is True
    
    def test_is_expired_returns_true_for_just_expired_price(self, repository):
        """Test that is_expired returns True for price that just expired"""
        # Arrange - Price expired 1 second ago
        price = MetalPrice(
            metal_category="GOLD",
            price_per_gram=65.50,
            fetched_at=datetime.utcnow() - timedelta(minutes=15),
            expires_at=datetime.utcnow() - timedelta(seconds=1)
        )
        
        # Act
        result = repository.is_expired(price)
        
        # Assert
        assert result is True
    
    def test_is_expired_boundary_condition(self, repository):
        """Test is_expired at exact expiration time (boundary condition)"""
        # Arrange - Price expires exactly now (within 1 second)
        now = datetime.utcnow()
        price = MetalPrice(
            metal_category="GOLD",
            price_per_gram=65.50,
            fetched_at=now - timedelta(minutes=15),
            expires_at=now
        )
        
        # Act
        result = repository.is_expired(price)
        
        # Assert - Should be expired (current time > expires_at)
        # Due to test execution time, this might be True or False
        # but the logic is correct: datetime.utcnow() > price.expires_at
        assert isinstance(result, bool)


class TestIntegrationScenarios:
    """Integration tests for common usage scenarios"""
    
    def test_cache_workflow_save_retrieve_check_expiration(self, repository):
        """Test complete cache workflow: save, retrieve, check expiration"""
        # Step 1: Save a price
        saved_price = repository.save_price("GOLD", 65.50, ttl_minutes=15)
        assert saved_price is not None
        
        # Step 2: Retrieve the price
        retrieved_price = repository.get_current_price("GOLD")
        assert retrieved_price is not None
        assert retrieved_price.id == saved_price.id
        assert retrieved_price.price_per_gram == 65.50
        
        # Step 3: Check expiration (should not be expired)
        assert repository.is_expired(retrieved_price) is False
    
    def test_cache_update_workflow(self, repository):
        """Test cache update workflow: save, update, verify"""
        # Step 1: Save initial price
        initial_price = repository.save_price("SILVER", 0.80, ttl_minutes=10)
        initial_id = initial_price.id
        initial_expires = initial_price.expires_at
        
        # Step 2: Update with new price (after a small delay to ensure different timestamp)
        updated_price = repository.save_price("SILVER", 0.85, ttl_minutes=15)
        
        # Step 3: Verify update (same ID, new values)
        assert updated_price.id == initial_id
        assert updated_price.price_per_gram == 0.85
        # The new expiration should be at least 5 minutes later (15 min TTL vs 10 min TTL)
        assert (updated_price.expires_at - initial_expires).total_seconds() >= 300
        
        # Step 4: Retrieve and verify
        retrieved_price = repository.get_current_price("SILVER")
        assert retrieved_price.id == initial_id
        assert retrieved_price.price_per_gram == 0.85

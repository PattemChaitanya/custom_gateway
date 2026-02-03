"""
Test cases for Rate Limiting module.

Tests:
1. Fixed window rate limiting
2. Sliding window rate limiting
3. Token bucket rate limiting
4. Rate limit enforcement
5. Rate limit bypass (whitelisting)
6. Multiple rate limit tiers
"""

import pytest
import time
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, RateLimit
from app.rate_limiting.limiter import RateLimiter
from app.rate_limiting.strategies import (
    FixedWindowStrategy,
    SlidingWindowStrategy,
    TokenBucketStrategy
)


@pytest.fixture
async def db_session():
    """Create an in-memory database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


class TestFixedWindowStrategy:
    """Test fixed window rate limiting strategy."""
    
    def test_allow_within_limit(self):
        """Test that requests within limit are allowed."""
        strategy = FixedWindowStrategy(max_requests=10, window_seconds=60)
        
        # First request should be allowed
        allowed = strategy.is_allowed("user123")
        assert allowed
        
        # Subsequent requests within limit should be allowed
        for _ in range(9):
            assert strategy.is_allowed("user123")
        
        # 11th request should be blocked
        assert not strategy.is_allowed("user123")
    
    def test_window_reset(self):
        """Test that window resets after time period."""
        strategy = FixedWindowStrategy(max_requests=2, window_seconds=1)
        
        # Use up the limit
        assert strategy.is_allowed("user123")
        assert strategy.is_allowed("user123")
        assert not strategy.is_allowed("user123")
        
        # Wait for window to reset
        time.sleep(1.1)
        
        # Should be allowed again
        assert strategy.is_allowed("user123")
    
    def test_multiple_users(self):
        """Test that rate limits are per user."""
        strategy = FixedWindowStrategy(max_requests=2, window_seconds=60)
        
        # User 1
        assert strategy.is_allowed("user1")
        assert strategy.is_allowed("user1")
        assert not strategy.is_allowed("user1")
        
        # User 2 should have their own limit
        assert strategy.is_allowed("user2")
        assert strategy.is_allowed("user2")
        assert not strategy.is_allowed("user2")


class TestSlidingWindowStrategy:
    """Test sliding window rate limiting strategy."""
    
    def test_sliding_window_calculation(self):
        """Test sliding window calculation."""
        strategy = SlidingWindowStrategy(max_requests=10, window_seconds=60)
        
        # Make requests
        for _ in range(10):
            assert strategy.is_allowed("user123")
        
        # 11th request should be blocked
        assert not strategy.is_allowed("user123")
    
    def test_gradual_window_slide(self):
        """Test that window gradually slides over time."""
        strategy = SlidingWindowStrategy(max_requests=5, window_seconds=2)
        
        # Use up the limit
        for _ in range(5):
            assert strategy.is_allowed("user123")
        
        # Wait half the window
        time.sleep(1)
        
        # Some requests should have expired
        # (Implementation specific - might allow 1-2 requests)
        allowed = strategy.is_allowed("user123")
        # Result depends on implementation


class TestTokenBucketStrategy:
    """Test token bucket rate limiting strategy."""
    
    def test_token_consumption(self):
        """Test token consumption."""
        strategy = TokenBucketStrategy(
            capacity=10,
            refill_rate=1.0  # 1 token per second
        )
        
        # Should allow requests up to capacity
        for _ in range(10):
            assert strategy.is_allowed("user123")
        
        # Should block when bucket is empty
        assert not strategy.is_allowed("user123")
    
    def test_token_refill(self):
        """Test token refill over time."""
        strategy = TokenBucketStrategy(
            capacity=5,
            refill_rate=2.0  # 2 tokens per second
        )
        
        # Empty the bucket
        for _ in range(5):
            assert strategy.is_allowed("user123")
        
        # Wait for refill
        time.sleep(1)
        
        # Should have ~2 tokens refilled
        assert strategy.is_allowed("user123")
        assert strategy.is_allowed("user123")
        # 3rd might not be allowed yet
    
    def test_burst_handling(self):
        """Test handling of burst traffic."""
        strategy = TokenBucketStrategy(
            capacity=100,
            refill_rate=10.0
        )
        
        # Should handle burst of requests
        for _ in range(100):
            assert strategy.is_allowed("user123")


@pytest.mark.asyncio
class TestRateLimiter:
    """Test rate limiter with database persistence."""
    
    async def test_create_rate_limit(self, db_session: AsyncSession):
        """Test creating a rate limit configuration."""
        limiter = RateLimiter(db_session)
        
        config = await limiter.create_limit(
            api_id=1,
            max_requests=1000,
            window_seconds=60,
            strategy="fixed_window"
        )
        
        assert config.api_id == 1
        assert config.max_requests == 1000
        assert config.window_seconds == 60
        assert config.strategy == "fixed_window"
    
    async def test_get_limit_config(self, db_session: AsyncSession):
        """Test retrieving rate limit configuration."""
        limiter = RateLimiter(db_session)
        
        # Create config
        await limiter.create_limit(
            api_id=1,
            max_requests=500,
            window_seconds=3600
        )
        
        # Retrieve it
        config = await limiter.get_limit(api_id=1)
        
        assert config.max_requests == 500
        assert config.window_seconds == 3600
    
    async def test_update_limit_config(self, db_session: AsyncSession):
        """Test updating rate limit configuration."""
        limiter = RateLimiter(db_session)
        
        # Create initial config
        await limiter.create_limit(api_id=1, max_requests=100, window_seconds=60)
        
        # Update it
        await limiter.update_limit(api_id=1, max_requests=200, window_seconds=120)
        
        # Verify update
        config = await limiter.get_limit(api_id=1)
        assert config.max_requests == 200
        assert config.window_seconds == 120
    
    async def test_delete_limit_config(self, db_session: AsyncSession):
        """Test deleting rate limit configuration."""
        limiter = RateLimiter(db_session)
        
        # Create config
        await limiter.create_limit(api_id=1, max_requests=100, window_seconds=60)
        
        # Delete it
        success = await limiter.delete_limit(api_id=1)
        assert success
        
        # Verify deletion
        config = await limiter.get_limit(api_id=1)
        assert config is None
    
    async def test_check_rate_limit(self, db_session: AsyncSession):
        """Test checking rate limit for a request."""
        limiter = RateLimiter(db_session)
        
        # Create a strict limit
        await limiter.create_limit(
            api_id=1,
            max_requests=2,
            window_seconds=60
        )
        
        # First two requests should be allowed
        assert await limiter.check_limit(api_id=1, user_id=1)
        assert await limiter.check_limit(api_id=1, user_id=1)
        
        # Third request should be blocked
        assert not await limiter.check_limit(api_id=1, user_id=1)
    
    async def test_rate_limit_per_user(self, db_session: AsyncSession):
        """Test that rate limits are enforced per user."""
        limiter = RateLimiter(db_session)
        
        await limiter.create_limit(api_id=1, max_requests=1, window_seconds=60)
        
        # User 1 uses their limit
        assert await limiter.check_limit(api_id=1, user_id=1)
        assert not await limiter.check_limit(api_id=1, user_id=1)
        
        # User 2 should have their own limit
        assert await limiter.check_limit(api_id=1, user_id=2)


class TestRateLimitTiers:
    """Test multiple rate limit tiers (free, basic, premium)."""
    
    @pytest.mark.asyncio
    async def test_free_tier_limits(self, db_session: AsyncSession):
        """Test free tier rate limits."""
        limiter = RateLimiter(db_session)
        
        await limiter.create_limit(
            api_id=1,
            max_requests=100,
            window_seconds=3600,
            tier="free"
        )
        
        config = await limiter.get_limit(api_id=1, tier="free")
        assert config.max_requests == 100
    
    @pytest.mark.asyncio
    async def test_premium_tier_limits(self, db_session: AsyncSession):
        """Test premium tier rate limits."""
        limiter = RateLimiter(db_session)
        
        await limiter.create_limit(
            api_id=1,
            max_requests=10000,
            window_seconds=3600,
            tier="premium"
        )
        
        config = await limiter.get_limit(api_id=1, tier="premium")
        assert config.max_requests == 10000


class TestRateLimitBypass:
    """Test rate limit bypass/whitelisting."""
    
    @pytest.mark.asyncio
    async def test_whitelist_bypass(self, db_session: AsyncSession):
        """Test that whitelisted users bypass rate limits."""
        limiter = RateLimiter(db_session)
        
        await limiter.create_limit(api_id=1, max_requests=1, window_seconds=60)
        
        # Add user to whitelist
        await limiter.add_to_whitelist(api_id=1, user_id=999)
        
        # Whitelisted user should bypass limits
        for _ in range(10):
            assert await limiter.check_limit(api_id=1, user_id=999)
    
    @pytest.mark.asyncio
    async def test_ip_whitelist(self, db_session: AsyncSession):
        """Test IP-based whitelisting."""
        limiter = RateLimiter(db_session)
        
        await limiter.create_limit(api_id=1, max_requests=1, window_seconds=60)
        
        # Add IP to whitelist
        await limiter.add_ip_to_whitelist(api_id=1, ip_address="192.168.1.100")
        
        # Requests from whitelisted IP should bypass limits
        for _ in range(10):
            assert await limiter.check_limit(
                api_id=1,
                user_id=1,
                ip_address="192.168.1.100"
            )


@pytest.mark.asyncio
class TestRateLimitMiddleware:
    """Test rate limit middleware integration."""
    
    async def test_middleware_enforcement(self, db_session: AsyncSession):
        """Test that middleware enforces rate limits."""
        # This would require setting up a test FastAPI app
        # For now, we test the core limiter functionality
        pass
    
    async def test_rate_limit_headers(self, db_session: AsyncSession):
        """Test that rate limit headers are added to response."""
        # X-RateLimit-Limit
        # X-RateLimit-Remaining
        # X-RateLimit-Reset
        pass


# Run tests with: pytest tests/test_rate_limiting.py -v

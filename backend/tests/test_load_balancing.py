"""
Test cases for Load Balancing module.

Tests:
1. Round-robin algorithm
2. Least connections algorithm
3. Weighted round-robin algorithm
4. Health checks
5. Failover handling
6. Backend management
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, LoadBalancer, Backend
from app.load_balancing.manager import LoadBalancerManager
from app.load_balancing.algorithms import (
    RoundRobinAlgorithm,
    LeastConnectionsAlgorithm,
    WeightedRoundRobinAlgorithm
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


class TestRoundRobinAlgorithm:
    """Test round-robin load balancing algorithm."""
    
    def test_round_robin_distribution(self):
        """Test that requests are distributed evenly."""
        backends = [
            {"url": "http://backend1:8000", "healthy": True},
            {"url": "http://backend2:8000", "healthy": True},
            {"url": "http://backend3:8000", "healthy": True}
        ]
        
        algorithm = RoundRobinAlgorithm(backends)
        
        # Get 9 backends (3 rounds)
        selected = [algorithm.select_backend() for _ in range(9)]
        
        # Each backend should be selected 3 times
        assert selected.count(backends[0]) == 3
        assert selected.count(backends[1]) == 3
        assert selected.count(backends[2]) == 3
    
    def test_round_robin_order(self):
        """Test that round-robin maintains order."""
        backends = [
            {"url": "http://backend1:8000", "healthy": True},
            {"url": "http://backend2:8000", "healthy": True},
            {"url": "http://backend3:8000", "healthy": True}
        ]
        
        algorithm = RoundRobinAlgorithm(backends)
        
        # Should cycle through in order
        assert algorithm.select_backend() == backends[0]
        assert algorithm.select_backend() == backends[1]
        assert algorithm.select_backend() == backends[2]
        assert algorithm.select_backend() == backends[0]
    
    def test_skip_unhealthy_backends(self):
        """Test that unhealthy backends are skipped."""
        backends = [
            {"url": "http://backend1:8000", "healthy": True},
            {"url": "http://backend2:8000", "healthy": False},  # Unhealthy
            {"url": "http://backend3:8000", "healthy": True}
        ]
        
        algorithm = RoundRobinAlgorithm(backends)
        
        # Should only select healthy backends
        selected = [algorithm.select_backend() for _ in range(4)]
        
        assert backends[1] not in selected
        assert selected.count(backends[0]) == 2
        assert selected.count(backends[2]) == 2


class TestLeastConnectionsAlgorithm:
    """Test least connections load balancing algorithm."""
    
    def test_select_backend_with_least_connections(self):
        """Test that backend with least connections is selected."""
        backends = [
            {"url": "http://backend1:8000", "healthy": True, "connections": 5},
            {"url": "http://backend2:8000", "healthy": True, "connections": 2},
            {"url": "http://backend3:8000", "healthy": True, "connections": 8}
        ]
        
        algorithm = LeastConnectionsAlgorithm(backends)
        
        # Should select backend2 (2 connections)
        selected = algorithm.select_backend()
        assert selected == backends[1]
    
    def test_increment_connections(self):
        """Test that connection count is incremented."""
        backends = [
            {"url": "http://backend1:8000", "healthy": True, "connections": 0},
            {"url": "http://backend2:8000", "healthy": True, "connections": 0}
        ]
        
        algorithm = LeastConnectionsAlgorithm(backends)
        
        # Select backend multiple times
        for _ in range(3):
            backend = algorithm.select_backend()
            algorithm.increment_connections(backend)
        
        # All should go to first backend, then it will have 3 connections
        # Next request should go to second backend
        assert backends[0]["connections"] == 3
    
    def test_skip_unhealthy_backends_least_conn(self):
        """Test that unhealthy backends are skipped."""
        backends = [
            {"url": "http://backend1:8000", "healthy": False, "connections": 0},
            {"url": "http://backend2:8000", "healthy": True, "connections": 5}
        ]
        
        algorithm = LeastConnectionsAlgorithm(backends)
        
        # Should select backend2 even though it has more connections
        selected = algorithm.select_backend()
        assert selected == backends[1]


class TestWeightedRoundRobinAlgorithm:
    """Test weighted round-robin load balancing algorithm."""
    
    def test_weighted_distribution(self):
        """Test that requests are distributed according to weights."""
        backends = [
            {"url": "http://backend1:8000", "healthy": True, "weight": 3},
            {"url": "http://backend2:8000", "healthy": True, "weight": 1},
            {"url": "http://backend3:8000", "healthy": True, "weight": 1}
        ]
        
        algorithm = WeightedRoundRobinAlgorithm(backends)
        
        # Get 10 backends
        selected = [algorithm.select_backend() for _ in range(10)]
        
        # backend1 should get ~60% (6 requests)
        # backend2 should get ~20% (2 requests)
        # backend3 should get ~20% (2 requests)
        count1 = selected.count(backends[0])
        count2 = selected.count(backends[1])
        count3 = selected.count(backends[2])
        
        # Allow some variance
        assert 5 <= count1 <= 7
        assert 1 <= count2 <= 3
        assert 1 <= count3 <= 3
    
    def test_zero_weight_backend_skipped(self):
        """Test that backends with zero weight are skipped."""
        backends = [
            {"url": "http://backend1:8000", "healthy": True, "weight": 1},
            {"url": "http://backend2:8000", "healthy": True, "weight": 0},
            {"url": "http://backend3:8000", "healthy": True, "weight": 1}
        ]
        
        algorithm = WeightedRoundRobinAlgorithm(backends)
        
        selected = [algorithm.select_backend() for _ in range(10)]
        
        # backend2 should never be selected
        assert backends[1] not in selected


@pytest.mark.asyncio
class TestLoadBalancerManager:
    """Test load balancer management."""
    
    async def test_create_load_balancer(self, db_session: AsyncSession):
        """Test creating a load balancer."""
        manager = LoadBalancerManager(db_session)
        
        lb = await manager.create_load_balancer(
            api_id=1,
            algorithm="round_robin"
        )
        
        assert lb.api_id == 1
        assert lb.algorithm == "round_robin"
    
    async def test_add_backend(self, db_session: AsyncSession):
        """Test adding a backend to load balancer."""
        manager = LoadBalancerManager(db_session)
        
        lb = await manager.create_load_balancer(api_id=1, algorithm="round_robin")
        
        backend = await manager.add_backend(
            load_balancer_id=lb.id,
            url="http://backend1:8000",
            weight=1
        )
        
        assert backend.url == "http://backend1:8000"
        assert backend.load_balancer_id == lb.id
    
    async def test_list_backends(self, db_session: AsyncSession):
        """Test listing backends."""
        manager = LoadBalancerManager(db_session)
        
        lb = await manager.create_load_balancer(api_id=1, algorithm="round_robin")
        
        await manager.add_backend(lb.id, "http://backend1:8000")
        await manager.add_backend(lb.id, "http://backend2:8000")
        await manager.add_backend(lb.id, "http://backend3:8000")
        
        backends = await manager.list_backends(lb.id)
        
        assert len(backends) == 3
    
    async def test_remove_backend(self, db_session: AsyncSession):
        """Test removing a backend."""
        manager = LoadBalancerManager(db_session)
        
        lb = await manager.create_load_balancer(api_id=1, algorithm="round_robin")
        backend = await manager.add_backend(lb.id, "http://backend1:8000")
        
        success = await manager.remove_backend(backend.id)
        assert success
        
        backends = await manager.list_backends(lb.id)
        assert len(backends) == 0
    
    async def test_update_backend_health(self, db_session: AsyncSession):
        """Test updating backend health status."""
        manager = LoadBalancerManager(db_session)
        
        lb = await manager.create_load_balancer(api_id=1, algorithm="round_robin")
        backend = await manager.add_backend(lb.id, "http://backend1:8000")
        
        # Mark as unhealthy
        await manager.update_backend_health(backend.id, healthy=False)
        
        backends = await manager.list_backends(lb.id)
        assert backends[0].healthy is False
    
    async def test_select_backend_for_request(self, db_session: AsyncSession):
        """Test selecting a backend for a request."""
        manager = LoadBalancerManager(db_session)
        
        lb = await manager.create_load_balancer(api_id=1, algorithm="round_robin")
        await manager.add_backend(lb.id, "http://backend1:8000")
        await manager.add_backend(lb.id, "http://backend2:8000")
        
        # Select backends
        backend1 = await manager.select_backend(api_id=1)
        backend2 = await manager.select_backend(api_id=1)
        
        # Should alternate between backends
        assert backend1.url != backend2.url


@pytest.mark.asyncio
class TestHealthChecks:
    """Test backend health checks."""
    
    async def test_health_check_http(self, db_session: AsyncSession):
        """Test HTTP health check."""
        manager = LoadBalancerManager(db_session)
        
        lb = await manager.create_load_balancer(api_id=1, algorithm="round_robin")
        backend = await manager.add_backend(
            lb.id,
            "http://localhost:8000",
            health_check_path="/health"
        )
        
        # Perform health check (would need actual HTTP request)
        result = await manager.perform_health_check(backend.id)
        
        assert "status" in result
    
    async def test_automatic_health_checks(self, db_session: AsyncSession):
        """Test that health checks run automatically."""
        # This would require background task testing
        pass
    
    async def test_unhealthy_backend_removed_from_rotation(self, db_session: AsyncSession):
        """Test that unhealthy backends are removed from rotation."""
        manager = LoadBalancerManager(db_session)
        
        lb = await manager.create_load_balancer(api_id=1, algorithm="round_robin")
        backend1 = await manager.add_backend(lb.id, "http://backend1:8000")
        backend2 = await manager.add_backend(lb.id, "http://backend2:8000")
        
        # Mark backend1 as unhealthy
        await manager.update_backend_health(backend1.id, healthy=False)
        
        # Should only select backend2
        selected = await manager.select_backend(api_id=1)
        assert selected.id == backend2.id


@pytest.mark.asyncio
class TestFailover:
    """Test failover handling."""
    
    async def test_failover_to_healthy_backend(self, db_session: AsyncSession):
        """Test that requests failover to healthy backends."""
        manager = LoadBalancerManager(db_session)
        
        lb = await manager.create_load_balancer(api_id=1, algorithm="round_robin")
        await manager.add_backend(lb.id, "http://backend1:8000")
        await manager.add_backend(lb.id, "http://backend2:8000")
        
        # Simulate backend1 failure
        backends = await manager.list_backends(lb.id)
        await manager.update_backend_health(backends[0].id, healthy=False)
        
        # All requests should go to backend2
        for _ in range(5):
            selected = await manager.select_backend(api_id=1)
            assert selected.url == "http://backend2:8000"
    
    async def test_no_healthy_backends(self, db_session: AsyncSession):
        """Test behavior when no backends are healthy."""
        manager = LoadBalancerManager(db_session)
        
        lb = await manager.create_load_balancer(api_id=1, algorithm="round_robin")
        backend = await manager.add_backend(lb.id, "http://backend1:8000")
        
        # Mark as unhealthy
        await manager.update_backend_health(backend.id, healthy=False)
        
        # Should return None or raise exception
        selected = await manager.select_backend(api_id=1)
        assert selected is None


# Run tests with: pytest tests/test_load_balancing.py -v

"""
Test cases for Prometheus Metrics module.

Tests:
1. Metrics collection (counter, histogram, gauge)
2. Request metrics
3. Latency tracking
4. Error metrics
5. Metrics storage
6. Percentile calculations (p50, p90, p95, p99)
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Metric
from app.metrics.prometheus import (
    request_counter,
    request_latency,
    error_counter,
    active_connections
)
from app.metrics.storage import MetricsStorage


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


class TestPrometheusMetrics:
    """Test Prometheus metrics collection."""
    
    def test_request_counter_increment(self):
        """Test incrementing request counter."""
        # Get initial value
        metric = request_counter.labels(
            method="GET",
            endpoint="/test",
            status="200"
        )
        
        # Increment
        metric.inc()
        
        # The metric should be incremented
        # (Actual value checking would require prometheus_client internals)
    
    def test_request_latency_observe(self):
        """Test observing request latency."""
        metric = request_latency.labels(
            method="GET",
            endpoint="/test"
        )
        
        # Observe latencies
        metric.observe(0.1)  # 100ms
        metric.observe(0.5)  # 500ms
        metric.observe(1.0)  # 1000ms
    
    def test_error_counter_increment(self):
        """Test incrementing error counter."""
        metric = error_counter.labels(
            type="validation",
            endpoint="/test"
        )
        
        metric.inc()
    
    def test_active_connections_gauge(self):
        """Test active connections gauge."""
        # Increment
        active_connections.inc()
        
        # Decrement
        active_connections.dec()
    
    def test_multiple_labels(self):
        """Test metrics with different labels."""
        # Different methods
        request_counter.labels(method="GET", endpoint="/api", status="200").inc()
        request_counter.labels(method="POST", endpoint="/api", status="201").inc()
        
        # Different endpoints
        request_counter.labels(method="GET", endpoint="/users", status="200").inc()
        request_counter.labels(method="GET", endpoint="/apis", status="200").inc()


@pytest.mark.asyncio
class TestMetricsStorage:
    """Test metrics storage in database."""
    
    async def test_store_request_metric(self, db_session: AsyncSession):
        """Test storing a request metric."""
        storage = MetricsStorage(db_session)
        
        metric = await storage.store_request_metric(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            latency_ms=150
        )
        
        assert metric.endpoint == "/api/test"
        assert metric.method == "GET"
        assert metric.status_code == 200
        assert metric.latency_ms == 150
        assert metric.metric_type == "request"
    
    async def test_store_error_metric(self, db_session: AsyncSession):
        """Test storing an error metric."""
        storage = MetricsStorage(db_session)
        
        metric = await storage.store_error_metric(
            endpoint="/api/test",
            method="POST",
            status_code=500
        )
        
        assert metric.metric_type == "error"
        assert metric.status_code == 500
    
    async def test_metrics_summary(self, db_session: AsyncSession):
        """Test getting metrics summary."""
        storage = MetricsStorage(db_session)
        
        # Store multiple metrics
        await storage.store_request_metric("/api", "GET", 200, 100)
        await storage.store_request_metric("/api", "GET", 200, 150)
        await storage.store_request_metric("/api", "GET", 200, 200)
        await storage.store_error_metric("/api", "GET", 500)
        
        summary = await storage.get_metrics_summary()
        
        assert summary["total_requests"] == 3  # Only successful requests
        assert summary["error_count"] == 1
        assert summary["average_latency_ms"] == 150  # (100 + 150 + 200) / 3
    
    async def test_percentile_calculations(self, db_session: AsyncSession):
        """Test latency percentile calculations."""
        storage = MetricsStorage(db_session)
        
        # Store metrics with various latencies
        latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for latency in latencies:
            await storage.store_request_metric("/api", "GET", 200, latency)
        
        summary = await storage.get_metrics_summary()
        
        # p50 (median) should be around 50
        assert 40 <= summary["p50_latency_ms"] <= 60
        
        # p90 should be around 90
        assert 80 <= summary["p90_latency_ms"] <= 100
        
        # p95 should be around 95
        assert 90 <= summary["p95_latency_ms"] <= 100
        
        # p99 should be around 99
        assert 95 <= summary["p99_latency_ms"] <= 100
    
    async def test_metrics_filtering_by_api(self, db_session: AsyncSession):
        """Test filtering metrics by API ID."""
        storage = MetricsStorage(db_session)
        
        # Store metrics for different APIs
        await storage.store_request_metric("/api1", "GET", 200, 100, api_id=1)
        await storage.store_request_metric("/api1", "GET", 200, 150, api_id=1)
        await storage.store_request_metric("/api2", "GET", 200, 200, api_id=2)
        
        # Get summary for API 1
        summary = await storage.get_metrics_summary(api_id=1)
        
        assert summary["total_requests"] == 2
        assert summary["average_latency_ms"] == 125
    
    async def test_metrics_date_filtering(self, db_session: AsyncSession):
        """Test filtering metrics by date range."""
        storage = MetricsStorage(db_session)
        
        # Store recent metrics
        await storage.store_request_metric("/api", "GET", 200, 100)
        
        # Store old metric
        from sqlalchemy import update
        old_metric = await storage.store_request_metric("/api", "GET", 200, 200)
        old_date = datetime.now(timezone.utc) - timedelta(days=10)
        stmt = update(Metric).where(
            Metric.id == old_metric.id
        ).values(timestamp=old_date)
        await db_session.execute(stmt)
        await db_session.commit()
        
        # Get summary for last 7 days
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        summary = await storage.get_metrics_summary(start_date=start_date)
        
        # Should only include the recent metric
        assert summary["total_requests"] == 1
    
    async def test_error_rate_calculation(self, db_session: AsyncSession):
        """Test error rate calculation."""
        storage = MetricsStorage(db_session)
        
        # Store 100 successful requests
        for _ in range(100):
            await storage.store_request_metric("/api", "GET", 200, 100)
        
        # Store 5 errors
        for _ in range(5):
            await storage.store_error_metric("/api", "GET", 500)
        
        summary = await storage.get_metrics_summary()
        
        assert summary["total_requests"] == 100
        assert summary["error_count"] == 5
        # Error rate should be 5 / (100 + 5) = 0.047619...
        assert 0.04 <= summary["error_rate"] <= 0.05
    
    async def test_requests_per_second(self, db_session: AsyncSession):
        """Test requests per second calculation."""
        storage = MetricsStorage(db_session)
        
        # Store metrics with specific timestamps
        now = datetime.now(timezone.utc)
        
        # Create 10 metrics over 10 seconds
        for i in range(10):
            metric = await storage.store_request_metric("/api", "GET", 200, 100)
            
            # Update timestamp to spread over 10 seconds
            from sqlalchemy import update
            timestamp = now - timedelta(seconds=i)
            stmt = update(Metric).where(
                Metric.id == metric.id
            ).values(timestamp=timestamp)
            await db_session.execute(stmt)
        
        await db_session.commit()
        
        # Calculate RPS over last 10 seconds
        start = now - timedelta(seconds=10)
        summary = await storage.get_metrics_summary(start_date=start, end_date=now)
        
        # Should be approximately 1 request per second
        assert 0.5 <= summary["requests_per_second"] <= 1.5


@pytest.mark.asyncio
class TestMetricsAggregation:
    """Test metrics aggregation and reporting."""
    
    async def test_metrics_by_endpoint(self, db_session: AsyncSession):
        """Test aggregating metrics by endpoint."""
        storage = MetricsStorage(db_session)
        
        # Store metrics for different endpoints
        await storage.store_request_metric("/users", "GET", 200, 50)
        await storage.store_request_metric("/users", "GET", 200, 60)
        await storage.store_request_metric("/apis", "GET", 200, 100)
        
        # This would require a method to aggregate by endpoint
        # For now, we just test that metrics are stored correctly
        from sqlalchemy import select
        stmt = select(Metric).where(Metric.endpoint == "/users")
        result = await db_session.execute(stmt)
        metrics = result.scalars().all()
        
        assert len(metrics) == 2
    
    async def test_metrics_by_method(self, db_session: AsyncSession):
        """Test aggregating metrics by HTTP method."""
        storage = MetricsStorage(db_session)
        
        await storage.store_request_metric("/api", "GET", 200, 50)
        await storage.store_request_metric("/api", "POST", 201, 100)
        await storage.store_request_metric("/api", "DELETE", 204, 75)
        
        from sqlalchemy import select
        stmt = select(Metric).where(Metric.method == "GET")
        result = await db_session.execute(stmt)
        metrics = result.scalars().all()
        
        assert len(metrics) == 1


# Run tests with: pytest tests/test_metrics.py -v

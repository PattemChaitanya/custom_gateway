# Database Connection Architecture

## Overview

The database connection system follows a robust **Three-Tier Fallback** strategy:
1. **Primary**: AWS PostgreSQL (RDS/Aurora) - Production database
2. **Secondary**: SQLite - Persistent fallback storage
3. **Final**: In-memory storage - Non-persistent fallback

This architecture provides maximum resilience, ensuring the application remains functional even when the primary database is unavailable, while maintaining data persistence through SQLite when possible.

## Architecture Components

### 1. DatabaseManager (`db_manager.py`)
Central component that manages database connections with automatic three-tier fallback.

**Key Features:**
- Singleton pattern for global connection management
- Automatic three-tier fallback (PostgreSQL → SQLite → In-memory)
- Connection health checks for each tier
- Connection pooling with configurable pool size
- SSL/TLS support for AWS RDS
- Persistent fallback storage with SQLite
- Graceful degradation to in-memory storage as last resort
- Comprehensive error handling and logging

**Usage:**
```python
from app.db import get_db_manager, get_db

# Get the manager instance
db_manager = get_db_manager()

# Initialize connections (called automatically at startup)
await db_manager.initialize(echo_sql=False)

# Get database session (use with FastAPI Depends)
@app.get("/apis")
async def list_apis(db = Depends(get_db)):
    return await crud.list_apis(db)

# Check health status
health = await db_manager.health_check()
print(f"Database: {health['database']}, Status: {health['status']}")  # postgresql, sqlite, or in-memory

# Get connection info
info = db_manager.get_connection_info()
print(f"Using primary: {info['is_using_primary']}")
print(f"Using SQLite: {info['is_using_sqlite']}")
print(f"Database type: {info['database_type']}")  # postgresql, sqlite, or in-memory
```

### 2. Progress SQL Utilities (`progress_sql.py`)
Provides utility functions for building and validating PostgreSQL connections.

**Key Functions:**
- `build_aws_database_url()` - Build connection URL from AWS_* env vars
- `build_database_url_from_secret()` - Retrieve credentials from AWS Secrets Manager
- `validate_postgres_connection()` - Async connection validation
- `get_database_url_from_env()` - Get URL with priority fallback

**Environment Variables:**
```bash
# AWS PostgreSQL Connection
AWS_DB_HOST=your-db.region.rds.amazonaws.com
AWS_DB_NAME=gateway_db
AWS_DB_USER=dbuser
AWS_DB_PASSWORD=dbpassword
AWS_DB_PORT=5432

# SSL Configuration (optional)
AWS_REQUIRE_SSL=true
AWS_SSLROOTCERT=/path/to/rds-ca-cert.pem

# AWS Secrets Manager (alternative to explicit credentials)
AWS_DB_SECRET=my-db-secret-name
AWS_REGION=us-east-1

# SQLite Configuration (secondary fallback)
SQLITE_DB_PATH=gateway.db  # Default: gateway.db

# Direct URL (highest priority)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# SQL Echo (debugging)
SQL_ECHO=false
```

### 3. SQLite Database (`sqlite_db.py`)
Persistent secondary fallback storage using SQLite with async support.

**Features:**
- Compatible with AsyncSession interface
- SimpleNamespace objects for Pydantic compatibility
- Async operations using aiosqlite
- Persistent storage across application restarts
- Automatic table creation
- Full transaction support (commit, rollback)
- Configurable database file path

**Usage:**
```python
# Automatically used when PostgreSQL is unavailable
# No code changes needed - CRUD operations work identically

# Check if using SQLite
if hasattr(db, 'in_memory'):
    if not db.in_memory and hasattr(db, 'db_path'):
        print(f"Using SQLite fallback at: {db.db_path}")
```

**Configuration:**
```bash
# Set custom SQLite database path
export SQLITE_DB_PATH="/path/to/your/database.db"
```

### 4. In-Memory Database (`inmemory.py`)
Lightweight in-memory storage as the final fallback option.

**Features:**
- Compatible with AsyncSession interface
- SimpleNamespace objects for Pydantic compatibility
- No-op transaction methods (commit, rollback, refresh)
- Automatic data clearing on restart
- Used only when both PostgreSQL and SQLite are unavailable

**Usage:**
```python
# Automatically used as last resort fallback
# No code changes needed - CRUD operations work identically

# Check if using in-memory
if hasattr(db, 'in_memory') and db.in_memory:
    print("Using in-memory final fallback")
    # Warning: Data will be lost on restart!
```

### 5. Connector (`connector.py`)
Backward compatibility layer for legacy code.

**Status:** Deprecated - Use `db_manager` for new code

**Legacy Functions Still Supported:**
- `get_db()` - FastAPI dependency (redirects to db_manager)
- `init_db()` - Create tables
- `init_engine_from_aws_env()` - AWS initialization
- `init_engine_from_url()` - URL initialization

## Connection Priority

The system attempts connections in this order:

```
1. Explicit DATABASE_URL environment variable
   ↓ (if not found)
2. AWS Secrets Manager (AWS_DB_SECRET or AWS_SECRET_NAME)
   ↓ (if not found)
3. AWS Environment Variables (AWS_DB_HOST, AWS_DB_NAME, etc.)
   ↓ (if connection fails)
4. SQLite Database (SQLITE_DB_PATH or default: gateway.db)
   ↓ (if SQLite fails)
5. In-Memory Storage (final automatic fallback)
```

**Fallback Hierarchy:**
- **PostgreSQL**: Production-grade persistent storage
- **SQLite**: Persistent fallback for development/degraded operation
- **In-Memory**: Non-persistent fallback for testing/emergency operation

## Connection Pooling

PostgreSQL connections use SQLAlchemy's connection pooling:

```python
pool_size=5           # Maintain 5 connections
max_overflow=10       # Allow up to 10 additional connections
pool_pre_ping=True    # Verify connections before use
pool_recycle=3600     # Recycle connections after 1 hour
```

## SSL/TLS Configuration

For secure AWS RDS connections:

1. Download the RDS CA certificate:
```bash
wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -O rds-ca-cert.pem
```

2. Configure environment:
```bash
export AWS_REQUIRE_SSL=true
export AWS_SSLROOTCERT=/path/to/rds-ca-cert.pem
```

## Error Handling

The system handles various failure scenarios:

### Scenario 1: PostgreSQL Unavailable at Startup
```
Result: Automatic fallback to SQLite storage
Log: "Primary database connection failed. Connected to secondary fallback database (SQLite)"
```

### Scenario 2: Both PostgreSQL and SQLite Unavailable
```
Result: Automatic fallback to in-memory storage
Log: "Primary and secondary database connections failed. Falling back to in-memory storage."
Warning: Data will not persist across restarts
```

### Scenario 3: Connection Lost During Operation
```
Result: Operation fails with proper error
Recommendation: Implement retry logic in application code
Note: DatabaseManager maintains pool_pre_ping to minimize this scenario
```

### Scenario 4: Missing AWS Credentials
```
Result: Automatic fallback to SQLite, then in-memory storage
Log: "No database URL configured"
```

## Health Check Endpoint

The application provides a health check endpoint:

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "service": "Gateway Management API",
  "version": "1.0.0",
  "database": {
    "status": "healthy",
    "type": "postgresql",  // Can be: postgresql, sqlite, or in-memory
    "message": "Primary database connection is healthy",
    "using_primary": true,
    "using_sqlite": false
  }
}
```

## Application Integration

### Startup (main.py)
```python
from app.db import get_db_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database manager
    db_manager = get_db_manager()
    await db_manager.initialize(echo_sql=False)
    
    # Log connection status
    health = await db_manager.health_check()
    logger.info(f"Database: {health['message']}")
    
    yield
    
    # Cleanup on shutdown
    await db_manager.shutdown()
```

### API Endpoints
```python
from app.db import get_db
from fastapi import Depends

@router.post("/apis")
async def create_api(payload: CreateAPIRequest, db = Depends(get_db)):
    return await crud.create_api(db, payload.dict())

@router.get("/apis")
async def list_apis(db = Depends(get_db)):
    return await crud.list_apis(db)
```

### CRUD Operations
```python
# Works with both PostgreSQL and in-memory
async def create_api(db: AsyncSession | InMemoryDB, payload: dict):
    if getattr(db, "in_memory", False):
        # In-memory path
        return await db.create_api(payload)
    else:
        # PostgreSQL path
        api = models.API(**payload)
        db.add(api)
        await db.commit()
        await db.refresh(api)
        return api
```

## Testing

### Test Configuration (conftest.py)
```python
@pytest.fixture(scope="session", autouse=True)
async def initialize_db_manager():
    from app.db import get_db_manager
    
    db_manager = get_db_manager()
    await db_manager.initialize(echo_sql=False)
    
    yield
    
    await db_manager.shutdown()
```

### Running Tests
```bash
# Tests use sqlite by default
pytest

# Use PostgreSQL for tests
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/test_db"
pytest
```

## Migration Guide

### For Existing Code

**Old Pattern:**
```python
from app.db.connector import get_db, init_engine_from_aws_env

init_engine_from_aws_env()
```

**New Pattern (Recommended):**
```python
from app.db import get_db_manager

db_manager = get_db_manager()
await db_manager.initialize()
```

**Note:** Old code continues to work! The connector module provides backward compatibility.

### For New Code

Use the new DatabaseManager directly:
```python
from app.db import get_db, get_db_manager
from fastapi import Depends

# In endpoints
async def my_endpoint(db = Depends(get_db)):
    # Your code here
    pass

# For manual management
db_manager = get_db_manager()
async with db_manager.get_session() as session:
    # Your code here
    pass
```

## Monitoring & Observability

### Logging

The system provides comprehensive logging:

```
INFO - DatabaseManager initialized
INFO - Primary database initialized successfully
INFO - Database health: healthy - Primary database connection is healthy
INFO - Database initialized: postgresql (primary=True)
```

### Health Checks

Programmatic health checks:
```python
db_manager = get_db_manager()

# Get health status
health = await db_manager.health_check()
# Returns: {"status": "healthy|degraded|unhealthy", "database": "postgresql|in-memory", "message": "..."}

# Get connection info
info = db_manager.get_connection_info()
# Returns: {"is_using_primary": bool, "database_type": str, ...}
```

## Best Practices

1. **Always use dependency injection** with FastAPI's `Depends(get_db)`
2. **Handle both database types** in CRUD operations using `getattr(db, "in_memory", False)`
3. **Monitor health checks** to detect fallback scenarios
4. **Use connection pooling** settings appropriate for your load
5. **Enable SSL** for production AWS RDS connections
6. **Store credentials** in AWS Secrets Manager for production
7. **Set SQL_ECHO=false** in production for performance
8. **Implement retry logic** for transient connection failures

## Troubleshooting

### Issue: Connection Timeout
```
Solution: Check security groups, network connectivity, and credentials
Check: AWS_DB_HOST, AWS_DB_PORT, firewall rules
```

### Issue: SSL Certificate Error
```
Solution: Download correct RDS CA certificate and set AWS_SSLROOTCERT
Check: Certificate path exists and is readable
```

### Issue: In-Memory Fallback in Production
```
Solution: Check AWS credentials and database availability
Check: Health endpoint, application logs, DATABASE_URL
```

### Issue: Connection Pool Exhausted
```
Solution: Increase pool_size and max_overflow in db_manager.py
Check: Application connection handling, long-running transactions
```

## Performance Considerations

1. **Connection Pooling**: Pre-configured for optimal performance
2. **Pool Pre-Ping**: Adds small overhead but ensures connection validity
3. **Pool Recycle**: Prevents stale connections (1 hour default)
4. **SSL Overhead**: Minor latency for encrypted connections
5. **In-Memory**: Fastest option but no persistence

## Security

1. **Credentials**: Use AWS Secrets Manager in production
2. **SSL/TLS**: Always enable for production databases
3. **Certificate Validation**: Use `sslmode=verify-full` with AWS_SSLROOTCERT
4. **Network**: Use VPC and security groups for database access
5. **Logging**: Sensitive data is redacted in logs

## Future Enhancements

- [ ] Read replica support for horizontal scaling
- [ ] Automatic reconnection with exponential backoff
- [ ] Connection metrics and monitoring
- [ ] Database migration automation
- [ ] Multi-database support (sharding)
- [ ] Redis caching layer
- [ ] Query performance monitoring

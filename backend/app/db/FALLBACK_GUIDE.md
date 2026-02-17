# Three-Tier Database Fallback Implementation Guide

## Overview
The Gateway Management system now implements a three-tier database fallback strategy for maximum resilience:

1. **PostgreSQL** (Primary) - Production database
2. **SQLite** (Secondary) - Persistent fallback  
3. **In-Memory** (Final) - Non-persistent fallback

## Quick Test

### Test 1: Normal Operation (PostgreSQL)
```bash
# Ensure PostgreSQL environment variables are set
export AWS_DB_HOST=your-db-host
export AWS_DB_NAME=gateway_db
export AWS_DB_USER=dbuser
export AWS_DB_PASSWORD=dbpassword

# Start the application
python -m uvicorn app.main:app --reload

# Expected log output:
# "Successfully connected to primary database (PostgreSQL)"
```

### Test 2: SQLite Fallback
```bash
# Unset PostgreSQL variables or use invalid credentials
unset AWS_DB_HOST AWS_DB_NAME AWS_DB_USER AWS_DB_PASSWORD
unset DATABASE_URL

# Optionally set custom SQLite path
export SQLITE_DB_PATH="./test_gateway.db"

# Start the application
python -m uvicorn app.main:app --reload

# Expected log output:
# "Primary database connection failed..."
# "Connected to secondary fallback database (SQLite)"

# Verify SQLite file was created
ls -lh ./test_gateway.db  # or gateway.db if using default
```

### Test 3: In-Memory Fallback
```bash
# Create a scenario where SQLite also fails (e.g., read-only filesystem)
export SQLITE_DB_PATH="/read-only/path/gateway.db"

# Start the application
python -m uvicorn app.main:app --reload

# Expected log output:
# "Primary database connection failed..."
# "Failed to initialize SQLite database..."
# "Falling back to in-memory storage"
```

## Checking Active Database

### Via Health Check Endpoint
```bash
curl http://localhost:8000/health | jq '.database'
```

Expected responses:

**PostgreSQL Active:**
```json
{
  "status": "healthy",
  "type": "postgresql",
  "message": "Primary database connection is healthy",
  "using_primary": true,
  "using_sqlite": false
}
```

**SQLite Active:**
```json
{
  "status": "healthy",
  "type": "sqlite",
  "message": "Using SQLite secondary fallback storage",
  "using_primary": false,
  "using_sqlite": true
}
```

**In-Memory Active:**
```json
{
  "status": "degraded",
  "type": "in-memory",
  "message": "Using final fallback in-memory storage",
  "using_primary": false,
  "using_sqlite": false
}
```

### Programmatically in Python
```python
from app.db import get_db_manager

db_manager = get_db_manager()
info = db_manager.get_connection_info()

if info['is_using_primary']:
    print("✓ Using PostgreSQL (Primary)")
elif info['is_using_sqlite']:
    print("✓ Using SQLite (Secondary)")
    print(f"  Database file: {info.get('sqlite_path')}")
else:
    print("⚠ Using In-Memory (Final Fallback)")
    print("  WARNING: Data will not persist!")
```

## Configuration

### Environment Variables

```bash
# PostgreSQL (Primary)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
# OR
AWS_DB_HOST=hostname
AWS_DB_NAME=dbname
AWS_DB_USER=username
AWS_DB_PASSWORD=password
AWS_DB_PORT=5432

# SQLite (Secondary)
SQLITE_DB_PATH=./data/gateway.db  # Default: gateway.db

# Debugging
SQL_ECHO=true  # Echo SQL statements (PostgreSQL only)
```

### Python Configuration
```python
from app.db import get_db_manager

# Initialize with specific SQLite path
db_manager = get_db_manager()
db_manager._sqlite_path = "/custom/path/gateway.db"
await db_manager.initialize()

# Force SQLite (bypass PostgreSQL)
await db_manager._initialize_sqlite_database()

# Force In-Memory (bypass both)
db_manager._initialize_fallback_database()
```

## Database Capabilities by Type

| Feature | PostgreSQL | SQLite | In-Memory |
|---------|-----------|---------|-----------|
| Persistence | ✓ | ✓ | ✗ |
| Transactions | ✓ | ✓ | Limited |
| Concurrent writes | ✓ | Limited | ✓ |
| Distributed | ✓ | ✗ | ✗ |
| Production-ready | ✓ | Dev/Staging | Testing only |
| Auto-reconnect | ✓ | N/A | N/A |
| Data survives restart | ✓ | ✓ | ✗ |

## Common Issues

### Issue 1: SQLite file permission denied
**Symptom:** Falls back to in-memory unexpectedly
**Solution:**
```bash
# Ensure directory exists and is writable
mkdir -p ./data
chmod 755 ./data
export SQLITE_DB_PATH=./data/gateway.db
```

### Issue 2: SQLite locking errors
**Symptom:** "database is locked" errors
**Solution:**
```python
# SQLite has limited concurrent write support
# For high concurrency, use PostgreSQL
# For development, single-threaded access is usually fine
```

### Issue 3: Data not persisting
**Symptom:** Data disappears after restart
**Check:**
```python
from app.db import get_db_manager

db_manager = get_db_manager()
info = db_manager.get_connection_info()
print(f"Database type: {info['database_type']}")

# If "in-memory", you need PostgreSQL or SQLite
```

## Migration Path

### Development → Production

**Development (SQLite):**
```bash
export SQLITE_DB_PATH=./dev_gateway.db
python -m uvicorn app.main:app
```

**Production (PostgreSQL):**
```bash
export DATABASE_URL=postgresql+asyncpg://prod-user:pass@prod-db:5432/gateway
python -m uvicorn app.main:app
```

### Data is automatically migrated when:
- Using Alembic migrations for schema changes
- Both databases follow the same schema

## Testing All Fallback Tiers

```python
# test_fallback.py
import asyncio
from app.db import get_db_manager

async def test_fallback_sequence():
    db_manager = get_db_manager()
    
    # Test 1: Try PostgreSQL
    await db_manager.initialize()
    info = db_manager.get_connection_info()
    print(f"Tier 1 - PostgreSQL: {info['is_using_primary']}")
    
    # Test 2: Force SQLite
    await db_manager.shutdown()
    await db_manager._initialize_sqlite_database()
    info = db_manager.get_connection_info()
    print(f"Tier 2 - SQLite: {info['is_using_sqlite']}")
    
    # Test 3: Force In-Memory
    await db_manager.shutdown()
    db_manager._initialize_fallback_database()
    info = db_manager.get_connection_info()
    print(f"Tier 3 - In-Memory: {not info['is_using_primary'] and not info['is_using_sqlite']}")

asyncio.run(test_fallback_sequence())
```

## Production Recommendations

1. **Always configure PostgreSQL** for production environments
2. **Use SQLite for:**
   - Development environments
   - Staging/testing
   - Edge deployments with limited connectivity
   - Graceful degradation scenarios

3. **Avoid In-Memory for:**
   - Production use
   - Any scenario requiring data persistence
   
4. **Monitor database type:**
   - Alert when not using primary database
   - Track fallback occurrences
   - Implement automatic recovery

## Additional Resources

- [Database Architecture README](./README.md)
- [SQLite Database Implementation](./sqlite_db.py)
- [Database Manager](./db_manager.py)
- [Connection Utilities](./progress_sql.py)

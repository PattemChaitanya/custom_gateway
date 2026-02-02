# Database Connection Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Application Layer                           │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────┐   │
│  │ FastAPI   │  │  CRUD     │  │  Router   │  │  Health      │   │
│  │ Endpoints │  │ Operations│  │  Logic    │  │  Checks      │   │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └──────┬───────┘   │
│        │              │              │                │            │
│        └──────────────┴──────────────┴────────────────┘            │
│                            │                                        │
│                      Depends(get_db)                               │
└────────────────────────────┼───────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Database Manager Layer                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    DatabaseManager                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │  │
│  │  │ initialize() │  │ get_session()│  │ health_check()   │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │  │
│  │                                                               │  │
│  │  Connection Priority Logic:                                  │  │
│  │  1. Check DATABASE_URL env var                              │  │
│  │  2. Try AWS Secrets Manager                                 │  │
│  │  3. Try AWS env variables                                   │  │
│  │  4. Fallback to in-memory                                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                             │                                       │
│              ┌──────────────┴──────────────┐                       │
│              ▼                              ▼                       │
│    ┌──────────────────┐          ┌──────────────────┐             │
│    │  Primary Path    │          │  Fallback Path   │             │
│    │  (PostgreSQL)    │          │  (In-Memory)     │             │
│    └────────┬─────────┘          └────────┬─────────┘             │
└─────────────┼────────────────────────────┼─────────────────────────┘
              │                            │
              ▼                            ▼
┌─────────────────────────┐  ┌──────────────────────────┐
│  PostgreSQL Layer       │  │  In-Memory Layer         │
│                         │  │                          │
│  ┌───────────────────┐  │  │  ┌────────────────────┐ │
│  │ SQLAlchemy        │  │  │  │ InMemoryDB         │ │
│  │ AsyncEngine       │  │  │  │                    │ │
│  │                   │  │  │  │ - API storage      │ │
│  │ Connection Pool:  │  │  │  │ - User storage     │ │
│  │ - size: 5         │  │  │  │ - Token storage    │ │
│  │ - overflow: 10    │  │  │  │                    │ │
│  │ - pre_ping: true  │  │  │  │ SimpleNamespace    │ │
│  │ - recycle: 3600s  │  │  │  │ objects            │ │
│  │                   │  │  │  │                    │ │
│  │ SSL/TLS Support   │  │  │  └────────────────────┘ │
│  └─────────┬─────────┘  │  └──────────────────────────┘
│            │            │
│            ▼            │
│  ┌───────────────────┐  │
│  │ AWS RDS/Aurora    │  │
│  │ PostgreSQL        │  │
│  │                   │  │
│  │ - Master DB       │  │
│  │ - Read Replicas   │  │
│  │ - Encrypted       │  │
│  └───────────────────┘  │
└─────────────────────────┘


Environment Configuration Flow:
═══════════════════════════════════════════════════════════════

Priority 1: Explicit URL
┌──────────────────────┐
│ DATABASE_URL env var │──────► Direct connection
└──────────────────────┘

Priority 2: AWS Secrets Manager
┌──────────────────────┐
│ AWS_DB_SECRET        │
│ AWS_SECRET_NAME      │──────► Fetch credentials
│ AWS_REGION           │        from Secrets Manager
└──────────────────────┘

Priority 3: AWS Environment Variables
┌──────────────────────┐
│ AWS_DB_HOST          │
│ AWS_DB_NAME          │
│ AWS_DB_USER          │──────► Build connection URL
│ AWS_DB_PASSWORD      │
│ AWS_DB_PORT          │
│ AWS_REQUIRE_SSL      │
│ AWS_SSLROOTCERT      │
└──────────────────────┘

Priority 4: Fallback
┌──────────────────────┐
│ No configuration     │──────► Use in-memory storage
└──────────────────────┘


Connection Lifecycle:
═══════════════════════════════════════════════════════════════

Application Startup
       │
       ▼
  Initialize DatabaseManager
       │
       ▼
  Try Primary (PostgreSQL)
       │
       ├─► Success ──► Create connection pool
       │                      │
       │                      ▼
       │              Validate connection
       │                      │
       │                      ▼
       │              Create session factory
       │                      │
       │                      ▼
       │              Create database tables
       │                      │
       │                      ▼
       │              Mark as using primary
       │
       └─► Failure ──► Initialize in-memory DB
                              │
                              ▼
                       Mark as using fallback
       │
       ▼
  Application Running
       │
       ├─► Handle requests with get_db()
       │
       ├─► Periodic health checks
       │
       ▼
  Application Shutdown
       │
       ▼
  Close connections
       │
       ▼
  Cleanup resources


Health Check States:
═══════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────┐
│ HEALTHY (Primary PostgreSQL)                            │
│ ┌───────────────────────────────────────────────────┐  │
│ │ Status: healthy                                   │  │
│ │ Database: postgresql                              │  │
│ │ Message: Primary database connection is healthy   │  │
│ │ Using Primary: true                               │  │
│ └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ DEGRADED (In-Memory Fallback)                           │
│ ┌───────────────────────────────────────────────────┐  │
│ │ Status: degraded                                  │  │
│ │ Database: in-memory                               │  │
│ │ Message: Using fallback in-memory storage         │  │
│ │ Using Primary: false                              │  │
│ └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ UNHEALTHY (Connection Failed)                           │
│ ┌───────────────────────────────────────────────────┐  │
│ │ Status: unhealthy                                 │  │
│ │ Database: postgresql                              │  │
│ │ Message: Health check error: [error details]      │  │
│ │ Using Primary: true (but failing)                 │  │
│ └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘


Module Dependencies:
═══════════════════════════════════════════════════════════

main.py
   │
   └─► db_manager.py (NEW)
          │
          ├─► progress_sql.py (REFACTORED)
          │      │
          │      ├─► boto3 (optional - AWS Secrets)
          │      ├─► psycopg2 (optional - validation)
          │      └─► dotenv (environment loading)
          │
          ├─► inmemory.py (ENHANCED)
          │
          └─► models.py (UNCHANGED)

connector.py (DEPRECATED - backward compatibility)
   │
   └─► db_manager.py
          │
          └─► [same as above]


Key Components:
═══════════════════════════════════════════════════════════

DatabaseManager (Singleton)
├─ Connection Management
│  ├─ Primary connection (PostgreSQL)
│  ├─ Fallback connection (In-memory)
│  └─ Automatic switching
├─ Health Monitoring
│  ├─ Connection validation
│  ├─ Status reporting
│  └─ Metrics collection
├─ Session Management
│  ├─ Session factory
│  ├─ Context manager
│  └─ Dependency injection
└─ Lifecycle Management
   ├─ Initialization
   ├─ Reinitialization
   └─ Cleanup

Progress SQL Utilities
├─ URL Building
│  ├─ From environment variables
│  ├─ From AWS Secrets Manager
│  └─ Priority resolution
├─ Validation
│  ├─ Sync validation (psycopg2)
│  ├─ Async validation wrapper
│  └─ SSL certificate handling
└─ Configuration
   ├─ Environment loading
   ├─ SSL setup
   └─ Connection parameters

In-Memory Database
├─ Storage
│  ├─ APIs
│  ├─ Users
│  ├─ Tokens
│  └─ OTPs
├─ Operations
│  ├─ CRUD methods
│  ├─ Transaction stubs
│  └─ Statistics
└─ Compatibility
   ├─ AsyncSession interface
   ├─ Pydantic support
   └─ No-op transactions
```

"""
SQLite Database Fallback

Provides a SQLite database implementation that mimics the SQLAlchemy
AsyncSession interface for fallback when PostgreSQL is unavailable but
we want persistent storage.
"""

import aiosqlite
import json
from typing import Dict, Optional, List, Any, Union
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
import logging
import os

logger = logging.getLogger(__name__)


def _to_iso(value) -> Optional[str]:
    """Convert a datetime (or already-string) value to an ISO-8601 string, or None."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


class QueryResult:
    """Wrapper for query results to mimic SQLAlchemy Result object."""

    def __init__(self, results: List[Any], rowcount: int = 0):
        """Initialize query result with list of objects."""
        self._results = results
        self.rowcount = rowcount

    def scalars(self):
        """Return scalar results accessor."""
        return ScalarResult(self._results)

    def scalar(self):
        """Return first column of first row, or None."""
        return self._results[0] if self._results else None

    def scalar_one_or_none(self):
        """Return first column of the only row, or None. Raise if multiple rows."""
        if len(self._results) == 0:
            return None
        if len(self._results) > 1:
            raise Exception("Multiple results found")
        return self._results[0]

    def first(self):
        """Return first result or None."""
        return self._results[0] if self._results else None

    def all(self):
        """Return all results."""
        return self._results


class ScalarResult:
    """Scalar result accessor to mimic SQLAlchemy ScalarResult."""

    def __init__(self, results: List[Any]):
        """Initialize with list of results."""
        self._results = results

    def first(self):
        """Return first result or None."""
        return self._results[0] if self._results else None

    def all(self):
        """Return all results."""
        return self._results

    def one(self):
        """Return single result, raise if multiple or none."""
        if len(self._results) == 0:
            raise Exception("No result found")
        if len(self._results) > 1:
            raise Exception("Multiple results found")
        return self._results[0]

    def one_or_none(self):
        """Return single result or None."""
        if len(self._results) == 0:
            return None
        if len(self._results) > 1:
            raise Exception("Multiple results found")
        return self._results[0]


class SQLiteDB:
    """
    SQLite database for fallback when PostgreSQL is unavailable.

    This class provides async methods that match the CRUD layer expectations,
    allowing seamless switching between PostgreSQL and SQLite storage.
    Objects returned are SimpleNamespace instances so Pydantic's `from_attributes`
    mode can read them like ORM objects.

    Data is persisted to a SQLite file and survives application restarts.
    """

    def __init__(self, db_path: str = "gateway.db") -> None:
        """
        Initialize SQLite database.

        Args:
            db_path: Path to SQLite database file
        """
        self.in_memory = False  # Flag to identify this as persistent DB
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None
        self._initialized = False

        logger.info(f"SQLite database initialized at: {db_path}")

    async def connect(self) -> None:
        """Establish connection to SQLite database."""
        if self._db is None:
            # Use timeout to prevent hanging on Windows
            self._db = await aiosqlite.connect(
                self.db_path,
                timeout=10.0  # 10 second timeout for connection
            )
            self._db.row_factory = aiosqlite.Row
            await self._db.execute("PRAGMA foreign_keys = ON")
            # Better concurrency
            await self._db.execute("PRAGMA journal_mode = WAL")
            await self._create_tables()
            self._initialized = True
            logger.info(f"Connected to SQLite database: {self.db_path}")

    async def disconnect(self) -> None:
        """Close SQLite database connection."""
        if self._db:
            await self._db.close()
            self._db = None
            self._initialized = False
            logger.info("Disconnected from SQLite database")

    async def _create_tables(self) -> None:
        """Create all necessary tables if they don't exist."""
        if not self._db:
            return

        # Users table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                is_active INTEGER DEFAULT 1 NOT NULL,
                is_superuser INTEGER DEFAULT 0 NOT NULL,
                roles TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            )
        """)

        # Refresh tokens table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL,
                revoked INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # OTPs table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                otp_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                consumed INTEGER DEFAULT 0,
                transport TEXT
            )
        """)

        # APIs table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS apis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                description TEXT,
                owner_id INTEGER,
                type TEXT,
                resource TEXT,
                config TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                UNIQUE(name, version),
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)

        # Roles table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                permissions TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            )
        """)

        # Permissions table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                resource TEXT NOT NULL,
                action TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # User roles table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
            )
        """)

        # Connectors table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS connectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_id INTEGER,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                config TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                FOREIGN KEY (api_id) REFERENCES apis(id) ON DELETE CASCADE
            )
        """)

        # Secrets table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS secrets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            )
        """)

        # API Keys table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                label TEXT,
                scopes TEXT,
                revoked INTEGER DEFAULT 0,
                environment_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT,
                last_used_at TEXT,
                usage_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)

        # Environments table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS environments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            )
        """)

        # Audit logs table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                metadata_json TEXT,
                status TEXT,
                error_message TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)

        # Metrics table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                metric_type TEXT NOT NULL,
                endpoint TEXT,
                method TEXT,
                status_code INTEGER,
                latency_ms INTEGER,
                api_id INTEGER,
                user_id INTEGER,
                metadata_json TEXT,
                FOREIGN KEY (api_id) REFERENCES apis(id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)

        await self._db.commit()
        logger.debug("SQLite tables created/verified")

    def _row_to_namespace(self, row: aiosqlite.Row) -> SimpleNamespace:
        """Convert SQLite row to SimpleNamespace object."""
        if row is None:
            return None

        obj = SimpleNamespace()
        for key in row.keys():
            value = row[key]
            # Handle JSON columns
            if key in ('config', 'resource', 'permissions', 'metadata', 'metadata_json') and value:
                try:
                    value = json.loads(value) if isinstance(
                        value, str) else value
                except (json.JSONDecodeError, TypeError):
                    pass
            # Handle boolean columns (SQLite stores as INTEGER)
            elif key in ('is_active', 'is_superuser', 'revoked', 'consumed'):
                value = bool(value)
            setattr(obj, key, value)
        return obj

    # API Management Methods

    async def create_api(self, payload: Dict[str, Any]) -> SimpleNamespace:
        """
        Create a new API entry in SQLite.

        Args:
            payload: Dictionary containing API data

        Returns:
            SimpleNamespace: Created API object

        Raises:
            ValueError: If API with same name and version exists
        """
        if not self._db:
            await self.connect()

        try:
            cursor = await self._db.execute("""
                INSERT INTO apis (name, version, description, owner_id, type, resource, config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload.get("name"),
                payload.get("version"),
                payload.get("description"),
                payload.get("owner_id"),
                payload.get("type"),
                json.dumps(payload.get("resource")) if payload.get(
                    "resource") else None,
                json.dumps(payload.get("config")) if payload.get(
                    "config") else None,
                payload.get("created_at", datetime.utcnow().isoformat()),
                payload.get("updated_at")
            ))

            await self._db.commit()
            api_id = cursor.lastrowid

            # Fetch and return the created API
            cursor = await self._db.execute("SELECT * FROM apis WHERE id = ?", (api_id,))
            row = await cursor.fetchone()

            logger.debug(
                f"Created API: {payload.get('name')} v{payload.get('version')} (id={api_id})")
            return self._row_to_namespace(row)

        except aiosqlite.IntegrityError:
            raise ValueError("API with same name and version already exists")

    async def list_apis(self) -> List[SimpleNamespace]:
        """
        List all APIs in SQLite.

        Returns:
            List[SimpleNamespace]: List of all API objects
        """
        if not self._db:
            await self.connect()

        cursor = await self._db.execute("SELECT * FROM apis")
        rows = await cursor.fetchall()
        return [self._row_to_namespace(row) for row in rows]

    async def get_api(self, api_id: int) -> Optional[SimpleNamespace]:
        """
        Get an API by ID.

        Args:
            api_id: API identifier

        Returns:
            SimpleNamespace | None: API object or None if not found
        """
        if not self._db:
            await self.connect()

        cursor = await self._db.execute("SELECT * FROM apis WHERE id = ?", (api_id,))
        row = await cursor.fetchone()
        return self._row_to_namespace(row) if row else None

    async def update_api(
        self,
        api: SimpleNamespace,
        patch: Dict[str, Any]
    ) -> SimpleNamespace:
        """
        Update an API with new data.

        Args:
            api: API object to update
            patch: Dictionary of fields to update

        Returns:
            SimpleNamespace: Updated API object
        """
        if not self._db:
            await self.connect()

        # Build UPDATE query dynamically
        updates = []
        values = []
        for key, value in patch.items():
            if value is not None and key != 'id':
                updates.append(f"{key} = ?")
                if key in ('config', 'resource') and isinstance(value, (dict, list)):
                    values.append(json.dumps(value))
                else:
                    values.append(value)

        if updates:
            values.append(api.id)
            query = f"UPDATE apis SET {', '.join(updates)} WHERE id = ?"
            await self._db.execute(query, values)
            await self._db.commit()

        # Fetch and return updated API
        return await self.get_api(api.id)

    async def delete_api(self, api: SimpleNamespace) -> None:
        """
        Delete an API from SQLite.

        Args:
            api: API object to delete
        """
        if not self._db:
            await self.connect()

        await self._db.execute("DELETE FROM apis WHERE id = ?", (api.id,))
        await self._db.commit()
        logger.debug(f"Deleted API:{api.name} (id={api.id})")

    # Session-like Methods (for compatibility with SQLAlchemy interface)

    async def commit(self) -> None:
        """Commit current transaction and process pending objects."""
        if self._db:
            # Process any pending objects first
            await self._process_pending_objects()
            await self._db.commit()

    async def rollback(self) -> None:
        """Rollback current transaction and clear pending objects."""
        if self._db:
            await self._db.rollback()
        # Clear pending objects on rollback
        if hasattr(self, '_pending_objects'):
            self._pending_objects.clear()

    async def refresh(self, obj: SimpleNamespace) -> None:
        """
        Refresh an object from the database.

        Args:
            obj: Object to refresh
        """
        # Determine object type and refresh from appropriate table
        if not hasattr(obj, 'id'):
            return

        if not self._db:
            await self.connect()

        # Try to determine table based on object attributes
        if hasattr(obj, 'hashed_password'):
            cursor = await self._db.execute("SELECT * FROM users WHERE id = ?", (obj.id,))
            row = await cursor.fetchone()
            if row:
                for key in row.keys():
                    setattr(obj, key, row[key])
        elif hasattr(obj, 'otp_hash'):
            cursor = await self._db.execute("SELECT * FROM otps WHERE id = ?", (obj.id,))
            row = await cursor.fetchone()
            if row:
                for key in row.keys():
                    setattr(obj, key, row[key])
        elif hasattr(obj, 'name') and hasattr(obj, 'version'):
            # API object
            cursor = await self._db.execute("SELECT * FROM apis WHERE id = ?", (obj.id,))
            row = await cursor.fetchone()
            if row:
                refreshed = self._row_to_namespace(row)
                for key in row.keys():
                    setattr(obj, key, getattr(refreshed, key))
        elif hasattr(obj, 'value') and hasattr(obj, 'name') and not hasattr(obj, 'version'):
            # Secret object
            cursor = await self._db.execute("SELECT * FROM secrets WHERE id = ?", (obj.id,))
            row = await cursor.fetchone()
            if row:
                refreshed = self._row_to_namespace(row)
                for key in row.keys():
                    setattr(obj, key, getattr(refreshed, key))
        elif hasattr(obj, 'config') and hasattr(obj, 'type') and hasattr(obj, 'api_id'):
            # Connector object
            cursor = await self._db.execute("SELECT * FROM connectors WHERE id = ?", (obj.id,))
            row = await cursor.fetchone()
            if row:
                refreshed = self._row_to_namespace(row)
                for key in row.keys():
                    setattr(obj, key, getattr(refreshed, key))

    async def flush(self) -> None:
        """Flush pending changes to the database."""
        if self._db:
            # Process pending objects before committing
            await self._process_pending_objects()
            await self._db.commit()

    def add(self, obj: SimpleNamespace) -> None:
        """
        Add object to SQLite database (queued for commit).

        Args:
            obj: Object to add (User, OTP, RefreshToken, Role, Permission, UserRole, API, etc.)
        """
        # Store object for insertion during flush/commit
        if not hasattr(self, '_pending_objects'):
            self._pending_objects = []
        self._pending_objects.append(obj)

    async def _process_pending_objects(self) -> None:
        """Process all pending objects and insert them into the database."""
        if not hasattr(self, '_pending_objects') or not self._pending_objects:
            return

        if not self._db:
            await self.connect()

        for obj in self._pending_objects:
            await self._insert_or_update_object(obj)

        # Clear pending objects after processing
        self._pending_objects.clear()

    async def _insert_or_update_object(self, obj: SimpleNamespace) -> None:
        """Insert or update a single object into the appropriate table."""
        # Check if object already has an ID (UPDATE) or needs INSERT
        has_id = hasattr(obj, 'id') and getattr(obj, 'id') is not None

        # Helper function to safely convert boolean to int, handling None
        def bool_to_int(value, default):
            return int(value if value is not None else default)

        try:
            # Determine object type and insert/update
            if hasattr(obj, 'hashed_password'):
                # User object
                if has_id:
                    await self._db.execute("""
                        UPDATE users 
                        SET email=?, hashed_password=?, is_active=?, is_superuser=?, roles=?, updated_at=?
                        WHERE id=?
                    """, (
                        getattr(obj, 'email', None),
                        getattr(obj, 'hashed_password', None),
                        bool_to_int(getattr(obj, 'is_active', None), True),
                        bool_to_int(getattr(obj, 'is_superuser', None), False),
                        getattr(obj, 'roles', ''),
                        datetime.utcnow().isoformat(),
                        obj.id
                    ))
                else:
                    cursor = await self._db.execute("""
                        INSERT INTO users (email, hashed_password, is_active, is_superuser, roles, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        getattr(obj, 'email', None),
                        getattr(obj, 'hashed_password', None),
                        bool_to_int(getattr(obj, 'is_active', None), True),
                        bool_to_int(getattr(obj, 'is_superuser', None), False),
                        getattr(obj, 'roles', ''),
                        getattr(obj, 'created_at',
                                datetime.utcnow().isoformat()),
                        getattr(obj, 'updated_at', None)
                    ))
                    obj.id = cursor.lastrowid

            elif hasattr(obj, 'name') and hasattr(obj, 'version'):
                # API object
                if has_id:
                    await self._db.execute("""
                        UPDATE apis 
                        SET name=?, version=?, description=?, owner_id=?, type=?, resource=?, config=?, updated_at=?
                        WHERE id=?
                    """, (
                        getattr(obj, 'name', None),
                        getattr(obj, 'version', None),
                        getattr(obj, 'description', None),
                        getattr(obj, 'owner_id', None),
                        getattr(obj, 'type', None),
                        json.dumps(getattr(obj, 'resource', None)) if hasattr(
                            obj, 'resource') and getattr(obj, 'resource') is not None else None,
                        json.dumps(getattr(obj, 'config', None)) if hasattr(
                            obj, 'config') and getattr(obj, 'config') is not None else None,
                        datetime.utcnow().isoformat(),
                        obj.id
                    ))
                else:
                    cursor = await self._db.execute("""
                        INSERT INTO apis (name, version, description, owner_id, type, resource, config, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        getattr(obj, 'name', None),
                        getattr(obj, 'version', None),
                        getattr(obj, 'description', None),
                        getattr(obj, 'owner_id', None),
                        getattr(obj, 'type', None),
                        json.dumps(getattr(obj, 'resource', None)) if hasattr(
                            obj, 'resource') and getattr(obj, 'resource') is not None else None,
                        json.dumps(getattr(obj, 'config', None)) if hasattr(
                            obj, 'config') and getattr(obj, 'config') is not None else None,
                        _to_iso(getattr(obj, 'created_at', None)
                                ) or datetime.utcnow().isoformat(),
                        _to_iso(getattr(obj, 'updated_at', None))
                    ))
                    obj.id = cursor.lastrowid

            elif hasattr(obj, 'otp_hash'):
                # OTP object
                if has_id:
                    await self._db.execute("""
                        UPDATE otps 
                        SET email=?, otp_hash=?, consumed=?, expires_at=?, attempts=?, transport=?
                        WHERE id=?
                    """, (
                        getattr(obj, 'email', None),
                        getattr(obj, 'otp_hash', None),
                        bool_to_int(getattr(obj, 'consumed', None), False),
                        _to_iso(getattr(obj, 'expires_at', None)),
                        getattr(obj, 'attempts', 0),
                        getattr(obj, 'transport', None),
                        obj.id
                    ))
                else:
                    cursor = await self._db.execute("""
                        INSERT INTO otps (email, otp_hash, consumed, created_at, expires_at, attempts, transport)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        getattr(obj, 'email', None),
                        getattr(obj, 'otp_hash', None),
                        bool_to_int(getattr(obj, 'consumed', None), False),
                        _to_iso(getattr(obj, 'created_at', None)
                                ) or datetime.utcnow().isoformat(),
                        _to_iso(getattr(obj, 'expires_at', None)),
                        getattr(obj, 'attempts', 0),
                        getattr(obj, 'transport', None)
                    ))
                    obj.id = cursor.lastrowid

            elif hasattr(obj, 'token') and hasattr(obj, 'user_id'):
                # RefreshToken object
                if has_id:
                    await self._db.execute("""
                        UPDATE refresh_tokens 
                        SET user_id=?, token=?, revoked=?, expires_at=?
                        WHERE id=?
                    """, (
                        getattr(obj, 'user_id', None),
                        getattr(obj, 'token', None),
                        bool_to_int(getattr(obj, 'revoked', None), False),
                        _to_iso(getattr(obj, 'expires_at', None)),
                        obj.id
                    ))
                else:
                    cursor = await self._db.execute("""
                        INSERT INTO refresh_tokens (user_id, token, revoked, created_at, expires_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        getattr(obj, 'user_id', None),
                        getattr(obj, 'token', None),
                        bool_to_int(getattr(obj, 'revoked', None), False),
                        _to_iso(getattr(obj, 'created_at', None)
                                ) or datetime.utcnow().isoformat(),
                        _to_iso(getattr(obj, 'expires_at', None))
                    ))
                    obj.id = cursor.lastrowid

            elif hasattr(obj, 'type') and hasattr(obj, 'config') and not hasattr(obj, 'version'):
                # Connector object
                if has_id:
                    await self._db.execute("""
                        UPDATE connectors
                        SET api_id=?, name=?, type=?, config=?, updated_at=?
                        WHERE id=?
                    """, (
                        getattr(obj, 'api_id', None),
                        getattr(obj, 'name', None),
                        getattr(obj, 'type', None),
                        json.dumps(getattr(obj, 'config', None)) if hasattr(
                            obj, 'config') and getattr(obj, 'config') is not None else None,
                        datetime.utcnow().isoformat(),
                        obj.id
                    ))
                else:
                    cursor = await self._db.execute("""
                        INSERT INTO connectors (api_id, name, type, config, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        getattr(obj, 'api_id', None),
                        getattr(obj, 'name', None),
                        getattr(obj, 'type', None),
                        json.dumps(getattr(obj, 'config', None)) if hasattr(
                            obj, 'config') and getattr(obj, 'config') is not None else None,
                        _to_iso(getattr(obj, 'created_at', None)
                                ) or datetime.utcnow().isoformat(),
                        getattr(obj, 'updated_at', None)
                    ))
                    obj.id = cursor.lastrowid

            elif hasattr(obj, 'name') and hasattr(obj, 'value'):
                # Secret object
                if has_id:
                    await self._db.execute("""
                        UPDATE secrets
                        SET name=?, value=?, description=?, tags=?, updated_at=?
                        WHERE id=?
                    """, (
                        getattr(obj, 'name', None),
                        getattr(obj, 'value', None),
                        getattr(obj, 'description', None),
                        getattr(obj, 'tags', None),
                        datetime.utcnow().isoformat(),
                        obj.id
                    ))
                else:
                    cursor = await self._db.execute("""
                        INSERT INTO secrets (name, value, description, tags, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        getattr(obj, 'name', None),
                        getattr(obj, 'value', None),
                        getattr(obj, 'description', None),
                        getattr(obj, 'tags', None),
                        _to_iso(getattr(obj, 'created_at', None)
                                ) or datetime.utcnow().isoformat(),
                        getattr(obj, 'updated_at', None)
                    ))
                    obj.id = cursor.lastrowid

            elif hasattr(obj, 'action') and hasattr(obj, 'status') and hasattr(obj, 'resource_type'):
                # AuditLog object
                if has_id:
                    await self._db.execute("""
                        UPDATE audit_logs
                        SET timestamp=?, user_id=?, action=?, resource_type=?, resource_id=?,
                            ip_address=?, user_agent=?, metadata_json=?, status=?, error_message=?
                        WHERE id=?
                    """, (
                        _to_iso(getattr(obj, 'timestamp', None)
                                ) or datetime.utcnow().isoformat(),
                        getattr(obj, 'user_id', None),
                        getattr(obj, 'action', None),
                        getattr(obj, 'resource_type', None),
                        getattr(obj, 'resource_id', None),
                        getattr(obj, 'ip_address', None),
                        getattr(obj, 'user_agent', None),
                        json.dumps(getattr(obj, 'metadata_json', None)) if getattr(
                            obj, 'metadata_json', None) is not None else None,
                        getattr(obj, 'status', None),
                        getattr(obj, 'error_message', None),
                        obj.id,
                    ))
                else:
                    cursor = await self._db.execute("""
                        INSERT INTO audit_logs (
                            timestamp, user_id, action, resource_type, resource_id,
                            ip_address, user_agent, metadata_json, status, error_message
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        _to_iso(getattr(obj, 'timestamp', None)
                                ) or datetime.utcnow().isoformat(),
                        getattr(obj, 'user_id', None),
                        getattr(obj, 'action', None),
                        getattr(obj, 'resource_type', None),
                        getattr(obj, 'resource_id', None),
                        getattr(obj, 'ip_address', None),
                        getattr(obj, 'user_agent', None),
                        json.dumps(getattr(obj, 'metadata_json', None)) if getattr(
                            obj, 'metadata_json', None) is not None else None,
                        getattr(obj, 'status', None),
                        getattr(obj, 'error_message', None),
                    ))
                    obj.id = cursor.lastrowid

            # Permission object (has resource and action) - check before Role
            elif hasattr(obj, 'resource') and hasattr(obj, 'action') and not hasattr(obj, 'version'):
                # Permission object (has resource and action)
                if has_id:
                    await self._db.execute("""
                        UPDATE permissions 
                        SET name=?, resource=?, action=?, description=?
                        WHERE id=?
                    """, (
                        getattr(obj, 'name', None),
                        getattr(obj, 'resource', None),
                        getattr(obj, 'action', None),
                        getattr(obj, 'description', None),
                        obj.id
                    ))
                else:
                    cursor = await self._db.execute("""
                        INSERT INTO permissions (name, resource, action, description, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        getattr(obj, 'name', None),
                        getattr(obj, 'resource', None),
                        getattr(obj, 'action', None),
                        getattr(obj, 'description', None),
                        _to_iso(getattr(obj, 'created_at', None)
                                ) or datetime.utcnow().isoformat()
                    ))
                    obj.id = cursor.lastrowid

            elif hasattr(obj, 'name') and hasattr(obj, 'description') and not hasattr(obj, 'version'):
                # Role object (has name and description, but no version like API)
                if has_id:
                    await self._db.execute("""
                        UPDATE roles 
                        SET name=?, description=?, permissions=?
                        WHERE id=?
                    """, (
                        getattr(obj, 'name', None),
                        getattr(obj, 'description', None),
                        json.dumps(getattr(obj, 'permissions', [])) if hasattr(
                            obj, 'permissions') else None,
                        obj.id
                    ))
                else:
                    cursor = await self._db.execute("""
                        INSERT INTO roles (name, description, permissions, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (
                        getattr(obj, 'name', None),
                        getattr(obj, 'description', None),
                        json.dumps(getattr(obj, 'permissions', [])) if hasattr(
                            obj, 'permissions') else None,
                        _to_iso(getattr(obj, 'created_at', None)
                                ) or datetime.utcnow().isoformat()
                    ))
                    obj.id = cursor.lastrowid

            elif hasattr(obj, 'user_id') and hasattr(obj, 'role_id'):
                # UserRole object
                if has_id:
                    await self._db.execute("""
                        UPDATE user_roles 
                        SET user_id=?, role_id=?
                        WHERE id=?
                    """, (
                        getattr(obj, 'user_id', None),
                        getattr(obj, 'role_id', None),
                        obj.id
                    ))
                else:
                    cursor = await self._db.execute("""
                        INSERT INTO user_roles (user_id, role_id, assigned_at)
                        VALUES (?, ?, ?)
                    """, (
                        getattr(obj, 'user_id', None),
                        getattr(obj, 'role_id', None),
                        _to_iso(getattr(obj, 'assigned_at', None)
                                ) or datetime.utcnow().isoformat()
                    ))
                    obj.id = cursor.lastrowid
            elif hasattr(obj, 'key') and hasattr(obj, 'scopes') and hasattr(obj, 'revoked'):
                # APIKey object
                if has_id:
                    await self._db.execute("""
                        UPDATE api_keys 
                        SET key=?, label=?, scopes=?, revoked=?, environment_id=?,
                            created_at=?, expires_at=?, last_used_at=?, usage_count=?, metadata=?
                        WHERE id=?
                    """, (
                        getattr(obj, 'key', None),
                        getattr(obj, 'label', None),
                        getattr(obj, 'scopes', None),
                        1 if getattr(obj, 'revoked', False) else 0,
                        getattr(obj, 'environment_id', None),
                        getattr(obj, 'created_at', datetime.utcnow()).isoformat() if getattr(
                            obj, 'created_at', None) else datetime.utcnow().isoformat(),
                        getattr(obj, 'expires_at', None).isoformat() if getattr(
                            obj, 'expires_at', None) else None,
                        getattr(obj, 'last_used_at', None).isoformat() if getattr(
                            obj, 'last_used_at', None) else None,
                        getattr(obj, 'usage_count', 0),
                        json.dumps(getattr(obj, 'metadata_json', None)) if getattr(
                            obj, 'metadata_json', None) else None,
                        obj.id
                    ))
                else:
                    cursor = await self._db.execute("""
                        INSERT INTO api_keys (key, label, scopes, revoked, environment_id,
                            created_at, expires_at, last_used_at, usage_count, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        getattr(obj, 'key', None),
                        getattr(obj, 'label', None),
                        getattr(obj, 'scopes', None),
                        1 if getattr(obj, 'revoked', False) else 0,
                        getattr(obj, 'environment_id', None),
                        getattr(obj, 'created_at', datetime.utcnow()).isoformat() if getattr(
                            obj, 'created_at', None) else datetime.utcnow().isoformat(),
                        getattr(obj, 'expires_at', None).isoformat() if getattr(
                            obj, 'expires_at', None) else None,
                        getattr(obj, 'last_used_at', None).isoformat() if getattr(
                            obj, 'last_used_at', None) else None,
                        getattr(obj, 'usage_count', 0),
                        json.dumps(getattr(obj, 'metadata_json', None)) if getattr(
                            obj, 'metadata_json', None) else None,
                    ))
                    obj.id = cursor.lastrowid
            elif hasattr(obj, 'slug') and hasattr(obj, 'name') and not hasattr(obj, 'version'):
                # Environment object
                if has_id:
                    await self._db.execute("""
                        UPDATE environments
                        SET name=?, slug=?, description=?, updated_at=?
                        WHERE id=?
                    """, (
                        getattr(obj, 'name', None),
                        getattr(obj, 'slug', None),
                        getattr(obj, 'description', None),
                        datetime.utcnow().isoformat(),
                        obj.id
                    ))
                else:
                    cursor = await self._db.execute("""
                        INSERT INTO environments (name, slug, description, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (
                        getattr(obj, 'name', None),
                        getattr(obj, 'slug', None),
                        getattr(obj, 'description', None),
                        getattr(obj, 'created_at', datetime.utcnow()).isoformat() if getattr(
                            obj, 'created_at', None) else datetime.utcnow().isoformat(),
                    ))
                    obj.id = cursor.lastrowid
            else:
                logger.warning(
                    f"Unknown object type, cannot insert/update: {type(obj)}")
                return

            action = "Updated" if has_id else "Inserted"
            logger.debug(
                f"{action} object in SQLite (id={getattr(obj, 'id', None)})")

        except Exception as e:
            logger.error(
                f"Failed to insert/update object in SQLite: {e}", exc_info=True)
            raise

    async def delete(self, obj: SimpleNamespace) -> None:
        """
        Delete an object from SQLite.

        Args:
            obj: Object to delete
        """
        if not hasattr(obj, 'id') or not self._db:
            return

        # Determine table based on object attributes
        if hasattr(obj, 'name') and hasattr(obj, 'version'):
            await self.delete_api(obj)
        elif hasattr(obj, 'hashed_password'):
            await self._db.execute("DELETE FROM users WHERE id = ?", (obj.id,))
        elif hasattr(obj, 'token'):
            await self._db.execute("DELETE FROM refresh_tokens WHERE id = ?", (obj.id,))
        elif hasattr(obj, 'otp_hash'):
            await self._db.execute("DELETE FROM otps WHERE id = ?", (obj.id,))
        elif hasattr(obj, 'key') and hasattr(obj, 'scopes') and hasattr(obj, 'revoked'):
            await self._db.execute("DELETE FROM api_keys WHERE id = ?", (obj.id,))
        elif hasattr(obj, 'slug') and hasattr(obj, 'name') and not hasattr(obj, 'version'):
            await self._db.execute("DELETE FROM environments WHERE id = ?", (obj.id,))
        elif hasattr(obj, 'value') and hasattr(obj, 'name') and not hasattr(obj, 'version'):
            await self._db.execute("DELETE FROM secrets WHERE id = ?", (obj.id,))
        elif hasattr(obj, 'config') and hasattr(obj, 'type') and hasattr(obj, 'api_id'):
            await self._db.execute("DELETE FROM connectors WHERE id = ?", (obj.id,))
        elif hasattr(obj, 'user_id') and hasattr(obj, 'role_id'):
            await self._db.execute("DELETE FROM user_roles WHERE id = ?", (obj.id,))
        elif hasattr(obj, 'resource') and hasattr(obj, 'action'):
            await self._db.execute("DELETE FROM permissions WHERE id = ?", (obj.id,))
        elif hasattr(obj, 'name') and hasattr(obj, 'permissions'):
            await self._db.execute("DELETE FROM roles WHERE id = ?", (obj.id,))
        elif hasattr(obj, 'action') and hasattr(obj, 'status') and hasattr(obj, 'resource_type'):
            await self._db.execute("DELETE FROM audit_logs WHERE id = ?", (obj.id,))

        await self._db.commit()

    async def execute(self, statement):
        """
        Execute a SQLAlchemy statement (SELECT or UPDATE) on SQLite data.

        Args:
            statement: SQLAlchemy select or update statement

        Returns:
            QueryResult: Object with scalars() method for result access
        """
        if not self._db:
            await self.connect()

        from app.db.models import User, OTP, RefreshToken, Role, Permission, UserRole, API, APIKey, Environment, Secret, Connector, AuditLog

        table_map = {
            User: 'users',
            OTP: 'otps',
            RefreshToken: 'refresh_tokens',
            Role: 'roles',
            Permission: 'permissions',
            UserRole: 'user_roles',
            API: 'apis',
            APIKey: 'api_keys',
            Environment: 'environments',
            Secret: 'secrets',
            Connector: 'connectors',
            AuditLog: 'audit_logs',
        }

        # Handle UPDATE statements
        if hasattr(statement, 'entity_description') and not hasattr(statement, 'column_descriptions'):
            try:
                entity_type = statement.entity_description.get('entity', None)
                table_name = table_map.get(entity_type)
                if not table_name:
                    return QueryResult([], rowcount=0)

                # Build SET clause from values
                set_parts = []
                params = []
                if hasattr(statement, '_values') and statement._values:
                    for col_clause, bind_param in statement._values.items():
                        col_name = col_clause.key if hasattr(
                            col_clause, 'key') else str(col_clause)
                        val = bind_param.value if hasattr(
                            bind_param, 'value') else bind_param
                        if isinstance(val, bool):
                            params.append(1 if val else 0)
                        else:
                            params.append(val)
                        set_parts.append(f"{col_name} = ?")

                if not set_parts:
                    return QueryResult([], rowcount=0)

                query = f"UPDATE {table_name} SET {', '.join(set_parts)}"

                # Apply WHERE clause
                if hasattr(statement, '_where_criteria') and statement._where_criteria:
                    where_parts = []
                    for criterion in statement._where_criteria:
                        try:
                            if hasattr(criterion, 'left') and hasattr(criterion, 'right'):
                                left_val = criterion.left.key if hasattr(
                                    criterion.left, 'key') else str(criterion.left)
                                right_val = criterion.right.value if hasattr(
                                    criterion.right, 'value') else criterion.right
                                where_parts.append(f"{left_val} = ?")
                                params.append(right_val)
                        except Exception as ex:
                            logger.debug(
                                f"Error evaluating UPDATE criterion: {ex}")

                    if where_parts:
                        query += " WHERE " + " AND ".join(where_parts)

                cursor = await self._db.execute(query, params)
                await self._db.commit()
                return QueryResult([], rowcount=cursor.rowcount)

            except Exception as e:
                logger.warning(f"UPDATE execution error: {e}", exc_info=True)
                return QueryResult([], rowcount=0)

        # Handle SELECT statements
        if hasattr(statement, '_propagate_attrs') and hasattr(statement, 'column_descriptions'):
            try:
                entities = statement.column_descriptions
                if entities:
                    entity_type = entities[0].get(
                        'entity', entities[0].get('type'))

                    table_name = table_map.get(entity_type)
                    if not table_name:
                        return QueryResult([])

                    # Build basic query
                    query = f"SELECT * FROM {table_name}"
                    params = []

                    # Apply where clause filtering
                    if hasattr(statement, '_where_criteria') and statement._where_criteria:
                        where_parts = []
                        for criterion in statement._where_criteria:
                            try:
                                # Handle NOT operator
                                if hasattr(criterion, '__class__') and 'UnaryExpression' in criterion.__class__.__name__:
                                    if hasattr(criterion, 'element') and hasattr(criterion.element, 'key'):
                                        attr_name = criterion.element.key
                                        where_parts.append(f"{attr_name} = 0")
                                # Handle regular comparison
                                elif hasattr(criterion, 'left') and hasattr(criterion, 'right'):
                                    left_val = criterion.left.key if hasattr(
                                        criterion.left, 'key') else str(criterion.left)
                                    right_val = criterion.right.value if hasattr(
                                        criterion.right, 'value') else criterion.right
                                    where_parts.append(f"{left_val} = ?")
                                    params.append(right_val)
                            except Exception as ex:
                                logger.debug(
                                    f"Error evaluating criterion: {ex}")

                        if where_parts:
                            query += " WHERE " + " AND ".join(where_parts)

                    # Execute query
                    cursor = await self._db.execute(query, params)
                    rows = await cursor.fetchall()
                    results = [self._row_to_namespace(row) for row in rows]

                    return QueryResult(results)

            except Exception as e:
                logger.warning(f"Query execution error: {e}", exc_info=True)
                return QueryResult([])

        return QueryResult([])

    # Utility Methods

    async def clear_all(self) -> None:
        """Clear all data from the SQLite database."""
        if not self._db:
            await self.connect()

        tables = ['apis', 'users', 'refresh_tokens',
                  'otps', 'roles', 'permissions', 'user_roles',
                  'connectors', 'secrets', 'api_keys', 'audit_logs', 'metrics']
        for table in tables:
            await self._db.execute(f"DELETE FROM {table}")

        await self._db.commit()
        logger.info("SQLite database cleared")

    async def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about the SQLite database.

        Returns:
            dict: Dictionary with counts of stored objects
        """
        if not self._db:
            await self.connect()

        stats = {}
        tables = {
            'apis': 'apis',
            'users': 'users',
            'refresh_tokens': 'refresh_tokens',
            'otps': 'otps',
            'roles': 'roles',
            'permissions': 'permissions',
            'user_roles': 'user_roles',
            'connectors': 'connectors',
            'secrets': 'secrets',
            'api_keys': 'api_keys',
            'audit_logs': 'audit_logs',
            'metrics': 'metrics',
        }

        for key, table in tables.items():
            cursor = await self._db.execute(f"SELECT COUNT(*) FROM {table}")
            row = await cursor.fetchone()
            stats[key] = row[0] if row else 0

        return stats

    def _parse_dt(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            return None

    async def list_audit_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[SimpleNamespace]:
        if not self._db:
            await self.connect()

        where_parts = []
        params: List[Any] = []

        if user_id is not None:
            where_parts.append("user_id = ?")
            params.append(user_id)
        if action and action.strip():
            where_parts.append("LOWER(action) = ?")
            params.append(action.strip().lower())
        if status and status.strip():
            where_parts.append("LOWER(status) = ?")
            params.append(status.strip().lower())
        if start_date and start_date.strip():
            where_parts.append("timestamp >= ?")
            params.append(start_date.strip())
        if end_date and end_date.strip():
            where_parts.append("timestamp <= ?")
            params.append(end_date.strip())

        query = "SELECT * FROM audit_logs"
        if where_parts:
            query += " WHERE " + " AND ".join(where_parts)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = await self._db.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_namespace(r) for r in rows]

    async def get_audit_log_statistics(self) -> Dict[str, Any]:
        if not self._db:
            await self.connect()

        cursor = await self._db.execute("SELECT COUNT(*) FROM audit_logs")
        total_row = await cursor.fetchone()
        audit_count = total_row[0] if total_row else 0

        cursor = await self._db.execute("SELECT COUNT(*) FROM metrics")
        metric_row = await cursor.fetchone()
        metrics_count = metric_row[0] if metric_row else 0

        cursor = await self._db.execute(
            "SELECT action, COUNT(id) AS c FROM audit_logs GROUP BY action"
        )
        logs_by_type = {row[0]: row[1] for row in await cursor.fetchall() if row[0]}

        cursor = await self._db.execute(
            "SELECT user_id, COUNT(id) AS c FROM audit_logs WHERE user_id IS NOT NULL GROUP BY user_id"
        )
        logs_by_user = {row[0]: row[1] for row in await cursor.fetchall()}

        cursor = await self._db.execute("SELECT MIN(timestamp) FROM audit_logs")
        oldest_audit_row = await cursor.fetchone()
        oldest_audit = oldest_audit_row[0] if oldest_audit_row else None

        cursor = await self._db.execute("SELECT MIN(timestamp) FROM metrics")
        oldest_metric_row = await cursor.fetchone()
        oldest_metric = oldest_metric_row[0] if oldest_metric_row else None

        return {
            "total_logs": audit_count,
            "audit_logs_count": audit_count,
            "metrics_count": metrics_count,
            "logs_by_type": logs_by_type,
            "logs_by_user": logs_by_user,
            "oldest_audit_log": oldest_audit,
            "oldest_metric": oldest_metric,
        }

    async def list_user_audit_activity(self, target_user_id: int, days: int = 30, limit: int = 500) -> List[SimpleNamespace]:
        if not self._db:
            await self.connect()

        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cursor = await self._db.execute(
            """
            SELECT * FROM audit_logs
            WHERE user_id = ? AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (target_user_id, since, limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_namespace(r) for r in rows]

    async def list_failed_audit_attempts(self, hours: int = 24, limit: int = 500) -> List[SimpleNamespace]:
        if not self._db:
            await self.connect()

        since = (datetime.now(timezone.utc) -
                 timedelta(hours=hours)).isoformat()
        cursor = await self._db.execute(
            """
            SELECT * FROM audit_logs
            WHERE timestamp >= ? AND (
                LOWER(COALESCE(status, '')) IN ('failure', 'error')
                OR LOWER(COALESCE(action, '')) LIKE '%failure%'
            )
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (since, limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_namespace(r) for r in rows]

    async def cleanup_old_logs(self, retention_days: int = 30) -> int:
        if not self._db:
            await self.connect()

        cutoff = (datetime.now(timezone.utc) -
                  timedelta(days=retention_days)).isoformat()

        cursor = await self._db.execute(
            "SELECT COUNT(*) FROM audit_logs WHERE timestamp < ?",
            (cutoff,),
        )
        row = await cursor.fetchone()
        audit_count = row[0] if row else 0

        await self._db.execute("DELETE FROM audit_logs WHERE timestamp < ?", (cutoff,))
        await self._db.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff,))
        await self._db.commit()

        return audit_count

    def __repr__(self) -> str:
        """String representation of the SQLite database."""
        return f"SQLiteDB(path={self.db_path}, initialized={self._initialized})"

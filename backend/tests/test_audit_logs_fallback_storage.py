from pathlib import Path

import pytest

from app.db.inmemory import InMemoryDB
from app.db.sqlite_db import SQLiteDB
from app.logging.audit import AuditLogger


@pytest.mark.asyncio
async def test_inmemory_audit_log_storage_and_query():
    db = InMemoryDB()
    logger = AuditLogger(db)

    await logger.log_event(
        action="LOGIN_FAILURE",
        status="failure",
        user_id=None,
        metadata={"source": "inmemory"},
    )

    rows = await db.list_audit_logs(limit=10)
    stats = await db.get_audit_log_statistics()

    assert len(rows) == 1
    assert rows[0].action == "LOGIN_FAILURE"
    assert rows[0].status == "failure"
    assert stats["total_logs"] == 1


@pytest.mark.asyncio
async def test_sqlite_audit_log_storage_and_query(tmp_path: Path):
    db_path = tmp_path / "audit_logs_test.db"
    db = SQLiteDB(str(db_path))
    await db.connect()

    try:
        logger = AuditLogger(db)
        await logger.log_event(
            action="KEY_REVOKE",
            status="success",
            user_id=None,
            metadata={"source": "sqlite"},
        )
        await db.commit()

        rows = await db.list_audit_logs(limit=10)
        stats = await db.get_audit_log_statistics()

        assert len(rows) == 1
        assert rows[0].action == "KEY_REVOKE"
        assert rows[0].status == "success"
        assert stats["total_logs"] == 1
    finally:
        await db.disconnect()

import asyncio
from app.db.sqlite_db import SQLiteDB
from app.db.inmemory import InMemoryDB
from app.logging.audit import AuditLogger


async def main():
    sqlite_db = SQLiteDB('test_audit_storage.db')
    await sqlite_db.connect()
    sqlite_logger = AuditLogger(sqlite_db)
    await sqlite_logger.log_event(action='LOGIN_SUCCESS', status='success', user_id=1, metadata={'source': 'sqlite'})
    await sqlite_db.commit()
    sqlite_rows = await sqlite_db.list_audit_logs(limit=10)
    sqlite_stats = await sqlite_db.get_audit_log_statistics()
    print('sqlite_rows', len(sqlite_rows))
    print('sqlite_total', sqlite_stats.get('total_logs'))
    await sqlite_db.disconnect()

    memory_db = InMemoryDB()
    memory_logger = AuditLogger(memory_db)
    await memory_logger.log_event(action='LOGIN_FAILURE', status='failure', user_id=2, metadata={'source': 'memory'})
    memory_rows = await memory_db.list_audit_logs(limit=10)
    memory_stats = await memory_db.get_audit_log_statistics()
    print('memory_rows', len(memory_rows))
    print('memory_total', memory_stats.get('total_logs'))


asyncio.run(main())
